import itertools
from pathlib import Path
from subprocess import PIPE, Popen

import pytest

from messageformat2.errors import (
    DuplicateDeclaration,
    DuplicateOptionName,
    MissingFallbackVariant,
    MissingSelectorAnnotation,
    ParseError,
    VariantKeyMismatch,
)
from messageformat2.parser import parse


def ruff_format(source):
    p = Popen(["ruff", "format", "-"], shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE)  # noqa: S603, S607
    output, err = p.communicate(source.encode("utf-8"))
    assert not err
    return output


@pytest.mark.parametrize(
    "message",
    [
        "",
        "Hello, World!",
        "{$name}",
        "Hello, {$name}!",
        "{$first}{$last}",
        "Hello, {:namespace:function @attr}!",
        "Hello, {$name :capitalize arg=yes opt=$variable}!",
        "Hello, {$name :capitalize @attr1 @attr2}!",
        "Hello, {$name @attr1=$variable @attr2=yes}!",
        "Hello, {1.23 :round}!",
        "Hello, {John :capitalize @attr}!",
        "Hello, {|quoted| :capitalize}!",
        "Hello, {|escaped \\| \\\\ literal|}!",
        "Hello, {#strong}John{/strong}!",
        "Hello, {#strong opt=42 @attr}John{/strong}!",
        "Hello, {#strong text=|John| /}!",
    ],
    ids=itertools.count(1),
)
def test_parse_simple_message(request, snapshot, message):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    idx = request.node.callspec.id

    ast = parse(message)
    formatted = ruff_format(repr(ast))
    snapshot.assert_match(formatted, f"simple_message_{idx}.txt")


@pytest.mark.parametrize(
    "message",
    [
        r"\\ backslash escape \\",
        r"\{ brace escape \}",
    ],
    ids=itertools.count(1),
)
def test_parse_simple_message_escapes(request, snapshot, message):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    idx = request.node.callspec.id

    ast = parse(message)
    formatted = ruff_format(repr(ast))
    snapshot.assert_match(formatted, f"simple_message_escapes_{idx}.txt")


@pytest.mark.parametrize(
    "message",
    [
        "{!reserved}",
        "{!reserved opt=42}",
        "{^private}",
        "{^private |pipe escape: \\| |}",
        "{^private |backslash escape: \\\\ |}",
    ],
    ids=itertools.count(1),
)
def test_unsupported_annotations(request, snapshot, message):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    idx = request.node.callspec.id

    ast = parse(message)
    formatted = ruff_format(repr(ast))
    snapshot.assert_match(formatted, f"unsupported_annotations_{idx}.txt")


@pytest.mark.parametrize(
    "message",
    [
        """\
.input {$date :datetime weekday=long month=medium day=short}
.local $numPigs = {$pigs :integer}
{{On {$date} you had this many pigs: {$numPigs}}}""",
        """\
.match {$count :integer}
0   {{You have no notifications.}}
one {{You have {$count} notification.}}
*   {{You have {$count} notifications.}}""",
        """\
.match {$a :integer} {$b :integer}
* * {{a = {$a}, b = {$b}}}""",
    ],
    ids=itertools.count(1),
)
def test_parse_complex_message(request, snapshot, message):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    idx = request.node.callspec.id

    ast = parse(message)
    formatted = ruff_format(repr(ast))
    snapshot.assert_match(formatted, f"complex_message_{idx}.txt")


@pytest.mark.parametrize(
    "message",
    [
        """\
.unknown {$x}
.match {$count :integer}
* {{Reserved statement}}""",
        """\
.unknown reserved-body |literal| {$x ^private @attr}
.match {$count :integer}
* {{Reserved statement}}""",
    ],
    ids=itertools.count(1),
)
def test_parse_unsupported_statement(request, snapshot, message):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    idx = request.node.callspec.id

    ast = parse(message)
    formatted = ruff_format(repr(ast))
    snapshot.assert_match(formatted, f"unsupported_statement_{idx}.txt")


@pytest.mark.parametrize(
    ("message", "error"),
    [
        (
            """\
.match {$count :integer}
0 1 {{You have no notifications.}}""",
            VariantKeyMismatch,
        ),
        (
            """\
.match {$count :integer}
0 {{You have no notifications.}}""",
            MissingFallbackVariant,
        ),
        (
            "{$count :integer opt=1 opt=2}",
            DuplicateOptionName,
        ),
        (
            "{#strong opt=1 opt=2}Click here!{/strong}",
            DuplicateOptionName,
        ),
        (
            ".local $var = {$var}{{Cannot refer to itself}}",
            DuplicateDeclaration,
        ),
        (
            """\
.input {$var :number}
.input {$var :number}
{{Redeclaration of the same variable}}""",
            DuplicateDeclaration,
        ),
        (
            """\
.local $n = {42 :fn opt=$count}
.input {$count :number}
{{Redeclaration of an implicit variable}}""",
            DuplicateDeclaration,
        ),
        (
            """\
.local $n = {42 :fn opt=$x}
.local $x = {$count :number}
{{Redeclaration of an implicit variable}}""",
            DuplicateDeclaration,
        ),
        (
            """\
.match {$count}
* {{You have no notifications.}}""",
            MissingSelectorAnnotation,
        ),
        (
            """\
.input {$count}
.local $n = {$count}
.match {$n}
* {{You have no notifications.}}""",
            MissingSelectorAnnotation,
        ),
    ],
)
def test_data_model_errors(message, error):
    with pytest.raises(error):
        parse(message)


@pytest.mark.parametrize(
    "message",
    [
        "}",
        " }}",
        "{$42var}",
        "{{Missing end braces",
        "{{Missing one end brace}",
        "Unknown {{expression}}",
        ".local $var = {|no message body|}",
        ".local $var = invalid",
        ".match {$count} {{Missing variants}}",
        ".match {$count} *",
        ".match {{$count}}",
        "{:func @}",
        "{:func :func}",
        "{:func @2}",
        "{:func @attr=}",
        "{:func @attr opt=2}",
    ],
)
def test_parse_errors(message):
    with pytest.raises(ParseError):
        parse(message)

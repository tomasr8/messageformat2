import itertools
from pathlib import Path
from subprocess import PIPE, Popen

import pytest

from messageformat2.datamodel import (
    Literal,
    LiteralExpression,
    LocalDeclaration,
    PatternMessage,
    VariableExpression,
    VariableRef,
)
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
    p = Popen(["ruff", "format", "-"], shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE)  # noqa: S607
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
        "Hello, {$name @attr1=|quoted| @attr2=yes}!",
        "Hello, {1.23 :round}!",
        "Hello, {John :capitalize @attr}!",
        "Hello, {|quoted| :capitalize}!",
        "Hello, {|escaped \\| \\\\ literal|}!",
        "Hello, {#strong}John{/strong}!",
        "Hello, {#strong opt=42 @attr}John{/strong}!",
        "Hello, {#strong text=|John| /}!",
        "Hello, {|braces \\{ \\} are escapable too|}!",
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
        r"\| pipe escape \|",
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
        """\
.input {$date :datetime weekday=long month=medium day=short}
.local $numPigs = {$pigs :integer}
{{On {$date} you had this many pigs: {$numPigs}}}""",
        """\
.input {$count :integer}
.match $count
0   {{You have no notifications.}}
one {{You have {$count} notification.}}
*   {{You have {$count} notifications.}}""",
        """\
.input {$a :integer}
.local $b = {$a :integer}
.match $a $b
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
    ("message", "error"),
    [
        (
            """\
.input {$count :integer}
.match $count
0 1 {{You have no notifications.}}""",
            VariantKeyMismatch,
        ),
        (
            """\
.input {$count :integer}
.match $count
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
.match $count
* {{You have no notifications.}}""",
            MissingSelectorAnnotation,
        ),
        (
            """\
.input {$count}
.match $count
* {{You have no notifications.}}""",
            MissingSelectorAnnotation,
        ),
        (
            """\
.local $count = {|42|}
.match $count
* {{You have no notifications.}}""",
            MissingSelectorAnnotation,
        ),
        (
            """\
.input {$count}
.local $n = {$count}
.match $n
* {{You have no notifications.}}""",
            MissingSelectorAnnotation,
        ),
        (
            """\
.local $n = {$count}
.match $n
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
        ".input {$count :integer} .match $count {{Missing variants}}",
        ".input {$count :integer} .match $count *",
        ".input {$count :integer} .match $count * {{foo}} extra",
        ".match {{$count}}",
        # selectors must be variables
        ".match {$count :integer} * {{foo}}",
        ".input {$count :integer} .match {$count} * {{foo}}",
        ".match * {{foo}}",
        ".match x * {{foo}}",
        ".match :x * {{foo}}",
        # required whitespace between selectors and keys
        ".input {$x :x} .match$x * {{foo}}",
        ".input {$x :x} .match $x* {{foo}}",
        ".input {$x :x} .match $x|x| {{foo}} * {{foo}}",
        ".input {$x :x} .local $y = {y :y} .match $x$y * * {{foo}}",
        ".input {$x :x} .local $y = {y :y} .match $x $y ** {{foo}}",
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


@pytest.mark.parametrize("ws", [" ", "\t", "\r", "\n", "\u3000"])
def test_whitespace(ws):
    ast = parse(f"{{{ws}foo{ws}}}")
    assert isinstance(ast, PatternMessage)
    assert ast.pattern == [LiteralExpression(arg=Literal(value="foo"), annotation=None, attributes=[])]


@pytest.mark.parametrize("ws", ["\u00a0", "\u000b", "\u000c", "\u2028"])
def test_invalid_whitespace(ws):
    with pytest.raises(ParseError):
        parse(f"{{{ws}foo{ws}}}")


@pytest.mark.parametrize(
    "message",
    [
        "\u200e .local $x = {1} {{ {$x}}}",
        ".local $x = {1} \u200f {{ {$x}}}",
        ".local $x = {1} {{ {$x}}} \u2066",
        ".local \u2067 $x = {1} {{ {$x}}}",
        ".local\u2067 $x = {1} {{ {$x}}}",
        ".local $x \u2068 = \u2069 {1} {{ {$x}}}",
        ".local $x = {\u200e 1 \u200f} {{ {$x}}}",
        ".local $x = {1 \u200e :string \u200f} {{ {$x}}}",
        ".local $x = {1 :string opt\u200f=\u200e1 @attr\u200f=\u200e1 } {{ {$x}}}",
        ".local $\u061cx = {1} {{ {$\u061cx}}}",
        ".local $\u200ex\u200f = {1} {{ {$x}}}",
        ".local $x = {1} {{ {$\u200ex\u200f}}}",
    ],
)
def test_bidi_marks_are_allowed_in_whitespace_and_around_names(message):
    ast = parse(message)
    assert isinstance(ast, PatternMessage)
    assert len(ast.declarations) == 1
    assert isinstance(ast.declarations[0], LocalDeclaration)
    assert ast.declarations[0].name == "x"
    assert ast.pattern == [" ", VariableExpression(arg=VariableRef(name="x"), annotation=None, attributes=[])]


@pytest.mark.parametrize(
    "message",
    [
        ".local $foo\u061cbar = {2} {{ }}",
        ".local $foo\u200ebar = {5} {{{$foo\u200ebar}}}",
        ".local $x = {1 :string} .match $x\u061c1 {{one}} * {{other}}",
    ],
)
def test_bidi_marks_are_not_allowed_inside_names(message):
    with pytest.raises(ParseError):
        parse(message)


@pytest.mark.parametrize(
    "message",
    [
        # reserved and private-use annotations were removed from the syntax
        "{!reserved}",
        "{^private}",
        "{$x !reserved}",
        "{|literal| ~reserved opt=1}",
        "hello {&private @attr}",
        "{%}",
        "{*}",
        "{<tag}",
        # reserved statements were removed from the syntax
        ".unknown {$x} {{Reserved statement}}",
        ".unknown reserved-body |literal| {$x} .input {$x :string} .match $x * {{}}",
        ".i {1} {{}}",
        ".l $y = {|bar|} {{}}",
        # attribute values can only be literals
        "{$x @attr=$var}",
        "{:f @attr=$var}",
        "{#tag @attr=$var}",
    ],
)
def test_removed_syntax_is_a_syntax_error(message):
    with pytest.raises(ParseError):
        parse(message)

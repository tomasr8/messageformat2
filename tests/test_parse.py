import itertools
from pathlib import Path
from subprocess import PIPE, Popen

import pytest

from messageformat2 import parse_message


# def test_queue_pop():
#     queue =


def ruff_format(source):
    p = Popen(["ruff", "format", "-"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
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

    ast = parse_message(message)
    formatted = ruff_format(repr(ast))
    snapshot.assert_match(formatted, f"simple_message_{idx}.txt")


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
.match {$a} {$b}
* * {{a = {$a}, b = {$b}}}""",
    ],
    ids=itertools.count(1),
)
def test_parse_complex_message(request, snapshot, message):
    snapshot.snapshot_dir = Path(__file__).parent / "data"
    idx = request.node.callspec.id

    ast = parse_message(message)
    formatted = ruff_format(repr(ast))
    snapshot.assert_match(formatted, f"complex_message_{idx}.txt")


@pytest.mark.parametrize(
    "message",
    [
        "}",
        "{$42var}",
    ],
)
def test_parse_errors(message):
    with pytest.raises(ValueError) as exc_info:
        parse_message(message)

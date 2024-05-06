import itertools

import pytest

from messageformat2.format import MessageContext, format_message
from messageformat2.parse import parse_message


def date(value: str | None = None, **kwargs) -> str:
    return "2024-06-07"


def append(value: str, text="", **kwargs) -> str:
    return value + text


def capitalize(value: str, start="yes", end="no", middle="no", **kwargs) -> str:
    if start == "yes":
        value = value[0].upper() + value[1:]
    if end == "yes":
        value = value[:-1] + value[-1].upper()
    if middle == "yes":
        value = value[0] + value[1:-1].upper() + value[-1]
    return value


def integer_selector(value: str, keys: list[str], **kwargs):
    return ("1", "one")


@pytest.mark.parametrize(
    ("message", "input_mapping", "formatted"),
    [
        ("", None, ""),
        ("Hello, World!", None, "Hello, World!"),
        ("Hello, {|World|}!", None, "Hello, World!"),
        ("Hello, {$name}!", {"name": "Alice"}, "Hello, Alice!"),
    ],
    ids=itertools.count(1),
)
def test_parse_simple_message(message, input_mapping, formatted):
    ast = parse_message(message)
    assert format_message(ast, {}, input_mapping) == formatted


@pytest.mark.parametrize(
    ("message", "input_mapping", "formatted"),
    [
        (
            """\
.local $n = {2}
{{n = {$n}}}""",
            None,
            "n = 2",
        ),
        (
            """\
.local $y = {$x}
{{x = {$x}, y = {$y}}}""",
            {"x": 42},
            "x = 42, y = 42",
        ),
        (
            """\
.input {$x}
.local $y = {$x}
{{x = {$x}, y = {$y}}}""",
            {"x": 42},
            "x = 42, y = 42",
        ),
    ],
    ids=itertools.count(1),
)
def test_declarations(message, input_mapping, formatted):
    ast = parse_message(message)
    assert format_message(ast, {}, input_mapping) == formatted


@pytest.mark.parametrize(
    ("message", "input_mapping", "formatted"),
    [
        ("{|john| :capitalize}", None, "John"),
        ("{|john| :capitalize end=yes}", None, "JohN"),
        ("{|john| :capitalize start=no middle=yes}", None, "jOHn"),
        (
            """\
.input {$name :capitalize}
.local $weirdName = {$name :capitalize middle=yes}
.local $weirderName = {$weirdName :capitalize start=no}
{{name = {$name}, weirdName={$weirdName} weirderName={$weirderName}}}""",
            {"name": "john"},
            "name = John, weirdName=JOHn weirderName=jOHn",
        ),
        ("{:date}", None, "2024-06-07"),
        (
            """\
.local $date = {:date}
{{The date is: {$date}}}""",
            None,
            "The date is: 2024-06-07",
        ),
    ],
    ids=itertools.count(1),
)
def test_annotations(message, input_mapping, formatted):
    ast = parse_message(message)

    assert format_message(ast, {"date": date, "capitalize": capitalize}, input_mapping) == formatted


@pytest.mark.parametrize(
    ("message", "input_mapping", "formatted"),
    [
        (
            """\
.local $name = {|john| :capitalize}
{{{|Hello, | :append text=$name}!}}""",
            None,
            "Hello, John!",
        ),
    ],
    ids=itertools.count(1),
)
def test_variable_options(message, input_mapping, formatted):
    ast = parse_message(message)

    def append(value: str, text="", **kwargs) -> str:
        return value + text

    assert format_message(ast, {"capitalize": capitalize, "append": append}, input_mapping) == formatted


@pytest.mark.parametrize(
    ("message", "input_mapping", "formatted"),
    [
        ('{#strong opt=|"abc"|}Click here!{/strong}', None, '<strong opt="abc">Click here!</strong>'),
        ('Hello, {#strong text=|"John"| /}!', None, 'Hello, <strong text="John"/>!'),
    ],
    ids=itertools.count(1),
)
def test_markup(message, input_mapping, formatted):
    ast = parse_message(message)
    assert format_message(ast, {}, input_mapping) == formatted


@pytest.mark.parametrize(
    ("message", "input_mapping", "formatted"),
    [
        (
            """\
.match {$count :integer_selector}
one {{You have {$count} notification.}}
1 {{You have one notification.}}
* {{You have {$count} notifications.}}""",
            {"count": 1},
            "You have one notification.",
        ),
    ],
    ids=itertools.count(1),
)
def test_selectors(message, input_mapping, formatted):
    ast = parse_message(message)
    # print(repr(ast))
    print("VARS", len(ast.variants))
    assert format_message(ast, {"integer_selector": integer_selector}, input_mapping) == formatted

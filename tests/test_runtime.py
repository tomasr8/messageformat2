from typing import Any

import pytest
from babel import Locale

from messageformat2 import Message
from messageformat2.errors import OperandMismatch, UnknownFunction, UnsupportedExpression, UnsupportedStatement


def date(value, locale, options) -> str:  # noqa: ARG001
    return "2024-06-07"


def append(value: str, locale, options) -> str:  # noqa: ARG001
    text = options.get("text", "")
    return value + text


def capitalize(value: str, locale, options) -> str:  # noqa: ARG001
    if options.get("start", "yes") == "yes":
        value = value[0].upper() + value[1:]
    if options.get("end", "no") == "yes":
        value = value[:-1] + value[-1].upper()
    if options.get("middle", "no") == "yes":
        value = value[0] + value[1:-1].upper() + value[-1]
    return value


def integer_formatter(value: Any, locale: Locale, options: dict[str, Any]):  # noqa: ARG001
    return str(int(value))


def integer_selector(value: Any, locale: Locale, options: dict[str, Any], keys: list[str]):  # noqa: ARG001
    return ["1", "one"]


def string_formatter_mutually_exclusive(value: Any, locale: Locale, options: dict[str, Any]):  # noqa: ARG001
    if options.get("foo") and options.get("bar"):
        msg = "foo and bar are mutually exclusive"
        raise OperandMismatch(msg)
    return str(value)


@pytest.mark.parametrize(
    ("message", "inputs", "formatted"),
    [
        ("", None, ""),
        ("Hello, World!", None, "Hello, World!"),
        ("Hello, {|World|}!", None, "Hello, World!"),
        ("Hello, {$name}!", {"name": "Alice"}, "Hello, Alice!"),
    ],
)
def test_parse_simple_message(message, inputs, formatted):
    assert Message(message).format(inputs) == formatted


@pytest.mark.parametrize(
    ("message", "inputs", "formatted"),
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
)
def test_declarations(message, inputs, formatted):
    assert Message(message).format(inputs) == formatted


@pytest.mark.parametrize(
    ("message", "inputs", "formatted"),
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
)
def test_annotations(message, inputs, formatted):
    assert (
        Message(message).format(
            inputs,
            "en",
            formatters={"date": date, "capitalize": capitalize},
        )
        == formatted
    )


@pytest.mark.parametrize(
    ("message", "inputs", "formatted"),
    [
        (
            """\
.local $name = {|john| :capitalize}
{{{|Hello, | :append text=$name}!}}""",
            None,
            "Hello, John!",
        ),
    ],
)
def test_variable_options(message, inputs, formatted):
    assert (
        Message(message).format(
            inputs,
            "en",
            formatters={"append": append, "capitalize": capitalize},
        )
        == formatted
    )


@pytest.mark.parametrize(
    ("message", "inputs", "formatted"),
    [
        ('{#strong opt=|"abc"|}Click here!{/strong}', None, '<strong opt="abc">Click here!</strong>'),
        ('Hello, {#strong text=|"John"| /}!', None, 'Hello, <strong text="John"/>!'),
    ],
)
def test_markup(message, inputs, formatted):
    assert Message(message).format(inputs) == formatted


@pytest.mark.parametrize(
    ("message", "inputs", "formatted"),
    [
        (
            """\
.match {$count :integer}
one {{You have {$count} notification.}}
1 {{You have one notification.}}
* {{You have {$count} notifications.}}""",
            {"count": 1},
            "You have one notification.",
        ),
        (
            """\
.match {$count :integer}
xxx {{You have {$count} notification.}}
yyy {{You have one notification.}}
*   {{You have {$count} notifications.}}""",
            {"count": 42},
            "You have 42 notifications.",
        ),
        (
            """\
.input {$count :integer}
.match {$count}
*   {{You have {$count} notifications.}}""",
            {"count": 42},
            "You have 42 notifications.",
        ),
    ],
)
def test_selectors(message, inputs, formatted):
    assert (
        Message(message).format(
            inputs,
            "en",
            formatters={"integer": integer_formatter},
            selectors={"integer": integer_selector},
        )
        == formatted
    )


@pytest.mark.parametrize(
    ("message", "inputs", "formatted"),
    [
        (" .input", None, " .input"),
        (" .local $n = {42}", None, " .local $n = 42"),
        (" .match {$count} This looks illegal bu isn't", {"count": 42}, " .match 42 This looks illegal bu isn't"),
    ],
)
def test_gotchas(message, inputs, formatted):
    assert (
        Message(message).format(
            inputs,
            "en",
            formatters={"integer": integer_formatter},
            selectors={"integer": integer_selector},
        )
        == formatted
    )


@pytest.mark.parametrize(
    ("message", "inputs", "error"),
    [
        ("{:unknown}", None, UnknownFunction),
        ("{|dog| :unknown cute=yes}", None, UnknownFunction),
        ("The value is {!horse}.", None, UnsupportedExpression),
        ("The value is {$x !horse}.", None, UnsupportedExpression),
        ("The value is {|literal| !horse}.", None, UnsupportedExpression),
        (
            """\
.match {$count !horse}
* {{The count is {$count}.}}""",
            {"count": 42},
            UnsupportedExpression,
        ),
        (".unknown {$x} .match {$count :integer} * {{Reserved statement}}", None, UnsupportedStatement),
        ("{|dog| :string foo=1 bar=2}", None, OperandMismatch),
    ],
)
def test_errors(message, inputs, error):
    with pytest.raises(error):
        Message(message).format(inputs, formatters={"string": string_formatter_mutually_exclusive})

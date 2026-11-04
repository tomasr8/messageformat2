import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from babel import Locale

from messageformat2 import Message
from messageformat2.builtins import LazyValue, xml_markup
from messageformat2.errors import (
    BadOption,
    BadSelector,
    MessageFunctionError,
    ParseError,
    UnknownFunction,
)


if TYPE_CHECKING:
    from messageformat2.builtins import Formatter


def date(value, locale, options) -> str:  # noqa: ARG001
    return "2024-06-07"


def append(value: str, locale, options) -> str:  # noqa: ARG001
    text = options.get("text", "")
    return value + text


def capitalize(value: str | LazyValue, locale, options) -> str:  # noqa: ARG001
    while isinstance(value, LazyValue):
        # re-annotation: inherit the options of the earlier :capitalize annotations
        assert value.fn_name == "capitalize"
        options = {**value.options, **options}
        value = value.value
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
        raise BadOption(msg)
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
    ("message", "inputs", "formatted", "xml"),
    [
        ("{#strong}Click here!{/strong}", None, "Click here!", "<strong>Click here!</strong>"),
        ('{#strong opt=|"abc"|}Click here!{/strong}', None, "Click here!", '<strong opt="abc">Click here!</strong>'),
        ('Hello, {#strong text=|"John"| /}!', None, "Hello, !", 'Hello, <strong text="John"/>!'),
        ("{#img alt=$alt @attr=1 /}", {"alt": "Cancel"}, "", "<img alt=Cancel/>"),
        ("{#ns:tag}content{/ns:tag}", None, "content", "<ns:tag>content</ns:tag>"),
    ],
)
def test_markup(message, inputs, formatted, xml):
    assert Message(message).format(inputs) == formatted
    assert Message(message).format(inputs, markup=xml_markup) == xml


def test_custom_markup():
    def markup(kind, name, options) -> str:  # noqa: ARG001
        return {"open": "[", "close": "]", "standalone": "|"}[kind]

    assert Message("{#b}bold{/b} {#br/}").format(markup=markup) == "[bold] |"


@pytest.mark.parametrize(
    ("message", "inputs", "formatted"),
    [
        (
            """\
.input {$count :integer}
.match $count
one {{You have {$count} notification.}}
1 {{You have one notification.}}
* {{You have {$count} notifications.}}""",
            {"count": 1},
            "You have one notification.",
        ),
        (
            """\
.local $count = {42 :integer}
.match $count
xxx {{You have {$count} notification.}}
yyy {{You have one notification.}}
*   {{You have {$count} notifications.}}""",
            {"count": 42},
            "You have 42 notifications.",
        ),
        (
            """\
.input {$count :integer}
.local $n = {$count}
.match $n
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
    ("inputs", "formatted"),
    [
        ({"count": 1, "n": 1}, "both are one"),
        ({"count": 1, "n": 2}, "count is one"),
        ({"count": 2, "n": 1}, "n is one"),
        ({"count": 2, "n": 2}, "neither is one"),
    ],
)
def test_multiple_selectors(inputs, formatted):
    message = """\
.input {$count :integer}
.input {$n :integer}
.match $count $n
1 1 {{both are one}}
1 * {{count is one}}
* 1 {{n is one}}
* * {{neither is one}}"""
    assert Message(message).format(inputs, "en") == formatted


@pytest.mark.parametrize(
    ("message", "inputs", "formatted"),
    [
        (" leading and trailing whitespace is text ", None, " leading and trailing whitespace is text "),
        ("\n  .local $n = {42}\n  {{n = {$n}}}\n", None, "n = 42"),
        ("\n  {{ quoted pattern whitespace is text }}\n", None, " quoted pattern whitespace is text "),
        ("{{.input}}", None, ".input"),
        ("{{ .match {$count} This looks illegal but isn't}}", {"count": 42}, " .match 42 This looks illegal but isn't"),
    ],
)
def test_gotchas(message, inputs, formatted):
    assert Message(message).format(inputs, "en") == formatted


@pytest.mark.parametrize(
    "message",
    [
        " .input",
        " .local $n = {42}",
        " .match {$count} This looks illegal and is",
        "\u3000.match",
    ],
)
def test_simple_message_cannot_start_with_period(message):
    with pytest.raises(ParseError):
        Message(message)


@pytest.mark.parametrize(
    ("message", "inputs", "error"),
    [
        ("{:unknown}", None, UnknownFunction),
        ("{|dog| :unknown cute=yes}", None, UnknownFunction),
        ("{|dog| :string foo=1 bar=2}", None, BadOption),
        ("{|dog| :raise}", None, MessageFunctionError),
        # selecting on a function which only supports formatting
        (".local $x = {42 :format-only} .match $x * {{foo}}", None, BadSelector),
        (".local $x = {42 :unknown} .match $x * {{foo}}", None, UnknownFunction),
    ],
)
def test_errors(message, inputs, error):
    def raise_some_error(value, locale, options) -> str:  # noqa: ARG001
        msg = "boom"
        raise RuntimeError(msg)

    formatters: dict[str, Formatter] = {
        "string": string_formatter_mutually_exclusive,
        "raise": raise_some_error,
        "format-only": date,
    }
    with pytest.raises(error):
        Message(message).format(inputs, formatters=formatters)


def test_input_names_are_nfc_normalized():
    nfd = "D\u0323\u0307"
    nfc = "\u1e0c\u0307"
    assert Message(f"{{${nfd}}}").format({nfc: "foo"}) == "foo"
    assert Message(f"{{${nfc}}}").format({nfd: "foo"}) == "foo"
    assert Message(f".input {{${nfd}}} {{{{{{${nfc}}}}}}}").format({nfd: "foo"}) == "foo"


def test_reannotation_passes_lazy_value_with_its_options():
    def fn(value, locale, options) -> str:  # noqa: ARG001
        if isinstance(value, LazyValue):
            value = f"{value.fn_name}[{value.value}:{sorted(value.options.items())}]"
        return f"{value}:{sorted(options.items())}:{sorted(options.literal)}"

    message = ".local $x = {42 :fn a=1 b=2} {{{$x :fn b=3 c=$c}}}"
    out = Message(message).format({"c": 4}, formatters={"fn": fn})
    assert out == "fn[42:[('a', '1'), ('b', '2')]]:[('b', '3'), ('c', 4)]:['b']"


def test_reannotation_with_different_function_passes_lazy_value():
    def shout(value, locale, options) -> str:  # noqa: ARG001
        assert isinstance(value, LazyValue)
        assert value.fn_name == "string"
        assert value.value == "alice"
        return str(value).upper()

    message = ".local $name = {alice :string} {{{$name :shout}}}"
    assert Message(message).format(formatters={"shout": shout}) == "ALICE"


def test_selector_errors_are_bad_selector_errors():
    def bad(value, locale, options, keys) -> list[str]:  # noqa: ARG001
        msg = "nope"
        raise BadOption(msg)

    message = ".local $x = {42 :bad} .match $x 1 {{one}} * {{other}}"
    with pytest.raises(BadSelector) as excinfo:
        Message(message).format(None, "en", formatters={"bad": date}, selectors={"bad": bad})
    assert isinstance(excinfo.value.__cause__, BadOption)


@pytest.mark.parametrize(
    ("value", "locale", "formatted"),
    [
        (1234.5, "en", "1,234.5"),
        (1234.5, "fr", "1\u202f234,5"),
        (1234567, "de", "1.234.567"),
        (Decimal("0.10"), "en", "0.1"),
        (True, "en", "True"),
        ("1234.5", "en", "1234.5"),
        (dt.datetime(2006, 1, 2, 15, 4, 6), "en", "Jan 2, 2006, 3:04 PM"),  # noqa: DTZ001
        (dt.date(2006, 1, 2), "en", "Jan 2, 2006"),
        (dt.time(15, 4), "en", "3:04 PM"),
        (None, "en", "None"),
    ],
)
def test_unannotated_variables_are_formatted_by_type(value, locale, formatted):
    assert Message("{$x}").format({"x": value}, locale) == formatted
    assert Message(".local $y = {$x} {{{$y}}}").format({"x": value}, locale) == formatted

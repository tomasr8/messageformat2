import pytest

from messageformat2 import Message
from messageformat2.errors import BadOperand, BadOption, BadSelector, BadVariantKey


@pytest.mark.parametrize(
    ("message", "inputs", "locale", "formatted"),
    [
        ("{4.2 :number}", None, "en", "4.2"),
        ("{-4.20 :number}", None, "en", "-4.2"),
        ("{|0.42e+1| :number}", None, "en", "4.2"),
        ("{1234567.891 :number}", None, "en", "1,234,567.891"),
        ("{1234567.891 :number}", None, "fr", "1\u202f234\u202f567,891"),
        ("{1234567.891 :number useGrouping=never}", None, "en", "1234567.891"),
        ("{$n :number}", {"n": 1.5}, "en", "1.5"),
        ("{$n :number}", {"n": "1.5"}, "en", "1.5"),
        ("{4.2 :number minimumFractionDigits=2}", None, "en", "4.20"),
        ("{4.2 :number minimumFractionDigits=$d}", {"d": 2}, "en", "4.20"),
        ("{4.25678 :number maximumFractionDigits=1}", None, "en", "4.3"),
        ("{4.2 :number minimumIntegerDigits=3}", None, "en", "004.2"),
        ("{1234.5678 :number maximumSignificantDigits=3}", None, "en", "1,230"),
        ("{1.5 :number minimumSignificantDigits=4}", None, "en", "1.500"),
        ("{42 :number signDisplay=always}", None, "en", "+42"),
        ("{-42 :number signDisplay=never}", None, "en", "42"),
        ("{0 :number signDisplay=exceptZero}", None, "en", "0"),
        ("{-0 :number signDisplay=negative}", None, "en", "0"),
        ("{-0 :number}", None, "en", "-0"),
        ("{4.2 :integer}", None, "en", "4"),
        ("{-4.7 :integer}", None, "en", "-4"),
        ("{|0.42e+1| :integer}", None, "en", "4"),
        ("{1234567 :integer}", None, "en", "1,234,567"),
        ("{41 :offset add=1}", None, "en", "42"),
        ("{52 :offset subtract=10}", None, "en", "42"),
        ("{41 :offset add=1 foo=13}", None, "en", "42"),
        # the options of an annotated operand are inherited
        (".local $x = {1.25 :integer} {{{$x :number}}}", None, "en", "1"),
        (".local $x = {1.25 :number minimumFractionDigits=2} {{{$x :integer}}}", None, "en", "1"),
        (".local $x = {41 :integer signDisplay=always} {{{$x :offset add=1}}}", None, "en", "+42"),
        (".local $x = {52 :number signDisplay=always} {{{$x :offset subtract=10}}}", None, "en", "+42"),
        (
            ".input {$n :number minimumFractionDigits=2 signDisplay=always} {{{$n :number minimumFractionDigits=1}}}",
            {"n": 3},
            "en",
            "+3.0",
        ),
    ],
)
def test_number_formatting(message, inputs, locale, formatted):
    assert Message(message).format(inputs, locale) == formatted


@pytest.mark.parametrize(
    ("message", "inputs", "error"),
    [
        ("{:number}", None, BadOperand),
        ("{foo :number}", None, BadOperand),
        ("{00 :number}", None, BadOperand),
        ("{1. :number}", None, BadOperand),
        ("{1e :number}", None, BadOperand),
        ("{|+1| :number}", None, BadOperand),
        ("{|0x1| :number}", None, BadOperand),
        ("{$n :number}", {"n": "foo"}, BadOperand),
        ("{$n :number}", {"n": True}, BadOperand),
        ("{$n :number}", {"n": None}, BadOperand),
        (".local $s = {foo :string} {{{$s :number}}}", None, BadOperand),
        ("{42 :number minimumFractionDigits=foo}", None, BadOption),
        ("{42 :number minimumFractionDigits=-1}", None, BadOption),
        ("{42 :number minimumFractionDigits=100}", None, BadOption),
        ("{42 :number signDisplay=foo}", None, BadOption),
        ("{42 :number useGrouping=foo}", None, BadOption),
        ("{42 :number select=foo}", None, BadOption),
        ("{42 :number select=$s}", {"s": "exact"}, BadOption),
        ("{42 :offset}", None, BadOption),
        ("{42 :offset add=foo}", None, BadOption),
        ("{42 :offset add=1 subtract=1}", None, BadOption),
        ("{:offset add=1}", None, BadOperand),
    ],
)
def test_number_errors(message, inputs, error):
    with pytest.raises(error):
        Message(message).format(inputs, "en")


PLURAL = """\
.input {$n :number}
.match $n
0    {{none}}
1    {{exactly one}}
one  {{one}}
few  {{few}}
many {{many}}
*    {{other}}"""


@pytest.mark.parametrize(
    ("inputs", "locale", "formatted"),
    [
        ({"n": 0}, "en", "none"),
        ({"n": 1}, "en", "exactly one"),
        ({"n": "1"}, "en", "exactly one"),
        ({"n": 1.0}, "en", "exactly one"),
        ({"n": 2}, "en", "other"),
        ({"n": 1}, "cs", "exactly one"),
        ({"n": 2}, "cs", "few"),
        ({"n": 2.5}, "cs", "many"),
        ({"n": 5}, "cs", "other"),
    ],
)
def test_plural_selection(inputs, locale, formatted):
    assert Message(PLURAL).format(inputs, locale) == formatted


def test_ordinal_selection():
    message = ".input {$n :integer select=ordinal} .match $n one {{st}} two {{nd}} few {{rd}} * {{th}}"
    assert [Message(message).format({"n": n}, "en") for n in (1, 2, 3, 4, 11, 21, 22)] == [
        "st",
        "nd",
        "rd",
        "th",
        "th",
        "st",
        "nd",
    ]


def test_exact_selection():
    message = ".input {$n :number select=exact} .match $n 1 {{one}} one {{keyword}} * {{other}}"
    assert Message(message).format({"n": 1}, "en") == "one"
    # keyword matching is disabled with select=exact; `one` is still a valid key though
    message = ".input {$n :number select=exact} .match $n one {{keyword}} * {{other}}"
    assert Message(message).format({"n": 1}, "en") == "other"


def test_exact_selection_uses_visible_fraction_digits():
    message = ".input {$n :number minimumFractionDigits=1} .match $n 1 {{int}} 1.0 {{decimal}} one {{one}} * {{other}}"
    assert Message(message).format({"n": 1}, "en") == "decimal"
    message = ".input {$n :number minimumFractionDigits=1} .match $n 1 {{int}} one {{one}} * {{other}}"
    assert Message(message).format({"n": 1}, "en") == "other"


def test_integer_selection_truncates():
    message = ".input {$n :integer} .match $n 1 {{=1}} one {{one}} * {{other}}"
    assert Message(message).format({"n": 1.2}, "en") == "=1"
    assert Message(message).format({"n": 1.9}, "en") == "=1"


def test_offset_selection():
    message = ".local $x = {10 :integer} .local $y = {$x :offset subtract=6} .match $y 10 {{=10}} 4 {{=4}} * {{other}}"
    assert Message(message).format(None, "en") == "=4"


def test_select_option_must_be_a_literal_for_selection():
    message = ".local $sel = {1 :integer select=exact} .local $bad = {$sel :integer} .match $bad 1 {{ONE}} * {{other}}"
    with pytest.raises(BadSelector) as excinfo:
        Message(message).format(None, "en")
    assert isinstance(excinfo.value.__cause__, BadOption)


def test_bad_variant_key():
    message = ".input {$n :number} .match $n horse {{horse}} * {{other}}"
    with pytest.raises(BadSelector) as excinfo:
        Message(message).format({"n": 1}, "en")
    assert isinstance(excinfo.value.__cause__, BadVariantKey)


def test_string_selection():
    message = ".input {$s :string} .match $s |1| {{one}} dog {{dog}} * {{other}}"
    assert Message(message).format({"s": "1"}) == "one"
    assert Message(message).format({"s": 1}) == "one"
    assert Message(message).format({"s": "dog"}) == "dog"
    assert Message(message).format({"s": "cat"}) == "other"


def test_string_selection_is_nfc_normalized():
    message = ".local $x = {D\u0323\u0307 :string} .match $x \u1e0c\u0307 {{Right}} * {{Wrong}}"
    assert Message(message).format() == "Right"


def test_string_errors():
    with pytest.raises(BadOperand):
        Message("{:string}").format()
    with pytest.raises(BadSelector):
        Message(".local $d = {|2024-05-01| :date} .match $d * {{The due date is {$d}}}").format()

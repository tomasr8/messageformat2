import datetime as dt

import pytest

from messageformat2 import Message
from messageformat2.builtins import Currency
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
        ("{0.000123456 :number maximumSignificantDigits=2}", None, "en", "0.00012"),
        # rounding: the default mode is halfExpand (ties away from zero), unlike Python's/Babel's half-even
        ("{2.5 :number maximumFractionDigits=0}", None, "en", "3"),
        ("{-2.5 :number maximumFractionDigits=0}", None, "en", "-3"),
        ("{2.5 :number maximumFractionDigits=0 roundingMode=halfEven}", None, "en", "2"),
        ("{2.5 :number maximumFractionDigits=0 roundingMode=halfTrunc}", None, "en", "2"),
        ("{2.5 :number maximumFractionDigits=0 roundingMode=halfCeil}", None, "en", "3"),
        ("{-2.5 :number maximumFractionDigits=0 roundingMode=halfCeil}", None, "en", "-2"),
        ("{2.5 :number maximumFractionDigits=0 roundingMode=halfFloor}", None, "en", "2"),
        ("{-2.5 :number maximumFractionDigits=0 roundingMode=halfFloor}", None, "en", "-3"),
        ("{2.1 :number maximumFractionDigits=0 roundingMode=ceil}", None, "en", "3"),
        ("{-2.1 :number maximumFractionDigits=0 roundingMode=ceil}", None, "en", "-2"),
        ("{2.9 :number maximumFractionDigits=0 roundingMode=floor}", None, "en", "2"),
        ("{-2.1 :number maximumFractionDigits=0 roundingMode=floor}", None, "en", "-3"),
        ("{2.1 :number maximumFractionDigits=0 roundingMode=expand}", None, "en", "3"),
        ("{-2.9 :number maximumFractionDigits=0 roundingMode=trunc}", None, "en", "-2"),
        ("{1.2345 :number maximumSignificantDigits=3 roundingMode=floor}", None, "en", "1.23"),
        ("{5 :number minimumFractionDigits=2 trailingZeroDisplay=stripIfInteger}", None, "en", "5"),
        ("{5.01 :number minimumFractionDigits=2 trailingZeroDisplay=stripIfInteger}", None, "en", "5.01"),
        ("{4.999 :number maximumFractionDigits=2 trailingZeroDisplay=stripIfInteger}", None, "en", "5"),
        ("{1.23 :number minimumFractionDigits=2 maximumFractionDigits=2 roundingIncrement=5}", None, "en", "1.25"),
        ("{1.22 :number minimumFractionDigits=2 maximumFractionDigits=2 roundingIncrement=5}", None, "en", "1.20"),
        ("{1234 :number minimumFractionDigits=0 maximumFractionDigits=0 roundingIncrement=50}", None, "en", "1,250"),
        (
            "{1234.5678 :number maximumFractionDigits=1 maximumSignificantDigits=3 roundingPriority=morePrecision}",
            None,
            "en",
            "1,234.6",
        ),
        (
            "{1234.5678 :number maximumFractionDigits=1 maximumSignificantDigits=3 roundingPriority=lessPrecision}",
            None,
            "en",
            "1,230",
        ),
        ("{1234.5678 :number maximumFractionDigits=1 maximumSignificantDigits=3}", None, "en", "1,230"),
        ("{1234 :number useGrouping=min2}", None, "en", "1234"),
        ("{12345 :number useGrouping=min2}", None, "en", "12,345"),
        ("{1234 :number useGrouping=always}", None, "en", "1,234"),
        ("{42 :number signDisplay=always}", None, "en", "+42"),
        ("{-42 :number signDisplay=never}", None, "en", "42"),
        ("{0 :number signDisplay=exceptZero}", None, "en", "0"),
        ("{-0 :number signDisplay=negative}", None, "en", "0"),
        ("{-0 :number}", None, "en", "-0"),
        ("{4.2 :integer}", None, "en", "4"),
        ("{-4.7 :integer}", None, "en", "-5"),
        ("{1.5 :integer}", None, "en", "2"),
        ("{-2.5 :integer}", None, "en", "-3"),
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
        ("{42 :number roundingMode=foo}", None, BadOption),
        ("{42 :number roundingPriority=foo}", None, BadOption),
        ("{42 :number trailingZeroDisplay=foo}", None, BadOption),
        ("{42 :number roundingIncrement=3}", None, BadOption),
        ("{42 :number roundingIncrement=5 maximumFractionDigits=2}", None, BadOption),
        ("{42 :number roundingIncrement=5 maximumSignificantDigits=2}", None, BadOption),
        ("{42 :number minimumFractionDigits=3 maximumFractionDigits=1}", None, BadOption),
        ("{42 :number minimumSignificantDigits=3 maximumSignificantDigits=1}", None, BadOption),
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


def test_integer_selection_rounds():
    message = ".input {$n :integer} .match $n 1 {{=1}} one {{one}} * {{other}}"
    assert Message(message).format({"n": 1.2}, "en") == "=1"
    assert Message(message).format({"n": 1.5}, "en") == "other"
    assert Message(message).format({"n": 0.5}, "en") == "=1"


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


DT = dt.datetime(2006, 1, 2, 15, 4, 6)  # noqa: DTZ001
AWARE = dt.datetime(2006, 1, 2, 15, 4, 6, tzinfo=dt.UTC)


@pytest.mark.parametrize(
    ("message", "inputs", "locale", "formatted"),
    [
        ("{$d :datetime}", {"d": DT}, "en", "Jan 2, 2006, 3:04 PM"),
        ("{$d :datetime}", {"d": DT}, "cs", "2. 1. 2006 15:04"),
        ("{$d :datetime dateLength=long timePrecision=second}", {"d": DT}, "en", "January 2, 2006, 3:04:06 PM"),
        ("{$d :datetime dateLength=short timePrecision=hour}", {"d": DT}, "en", "1/2/06, 3 PM"),
        (
            "{$d :datetime dateFields=year-month-day-weekday dateLength=long}",
            {"d": DT},
            "en",
            "Monday, January 2, 2006, 3:04 PM",
        ),
        ("{$d :datetime dateFields=month-day}", {"d": DT}, "en", "Jan 2, 3:04 PM"),
        ("{$d :datetime hour12=false}", {"d": DT}, "en", "Jan 2, 2006, 15:04"),
        ("{$d :datetime hour12=true}", {"d": DT}, "cs", "2. 1. 2006 3:04\u202fodp."),
        ("{$d :datetime timeZoneStyle=short}", {"d": AWARE}, "en", "Jan 2, 2006, 3:04 PM UTC"),
        (
            "{$d :datetime timeZone=|Europe/Zurich| timeZoneStyle=long}",
            {"d": AWARE},
            "en",
            "Jan 2, 2006, 4:04 PM Central European Standard Time",
        ),
        ("{$d :datetime timeZone=|+01:00| timeZoneStyle=short}", {"d": DT}, "en", "Jan 2, 2006, 3:04 PM +0100"),
        ("{$d :datetime timeZone=input timeZoneStyle=short}", {"d": AWARE}, "en", "Jan 2, 2006, 3:04 PM UTC"),
        ("{|2006-01-02T15:04:06| :datetime}", None, "en", "Jan 2, 2006, 3:04 PM"),
        ("{|2006-01-02T15:04:06Z| :datetime timeZoneStyle=short}", None, "en", "Jan 2, 2006, 3:04 PM UTC"),
        ("{$d :datetime}", {"d": "2006-01-02T15:04:06"}, "en", "Jan 2, 2006, 3:04 PM"),
        ("{$d :date}", {"d": DT}, "en", "Jan 2, 2006"),
        ("{$d :date}", {"d": DT.date()}, "en", "Jan 2, 2006"),
        ("{$d :date length=long}", {"d": DT}, "fr", "2 janvier 2006"),
        ("{$d :date length=short}", {"d": DT}, "en", "1/2/06"),
        ("{$d :date fields=weekday length=long}", {"d": DT}, "en", "Monday"),
        ("{$d :date fields=month-day-weekday}", {"d": DT}, "en", "Mon, Jan 2"),
        ("{$d :date fields=year-month-day-weekday length=long}", {"d": DT}, "en", "Monday, January 2, 2006"),
        ("{|2006-01-02| :date}", None, "en", "Jan 2, 2006"),
        ("{$d :time}", {"d": DT}, "en", "3:04 PM"),
        ("{$d :time}", {"d": DT.time()}, "en", "3:04 PM"),
        ("{$d :time precision=second}", {"d": DT}, "cs", "15:04:06"),
        ("{$d :time precision=hour}", {"d": DT}, "en", "3 PM"),
        ("{$d :time hour12=false}", {"d": DT}, "en", "15:04"),
        ("{$d :time timeZone=UTC timeZoneStyle=short}", {"d": DT}, "en", "3:04 PM UTC"),
        # the resolved value of a date/time function can be used as an operand; only override options are inherited
        (".local $x = {$d :datetime dateLength=long timeZone=UTC} {{{$x :date}}}", {"d": DT}, "en", "Jan 2, 2006"),
        (
            ".local $x = {$d :datetime dateLength=long timeZone=UTC} {{{$x :time timeZoneStyle=short}}}",
            {"d": DT},
            "en",
            "3:04 PM UTC",
        ),
        (".local $x = {$d :datetime dateLength=long} {{{$x :datetime}}}", {"d": DT}, "en", "Jan 2, 2006, 3:04 PM"),
        (".local $x = {$d :date length=long} {{{$x}}}", {"d": DT}, "en", "January 2, 2006"),
    ],
)
def test_datetime_formatting(message, inputs, locale, formatted):
    assert Message(message).format(inputs, locale) == formatted


@pytest.mark.parametrize(
    ("message", "inputs", "error"),
    [
        ("{:datetime}", None, BadOperand),
        ("{:date}", None, BadOperand),
        ("{:time}", None, BadOperand),
        ("{horse :datetime}", None, BadOperand),
        ("{$d :datetime}", {"d": True}, BadOperand),
        ("{$d :datetime}", {"d": 1136214246}, BadOperand),
        ("{$d :datetime}", {"d": DT.date()}, BadOperand),
        ("{$d :datetime}", {"d": DT.time()}, BadOperand),
        ("{$d :date}", {"d": DT.time()}, BadOperand),
        ("{$d :time}", {"d": DT.date()}, BadOperand),
        (".local $n = {42 :number} {{{$n :datetime}}}", None, BadOperand),
        ("{$d :datetime timeZone=input}", {"d": DT}, BadOperand),
        ("{$d :datetime dateLength=huge}", {"d": DT}, BadOption),
        ("{$d :datetime dateLength=$l}", {"d": DT, "l": "long"}, BadOption),
        ("{$d :date fields=$f}", {"d": DT, "f": "weekday"}, BadOption),
        ("{$d :time precision=$p}", {"d": DT, "p": "second"}, BadOption),
        ("{$d :datetime hour12=maybe}", {"d": DT}, BadOption),
        ("{$d :datetime timeZone=|Mars/Olympus|}", {"d": DT}, BadOption),
    ],
)
def test_datetime_errors(message, inputs, error):
    with pytest.raises(error):
        Message(message).format(inputs, "en")


@pytest.mark.parametrize(
    ("message", "inputs", "locale", "formatted"),
    [
        ("{0.12345678 :percent}", None, "en", "12%"),
        ("{0.12345678 :percent maximumFractionDigits=1}", None, "en", "12.3%"),
        ("{0.12 :percent minimumFractionDigits=1}", None, "en", "12.0%"),
        ("{0.12 :percent minimumSignificantDigits=1}", None, "en", "12%"),
        ("{0.125 :percent maximumFractionDigits=0}", None, "en", "13%"),
        ("{1 :percent}", None, "de", "100\u00a0%"),
        ("{-0.5 :percent}", None, "en", "-50%"),
        ("{0.5 :percent signDisplay=always}", None, "en", "+50%"),
        ("{12.345 :percent}", None, "en", "1,235%"),
        ("{12.345 :percent useGrouping=never}", None, "en", "1235%"),
        ("{$x :percent}", {"x": 0.99}, "en", "99%"),
        # the resolved value of :percent is not multiplied by 100
        (".local $n = {0.42 :number} {{{$n :percent}}}", None, "en", "42%"),
        (".local $n = {42 :integer} {{{$n :percent}}}", None, "en", "4,200%"),
        (".local $n = {0.01 :percent} {{{$n :percent}}}", None, "en", "1%"),
        (".local $n = {0.01 :percent} {{{$n :number}}}", None, "en", "0.01"),
        (".local $n = {0.4 :percent minimumFractionDigits=1} {{{$n :percent}}}", None, "en", "40.0%"),
        # roundingIncrement is not a :percent option and is ignored
        ("{0.1234 :percent roundingIncrement=5}", None, "en", "12%"),
    ],
)
def test_percent_formatting(message, inputs, locale, formatted):
    assert Message(message).format(inputs, locale) == formatted


def test_percent_selection():
    message = ".input {$n :percent} .match $n 1 {{=1}} one {{one}} * {{other}}"
    assert Message(message).format({"n": 0.01}, "en") == "=1"
    assert Message(message).format({"n": "0.01"}, "en") == "=1"
    assert Message(message).format({"n": 0.02}, "en") == "other"
    assert Message(message).format({"n": 1}, "en") == "other"
    # :percent always uses plural selection; select= on the operand is discarded
    message = ".local $x = {0.01 :number select=ordinal} .local $n = {$x :percent} .match $n one {{one}} * {{other}}"
    assert Message(message).format(None, "en") == "one"


@pytest.mark.parametrize(
    ("message", "inputs", "error"),
    [
        ("{:percent}", None, BadOperand),
        ("{foo :percent}", None, BadOperand),
        ("{1 :percent maximumFractionDigits=foo}", None, BadOption),
        ("{1 :percent roundingMode=foo}", None, BadOption),
    ],
)
def test_percent_errors(message, inputs, error):
    with pytest.raises(error):
        Message(message).format(inputs, "en")


@pytest.mark.parametrize(
    ("message", "inputs", "locale", "formatted"),
    [
        ("{42 :currency currency=EUR}", None, "en", "€42.00"),
        ("{42 :currency currency=EUR}", None, "de", "42,00\u00a0€"),
        ("{42 :currency currency=eur}", None, "ja", "€42.00"),
        ("{42 :currency currency=JPY}", None, "en", "¥42"),
        ("{42.567 :currency currency=JPY}", None, "en", "¥43"),
        ("{-42.5 :currency currency=USD}", None, "en", "-$42.50"),
        ("{-42.5 :currency currency=USD currencySign=accounting}", None, "en", "($42.50)"),
        ("{42 :currency currency=EUR fractionDigits=auto}", None, "en", "€42.00"),
        ("{42 :currency currency=EUR fractionDigits=0}", None, "en", "€42"),
        ("{42.123 :currency currency=EUR fractionDigits=3}", None, "en", "€42.123"),
        ("{1234.5 :currency currency=EUR fractionDigits=0 roundingMode=floor}", None, "en", "€1,234"),
        ("{1234.5 :currency currency=EUR useGrouping=never}", None, "en", "€1234.50"),
        ("{42 :currency currency=USD currencyDisplay=symbol}", None, "en", "$42.00"),
        ("{42 :currency currency=USD currencyDisplay=narrowSymbol}", None, "en", "$42.00"),
        ("{42 :currency currency=USD currencyDisplay=code}", None, "en", "USD42.00"),
        ("{42 :currency currency=USD currencyDisplay=name}", None, "en", "42.00 US dollars"),
        ("{42 :currency currency=USD currencyDisplay=never}", None, "en", "42.00"),
        ("{42 :currency currency=USD currencyDisplay=never}", None, "de", "42,00"),
        ("{5 :currency currency=USD trailingZeroDisplay=stripIfInteger}", None, "en", "$5"),
        ("{5.01 :currency currency=USD trailingZeroDisplay=stripIfInteger}", None, "en", "$5.01"),
        ("{42 :currency currency=USD minimumIntegerDigits=4}", None, "en", "$0,042.00"),
        # currency values as operands
        ("{$p :currency}", {"p": Currency(42, "EUR")}, "en", "€42.00"),
        ("{$p :currency}", {"p": Currency("42.5", "gbp")}, "en", "£42.50"),
        ("{$p :currency}", {"p": {"value": 42.5, "currency": "GBP"}}, "en", "£42.50"),
        ("{$p :currency currencyDisplay=code}", {"p": Currency(42, "EUR")}, "en", "EUR42.00"),
        # the options of annotated operands are inherited
        (".local $n = {42 :number} {{{$n :currency currency=EUR}}}", None, "en", "€42.00"),
        (".local $n = {42.7 :integer} {{{$n :currency currency=EUR}}}", None, "en", "€43.00"),
        (".local $n = {42 :currency currency=EUR} {{{$n :currency}}}", None, "en", "€42.00"),
        (".local $n = {42 :currency currency=EUR} {{{$n :currency currencyDisplay=code}}}", None, "en", "EUR42.00"),
        (
            (
                ".input {$n :currency currency=USD trailingZeroDisplay=stripIfInteger} "
                "{{{$n :currency currencySign=accounting}}}"
            ),
            {"n": -5},
            "en",
            "($5)",
        ),
    ],
)
def test_currency_formatting(message, inputs, locale, formatted):
    assert Message(message).format(inputs, locale) == formatted


@pytest.mark.parametrize(
    ("message", "inputs", "error"),
    [
        ("{:currency}", None, BadOperand),
        ("{foo :currency}", None, BadOperand),
        ("{42 :currency}", None, BadOperand),
        (".local $n = {42 :number} {{{$n :currency}}}", None, BadOperand),
        ("{$p :currency}", {"p": Currency(42, "EURO")}, BadOperand),
        ("{$p :currency}", {"p": Currency("foo", "EUR")}, BadOperand),
        ("{42 :currency currency=EURO}", None, BadOption),
        ("{42 :currency currency=12}", None, BadOption),
        ("{$p :currency currency=USD}", {"p": Currency(42, "EUR")}, BadOption),
        (".local $n = {42 :currency currency=EUR} {{{$n :currency currency=USD}}}", None, BadOption),
        ("{42 :currency currency=EUR currencyDisplay=foo}", None, BadOption),
        ("{42 :currency currency=EUR fractionDigits=foo}", None, BadOption),
        # a currency value is not a numeric operand, and :currency is not a selector
        (".local $n = {42 :currency currency=EUR} {{{$n :number}}}", None, BadOperand),
        (".local $n = {42 :currency currency=EUR} .match $n * {{other}}", None, BadSelector),
    ],
)
def test_currency_errors(message, inputs, error):
    with pytest.raises(error):
        Message(message).format(inputs, "en")

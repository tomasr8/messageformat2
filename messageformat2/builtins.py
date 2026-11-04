import copy
import datetime as dt
import re
import unicodedata
import zoneinfo
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Context, Decimal
from typing import TYPE_CHECKING, Any, Literal, Protocol, Self

from babel import Locale
from babel.dates import format_datetime as _format_datetime
from babel.dates import format_time as _format_time
from babel.dates import match_skeleton
from babel.numbers import get_minus_sign_symbol, get_plus_sign_symbol, parse_pattern

from messageformat2.errors import (
    BadOperand,
    BadOption,
    BadSelector,
    BadVariantKey,
    MessageFunctionError,
    UnknownFunction,
)


if TYPE_CHECKING:
    from messageformat2.runtime import FormattingContext


class ResolvedOptions(dict[str, Any]):
    """The resolved options of an expression, mapping option names to their resolved values.

    `literal` holds the names of the options whose value was set by a literal in the expression itself
    (as opposed to a variable, or an option inherited from an annotated operand). Some functions
    require certain options (e.g. `select` on `:number`) to be set by a literal.
    """

    literal: frozenset[str]

    def __init__(self, values: dict[str, Any] | None = None, *, literal: frozenset[str] = frozenset()) -> None:
        super().__init__(values or {})
        self.literal = literal


class LazyValue:
    """The resolved value of an expression with a function.

    The function is only called when the value is formatted or used for selection. A `LazyValue` is passed
    as the operand of a function when a variable that was already annotated with a *different* function
    is annotated again, e.g. `$y` in `.local $x = {42 :integer} .local $y = {$x :number}`. The function
    handler can then inspect `fn_name`, `value` and `options` of the operand (`str(operand)` gives its
    formatted value).
    """

    def __init__(self, *, fn_name: str, value: Any, options: ResolvedOptions | None, ctx: "FormattingContext") -> None:
        self.fn_name = fn_name
        self.value = value
        self.options = options if options is not None else ResolvedOptions()
        self._ctx = ctx

    def format(self) -> str:
        ctx = self._ctx
        if formatter := ctx.registry.formatters.get(self.fn_name):
            try:
                return str(formatter(value=self.value, locale=ctx.locale, options=self.options))
            except MessageFunctionError:
                raise
            except Exception as e:
                msg = f"Exception raised while evaluating formatter :{self.fn_name}"
                raise MessageFunctionError(msg) from e
        if self.fn_name in ctx.registry.selectors:
            msg = f"Function :{self.fn_name} does not support formatting"
            raise MessageFunctionError(msg)
        msg = f"Unknown function: {self.fn_name}"
        raise UnknownFunction(msg)

    def select(self, keys: list[str]) -> list[str]:
        ctx = self._ctx
        if selector := ctx.registry.selectors.get(self.fn_name):
            try:
                return selector(value=self.value, locale=ctx.locale, options=self.options, keys=keys)
            except Exception as e:
                # Any error while selecting is a Bad Selector error; the original error is available as `__cause__`
                msg = f"Bad selector: error while evaluating selector :{self.fn_name}: {e}"
                raise BadSelector(msg) from e
        if self.fn_name in ctx.registry.formatters:
            msg = f"Bad selector: function :{self.fn_name} does not support selection"
            raise BadSelector(msg)
        msg = f"Unknown function: {self.fn_name}"
        raise UnknownFunction(msg)

    def __str__(self) -> str:
        return self.format()

    def __repr__(self) -> str:
        return f"LazyValue({self.fn_name}({self.value!r}, {dict(self.options)!r}))"


class Formatter(Protocol):
    def __call__(self, value: Any, locale: Locale, options: ResolvedOptions) -> Any: ...


class Selector(Protocol):
    def __call__(self, value: Any, locale: Locale, options: ResolvedOptions, keys: list[str]) -> list[str]: ...


NUMBER_LITERAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?$")
"""The `number-literal` production: the only strings accepted as numeric operands."""
DIGIT_SIZE_OPTION = re.compile(r"^(?:0|[1-9][0-9]?)$")
PLURAL_KEYWORDS = frozenset({"zero", "one", "two", "few", "many", "other"})
NUMERIC_FUNCTIONS = frozenset({"number", "integer", "offset"})
SIGN_DISPLAY = frozenset({"auto", "always", "exceptZero", "negative", "never"})
USE_GROUPING = frozenset({"auto", "always", "never", "min2"})
SELECT = frozenset({"plural", "ordinal", "exact"})
# Options of an operand which are discarded by `:integer`
INTEGER_DISCARDED_OPTIONS = ("minimumFractionDigits", "maximumFractionDigits", "minimumSignificantDigits")
# Options which affect the serialization of integers for exact matching
EXACT_MATCH_OPTIONS = (
    "minimumFractionDigits",
    "minimumIntegerDigits",
    "minimumSignificantDigits",
    "maximumSignificantDigits",
)


class MarkupFormatter(Protocol):
    def __call__(self, kind: Literal["open", "standalone", "close"], name: str, options: dict[str, Any]) -> str: ...


def xml_markup(kind: Literal["open", "standalone", "close"], name: str, options: dict[str, Any]) -> str:
    """Format markup as XML-ish tags: `{#b}bold{/b}` -> `<b>bold</b>`, `{#img src=x /}` -> `<img src=x/>`.

    By default markup is formatted as an empty string as required by the spec; pass `markup=xml_markup` to
    `Message.format()` to get tags instead.
    """
    attributes = "".join(f" {key}={value}" for key, value in options.items())
    if kind == "open":
        return f"<{name}{attributes}>"
    if kind == "standalone":
        return f"<{name}{attributes}/>"
    return f"</{name}{attributes}>"


def string_formatter(value: Any, locale: Locale, options: dict[str, Any]) -> str:  # noqa: ARG001
    if value is None:
        msg = ":string requires an operand"
        raise BadOperand(msg)
    return str(value)


def string_selector(value: Any, locale: Locale, options: dict[str, Any], keys: list[str]) -> list[str]:
    # The string value is compared to the keys in NFC (the keys are already normalized)
    string = unicodedata.normalize("NFC", string_formatter(value, locale=locale, options=options))
    return [string] if string in keys else []


def to_decimal(value: Any) -> Decimal:
    """Convert a numeric operand to a Decimal, raising BadOperand for anything which is not a number."""
    if isinstance(value, bool):
        msg = f"Bad operand: {value!r} is not a number"
        raise BadOperand(msg)
    if isinstance(value, (int, Decimal)):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str) and NUMBER_LITERAL.match(value):
        return Decimal(value)
    msg = f"Bad operand: {value!r} is not a number"
    raise BadOperand(msg)


def digit_size_option(options: dict[str, Any], name: str) -> int | None:
    """Return the value of a digit size option (a small non-negative integer), or None if not set."""
    if (value := options.get(name)) is None:
        return None
    if isinstance(value, bool) or (not isinstance(value, int) and not DIGIT_SIZE_OPTION.match(str(value))):
        msg = f"Bad option: {name}={value!r} is not a digit size option"
        raise BadOption(msg)
    return int(value)


def choice_option(options: dict[str, Any], name: str, choices: frozenset[str], default: str | None) -> str | None:
    """Return the value of an option which must be one of `choices` (`default` if the option is not set)."""
    if name not in options:
        return default
    value = options[name]
    if value not in choices:
        msg = f"Bad option: {name}={value!r} is not one of {sorted(choices)}"
        raise BadOption(msg)
    return value


def numeric_operand(value: Any, options: ResolvedOptions, fn_name: str) -> tuple[Decimal, ResolvedOptions]:
    """Resolve the operand of a numeric function.

    The operand is either a number, a string matching `number-literal`, or the resolved value of another
    numeric function whose options are inherited (with the options of the expression taking priority).
    """
    if isinstance(value, LazyValue):
        if value.fn_name not in NUMERIC_FUNCTIONS:
            msg = f"Bad operand: the resolved value of :{value.fn_name} cannot be used as a numeric operand"
            raise BadOperand(msg)
        number, inherited = numeric_value(value)
        if fn_name == "integer":
            inherited = ResolvedOptions({k: v for k, v in inherited.items() if k not in INTEGER_DISCARDED_OPTIONS})
        # options inherited from the operand were not set by a literal in *this* expression
        return number, ResolvedOptions({**inherited, **options}, literal=options.literal)
    return to_decimal(value), options


def numeric_value(lazy: LazyValue) -> tuple[Decimal, ResolvedOptions]:
    """Return the numeric value and the resolved options of a value annotated with a numeric function."""
    number, options = numeric_operand(lazy.value, lazy.options, lazy.fn_name)
    if lazy.fn_name == "integer":
        number = number.to_integral_value(rounding=ROUND_DOWN)
    elif lazy.fn_name == "offset":
        number += offset_delta(lazy.options)
        options = ResolvedOptions({k: v for k, v in options.items() if k not in ("add", "subtract")})
    return number, options


def offset_delta(options: dict[str, Any]) -> Decimal:
    add, subtract = digit_size_option(options, "add"), digit_size_option(options, "subtract")
    if (add is None) == (subtract is None):
        msg = "Bad option: :offset requires exactly one of the options 'add' and 'subtract'"
        raise BadOption(msg)
    return Decimal(add) if add is not None else -Decimal(subtract)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def _integer_digits(number: Decimal) -> int:
    return max(number.adjusted() + 1, 1) if number != 0 else 1


def check_select_option(options: ResolvedOptions) -> str:
    """Validate the `select` option, which must be set by a literal in the expression itself."""
    if "select" in options and "select" not in options.literal:
        msg = "Bad option: the 'select' option must be set by a literal"
        raise BadOption(msg)
    return choice_option(options, "select", SELECT, "plural") or "plural"


def format_numeric(number: Decimal, locale: Locale, options: ResolvedOptions) -> str:
    """Format a number according to the `:number`/`:integer` options."""
    check_select_option(options)
    sign_display = choice_option(options, "signDisplay", SIGN_DISPLAY, "auto") or "auto"
    use_grouping = choice_option(options, "useGrouping", USE_GROUPING, "auto") or "auto"
    numbering_system = options.get("numberingSystem", "default")
    min_int = digit_size_option(options, "minimumIntegerDigits")
    min_frac = digit_size_option(options, "minimumFractionDigits")
    max_frac = digit_size_option(options, "maximumFractionDigits")
    min_sig = digit_size_option(options, "minimumSignificantDigits")
    max_sig = digit_size_option(options, "maximumSignificantDigits")

    if max_sig is not None:
        number = Context(prec=max(max_sig, 1), rounding=ROUND_HALF_EVEN).create_decimal(number)

    pattern = copy.copy(parse_pattern(locale.decimal_formats[None]))
    frac_min, frac_max = pattern.frac_prec
    if min_frac is not None:
        frac_min = min_frac
        frac_max = max(frac_max, min_frac)
    if max_frac is not None:
        frac_max = max_frac
        frac_min = min(frac_min, max_frac)
    if min_sig is not None:
        needed = max(min_sig - _integer_digits(number), 0)
        frac_min, frac_max = max(frac_min, needed), max(frac_max, needed)
    pattern.frac_prec = (frac_min, frac_max)
    if min_int is not None:
        pattern.int_prec = (max(min_int, 1), pattern.int_prec[1])

    formatted = pattern.apply(
        abs(number), locale, group_separator=use_grouping != "never", numbering_system=numbering_system
    )
    negative = number.is_signed()
    show_sign = {
        "auto": negative,
        "always": True,
        "exceptZero": number != 0,
        "negative": number < 0,
        "never": False,
    }[sign_display]
    if not show_sign:
        return formatted
    if negative:
        return get_minus_sign_symbol(locale, numbering_system=numbering_system) + formatted
    return get_plus_sign_symbol(locale, numbering_system=numbering_system) + formatted


def select_numeric(number: Decimal, locale: Locale, options: ResolvedOptions, keys: list[str]) -> list[str]:
    """Return the matching keys for a number, best match first: an exact match, then a plural/ordinal keyword."""
    select = check_select_option(options)

    min_frac = digit_size_option(options, "minimumFractionDigits")
    if min_frac is not None and -number.as_tuple().exponent < min_frac:  # type: ignore[operator]  # ty: ignore[unsupported-operator]
        number = number.quantize(Decimal(10) ** -min_frac)

    if number == number.to_integral_value() and not any(options.get(name) for name in EXACT_MATCH_OPTIONS):
        exact = str(int(number))
    else:
        exact = format(number, "f")

    keyword = None
    if select == "plural":
        keyword = locale.plural_form(number)
    elif select == "ordinal":
        keyword = locale.ordinal_form(number)

    matches = []
    for key in keys:
        if NUMBER_LITERAL.match(key):
            if key == exact:
                matches.insert(0, key)
        elif key in PLURAL_KEYWORDS:
            if key == keyword:
                matches.append(key)
        else:
            msg = f"Bad variant key: {key!r} is neither a number nor a plural category"
            raise BadVariantKey(msg)
    return matches


def number_formatter(value: Any, locale: Locale, options: ResolvedOptions) -> str:
    number, options = numeric_operand(value, options, "number")
    return format_numeric(number, locale, options)


def number_selector(value: Any, locale: Locale, options: ResolvedOptions, keys: list[str]) -> list[str]:
    number, options = numeric_operand(value, options, "number")
    return select_numeric(number, locale, options, keys)


def integer_formatter(value: Any, locale: Locale, options: ResolvedOptions) -> str:
    number, options = numeric_operand(value, options, "integer")
    number = number.to_integral_value(rounding=ROUND_DOWN)
    options = ResolvedOptions({**options, "maximumFractionDigits": 0}, literal=options.literal)
    return format_numeric(number, locale, options)


def integer_selector(value: Any, locale: Locale, options: ResolvedOptions, keys: list[str]) -> list[str]:
    number, options = numeric_operand(value, options, "integer")
    number = number.to_integral_value(rounding=ROUND_DOWN)
    return select_numeric(number, locale, options, keys)


def offset_formatter(value: Any, locale: Locale, options: ResolvedOptions) -> str:
    number, options = numeric_operand(value, options, "offset")
    number += offset_delta(options)
    inherited = {k: v for k, v in options.items() if k not in ("add", "subtract")}
    return format_numeric(number, locale, ResolvedOptions(inherited, literal=options.literal))


def offset_selector(value: Any, locale: Locale, options: ResolvedOptions, keys: list[str]) -> list[str]:
    number, options = numeric_operand(value, options, "offset")
    number += offset_delta(options)
    inherited = {k: v for k, v in options.items() if k not in ("add", "subtract")}
    return select_numeric(number, locale, ResolvedOptions(inherited, literal=options.literal), keys)


DATETIME_FUNCTIONS = frozenset({"datetime", "date", "time"})
# Options which are inherited from an annotated date/time operand
DATETIME_OVERRIDE_OPTIONS = ("timeZone", "hour12", "calendar")
DATE_FIELDS = frozenset(
    {"weekday", "day-weekday", "month-day", "month-day-weekday", "year-month-day", "year-month-day-weekday"}
)
DATE_LENGTH = frozenset({"long", "medium", "short"})
TIME_PRECISION = frozenset({"hour", "minute", "second"})
TIME_ZONE_STYLE = frozenset({"long", "short"})
HOUR12 = frozenset({"true", "false"})
# Skeletons (or standard formats, as "std:<length>") for the date part, by (fields, length)
_DATE_SKELETONS = {
    ("year-month-day", "short"): "std:short",
    ("year-month-day", "medium"): "std:medium",
    ("year-month-day", "long"): "std:long",
    ("year-month-day-weekday", "short"): "yMEd",
    ("year-month-day-weekday", "medium"): "yMMMEd",
    ("year-month-day-weekday", "long"): "std:full",
    ("month-day", "short"): "Md",
    ("month-day", "medium"): "MMMd",
    ("month-day", "long"): "MMMMd",
    ("month-day-weekday", "short"): "MEd",
    ("month-day-weekday", "medium"): "MMMEd",
    ("month-day-weekday", "long"): "MMMMEEEEd",
    ("day-weekday", "short"): "Ed",
    ("day-weekday", "medium"): "Ed",
    ("day-weekday", "long"): "EEEEd",
    ("weekday", "short"): "E",
    ("weekday", "medium"): "E",
    ("weekday", "long"): "EEEE",
}
_TIME_ZONE_OFFSET = re.compile(r"^[+-](?:0[0-9]|1[0-3]):[0-5][0-9]$|^[+-]14:00$")


def datetime_operand(value: Any, options: ResolvedOptions) -> tuple[Any, ResolvedOptions]:
    """Resolve the operand of a date/time function.

    The operand is a `datetime`, `date` or `time`, an ISO 8601 date or datetime string, or the resolved value
    of another date/time function, in which case its date/time override options are inherited.
    """
    if isinstance(value, LazyValue):
        if value.fn_name not in DATETIME_FUNCTIONS:
            msg = f"Bad operand: the resolved value of :{value.fn_name} cannot be used as a date/time operand"
            raise BadOperand(msg)
        operand, inherited = datetime_operand(value.value, value.options)
        inherited = {k: v for k, v in inherited.items() if k in DATETIME_OVERRIDE_OPTIONS}
        return operand, ResolvedOptions({**inherited, **options}, literal=options.literal)
    if isinstance(value, str):
        try:
            return dt.datetime.fromisoformat(value), options
        except ValueError as e:
            msg = f"Bad operand: {value!r} is not an ISO 8601 date or datetime"
            raise BadOperand(msg) from e
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value, options
    msg = f"Bad operand: {value!r} is not a date/time value"
    raise BadOperand(msg)


def literal_option(options: ResolvedOptions, name: str, choices: frozenset[str], default: str | None) -> str | None:
    """Return the value of an option which must be set by a literal, validated against `choices`."""
    if name not in options:
        return default
    if name not in options.literal:
        msg = f"Bad option: the {name!r} option must be set by a literal"
        raise BadOption(msg)
    return choice_option(options, name, choices, default)


def _time_zone(options: ResolvedOptions, operand: Any) -> dt.tzinfo | None:
    tz = options.get("timeZone")
    if tz is None:
        return None
    if isinstance(tz, dt.tzinfo):
        return tz
    if tz == "input":
        if getattr(operand, "tzinfo", None) is None:
            msg = "Bad operand: timeZone=input requires an operand with a time zone or offset"
            raise BadOperand(msg)
        return operand.tzinfo
    if tz == "UTC":
        return dt.UTC
    if _TIME_ZONE_OFFSET.match(str(tz)):
        sign = -1 if tz[0] == "-" else 1
        hours, minutes = int(tz[1:3]), int(tz[4:6])
        return dt.timezone(sign * dt.timedelta(hours=hours, minutes=minutes))
    try:
        return zoneinfo.ZoneInfo(str(tz))
    except (zoneinfo.ZoneInfoNotFoundError, ValueError) as e:
        msg = f"Bad option: timeZone={tz!r} is not a known time zone"
        raise BadOption(msg) from e


def _apply_time_zone(operand: dt.datetime, options: ResolvedOptions) -> dt.datetime:
    tz = _time_zone(options, operand)
    if tz is None:
        return operand
    if operand.tzinfo is None:
        return operand.replace(tzinfo=tz)
    return operand.astimezone(tz)


def _date_pattern(locale: Locale, fields: str, length: str) -> str:
    skeleton = _DATE_SKELETONS[(fields, length)]
    if skeleton.startswith("std:"):
        return locale.date_formats[skeleton[4:]].pattern
    if skeleton == "EEEE":
        return "EEEE"
    if skeleton not in locale.datetime_skeletons:
        skeleton = match_skeleton(skeleton, locale.datetime_skeletons, allow_different_fields=True)
    return locale.datetime_skeletons[skeleton].pattern


def _time_pattern(locale: Locale, precision: str, hour12: str | None, time_zone_style: str | None) -> str:
    if hour12 is None:
        # the locale's preferred hour cycle, taken from its standard short time format
        hour = "h" if "h" in locale.time_formats["short"].pattern else "H"
    else:
        hour = "h" if hour12 == "true" else "H"
    skeleton = hour + {"hour": "", "minute": "m", "second": "ms"}[precision]
    if skeleton not in locale.datetime_skeletons:
        skeleton = match_skeleton(skeleton, locale.datetime_skeletons, allow_different_fields=True)
    pattern = locale.datetime_skeletons[skeleton].pattern
    if time_zone_style == "short":
        pattern += " z"
    elif time_zone_style == "long":
        pattern += " zzzz"
    return pattern


def datetime_formatter(value: Any, locale: Locale, options: ResolvedOptions) -> str:
    operand, options = datetime_operand(value, options)
    if not isinstance(operand, dt.datetime):
        msg = f"Bad operand: :datetime requires a datetime, got {operand!r}"
        raise BadOperand(msg)
    fields = literal_option(options, "dateFields", DATE_FIELDS, "year-month-day") or "year-month-day"
    length = literal_option(options, "dateLength", DATE_LENGTH, "medium") or "medium"
    precision = literal_option(options, "timePrecision", TIME_PRECISION, "minute") or "minute"
    time_zone_style = literal_option(options, "timeZoneStyle", TIME_ZONE_STYLE, None)
    hour12 = choice_option(options, "hour12", HOUR12, None)
    operand = _apply_time_zone(operand, options)
    date_pattern = _date_pattern(locale, fields, length)
    time_pattern = _time_pattern(locale, precision, hour12, time_zone_style)
    # The locale's datetime format is a template like "{1}, {0}" ({1} = date, {0} = time)
    datetime_format = str(locale.datetime_formats[length]).replace("'", "")
    combined = datetime_format.replace("{1}", date_pattern).replace("{0}", time_pattern)
    return _format_datetime(operand, format=combined, locale=locale)


def date_formatter(value: Any, locale: Locale, options: ResolvedOptions) -> str:
    operand, options = datetime_operand(value, options)
    if not isinstance(operand, dt.date):  # datetime is a subclass of date
        msg = f"Bad operand: :date requires a date or datetime, got {operand!r}"
        raise BadOperand(msg)
    fields = literal_option(options, "fields", DATE_FIELDS, "year-month-day") or "year-month-day"
    length = literal_option(options, "length", DATE_LENGTH, "medium") or "medium"
    if isinstance(operand, dt.datetime):
        operand = _apply_time_zone(operand, options)
    return _format_datetime(operand, format=_date_pattern(locale, fields, length), locale=locale)


def time_formatter(value: Any, locale: Locale, options: ResolvedOptions) -> str:
    operand, options = datetime_operand(value, options)
    if not isinstance(operand, (dt.datetime, dt.time)):
        msg = f"Bad operand: :time requires a time or datetime, got {operand!r}"
        raise BadOperand(msg)
    precision = literal_option(options, "precision", TIME_PRECISION, "minute") or "minute"
    time_zone_style = literal_option(options, "timeZoneStyle", TIME_ZONE_STYLE, None)
    hour12 = choice_option(options, "hour12", HOUR12, None)
    pattern = _time_pattern(locale, precision, hour12, time_zone_style)
    if isinstance(operand, dt.datetime):
        return _format_datetime(_apply_time_zone(operand, options), format=pattern, locale=locale)
    return _format_time(operand, format=pattern, tzinfo=_time_zone(options, operand), locale=locale)


@dataclass(frozen=True)
class Registry:
    formatters: dict[str, Formatter] = field(default_factory=dict)
    selectors: dict[str, Selector] = field(default_factory=dict)
    markup: MarkupFormatter | None = None
    """How to format markup when formatting to a string; `None` formats all markup as an empty string."""

    def extend(
        self,
        *,
        formatters: dict[str, Formatter] | None = None,
        selectors: dict[str, Selector] | None = None,
        markup: MarkupFormatter | None = None,
    ) -> Self:
        return type(self)(
            formatters={**self.formatters, **(formatters or {})},
            selectors={**self.selectors, **(selectors or {})},
            markup=markup or self.markup,
        )


default_registry = Registry(
    formatters={
        "string": string_formatter,
        "number": number_formatter,
        "integer": integer_formatter,
        "offset": offset_formatter,
        "datetime": datetime_formatter,
        "date": date_formatter,
        "time": time_formatter,
    },
    selectors={
        "string": string_selector,
        "number": number_selector,
        "integer": integer_selector,
        "offset": offset_selector,
    },
)
"""The default registry of formatters and selectors."""

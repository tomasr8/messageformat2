import datetime as _datetime
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, Self

from babel import Locale
from babel.dates import format_date as _format_date
from babel.dates import format_datetime as _format_datetime
from babel.dates import format_time as _format_time
from babel.dates import match_skeleton
from babel.numbers import format_compact_decimal, format_decimal, format_percent, format_scientific

from messageformat2.errors import InvalidExpression


def format_skeleton(
    skeleton: str,
    dt: _datetime.datetime,
    locale: Locale,
) -> str:
    locale = Locale.parse(locale)
    matched = skeleton
    if skeleton not in locale.datetime_skeletons:
        matched = match_skeleton(
            skeleton,
            locale.datetime_skeletons,
            allow_different_fields=True)
    fmt = locale.datetime_skeletons[matched]
    return _format_datetime(dt, format=fmt, locale=locale)


class Formatter(Protocol):
    def __call__(self, value: Any, locale: Locale, options: dict[str, Any]) -> Any: ...


class Selector(Protocol):
    def __call__(self, value: Any, locale: Locale, options: dict[str, Any], keys: list[str]) -> list[str]: ...


def string_formatter(value: Any, locale: Locale, options: dict[str, Any]) -> str:  # noqa: ARG001
    return str(value)


def string_selector(value: Any, locale: Locale, options: dict[str, Any], keys: list[str]) -> list[str]:
    string = string_formatter(value, locale=locale, options=options)
    return [string] if string in keys else []


def format_number(  # noqa: PLR0913
    number: Any,
    *,
    locale: Locale,
    compactDisplay: Literal["short", "long"] = "short",
    notation: Literal["standard", "scientific", "engineering", "compact"] = "standard",
    numberingSystem: str = "default",
    signDisplay: Literal["auto", "always", "exceptZero", "negative", "never"] = "auto",  # noqa: ARG001
    style: Literal["decimal", "percent"] = "decimal",
    useGrouping: Literal["auto", "always", "never", "min2"] = "auto",
    minimumFractionDigits: int | None = None,  # noqa: ARG001
    maximumFractionDigits: int | None = None,  # noqa: ARG001
    **kwargs,  # noqa: ARG001
) -> str:
    if notation == "compact":
        # fraction_digits =
        return format_compact_decimal(
            number, format_type=compactDisplay, locale=locale, numbering_system=numberingSystem
        )
    if notation in ("scientific", "engineering"):
        # babel has 'format_engineering' method..
        return format_scientific(number, locale=locale, numbering_system=numberingSystem)
    group_separator = useGrouping != "never"
    if style == "percent":
        return format_percent(
            number,
            locale=locale,
            group_separator=group_separator,
            numbering_system=numberingSystem,
        )
    return format_decimal(number, locale=locale, group_separator=group_separator, numbering_system=numberingSystem)


def keyword_selector(
    number: float, *, locale: Locale, keys: list[str], select: Literal["exact", "plural", "ordinal"] = "plural"
) -> list[str]:
    if select == "plural":
        keyword = locale.plural_form(number)
    elif select == "ordinal":
        keyword = locale.ordinal_form(number)
    else:
        msg = f"Unknown select type: {select}"
        raise InvalidExpression(msg)

    return [keyword] if keyword in keys else []


def number_formatter(value: Any, locale: Locale, options: dict[str, Any]) -> str:
    return format_number(value, locale=locale, **options)


def number_selector(value: Any, locale: Locale, options: dict[str, Any], keys: list[str]) -> list[str]:
    select = options.get("select", "plural")
    number = format_number(value, locale=locale, **options)

    exact_keys = [number] if number in keys else []
    if select == "exact":
        return exact_keys
    keyword_keys = keyword_selector(value, locale=locale, keys=keys, select=select)
    return exact_keys + keyword_keys


def format_integer(  # noqa: PLR0913
    value: Any,
    *,
    locale: Locale,
    numberingSystem: str = "default",
    signDisplay: Literal["auto", "always", "exceptZero", "negative", "never"] = "auto",  # noqa: ARG001
    style: Literal["decimal", "percent"] = "decimal",
    useGrouping: Literal["auto", "always", "min2"] = "auto",  # noqa: ARG001
    minimumIntegerDigits: int | None = 1,  # noqa: ARG001
    maximumSignificantDigits: int | None = None,  # noqa: ARG001
    **kwargs,  # noqa: ARG001
) -> str:
    if style == "percent":
        return format_percent(
            value,
            locale=locale,
            numbering_system=numberingSystem,
        )
    if style == "decimal":
        return format_decimal(
            value,
            locale=locale,
            numbering_system=numberingSystem,
        )
    msg = f"Unknown style: {style}"
    raise InvalidExpression(msg)


def integer_formatter(value: Any, locale: Locale, options: dict[str, Any]) -> str:  # noqa: ARG001
    return str(int(value))


def integer_selector(value: Any, locale: Locale, options: dict[str, Any], keys: list[str]) -> list[str]:
    select = options.get("select", "plural")
    integer = format_integer(value, locale=locale, **options)

    exact_keys = [integer] if integer in keys else []
    if select == "exact":
        return exact_keys
    keyword_keys = keyword_selector(value, locale=locale, keys=keys, select=select)
    return exact_keys + keyword_keys


def format_datetime(  # noqa: PLR0915, PLR0913, PLR0912, C901
    dt: _datetime.datetime,
    locale: Locale,
    dateStyle: Literal["full", "long", "medium", "short"] | None = None,
    timeStyle: Literal["full", "long", "medium", "short"] | None = None,  # noqa: ARG001
    weekday: Literal["long", "short", "narrow"] | None = None,
    era: Literal["long", "short", "narrow"] | None = None,
    year: Literal["numeric", "2-digit"] | None = None,
    month: Literal["numeric", "2-digit", "long", "short", "narrow"] | None = None,
    day: Literal["numeric", "2-digit"] | None = None,
    hour: Literal["numeric", "2-digit"] | None = None,
    minute: Literal["numeric", "2-digit"] | None = None,
    second: Literal["numeric", "2-digit"] | None = None,
    fractionalSecondDigits: Literal["1", "2", "3"] | None = None,
    hourCycle: Literal["h11", "h12", "h23", "h24"] | None = None,
    timeZoneName: Literal["long", "short", "shortOffset", "longOffset", "shortGeneric", "longGeneric"] | None = None,  # noqa: ARG001
    **kwargs,  # noqa: ARG001
) -> str:
    if dateStyle:
        return _format_datetime(dt, format=dateStyle, locale=locale)

    skeleton = ""
    if weekday:
        if weekday == "short":
            skeleton += "EEE"
        elif weekday == "long":
            skeleton += "EEEE"
        else:
            skeleton += "EEEEE"
    if era:
        if era == "short":
            skeleton += "GGG"
        elif era == "long":
            skeleton += "GGGG"
        else:
            skeleton += "GGGGG"

    if year:
        if year == "numeric":
            skeleton += "y"
        else:
            skeleton += "yy"

    if month:
        if month == "numeric":
            skeleton += "M"
        elif month == "2-digit":
            skeleton += "MM"
        elif month == "short":
            skeleton += "MMM"
        elif month == "narrow":
            skeleton += "MMMMM"
        else:
            skeleton += "MMMM"

    if day:
        if day == "numeric":
            skeleton += "d"
        else:
            skeleton += "dd"

    if hour:
        h = "h"
        if hourCycle:
            if hourCycle == "h11":
                h = "K"
            elif hourCycle == "h12":
                h = "h"
            elif hourCycle == "h23":
                h = "H"
            elif hourCycle == "h24":
                h = "k"

        if hour == "numeric":
            skeleton += f"{h}"
        else:
            skeleton += f"{h}{h}"

    if minute:
        if minute == "numeric":
            skeleton += "m"
        else:
            skeleton += "mm"

    if second:
        if second == "numeric":
            skeleton += "s"
        else:
            skeleton += "ss"

    if fractionalSecondDigits:
        if fractionalSecondDigits == "1":
            skeleton += "S"
        elif fractionalSecondDigits == "2":
            skeleton += "SS"
        else:
            skeleton += "SSS"

    return format_skeleton(skeleton, dt, locale=locale)


def datetime_formatter(value: Any, locale: Locale, options: dict[str, Any]) -> str:
    if isinstance(value, str):
        value = _datetime.datetime.fromisoformat(value)
    return _format_datetime(value, locale=locale, **options)


def format_date(
    dt: _datetime.datetime,
    *,
    locale: Locale,
    style: Literal["full", "long", "medium", "short"] = "short",
    **kwargs,  # noqa: ARG001
) -> str:
    return _format_date(dt, format=style, locale=locale)


def date_formatter(value: Any, locale: Locale, options: dict[str, Any]) -> str:
    if isinstance(value, str):
        value = _datetime.datetime.fromisoformat(value)
    return format_date(value, locale=locale, **options)


def format_time(
    time: _datetime.time,
    *,
    locale: Locale,
    style: Literal["full", "long", "medium", "short"] = "short",
    **kwargs,  # noqa: ARG001
) -> str:
    return _format_time(time, format=style, locale=locale)


def time_formatter(value: Any, locale: Locale, options: dict[str, Any]) -> str:
    if isinstance(value, str):
        value = _datetime.datetime.fromisoformat(value)
    if isinstance(value, _datetime.datetime):
        value = value.time()
    return format_time(value, locale=locale, **options)


@dataclass(frozen=True)
class Registry:
    formatters: dict[str, Formatter] = field(default_factory=dict)
    selectors: dict[str, Selector] = field(default_factory=dict)

    def extend(
        self, *, formatters: dict[str, Formatter] | None = None, selectors: dict[str, Selector] | None = None
    ) -> Self:
        return type(self)(
            formatters={**self.formatters, **(formatters or {})},
            selectors={**self.selectors, **(selectors or {})},
        )


default_registry = Registry(
    formatters={
        "string": string_formatter,
        "number": number_formatter,
        "integer": integer_formatter,
        "datetime": datetime_formatter,
        "date": date_formatter,
        "time": time_formatter,
    },
    selectors={
        "string": string_selector,
        "number": number_selector,
        "integer": integer_selector,
    },
)
"""The default registry of formatters and selectors."""

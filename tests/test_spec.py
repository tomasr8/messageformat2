"""Run the official Unicode MessageFormat test suite (see tests/spec/README.md).

Every test case formats `src` with the given `params` and `locale` and expects either
the formatted string `exp` or at least one of the errors listed in `expErrors`.
Since this implementation raises on the first error, a test passes if the raised error
is one of the expected ones.
"""

import datetime as dt
import json
import math
import re
from pathlib import Path
from typing import Any

import pytest
from babel import Locale

from messageformat2 import Message
from messageformat2.builtins import Formatter, LazyValue, ResolvedOptions, Selector
from messageformat2.errors import (
    BadOperand,
    BadOption,
    BadSelector,
    BadVariantKey,
    DataModelError,
    DuplicateDeclaration,
    DuplicateOptionName,
    DuplicateVariant,
    MessageFormatError,
    MissingFallbackVariant,
    MissingSelectorAnnotation,
    ParseError,
    UnknownFunction,
    UnresolvedVariable,
    VariantKeyMismatch,
)


SPEC_DIR = Path(__file__).parent / "spec"

ERRORS = {
    "syntax-error": ParseError,
    "variant-key-mismatch": VariantKeyMismatch,
    "missing-fallback-variant": MissingFallbackVariant,
    "missing-selector-annotation": MissingSelectorAnnotation,
    "duplicate-declaration": DuplicateDeclaration,
    "duplicate-option-name": DuplicateOptionName,
    "duplicate-variant": DuplicateVariant,
    "unresolved-variable": UnresolvedVariable,
    "unknown-function": UnknownFunction,
    "bad-selector": BadSelector,
    "bad-operand": BadOperand,
    "bad-option": BadOption,
    "bad-variant-key": BadVariantKey,
}

# Optional features (test "tags") which are not implemented
UNSUPPORTED_TAGS = {":currency", ":percent", "u:dir", "u:id"}

# Bidi isolation of placeholders is not implemented: tests expecting it are compared without the isolates
BIDI_ISOLATES = re.compile("[" + chr(0x2066) + "-" + chr(0x2069) + "]")

NUMBER_LITERAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?$")


# The `:test:function`, `:test:select` and `:test:format` functions defined by the test suite
class TestValue:
    __test__ = False

    def __init__(self, value: float, decimal_places: int, fails_format: bool, fails_select: bool) -> None:  # noqa: FBT001
        self.value = value
        self.decimal_places = decimal_places
        self.fails_format = fails_format
        self.fails_select = fails_select


def resolve_test_value(value: Any, options: ResolvedOptions) -> TestValue:
    decimal_places, fails_format, fails_select = 0, False, False
    if isinstance(value, LazyValue):
        if not value.fn_name.startswith("test:"):
            msg = "bad operand"
            raise BadOperand(msg)
        value = resolve_test_value(value.value, value.options)
    if isinstance(value, TestValue):
        number, decimal_places = value.value, value.decimal_places
        fails_format, fails_select = value.fails_format, value.fails_select
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        number = value
    elif isinstance(value, str) and NUMBER_LITERAL.match(value):
        number = float(value)
    else:
        msg = "bad operand"
        raise BadOperand(msg)
    if "decimalPlaces" in options:
        if options["decimalPlaces"] in (0, 1, "0", "1"):
            decimal_places = int(options["decimalPlaces"])
        else:
            msg = "bad option"
            raise BadOption(msg)
    if "fails" in options:
        match options["fails"]:
            case "always":
                fails_format = fails_select = True
            case "format":
                fails_format = True
            case "select":
                fails_select = True
            case "never":
                pass
            case _:
                msg = "bad option"
                raise BadOption(msg)
    return TestValue(number, decimal_places, fails_format, fails_select)


def tf_formatter(value: Any, locale: Locale, options: ResolvedOptions) -> str:  # noqa: ARG001
    resolved = resolve_test_value(value, options)
    if resolved.fails_format:
        msg = "fails=format"
        raise BadOption(msg)
    magnitude = abs(resolved.value)
    formatted = ("-" if resolved.value < 0 else "") + str(math.floor(magnitude))
    if resolved.decimal_places == 1:
        formatted += "." + str(math.floor((magnitude - math.floor(magnitude)) * 10))
    return formatted


def tf_selector(value: Any, locale: Locale, options: ResolvedOptions, keys: list[str]) -> list[str]:  # noqa: ARG001
    resolved = resolve_test_value(value, options)
    if resolved.fails_select:
        msg = "fails=select"
        raise BadOption(msg)
    if resolved.value == 1:
        matching = ["1.0", "1"] if resolved.decimal_places == 1 else ["1"]
        return [key for key in matching if key in keys]
    return []


def not_formattable(value: Any, locale: Locale, options: ResolvedOptions) -> str:  # noqa: ARG001
    resolve_test_value(value, options)
    msg = "not-formattable"
    raise BadOption(msg)


def not_selectable(value: Any, locale: Locale, options: ResolvedOptions, keys: list[str]) -> list[str]:  # noqa: ARG001
    resolve_test_value(value, options)
    msg = "not-selectable"
    raise BadSelector(msg)


FORMATTERS: dict[str, Formatter] = {
    "test:function": tf_formatter,
    "test:format": tf_formatter,
    "test:select": not_formattable,
}
SELECTORS: dict[str, Selector] = {
    "test:function": tf_selector,
    "test:select": tf_selector,
    "test:format": not_selectable,
}


def load_tests() -> list[Any]:
    params = []
    for path in sorted(SPEC_DIR.glob("**/*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        defaults = data.get("defaultTestProperties", {})
        for i, test in enumerate(data["tests"]):
            test = {**defaults, **test}  # noqa: PLW2901
            marks = []
            if unsupported := UNSUPPORTED_TAGS & set(test.get("tags", [])):
                marks.append(pytest.mark.skip(reason=f"unsupported: {', '.join(sorted(unsupported))}"))
            name = f"{path.relative_to(SPEC_DIR)}[{i}] {test['src'][:60]}"
            params.append(pytest.param(test, id=name, marks=marks))
    return params


def run(test: dict[str, Any], on_error: Any = None) -> str:
    locale = test.get("locale", "en-US").replace("-", "_")
    if locale == "und":
        locale = "en"
    inputs = {}
    for param in test.get("params", []):
        value = param["value"]
        if param.get("type") == "datetime":
            value = dt.datetime.fromisoformat(value)
        inputs[param["name"]] = value
    return Message(test["src"]).format(inputs, locale, formatters=FORMATTERS, selectors=SELECTORS, on_error=on_error)


def expected_output(test: dict[str, Any]) -> str | None:
    expected = test.get("exp")
    if expected is not None and test.get("bidiIsolation") == "default":
        expected = BIDI_ISOLATES.sub("", expected)
    return expected


@pytest.mark.parametrize("test", load_tests())
def test_spec_strict(test: dict[str, Any]) -> None:
    """Strict mode: the first error is raised and must be one of the expected ones."""
    expected_errors = [ERRORS[error["type"]] for error in test.get("expErrors", [])]
    try:
        formatted = run(test)
    except MessageFormatError as e:
        error = e
    else:
        assert not expected_errors, f"expected one of {expected_errors}, got {formatted!r}"
        expected = expected_output(test)
        if expected is not None:
            assert formatted == expected
        return
    assert expected_errors, f"unexpected error: {error!r}"
    assert isinstance(error, tuple(expected_errors)), f"got {error!r}, expected one of {expected_errors}"


@pytest.mark.parametrize("test", load_tests())
def test_spec_fallback(test: dict[str, Any]) -> None:
    """Fallback mode: errors are collected, the output must match `exp` (with fallback values) exactly."""
    expected_errors = {ERRORS[error["type"]] for error in test.get("expErrors", [])}
    errors: list[MessageFormatError] = []
    try:
        formatted = run(test, on_error=errors.append)
    except (ParseError, DataModelError) as e:  # syntax and data model errors are always raised
        error = e
    else:
        error = None
    if error is not None:
        assert type(error) in expected_errors, f"got {error!r}, expected one of {expected_errors}"
        return
    if expected_errors:
        assert errors, f"expected one of {expected_errors}, got {formatted!r} without errors"
        assert expected_errors & {type(e) for e in errors}, f"got {errors!r}, expected one of {expected_errors}"
    else:
        assert not errors, f"unexpected errors: {errors!r}"
    expected = expected_output(test)
    if expected is not None:
        assert formatted == expected

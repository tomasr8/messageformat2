import datetime as dt
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from typing import Literal as TypingLiteral

from babel import Locale

from messageformat2.builtins import Direction, FormattedValue, LazyValue, Registry, ResolvedOptions
from messageformat2.errors import (
    BadOption,
    BadSelector,
    MessageFormatError,
    MessageFunctionError,
    UnknownFunction,
    UnresolvedVariable,
)
from messageformat2.parser import (
    CatchallKey,
    Expression,
    FunctionAnnotation,
    FunctionExpression,
    InputDeclaration,
    Literal,
    LiteralExpression,
    Markup,
    Message,
    Option,
    Pattern,
    PatternMessage,
    SelectMessage,
    VariableExpression,
    VariableRef,
    Variant,
)


@dataclass
class Fallback:
    """The resolved value of an expression or variable which failed to resolve or format.

    `source` is the string representation of the failed part: `$name` for a variable, `|literal|` for a literal
    operand and `:function` for a function expression. It is formatted as `{source}`.
    """

    source: str

    def __str__(self) -> str:
        return f"{{{self.source}}}"


LRI, RLI, FSI, PDI = "\u2066", "\u2067", "\u2068", "\u2069"
U_DIR_VALUES = ("ltr", "rtl", "auto", "inherit")


@dataclass
class FormattingContext:
    locale: Locale
    inputs: dict[str, Any]
    registry: Registry
    declarations: dict[str, Any]
    resolved: dict[str, Any] = field(default_factory=dict)
    """The resolved values of the declared variables which have been referenced so far."""
    on_error: Callable[[MessageFormatError], None] | None = None
    """Error sink. If None, the first error is raised; otherwise errors are reported and fallback values used."""
    bidi_isolation: bool = False
    """The bidirectional isolation strategy: isolate placeholders with Unicode isolate controls, or not at all."""

    @property
    def direction(self) -> Direction:
        """The directionality of the message as a whole, taken from the locale."""
        return self.locale.text_direction  # type: ignore[return-value]  # ty: ignore[invalid-return-type]

    def emit[T](self, error: MessageFormatError, fallback: T) -> T:
        """Report an error: raise it in strict mode, otherwise pass it to `on_error` and return `fallback`."""
        if self.on_error is None:
            raise error
        self.on_error(error)
        return fallback


def format_message(  # noqa: PLR0913
    message: Message,
    locale: Locale,
    inputs: dict[str, Any],
    registry: Registry,
    *,
    on_error: Callable[[MessageFormatError], None] | None = None,
    bidi_isolation: bool = False,
) -> str:
    ctx = FormattingContext(
        locale=locale,
        inputs=inputs,
        registry=registry,
        declarations={},
        on_error=on_error,
        bidi_isolation=bidi_isolation,
    )
    match message:
        case PatternMessage():
            return format_pattern_message(message, ctx)
        case _:
            return format_select_message(message, ctx)


def format_pattern_message(message: PatternMessage, ctx: FormattingContext) -> str:
    for decl in message.declarations:
        ctx.declarations[decl.name] = decl
    return format_pattern(message.pattern, ctx)


def format_pattern(pattern: Pattern, ctx: FormattingContext) -> str:
    output = ""
    for part in pattern:
        match part:
            case str():
                output += part
            case LiteralExpression() | VariableExpression() | FunctionExpression():
                output += format_expression(part, ctx)
            case Markup():
                output += format_markup(part, ctx)
    return output


def format_select_message(message: SelectMessage, ctx: FormattingContext) -> str:
    for decl in message.declarations:
        ctx.declarations[decl.name] = decl

    # Resolve Selectors: for each selector, the keys it matches, best match first
    matches: list[list[str]] = []
    for i, selector in enumerate(message.selectors):
        keys = [key.value for v in message.variants if isinstance(key := v.keys[i], Literal)]
        matches.append(select_keys(selector, keys, ctx))

    # Compare Variants: keep the best of the matching variants, in source order
    best: Variant | None = None
    for variant in message.variants:
        if not selectors_match(matches, variant.keys):
            continue
        if best is None or selectors_compare(matches, variant.keys, best.keys):
            best = variant
    assert best is not None  # guaranteed by the Missing Fallback Variant check
    return format_pattern(best.value, ctx)


def selectors_match(matches: list[list[str]], keys: list[Literal | CatchallKey]) -> bool:
    """Whether every key of a variant is the catch-all or matched by its selector."""
    return all(
        isinstance(key, CatchallKey) or key.value in selector for selector, key in zip(matches, keys, strict=True)
    )


def selectors_compare(
    matches: list[list[str]], keys1: list[Literal | CatchallKey], keys2: list[Literal | CatchallKey]
) -> bool:
    """Whether the (matching) keys `keys1` are a better match than `keys2`.

    Keys are compared selector by selector: a literal key beats the catch-all, and a key earlier in the
    selector's list of matches beats a later one. The first difference decides.
    """
    for selector, key1, key2 in zip(matches, keys1, keys2, strict=True):
        if isinstance(key1, CatchallKey) and isinstance(key2, CatchallKey):
            continue
        if isinstance(key1, CatchallKey):
            return False
        if isinstance(key2, CatchallKey):
            return True
        if (rank := selector.index(key1.value)) != (other := selector.index(key2.value)):
            return rank < other
    return False


def select_keys(selector: VariableRef, keys: list[str], ctx: FormattingContext) -> list[str]:
    """Return the keys matched by a selector, best match first.

    When the selector cannot be resolved or fails, a Bad Selector error is emitted and no key matches
    (so only the catch-all `*` variants remain).
    """
    resolved = resolve_variable(selector.name, ctx)
    if not isinstance(resolved, LazyValue):
        msg = f"Bad selector: ${selector.name} does not support selection"
        return ctx.emit(BadSelector(msg), [])
    try:
        return resolved.select(keys)
    except BadSelector as e:
        if ctx.on_error is not None and isinstance(e.__cause__, MessageFunctionError):
            ctx.on_error(e.__cause__)
        return ctx.emit(e, [])


def format_expression(expression: Expression, ctx: FormattingContext) -> str:
    resolved = resolve_expression(expression, ctx)
    match expression:
        case VariableExpression(annotation=None):
            resolved = apply_default_function(resolved, ctx)
    if not isinstance(resolved, LazyValue):
        # literals, unannotated input values and fallback values have an unknown direction
        return bidi_isolate(FormattedValue(str(resolved)), ctx, isolate=False)
    try:
        formatted = resolved.formatted()
    except MessageFormatError as e:
        formatted = FormattedValue(str(ctx.emit(e, Fallback(expression_source(expression)))))
    # `u:dir` (other than `inherit`) requests isolation even when the directions match
    return bidi_isolate(formatted, ctx, isolate=resolved.u_dir is not None)


def bidi_isolate(formatted: FormattedValue, ctx: FormattingContext, *, isolate: bool) -> str:
    """Apply the Default Bidi Strategy: wrap a formatted placeholder in Unicode isolate controls.

    A value whose direction matches the message's needs no isolation (unless requested with `u:dir`); a value
    with the opposite direction is wrapped in LRI/RLI, a value of unknown direction in FSI.
    """
    if not ctx.bidi_isolation:
        return formatted.text
    if formatted.direction == "ltr":
        if ctx.direction == "ltr" and not isolate:
            return formatted.text
        return LRI + formatted.text + PDI
    if formatted.direction == "rtl":
        return RLI + formatted.text + PDI
    return FSI + formatted.text + PDI


def expression_source(expression: Expression) -> str:
    """The fallback representation of an expression: its operand, or the function if it has no operand."""
    match expression:
        case LiteralExpression(arg=literal):
            return str(literal)
        case VariableExpression(arg=VariableRef(name=name)):
            return f"${name}"
        case FunctionExpression(annotation=FunctionAnnotation(name=name)):
            return f":{name}"
    raise TypeError(expression)


def apply_default_function(resolved: Any, ctx: FormattingContext) -> Any:
    """Format an unannotated variable according to its type, e.g. a number as if it were annotated with `:number`."""
    if isinstance(resolved, bool):
        return resolved
    if isinstance(resolved, (int, float, Decimal)):
        fn_name = "number"
    elif isinstance(resolved, dt.datetime):
        fn_name = "datetime"
    elif isinstance(resolved, dt.date):
        fn_name = "date"
    elif isinstance(resolved, dt.time):
        fn_name = "time"
    else:
        return resolved
    if fn_name not in ctx.registry.formatters:
        return resolved
    return LazyValue(fn_name=fn_name, value=resolved, options=ResolvedOptions(), ctx=ctx)


def format_markup(markup: Markup, ctx: FormattingContext) -> str:
    # Markup resolution always succeeds: errors from option resolution are reported but non-fatal
    options = resolve_options(markup.options, ctx)
    process_u_options(options, ctx, markup=True)
    # When formatting to a string, the default representation of all markup is an empty string
    if ctx.registry.markup is None:
        return ""
    return ctx.registry.markup(markup.kind, markup.name, options)


def resolve_options(options: list[Option], ctx: FormattingContext) -> ResolvedOptions:
    # An option whose value is a fallback value is omitted from the resolved options
    values = {opt.name: resolve_option(opt, ctx) for opt in options}
    return ResolvedOptions(
        {name: value for name, value in values.items() if not isinstance(value, Fallback)},
        literal=frozenset(opt.name for opt in options if isinstance(opt.value, Literal)),
    )


def resolve_option(option: Option, ctx: FormattingContext) -> Any:
    match option.value:
        case Literal(value=value):
            return value
        case VariableRef(name=name):
            resolved = resolve_variable(name, ctx)
            if isinstance(resolved, LazyValue):
                try:
                    return resolved.format()
                except MessageFormatError as e:
                    resolved = ctx.emit(e, Fallback(f"${name}"))
            if isinstance(resolved, Fallback):
                msg = f"Bad option: the value of the option {option.name!r} (${name}) could not be resolved"
                return ctx.emit(BadOption(msg), resolved)
            return resolved


def annotate(resolved: Any, fn_name: str, options: ResolvedOptions, source: str, ctx: FormattingContext) -> Any:
    """Apply the function `fn_name` to a resolved value (function resolution).

    If the value is already annotated (a `LazyValue`), it is passed to the function handler as its operand:
    whether and how the options of the operand are inherited is up to the function.
    An unknown function is an Unknown Function error; if the operand is a fallback value or the function
    is unknown, the resolved value is a fallback value with the given `source`.
    """
    if fn_name not in ctx.registry.formatters and fn_name not in ctx.registry.selectors:
        msg = f"Unknown function: {fn_name}"
        return ctx.emit(UnknownFunction(msg), Fallback(source))
    if isinstance(resolved, Fallback):
        return Fallback(source)
    u_dir = process_u_options(options, ctx, markup=False)
    return LazyValue(fn_name=fn_name, value=resolved, options=options, ctx=ctx, u_dir=u_dir)


def process_u_options(
    options: ResolvedOptions, ctx: FormattingContext, *, markup: bool
) -> TypingLiteral["ltr", "rtl", "auto"] | None:
    """Process and remove the `u:` namespace options, which apply to all functions and markup.

    `u:dir` sets the directionality of the expression's value (and requests its isolation); it is not allowed
    on markup. `u:id` is validated but has no effect when formatting to a string. Returns the `u:dir` value.
    """
    u_dir = None
    if "u:dir" in options:
        value = options.pop("u:dir")
        if markup:
            msg = "Bad option: u:dir is not allowed on markup"
            ctx.emit(BadOption(msg), None)
        elif value not in U_DIR_VALUES:
            msg = f"Bad option: u:dir={value!r} is not one of {list(U_DIR_VALUES)}"
            ctx.emit(BadOption(msg), None)
        elif value != "inherit":
            u_dir = value
    if "u:id" in options:
        value = options.pop("u:id")
        if not isinstance(value, str):
            msg = f"Bad option: u:id={value!r} is not a string"
            ctx.emit(BadOption(msg), None)
    return u_dir


def resolve_expression(expression: Expression, ctx: FormattingContext) -> Any | LazyValue:
    match expression:
        case LiteralExpression(arg=Literal(value), annotation=annotation):
            if not annotation:
                return value
            options = resolve_options(annotation.options, ctx)
            return annotate(value, annotation.name, options, expression_source(expression), ctx)
        case VariableExpression(arg=VariableRef(ref), annotation=annotation):
            if not annotation:
                return resolve_variable(ref, ctx)
            resolved = resolve_variable(ref, ctx)
            options = resolve_options(annotation.options, ctx)
            return annotate(resolved, annotation.name, options, f"${ref}", ctx)
        case FunctionExpression(annotation=FunctionAnnotation(name=name, options=options)):
            options = resolve_options(options, ctx)
            return annotate(None, name, options, f":{name}", ctx)


def resolve_variable(name: str, ctx: FormattingContext) -> Any:
    if name not in ctx.declarations:
        return resolve_global(name, ctx)
    # A declaration is resolved (and its errors reported) once, however often the variable is referenced
    if name not in ctx.resolved:
        ctx.resolved[name] = resolve_declaration(name, ctx)
    return ctx.resolved[name]


def resolve_declaration(name: str, ctx: FormattingContext) -> Any:
    match ctx.declarations[name]:
        case InputDeclaration(value=VariableExpression(annotation=annotation)):
            resolved = resolve_global(name, ctx)
            if not annotation:
                return resolved
            options = resolve_options(annotation.options, ctx)
            return annotate(resolved, annotation.name, options, f"${name}", ctx)
        case decl:
            resolved = resolve_expression(decl.value, ctx)
            # The fallback value of a variable is `$name`, whatever the declaration contained
            return Fallback(f"${name}") if isinstance(resolved, Fallback) else resolved


def resolve_global(name: str, ctx: FormattingContext) -> Any:
    if name in ctx.inputs:
        return ctx.inputs[name]
    # Variable names are compared after NFC normalization; `name` is already normalized by the parser
    for key, value in ctx.inputs.items():
        if unicodedata.normalize("NFC", key) == name:
            return value
    msg = f"Unresolved variable: {name}"
    return ctx.emit(UnresolvedVariable(msg), Fallback(f"${name}"))

import datetime as dt
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from babel import Locale

from messageformat2.builtins import LazyValue, Registry, ResolvedOptions
from messageformat2.errors import (
    BadSelector,
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
class FormattingContext:
    locale: Locale
    inputs: dict[str, Any]
    registry: Registry
    declarations: dict[str, Any]
    strict: bool = True


def format_message(message: Message, locale: Locale, inputs: dict[str, Any], registry: Registry) -> str:
    ctx = FormattingContext(
        locale=locale,
        inputs=inputs,
        registry=registry,
        declarations={},
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

    selectors = [resolve_selector(selector, ctx) for selector in message.selectors]

    pref = []
    for i, selector in enumerate(selectors):
        keys = [key.value for v in message.variants if isinstance(key := v.keys[i], Literal)]
        pref.append(selector.select(keys))

    variants = filter_variants(pref, message.variants)
    pattern = sort_variants(pref, variants)
    return format_pattern(pattern, ctx)


def filter_variants(pref: list, variants: list[Variant]) -> list[Variant]:
    filtered = []
    for v in variants:
        include = True
        for i, matches in enumerate(pref):
            key = v.keys[i]
            if isinstance(key, CatchallKey):
                continue
            assert isinstance(key, Literal)
            ks = key.value
            if ks not in matches:
                include = False
        if include:
            filtered.append(v)
    return filtered


def sort_variants(pref: list, variants: list[Variant]) -> Pattern:
    sortable = [[-1, v] for v in variants]

    i = len(pref) - 1
    while i >= 0:
        matches = pref[i]
        minpref = len(matches)
        for s in sortable:
            matchpref = minpref
            key = s[1].keys[i]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
            if not isinstance(key, CatchallKey):
                assert isinstance(key, Literal)
                ks = key.value
                matchpref = matches.index(ks)
            s[0] = matchpref
        sortable.sort(key=lambda x: x[0])
        i = i - 1
    return sortable[0][1].value  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]


def resolve_selector(selector: VariableRef, ctx: FormattingContext) -> LazyValue:
    resolved = resolve_variable(selector.name, ctx)
    if not isinstance(resolved, LazyValue):
        msg = f"Bad selector: ${selector.name} does not support selection"
        raise BadSelector(msg)
    return resolved


def format_expression(expression: Expression, ctx: FormattingContext) -> str:
    resolved = resolve_expression(expression, ctx)
    match expression:
        case VariableExpression(annotation=None):
            resolved = apply_default_function(resolved, ctx)
    return str(resolved)


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
    # When formatting to a string, the default representation of all markup is an empty string
    if ctx.registry.markup is None:
        return ""
    return ctx.registry.markup(markup.kind, markup.name, resolve_options(markup.options, ctx))


def resolve_options(options: list[Option], ctx: FormattingContext) -> ResolvedOptions:
    return ResolvedOptions({opt.name: resolve_option(opt, ctx) for opt in options})


def resolve_option(option: Option, ctx: FormattingContext) -> Any:
    match option.value:
        case Literal(value=value):
            return value
        case VariableRef(name=name):
            resolved = resolve_variable(name, ctx)
            match resolved:
                case LazyValue() as lazy_value:
                    return lazy_value.format()
                case _:
                    return resolved


def annotate(resolved: Any, fn_name: str, options: ResolvedOptions, ctx: FormattingContext) -> LazyValue:
    """Apply the function `fn_name` to a resolved value.

    If the value is already annotated (a `LazyValue`), it is passed to the function handler as its operand:
    whether and how the options of the operand are inherited is up to the function.
    """
    return LazyValue(fn_name=fn_name, value=resolved, options=options, ctx=ctx)


def resolve_expression(expression: Expression, ctx: FormattingContext) -> Any | LazyValue:
    match expression:
        case LiteralExpression(arg=Literal(value), annotation=annotation):
            if not annotation:
                return value
            options = resolve_options(annotation.options, ctx)
            return LazyValue(fn_name=annotation.name, value=value, options=options, ctx=ctx)
        case VariableExpression(arg=VariableRef(ref), annotation=annotation):
            if not annotation:
                return resolve_variable(ref, ctx)
            resolved = resolve_variable(ref, ctx)
            options = resolve_options(annotation.options, ctx)
            return annotate(resolved, annotation.name, options, ctx)
        case FunctionExpression(annotation=FunctionAnnotation(name=name, options=options)):
            options = resolve_options(options, ctx)
            return LazyValue(fn_name=name, value=None, options=options, ctx=ctx)


def resolve_variable(name: str, ctx: FormattingContext) -> Any:
    if name in ctx.declarations:
        decl = ctx.declarations[name]
        match decl:
            case InputDeclaration(value=VariableExpression(annotation=annotation)):
                resolved = resolve_global(name, ctx)
                if not annotation:
                    return resolved
                options = resolve_options(annotation.options, ctx)
                return annotate(resolved, annotation.name, options, ctx)
            case _:
                expression = decl.value
                return resolve_expression(expression, ctx)
    return resolve_global(name, ctx)


def resolve_global(name: str, ctx: FormattingContext) -> Any:
    if name in ctx.inputs:
        return ctx.inputs[name]
    # Variable names are compared after NFC normalization; `name` is already normalized by the parser
    for key, value in ctx.inputs.items():
        if unicodedata.normalize("NFC", key) == name:
            return value
    msg = f"Unresolved variable: {name}"
    raise UnresolvedVariable(msg)

from dataclasses import dataclass
from typing import Any

from babel import Locale

from messageformat2.builtins import Registry
from messageformat2.errors import (
    InvalidExpression,
    SelectionError,
    UnknownFunction,
    UnresolvedVariable,
    UnsupportedExpression,
    UnsupportedStatement,
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
    UnsupportedAnnotation,
    VariableExpression,
    VariableRef,
    Variant,
)
from messageformat2.parser import (
    UnsupportedExpression as _UnsupportedExpression,
)
from messageformat2.parser import UnsupportedStatement as _UnsupportedStatement


@dataclass
class FormattingContext:
    locale: Locale
    inputs: dict[str, Any]
    registry: Registry
    declarations: dict[str, Any]
    strict: bool = True


class LazyValue:
    def __init__(self, *, fn_name: str, value: Any = None, options: dict[str, Any] | None = None):
        self.fn_name = fn_name
        self.value = value
        self.options = options or {}

    def format(self, ctx: FormattingContext) -> str:
        if annotation := ctx.registry.formatters.get(self.fn_name):
            try:
                return str(annotation(value=self.value, locale=ctx.locale, options=self.options))
            except InvalidExpression:
                raise
            except Exception as e:
                msg = "Exception raised while evaluating formatter"
                raise InvalidExpression(msg) from e
        msg = f"Unknown function: {self.fn_name}"
        raise UnknownFunction(msg)

    def select(self, ctx: FormattingContext, *, keys: list[str]) -> list[str]:
        if selector := ctx.registry.selectors.get(self.fn_name):
            try:
                return selector(value=self.value, locale=ctx.locale, options=self.options, keys=keys)
            except SelectionError:
                raise
            except Exception as e:
                msg = "Exception raised while evaluating selector"
                raise SelectionError(msg) from e
        msg = f"Unknown selector: {self.fn_name}"
        raise UnknownFunction(msg)

    def __repr__(self):
        return f"LazyValue({self.fn_name}({self.value}, {self.options}))"


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
        match decl:
            case _UnsupportedStatement():
                msg = "Unsupported statement"
                raise UnsupportedStatement(msg)
            case _:
                ctx.declarations[decl.name] = decl
    return format_pattern(message.pattern, ctx)


def format_pattern(pattern: Pattern, ctx: FormattingContext) -> str:
    output = ""
    for part in pattern:
        match part:
            case str():
                output += part
            case LiteralExpression() | VariableExpression() | FunctionExpression() | _UnsupportedExpression():
                output += format_expression(part, ctx)
            case Markup():
                output += format_markup(part, ctx)
    return output


def format_select_message(message: SelectMessage, ctx: FormattingContext) -> str:
    for decl in message.declarations:
        match decl:
            case _UnsupportedStatement():
                msg = "Unsupported statement"
                raise UnsupportedStatement(msg)
            case _:
                ctx.declarations[decl.name] = decl

    selectors = [resolve_selector(selector, ctx) for selector in message.selectors]

    pref = []
    for i, selector in enumerate(selectors):
        keys = [key.value for v in message.variants if isinstance(key := v.keys[i], Literal)]
        pref.append(selector.select(ctx, keys=keys))

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
            key = s[1].keys[i]
            if not isinstance(key, CatchallKey):
                assert isinstance(key, Literal)
                ks = key.value
                matchpref = matches.index(ks)
            s[0] = matchpref
        sortable.sort(key=lambda x: x[0])
        i = i - 1
    return sortable[0][1].value


def resolve_selector(selector: Expression, ctx: FormattingContext) -> Any | LazyValue:
    return resolve_expression(selector, ctx)


def format_expression(expression: Expression, ctx: FormattingContext) -> str:
    resolved = resolve_expression(expression, ctx)
    match resolved:
        case LazyValue() as lazy_value:
            return lazy_value.format(ctx)
        case _:
            return str(resolved)


def format_markup(markup: Markup, ctx: FormattingContext) -> str:
    options = format_options(markup.options, ctx)
    options = f" {options}" if options else ""

    if markup.kind == "standalone":
        return f"<{markup.name}{options}/>"
    if markup.kind == "open":
        return f"<{markup.name}{options}>"
    return f"</{markup.name}{options}>"


def format_options(options: list[Option], ctx: FormattingContext) -> str:
    return " ".join(format_option(opt, ctx) for opt in options)


def format_option(option: Option, ctx: FormattingContext) -> str:
    value = resolve_option(option, ctx)
    return f"{option.name}={value}"


def resolve_options(options: list[Option], ctx: FormattingContext) -> dict[str, Any]:
    return {opt.name: resolve_option(opt, ctx) for opt in options}


def resolve_option(option: Option, ctx: FormattingContext) -> Any:
    match option.value:
        case Literal(value=value):
            return value
        case VariableRef(name=name):
            resolved = resolve_variable(name, ctx)
            match resolved:
                case LazyValue() as lazy_value:
                    return lazy_value.format(ctx)
                case _:
                    return resolved


def resolve_expression(expression: Expression, ctx: FormattingContext) -> Any | LazyValue:
    match expression:
        case LiteralExpression(arg=Literal(value), annotation=annotation):
            if not annotation:
                return value
            match annotation:
                case FunctionAnnotation(name=name, options=options):
                    options = resolve_options(options, ctx)
                    return LazyValue(fn_name=name, value=value, options=options)
                case UnsupportedAnnotation():
                    msg = "Unsupported expression"
                    raise UnsupportedExpression(msg)
        case VariableExpression(arg=VariableRef(ref), annotation=annotation):
            if not annotation:
                return resolve_variable(ref, ctx)
            match annotation:
                case FunctionAnnotation(name=name, options=options):
                    resolved = resolve_variable(ref, ctx)
                    options = resolve_options(options, ctx)
                    match resolved:
                        case LazyValue(fn_name=lazy_function, value=lazy_value, options=lazy_options):
                            if lazy_function and lazy_function != name:
                                msg = f"Function mismatch: {lazy_function} != {name}"
                                raise ValueError(msg)
                            return LazyValue(fn_name=name, value=lazy_value, options=(lazy_options or {}) | options)
                        case _:
                            return LazyValue(fn_name=name, value=resolved, options=options)
                case UnsupportedAnnotation():
                    msg = "Unsupported expression"
                    raise UnsupportedExpression(msg)
        case FunctionExpression(annotation=FunctionAnnotation(name=name, options=options)):
            options = resolve_options(options, ctx)
            return LazyValue(fn_name=name, value=None, options=options)
        case _UnsupportedExpression(annotation=annotation):
            msg = f"Unsupported expression: {annotation}"
            raise UnsupportedExpression(msg)


def resolve_variable(name: str, ctx: FormattingContext) -> Any:
    if name in ctx.declarations:
        decl = ctx.declarations[name]
        match decl:
            case InputDeclaration(value=VariableExpression(annotation=annotation)):
                if not annotation:
                    return resolve_global(name, ctx)
                match annotation:
                    case FunctionAnnotation(name=fn_name, options=options):
                        resolved = resolve_global(name, ctx)
                        options = resolve_options(options, ctx)
                        match resolved:
                            case LazyValue(fn_name=lazy_fn_name, value=lazy_value, options=lazy_options):
                                if lazy_fn_name and lazy_fn_name != fn_name:
                                    msg = f"Function mismatch: {lazy_fn_name} != {fn_name}"
                                    raise ValueError(msg)
                                return LazyValue(
                                    fn_name=fn_name, value=lazy_value, options=(lazy_options or {}) | options
                                )
                            case _:
                                return LazyValue(fn_name=fn_name, value=resolved, options=options)
                    case UnsupportedAnnotation(annotation=annotation):
                        msg = f"Unsupported expression: {annotation}"
                        raise UnsupportedExpression(msg)
            case _:
                expression = decl.value
                return resolve_expression(expression, ctx)
    return resolve_global(name, ctx)


def resolve_global(name: str, ctx: FormattingContext) -> Any:
    if name in ctx.inputs:
        return ctx.inputs[name]
    msg = f"Unresolved variable: {name}"
    raise UnresolvedVariable(msg)

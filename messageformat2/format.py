from dataclasses import dataclass
from typing import Any, Self

from messageformat2.parse import (
    Expression,
    FunctionAnnotation,
    FunctionExpression,
    InputDeclaration,
    Literal,
    LiteralExpression,
    LocalDeclaration,
    Markup,
    Message,
    Option,
    PatternMessage,
    VariableExpression,
    VariableRef,
    CatchallKey,
)


class FormatError(Exception):
    pass


class SelectionError(FormatError):
    pass


@dataclass
class MessageContext:
    registry: dict[str, callable]
    input_mapping: dict[str, Any]
    declarations: dict[str, Any]


def integer(value: Any, **kwargs) -> int:
    return value


def integer_selector(value: Any, keys: list[str], **kwargs):
    value = int(value)

    matches = []
    if integer(value) in keys:
        matches.append(integer(value))

    if value == 1:
        matches.append("one")
    elif value >= 2 and value <= 4:
        matches.append("few")
    else:
        matches.append("many")
    return matches


class IntermediateValue:
    def __init__(
        self,
        value: VariableRef | Literal | None = None,
        fn: str | None = None,
        options: dict[str, Any] | None = None,
    ):
        self.value = value
        self.fn = fn
        self.options = options

    def extend(self, fn: str | None = None, options: dict[str, Any] | None = None) -> Self:
        if self.fn and fn:
            assert self.fn == fn, f"{self.fn} != {fn}"
        return IntermediateValue(
            value=self.value,
            fn=self.fn or fn,
            options=(self.options or {}) | (options or {}),
        )

    def format(self, ctx: MessageContext) -> str:
        if self.fn:
            return ctx.registry[self.fn](self.value, **self.options)
        return str(self.value)

    def __repr__(self) -> str:
        return f"IntermediateValue(value={self.value}, fn={self.fn}, options={self.options})"


def format_message(message: Message, registry, input_mapping):
    ctx = MessageContext(
        registry=registry,
        input_mapping=input_mapping,
        declarations={},
    )
    match message:
        case PatternMessage():
            return format_pattern_message(message, ctx)
        case _:
            return format_select_message(message, ctx)


def format_pattern_message(message: PatternMessage, ctx: MessageContext):
    output = ""
    for decl in message.declarations:
        ctx.declarations[decl.name] = decl
    for part in message.pattern:
        match part:
            case str():
                output += part
            case LiteralExpression() | VariableExpression() | FunctionExpression():
                output += format_expression(part, ctx)
            case Markup():
                output += format_markup(part, ctx)
    return output


def format_select_message(message: Message, ctx: MessageContext):
    output = ""
    for decl in message.declarations:
        ctx.declarations[decl.name] = decl

    # print("SELECTORS", message.selectors)
    selectors = [resolve_selector(selector, ctx) for selector in message.selectors]

    pref = []
    for i, sel in enumerate(selectors):
        keys = [v.keys[i] for v in message.variants if isinstance(v.keys[i], Literal)]
        # print("KEYS", keys)
        # print("SEL", sel)
        pref.append(ctx.registry[sel.fn](sel.value, keys, **sel.options))
    # print("PREF", pref)

    variants = []
    # print("MSG VARIANTS", len(message.variants))
    for v in message.variants:
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
            variants.append(v)
    # print("VARIANTS", len(variants))

    sortable = []
    for v in message.variants:
        sortable.append([-1, v])
    # print("SORTABLE", sortable)

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

    pattern = sortable[0][1].value
    for part in pattern:
        match part:
            case str():
                output += part
            case LiteralExpression() | VariableExpression() | FunctionExpression():
                output += format_expression(part, ctx)
            case Markup():
                output += format_markup(part, ctx)

    return output


def resolve_selector(selector: Expression, ctx: MessageContext):
    match selector:
        case LiteralExpression(arg=Literal(value), annotation=annotation):
            if not annotation:
                raise SelectionError("Selection not supported for this expression")
            match annotation:
                case FunctionAnnotation(name, options):
                    options = resolve_options(options, ctx)
                    return IntermediateValue(value, name, options)
                case _:
                    raise ValueError(f"Unsupported annotation: {annotation}")
        case VariableExpression(arg=VariableRef(name), annotation=annotation):
            if not annotation:
                raise SelectionError("Selection not supported for this expression")
            match annotation:
                case FunctionAnnotation(name=fn, options=options):
                    options = resolve_options(options, ctx)
                    return resolve_variable(name, ctx).extend(fn, options)
                case _:
                    raise ValueError(f"Unsupported annotation: {annotation}")
        case FunctionExpression(annotation=FunctionAnnotation(name, options)):
            options = resolve_options(options, ctx)
            return IntermediateValue(value, name, options)


def format_expression(expression: Expression, ctx: MessageContext):
    match expression:
        case LiteralExpression(arg=Literal(value), annotation=annotation):
            if not annotation:
                return value
            match annotation:
                case FunctionAnnotation(name, options):
                    options = resolve_options(options, ctx)
                    return ctx.registry[name](value, **options)
                case _:
                    raise ValueError(f"Unsupported annotation: {annotation}")
        case VariableExpression(arg=VariableRef(name), annotation=annotation):
            res = resolve_variable(name, ctx)
            return res.format(ctx)
        case FunctionExpression(annotation=FunctionAnnotation(name, options)):
            options = resolve_options(options, ctx)
            return ctx.registry[name](**options)


def format_markup(markup: Markup, ctx: MessageContext):
    options = format_options(markup.options, ctx)
    options = f" {options}" if options else ""

    if markup.kind == "standalone":
        return f"<{markup.name}{options}/>"
    if markup.kind == "open":
        return f"<{markup.name}{options}>"
    return f"</{markup.name}{options}>"


def format_options(options, ctx: MessageContext):
    return " ".join(format_option(opt, ctx) for opt in options)


def format_option(option: Option, ctx: MessageContext):
    value = resolve_option(option, ctx)
    return f"{option.name}={value}"


def resolve_options(options: list[Option], ctx: MessageContext):
    return {opt.name: resolve_option(opt, ctx) for opt in options}


def resolve_option(option: Option, ctx: MessageContext):
    match option.value:
        case Literal(value):
            return value
        case VariableRef(name):
            return resolve_variable(name, ctx).format(ctx)


def resolve_variable(name: str, ctx: MessageContext):
    if name in ctx.declarations:
        decl = ctx.declarations[name]
        match decl.value:
            case LiteralExpression(arg=Literal(value), annotation=annotation):
                if not annotation:
                    return IntermediateValue(value)
                match annotation:
                    case FunctionAnnotation(name, options):
                        options = resolve_options(options, ctx)
                        return IntermediateValue(value, name, options)
                    case _:
                        raise ValueError(f"Unsupported annotation: {annotation}")
            case VariableExpression(arg=VariableRef(name), annotation=annotation):
                if not annotation:
                    if isinstance(decl, InputDeclaration):
                        return IntermediateValue(value=ctx.input_mapping[name])
                    if name in ctx.declarations:
                        return resolve_variable(name, ctx)
                    return IntermediateValue(value=ctx.input_mapping[name])
                match annotation:
                    case FunctionAnnotation(name=fn, options=options):
                        options = resolve_options(options, ctx)
                        if isinstance(decl, InputDeclaration):
                            return IntermediateValue(value=ctx.input_mapping[name]).extend(fn, options)
                        return resolve_variable(name, ctx).extend(fn, options)
                    case _:
                        raise ValueError(f"Unsupported annotation: {annotation}")
            case FunctionExpression(annotation=FunctionAnnotation(name, options)):
                options = resolve_options(options, ctx)
                return IntermediateValue(value=None, fn=name, options=options)

    elif name in ctx.input_mapping:
        return IntermediateValue(value=ctx.input_mapping[name])
    raise ValueError(f"Variable {name} not found in declarations or input mapping")

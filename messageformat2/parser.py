import re

from messageformat2.datamodel import (
    Attribute,
    CatchallKey,
    DataModelValidator,
    Declaration,
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
    Pattern,
    PatternMessage,
    SelectMessage,
    UnsupportedAnnotation,
    UnsupportedExpression,
    UnsupportedStatement,
    VariableExpression,
    VariableRef,
    Variant,
    _Matcher,
)
from messageformat2.errors import ParseError


_name_start = (
    "^"
    "[a-zA-Z_"
    "\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u02ff"
    "\u0370-\u037d\u037f-\u1fff\u200c-\u200d"
    "\u2070-\u218f\u2c00-\u2fef\u3001-\ud7ff"
    "\uf900-\ufdcf\ufdf0-\ufffd\U00010000-\U000effff]"
)
name_start = re.compile(_name_start)
name_char = re.compile(rf"{_name_start}|[0-9-.\u00B7\u0300-\u036F\u203F-\u2040]")

number_literal = re.compile(r"^-?(?:(?:0|[1-9])\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")

_whitespace = r"[\s\u3000]"
whitespace = re.compile(f"^{_whitespace}")

text_escape = re.compile(r"^\\[\\{}]")
quoted_escape = re.compile(r"^\\[\\|]")
_reserved_escape = r"^\\[\\{|}]"
reserved_escape = re.compile(f"^{_reserved_escape}")

_content_char = (
    "[\u0001-\u0008]|[\u000b-\u000c]|[\u000e-\u001f]|"
    "[\u0021-\\\u002d]|"  # \u002d is '-' so needs to be escaped
    "[\u002f-\u003f]|[\u0041-\u005b]|"
    "[\u005d-\u007a]|[\u007e-\u2fff]|[\u3001-\ud7ff]|[\ue000-\U0010ffff]"
)
content_char = re.compile(f"^{_content_char}")

simple_start_char = re.compile(rf"^{_content_char}|{_whitespace}|[@|]")
text_char = re.compile(rf"^{_content_char}|{_whitespace}|[.@|]")
quoted_char = re.compile(rf"^{_content_char}|{_whitespace}|[.@{{}}]")
_reserved_char = rf"{_content_char}|[.]"
reserved_char = re.compile(rf"^{_reserved_char}")

markup_start = re.compile(rf"{{{_whitespace}?[#/]")
annotation_start = re.compile(r"^[:^&!%*+<>?~]")
input_start = re.compile(r"^\.input")
local_start = re.compile(r"^\.local")
match_start = re.compile(r"^\.match")
quoted_pattern_start = re.compile(r"^\{\{")
quoted_pattern_end = re.compile(r"^\}\}")
reserved_body_part_start = re.compile(rf"^{_reserved_char}|{_reserved_escape}|\|")


class Queue:
    def __init__(self, text: str) -> None:
        self.queue = text

    def pop(self, char: str | None = None) -> str:
        if not self.queue:
            msg = "Unexpect end of input"
            raise ParseError(msg)

        s, rest = self.queue[0], self.queue[1:]
        self.queue = rest

        if char is not None and s != char:
            msg = f"Expected: {char}, got: {s}"
            raise ParseError(msg)

        return s

    def peek(self) -> str | None:
        if self.queue:
            return self.queue[0]
        return None

    def peek_after_whitespace(self) -> str | None:
        if self.queue:
            i = 0
            while i < len(self.queue) and whitespace.match(self.queue[i]):
                i += 1
            return self.queue[i]
        return None

    def matches(self, pattern: re.Pattern) -> bool:
        if self.queue:
            return bool(pattern.match(self.queue))
        return False

    def matches_after_whitespace(self, pattern: re.Pattern) -> bool:
        if self.queue:
            i = 0
            while i < len(self.queue) and whitespace.match(self.queue[i]):
                i += 1
            return bool(pattern.match(self.queue[i:]))
        return False

    def pop_match(self, pattern: re.Pattern) -> str:
        if self.queue:
            match = pattern.match(self.queue)
            if not match:
                msg = f"Did not match: {self.queue[0]}"
                raise ParseError(msg)
            s, rest = match.group(), self.queue[match.end() :]
            self.queue = rest
            return s
        msg = "Unexpected end of input"
        raise ParseError(msg)

    def __len__(self) -> int:
        return len(self.queue)

    def __bool__(self) -> bool:
        return bool(self.queue)


def parse(msg: str) -> Message:
    ast = parse_message(msg)
    DataModelValidator().visit(ast)
    return ast


def parse_message(msg: str) -> Message:
    queue = Queue(msg)
    message = parse_complex_message(queue) if queue.peek() == "." else parse_simple_message(queue)
    if queue:
        msg = f"Expected end of message but instead got: {queue.peek()}"
        raise ParseError(msg)
    return message


def parse_simple_message(queue: Queue) -> PatternMessage:
    if not queue:
        return PatternMessage(declarations=[], pattern=[])
    simple_start = parse_simple_start(queue)
    pattern = parse_pattern(queue)

    if not pattern:
        return PatternMessage(declarations=[], pattern=simple_start)

    x = simple_start[-1]
    y = pattern[0]
    match (x, y):
        case (str(), str()):
            pattern = simple_start[:-1] + [x + y] + pattern[1:]
            return PatternMessage(declarations=[], pattern=pattern)
        case _:
            return PatternMessage(declarations=[], pattern=simple_start + pattern)


def parse_complex_message(queue: Queue) -> Message:
    declarations = []
    while queue.peek() == "." and not queue.matches(match_start):
        declarations.append(parse_declaration(queue))
        parse_optional_whitespace(queue)

    body = parse_complex_body(queue)
    match body:
        case _Matcher(selectors=selectors, variants=variants):
            return SelectMessage(declarations=declarations, selectors=selectors, variants=variants)
        case _:
            return PatternMessage(declarations=declarations, pattern=body)


def parse_declaration(queue: Queue) -> Declaration:
    if queue.matches(input_start):
        return parse_input_declaration(queue)
    if queue.matches(local_start):
        return parse_local_declaration(queue)
    return parse_reserved_statement(queue)


def parse_input_declaration(queue: Queue) -> InputDeclaration:
    queue.pop_match(input_start)
    parse_optional_whitespace(queue)
    queue.pop("{")
    expression = parse_variable_expression(queue)
    queue.pop("}")
    return InputDeclaration(name=expression.arg.name, value=expression)


def parse_local_declaration(queue: Queue) -> LocalDeclaration:
    queue.pop_match(local_start)
    parse_whitespace(queue)
    variable = parse_variable(queue)
    parse_optional_whitespace(queue)
    queue.pop("=")
    parse_optional_whitespace(queue)
    return LocalDeclaration(name=variable.name, value=parse_expression(queue))


def parse_complex_body(queue: Queue) -> _Matcher | Pattern:
    if queue.matches(quoted_pattern_start):
        return parse_quoted_pattern(queue)
    return parse_matcher(queue)


def parse_quoted_pattern(queue: Queue) -> Pattern:
    queue.pop_match(quoted_pattern_start)
    pattern = parse_pattern(queue)
    queue.pop_match(quoted_pattern_end)
    return pattern


def parse_matcher(queue: Queue) -> _Matcher:
    queue.pop_match(match_start)
    parse_optional_whitespace(queue)
    selectors = [parse_selector(queue)]
    while queue.peek_after_whitespace() == "{":
        parse_optional_whitespace(queue)
        selectors.append(parse_selector(queue))

    parse_optional_whitespace(queue)
    variants = [parse_variant(queue)]

    while queue.peek_after_whitespace():
        parse_optional_whitespace(queue)
        variants.append(parse_variant(queue))

    return _Matcher(selectors=selectors, variants=variants)


def parse_selector(queue: Queue) -> Expression:
    return parse_expression(queue)


def parse_variant(queue: Queue) -> Variant:
    keys = [parse_key(queue)]

    while queue.peek_after_whitespace() and not queue.matches_after_whitespace(quoted_pattern_start):
        parse_whitespace(queue)
        keys.append(parse_key(queue))

    parse_optional_whitespace(queue)
    return Variant(keys=keys, value=parse_quoted_pattern(queue))


def parse_key(queue: Queue) -> Literal | CatchallKey:
    if queue.peek() == "*":
        queue.pop()
        return CatchallKey(value=None)
    return parse_literal(queue)


def parse_simple_start(queue: Queue) -> Pattern:
    if queue.peek() == "{":
        return [parse_placeholder(queue)]
    if queue.matches(simple_start_char):
        return [queue.pop()]
    if queue.matches(text_escape):
        text = queue.pop_match(text_escape)
        text = text.replace(r"\{", "{").replace(r"\}", "}").replace(r"\\", "\\")
        return [text]
    msg = f"Invalid character: {queue.peek()}"
    raise ParseError(msg)


def parse_pattern(queue: Queue) -> Pattern:
    pattern = []
    string = ""
    while queue and not queue.matches(quoted_pattern_end):
        if queue.matches(text_char):
            string += queue.pop()
        elif queue.matches(text_escape):
            escape = queue.pop_match(text_escape)
            string += escape.replace(r"\{", "{").replace(r"\}", "}").replace(r"\\", "\\")
        else:
            if string:
                pattern.append(string)
                string = ""
            pattern.append(parse_placeholder(queue))
    if string:
        pattern.append(string)
        string = ""
    return pattern


def parse_placeholder(queue: Queue) -> Markup | Expression:
    if queue.matches(markup_start):
        return parse_markup(queue)
    return parse_expression(queue)


def parse_markup(queue: Queue) -> Markup:
    queue.pop("{")
    parse_optional_whitespace(queue)

    type_ = queue.pop()
    standalone = False

    name = parse_identifier(queue)
    options = []
    attributes = []

    while queue.peek_after_whitespace() not in {"/", "}"}:
        parse_whitespace(queue)
        if queue.peek() == "@":
            attributes.append(parse_attribute(queue))
        else:
            options.append(parse_option(queue))

    parse_optional_whitespace(queue)

    if type_ == "#" and queue.peek() == "/":
        standalone = True
        queue.pop()

    queue.pop("}")
    kind = "standalone" if standalone else "open" if type_ == "#" else "close"
    return Markup(kind=kind, name=name, options=options, attributes=attributes)


def parse_expression(queue: Queue) -> Expression:
    queue.pop("{")
    parse_optional_whitespace(queue)

    if queue.peek() == "$":
        expression = parse_variable_expression(queue)
    elif queue.peek() == ":":
        annotation = parse_function_annotation(queue)
        attributes = []
        while queue.peek_after_whitespace() != "}":
            parse_whitespace(queue)
            attributes.append(parse_attribute(queue))
        expression = FunctionExpression(annotation=annotation, attributes=attributes)
    elif queue.peek() in {"^", "&", "!", "%", "*", "+", "<", ">", "?", "~"}:
        annotation = parse_unsupported_annotation(queue)
        attributes = []
        while queue.peek_after_whitespace() != "}":
            parse_whitespace(queue)
            attributes.append(parse_attribute(queue))
        expression = UnsupportedExpression(annotation=annotation, attributes=attributes)
    else:
        literal = parse_literal(queue)
        annotation = None
        attributes = []

        if queue.peek_after_whitespace() in {":", "^", "&", "!", "%", "*", "+", "<", ">", "?", "~"}:
            parse_whitespace(queue)
            annotation = parse_annotation(queue)

        while queue.peek_after_whitespace() != "}":
            parse_whitespace(queue)
            attributes.append(parse_attribute(queue))
        expression = LiteralExpression(arg=literal, annotation=annotation, attributes=attributes)

    parse_optional_whitespace(queue)
    queue.pop("}")
    return expression


def parse_variable_expression(queue: Queue) -> VariableExpression:
    variable = parse_variable(queue)
    annotation = None
    attributes = []

    if queue.peek_after_whitespace() in {":", "^", "&", "!", "%", "*", "+", "<", ">", "?", "~"}:
        parse_whitespace(queue)
        annotation = parse_annotation(queue)

    while queue.peek_after_whitespace() != "}":
        parse_whitespace(queue)
        attributes.append(parse_attribute(queue))
    return VariableExpression(arg=variable, annotation=annotation, attributes=attributes)


def parse_identifier(queue: Queue) -> str:
    namespace = parse_namespace(queue)
    if queue.peek() == ":":
        queue.pop()
        name = parse_name(queue)
        return f"{namespace}:{name}"
    return namespace


def parse_namespace(queue: Queue) -> str:
    return parse_name(queue)


def parse_name(queue: Queue) -> str:
    if not queue.matches(name_start):
        msg = f"Invalid name start: {queue.peek()}"
        raise ParseError(msg)
    name = queue.pop()

    while queue.matches(name_char):
        name += queue.pop()
    return name


def parse_annotation(queue: Queue) -> FunctionAnnotation | UnsupportedAnnotation:
    if queue.peek() == ":":
        return parse_function_annotation(queue)
    return parse_unsupported_annotation(queue)


def parse_function_annotation(queue: Queue) -> FunctionAnnotation:
    queue.pop(":")
    name = parse_identifier(queue)
    options = []
    while queue.peek_after_whitespace() and queue.matches_after_whitespace(name_start):
        parse_whitespace(queue)
        options.append(parse_option(queue))

    return FunctionAnnotation(name=name, options=options)


def parse_unsupported_annotation(queue: Queue) -> UnsupportedAnnotation:
    source = queue.pop()
    if queue.matches_after_whitespace(reserved_body_part_start):
        source += parse_optional_whitespace(queue)
        source += parse_reserved_body(queue)
    return UnsupportedAnnotation(source=source)


def parse_reserved_statement(queue: Queue) -> UnsupportedStatement:
    queue.pop(".")
    keyword = parse_name(queue)

    body = ""
    if queue.matches_after_whitespace(reserved_body_part_start):
        body += parse_whitespace(queue)
        body += parse_reserved_body(queue)

    parse_optional_whitespace(queue)
    expressions = [parse_expression(queue)]

    while queue.peek_after_whitespace() == "{":
        parse_optional_whitespace(queue)
        expressions.append(parse_expression(queue))

    return UnsupportedStatement(keyword=keyword, body=body or None, expressions=expressions)


def parse_reserved_body(queue: Queue) -> str:
    body = parse_reserved_body_part(queue)
    while queue.matches_after_whitespace(reserved_body_part_start):
        body += parse_optional_whitespace(queue)
        body += parse_reserved_body_part(queue)
    return body


def parse_reserved_body_part(queue: Queue) -> str:
    part = ""
    while True:
        if queue.matches(reserved_char):
            part += queue.pop()
        elif queue.matches(reserved_escape):
            part += queue.pop_match(reserved_escape)
        elif queue.peek() == "|":
            part += str(parse_quoted_literal(queue))
        else:
            break
    return part


def parse_attribute(queue: Queue) -> Attribute:
    queue.pop("@")
    name = parse_identifier(queue)

    if queue.peek_after_whitespace() != "=":
        return Attribute(name=name, value=None)

    parse_optional_whitespace(queue)
    queue.pop()  # '='
    parse_optional_whitespace(queue)

    value = parse_variable(queue) if queue.peek() == "$" else parse_literal(queue)
    return Attribute(name=name, value=value)


def parse_option(queue: Queue) -> Option:
    name = parse_identifier(queue)

    parse_optional_whitespace(queue)
    if queue.peek() != "=":
        msg = f"Invalid option: {name}"
        raise ParseError(msg)
    queue.pop()
    parse_optional_whitespace(queue)

    value = parse_variable(queue) if queue.peek() == "$" else parse_literal(queue)
    return Option(name=name, value=value)


def parse_variable(queue: Queue) -> VariableRef:
    if queue.peek() != "$":
        msg = f"Invalid variable: {queue.peek()}"
        raise ParseError(msg)
    queue.pop()
    return VariableRef(name=parse_name(queue))


def parse_literal(queue: Queue) -> Literal:
    return parse_quoted_literal(queue) if queue.peek() == "|" else parse_unquoted_literal(queue)


def parse_quoted_literal(queue: Queue) -> Literal:
    literal = ""
    queue.pop("|")
    while True:
        if queue.matches(quoted_escape):
            escape = queue.pop_match(quoted_escape)
            if escape == r"\\":
                literal += "\\"
            else:
                literal += "|"
        elif queue.matches(quoted_char):
            literal += queue.pop()
        else:
            break

    queue.pop("|")
    return Literal(value=literal)


def parse_unquoted_literal(queue: Queue) -> Literal:
    if queue.matches(number_literal):
        return Literal(value=queue.pop_match(number_literal))
    return Literal(value=parse_name(queue))


def parse_whitespace(queue: Queue) -> str:
    if not queue.matches(whitespace):
        msg = f"Expected whitespace: {queue.peek()}"
        raise ParseError(msg)
    return parse_optional_whitespace(queue)


def parse_optional_whitespace(queue: Queue) -> str:
    ws = ""
    while queue.matches(whitespace):
        ws += queue.pop()
    return ws

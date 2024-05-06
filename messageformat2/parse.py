import re
import warnings
from dataclasses import dataclass
from typing import Literal as TypingLiteral


warnings.simplefilter(action="ignore", category=FutureWarning)

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
reserved_escape = re.compile(r"^\\[\\{|}]")

_content_char = (
    "^"
    "[\u0001-\u0008]|[\u000b-\u000c]|[\u000e-\u001f]|"
    "[\u0021-\u002d]|[\u002f-\u003f]|[\u0041-\u005b]|"
    "[\u005d-\u007a]|[\u007e-\u2fff]|[\u3001-\ud7ff]|[\ue000-\U0010ffff]"
)
content_char = re.compile(_content_char)

simple_start_char = re.compile(rf"{_content_char}|{_whitespace}|[@|]")
text_char = re.compile(rf"{_content_char}|{_whitespace}|[.@|]")
quoted_char = re.compile(rf"{_content_char}|{_whitespace}|[.@{{}}]")
reserved_char = re.compile(rf"{_content_char}|[.]")

markup_start = re.compile(rf"{{{_whitespace}?[#/]")
annotation_start = re.compile(r"^[:^&!%*+<>?~]")
input_start = re.compile(r"^\.input")
local_start = re.compile(r"^\.local")
match_start = re.compile(r"^\.match")
quoted_pattern_start = re.compile(r"^\{\{")
quoted_pattern_end = re.compile(r"^\}\}")


class Queue:
    def __init__(self, text: str) -> None:
        self.queue = text

    def pop(self) -> str | None:
        if self.queue:
            s, rest = self.queue[0], self.queue[1:]
            self.queue = rest
            return s
        return None

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
            return pattern.match(self.queue)
        return False

    def matches_after_whitespace(self, pattern: re.Pattern) -> bool:
        if self.queue:
            i = 0
            while i < len(self.queue) and whitespace.match(self.queue[i]):
                i += 1
            return pattern.match(self.queue[i:])
        return False

    def pop_match(self, pattern: re.Pattern) -> str:
        if self.queue:
            match = pattern.match(self.queue)
            if not match:
                raise ValueError(f"Did not match: {self.queue[0]}")
            s, rest = match.group(), self.queue[match.end() :]
            self.queue = rest
            return s
        return None

    def __len__(self) -> int:
        return len(self.queue)

    def __bool__(self) -> bool:
        return bool(self.queue)


@dataclass
class VariableRef:
    name: str
    # type: str = 'variable'


@dataclass
class Literal:
    value: str
    # type: str = 'literal'


@dataclass
class Attribute:
    name: str
    value: Literal | VariableRef


@dataclass
class Option:
    name: str
    value: Literal | VariableRef


@dataclass
class FunctionAnnotation:
    name: str
    options: list[Option]
    # type: str = 'function'


@dataclass
class UnsupportedAnnotation:
    source: str
    # type: str = 'unsupported-annotation'


@dataclass
class VariableExpression:
    arg: VariableRef
    annotation: FunctionAnnotation | UnsupportedAnnotation | None
    attributes: list[Attribute]
    # type: str = 'expression'


@dataclass
class LiteralExpression:
    arg: Literal
    annotation: FunctionAnnotation | UnsupportedAnnotation | None
    attributes: list[Attribute]
    # type: str = 'expression'


@dataclass
class FunctionExpression:
    annotation: FunctionAnnotation
    attributes: list[Attribute]
    # type: str = 'expression'


@dataclass
class Markup:
    kind: TypingLiteral["open", "standalone", "close"]
    name: str
    options: list[Option]
    attributes: list[Attribute]
    # type: str = 'Markup'


type Expression = LiteralExpression | VariableExpression | FunctionExpression
type Pattern = list[str | Expression | Markup]


@dataclass
class CatchallKey:
    value: str | None
    # type: str = '*'


@dataclass
class Variant:
    keys: list[Literal | CatchallKey]
    value: Pattern


@dataclass
class Matcher:
    selectors: list[Expression]
    variants: list[Variant]


@dataclass
class InputDeclaration:
    name: str
    value: VariableExpression
    # type: str = "input"


@dataclass
class LocalDeclaration:
    name: str
    value: Expression
    # type: str = "local"


type Declaration = InputDeclaration | LocalDeclaration


@dataclass
class PatternMessage:
    declarations: list[Declaration]
    pattern: Pattern
    # type: str = 'message'


@dataclass
class SelectMessage:
    declarations: list[Declaration]
    selectors: list[Expression]
    variants: list[Variant]
    # type: str = 'select'


type Message = PatternMessage | SelectMessage


def parse_message(msg: str):
    queue = Queue(msg)
    if queue.matches(input_start) or queue.matches(local_start) or queue.matches(match_start):
        return parse_complex_message(queue)
    return parse_simple_message(queue)


def parse_simple_message(queue: Queue):
    if not queue:
        return PatternMessage(declarations=[], pattern=[])
    simple_start = parse_simple_start(queue)
    pattern = parse_pattern(queue)

    if not pattern:
        return PatternMessage(declarations=[], pattern=simple_start)

    match (simple_start[-1], pattern[0]):
        case (str(), str()):
            return PatternMessage(
                declarations=[], pattern=simple_start[:-1] + [simple_start[-1] + pattern[0]] + pattern[1:]
            )
        case _:
            return PatternMessage(declarations=[], pattern=simple_start + pattern)


def parse_complex_message(queue: Queue):
    declarations = []
    while queue.matches(input_start) or queue.matches(local_start):
        declarations.append(parse_declaration(queue))
        parse_whitespace(queue)
    body = parse_complex_body(queue)
    match body:
        case Matcher(selectors=selectors, variants=variants):
            return SelectMessage(declarations=declarations, selectors=selectors, variants=variants)
        case _:
            return PatternMessage(declarations=declarations, pattern=body)


def parse_declaration(queue: Queue):
    if queue.matches(input_start):
        return parse_input_declaration(queue)
    elif queue.matches(local_start):
        return parse_local_declaration(queue)
    return parse_reserved_statement(queue)


def parse_input_declaration(queue: Queue):
    queue.pop_match(input_start)
    parse_whitespace(queue)
    assert queue.pop() == "{"
    expression = parse_variable_expression(queue)
    assert queue.pop() == "}"
    return InputDeclaration(name=expression.arg.name, value=expression)


def parse_local_declaration(queue: Queue):
    queue.pop_match(local_start)
    parse_whitespace(queue, optional=False)
    variable = parse_variable(queue)
    parse_whitespace(queue)
    assert queue.pop() == "="
    parse_whitespace(queue)
    return LocalDeclaration(name=variable.name, value=parse_expression(queue))


def parse_reserved_statement(queue: Queue):
    raise ValueError(f"Invalid statement: {queue.peek()}")


def parse_complex_body(queue: Queue):
    if queue.matches(quoted_pattern_start):
        return parse_quoted_pattern(queue)
    return parse_matcher(queue)


def parse_quoted_pattern(queue: Queue):
    queue.pop_match(quoted_pattern_start)
    pattern = parse_pattern(queue)
    queue.pop_match(quoted_pattern_end)
    return pattern


def parse_matcher(queue: Queue):
    print("parse_matcher", queue.queue)
    queue.pop_match(match_start)
    parse_whitespace(queue)
    selectors = [parse_selector(queue)]
    while queue.peek_after_whitespace() == "{":
        parse_whitespace(queue)
        selectors.append(parse_selector(queue))

    parse_whitespace(queue)
    variants = [parse_variant(queue)]

    print("parse_matcher 2", queue.queue)

    while queue.peek_after_whitespace():
        # print("parse_matcher 3", queue.queue)
        parse_whitespace(queue)
        variants.append(parse_variant(queue))

    return Matcher(selectors=selectors, variants=variants)


def parse_selector(queue: Queue):
    return parse_expression(queue)


def parse_variant(queue: Queue):
    keys = [parse_key(queue)]

    while queue.peek_after_whitespace() and not queue.matches_after_whitespace(quoted_pattern_start):
        parse_whitespace(queue, optional=False)
        keys.append(parse_key(queue))

    parse_whitespace(queue)
    return Variant(keys=keys, value=parse_quoted_pattern(queue))


def parse_key(queue: Queue):
    if queue.peek() == "*":
        queue.pop()
        return CatchallKey(value=None)
    return parse_literal(queue)


def parse_simple_start(queue: Queue):
    if queue.peek() == "{":
        return [parse_placeholder(queue)]
    char = queue.pop()
    if simple_start_char.match(char) or text_escape.match(char):
        return [char]
    raise ValueError(f"Invalid character: {char}")


def parse_pattern(queue: Queue):
    pattern = []
    string = ""
    while queue and not queue.matches(quoted_pattern_end):
        char = queue.peek()
        if text_char.match(char) or text_escape.match(char):
            string += queue.pop()
        else:
            if string:
                pattern.append(string)
                string = ""
            pattern.append(parse_placeholder(queue))
    if string:
        pattern.append(string)
        string = ""
    return pattern


def parse_placeholder(queue: Queue):
    if queue.matches(markup_start):
        return parse_markup(queue)
    return parse_expression(queue)


def parse_markup(queue: Queue):
    assert queue.pop() == "{"
    parse_whitespace(queue)

    type_ = queue.pop()
    standalone = False

    name = parse_identifier(queue)
    options = []
    attributes = []

    while queue.peek_after_whitespace() not in {"/", "}"}:
        parse_whitespace(queue, optional=False)
        if queue.peek() == "@":
            attributes.append(parse_attribute(queue))
        else:
            options.append(parse_option(queue))

    parse_whitespace(queue)

    if type_ == "#" and queue.peek() == "/":
        standalone = True
        queue.pop()

    assert queue.pop() == "}"
    kind = "standalone" if standalone else "open" if type_ == "#" else "close"
    return Markup(kind=kind, name=name, options=options, attributes=attributes)


def parse_expression(queue: Queue):
    assert queue.pop() == "{"

    parse_whitespace(queue)

    if queue.peek() == "$":
        expression = parse_variable_expression(queue)
    elif queue.peek() in (":", "^", "&", "!", "%", "*", "+", "<", ">", "?", "~"):
        annotation = parse_annotation(queue)
        attributes = []
        while queue.peek_after_whitespace() != "}":
            parse_whitespace(queue, optional=False)
            attributes.append(parse_attribute(queue))
        expression = FunctionExpression(annotation=annotation, attributes=attributes)
    else:
        literal = parse_literal(queue)
        annotation = None
        attributes = []

        if queue.peek_after_whitespace() in {":", "^", "&", "!", "%", "*", "+", "<", ">", "?", "~"}:
            parse_whitespace(queue, optional=False)
            annotation = parse_annotation(queue)

        while queue.peek_after_whitespace() != "}":
            parse_whitespace(queue, optional=False)
            attributes.append(parse_attribute(queue))
        expression = LiteralExpression(arg=literal, annotation=annotation, attributes=attributes)

    # TODO parse attributes

    parse_whitespace(queue)

    assert queue.pop() == "}"
    return expression


def parse_variable_expression(queue: Queue):
    variable = parse_variable(queue)
    annotation = None
    attributes = []

    if queue.peek_after_whitespace() in {":", "^", "&", "!", "%", "*", "+", "<", ">", "?", "~"}:
        parse_whitespace(queue, optional=False)
        annotation = parse_annotation(queue)

    while queue.peek_after_whitespace() != "}":
        parse_whitespace(queue, optional=False)
        attributes.append(parse_attribute(queue))
    return VariableExpression(arg=variable, annotation=annotation, attributes=attributes)


def parse_identifier(queue: Queue):
    namespace = parse_namespace(queue)
    if queue.peek() == ":":
        queue.pop()
        name = parse_name(queue)
        return f"{namespace}:{name}"
    return namespace


def parse_namespace(queue: Queue):
    return parse_name(queue)


def parse_name(queue: Queue):
    if not queue.matches(name_start):
        raise ValueError(f"Invalid name start: {queue.peek()}")
    name = queue.pop()

    while queue.matches(name_char):
        name += queue.pop()
    return name


def parse_annotation(queue: Queue):
    if queue.peek() == ":":
        return parse_function_annotation(queue)
    elif queue.peek() in {"^", "&"}:
        # TODO parse private use annotation
        return parse_private_use_annotation(queue)
    else:
        # TODO parse reserved annotation
        return parse_reserved_annotation(queue)


def parse_function_annotation(queue: Queue):
    assert queue.pop() == ":"
    name = parse_identifier(queue)
    options = []

    while queue.peek_after_whitespace() and name_start.match(queue.peek_after_whitespace()):
        parse_whitespace(queue, optional=False)
        options.append(parse_option(queue))

    return FunctionAnnotation(name=name, options=options)


def parse_attribute(queue: Queue):
    assert queue.pop() == "@"
    name = parse_identifier(queue)

    if queue.peek_after_whitespace() != "=":
        return Attribute(name=name, value=None)

    parse_whitespace(queue)
    queue.pop()  # '='
    parse_whitespace(queue)

    if queue.peek() == "$":
        value = parse_variable(queue)
    else:
        value = parse_literal(queue)
    return Attribute(name=name, value=value)


def parse_option(queue: Queue):
    name = parse_identifier(queue)

    parse_whitespace(queue)
    if queue.peek() != "=":
        raise ValueError(f"Invalid option: {name}")
    queue.pop()
    parse_whitespace(queue)

    if queue.peek() == "$":
        value = parse_variable(queue)
    else:
        value = parse_literal(queue)
    return Option(name=name, value=value)


def parse_variable(queue: Queue):
    if queue.peek() != "$":
        raise ValueError(f"Invalid variable: {queue.peek()}")
    queue.pop()
    return VariableRef(name=parse_name(queue))


def parse_literal(queue: Queue):
    if queue.peek() == "|":
        value = parse_quoted_literal(queue)
    else:
        value = parse_unquoted_literal(queue)
    return Literal(value=value)


def parse_quoted_literal(queue: Queue):
    literal = ""
    assert queue.pop() == "|"
    while True:
        if queue.matches(quoted_escape):
            escape = queue.pop_match(quoted_escape)
            if escape == r"\\":
                literal += "\\"
            else:
                literal += "|"
            # literal += queue.pop_match(quoted_escape)
        elif queue.matches(quoted_char):
            literal += queue.pop()
        else:
            break

    assert queue.pop() == "|"
    return f"{literal}"


def parse_unquoted_literal(queue: Queue):
    # print("parse_unquoted_literal", queue.queue)
    if queue.matches(number_literal):
        return queue.pop_match(number_literal)
    return parse_name(queue)


def parse_whitespace(queue: Queue, optional=True):
    if not optional and not queue.matches(whitespace):
        raise ValueError(f"Expected whitespace: {queue.peek()}")

    while queue.matches(whitespace):
        queue.pop()

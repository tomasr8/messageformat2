from dataclasses import dataclass
from typing import Any
from typing import Literal as TypingLiteral

from messageformat2.errors import (
    DuplicateDeclaration,
    DuplicateOptionName,
    MissingFallbackVariant,
    MissingSelectorAnnotation,
    VariantKeyMismatch,
)


class Node:
    """Base class for all nodes in the data model AST."""

    @property
    def fields(self) -> tuple[str, ...]:
        return ()


def dump(node: Node) -> str:
    """Return a string representation of the node and its children.

    Args:
        node: The node to dump.

    Examples:
        >>> from messageformat2.message import Message
        >>> msg = Message("Hello, {$name}!")
        >>> dump(msg.datamodel)
        'Hello, {$name}!'
    """
    return str(node)


@dataclass
class VariableRef(Node):
    name: str

    def __str__(self) -> str:
        return f"${self.name}"


@dataclass
class Literal(Node):
    value: str

    def __str__(self) -> str:
        value = self.value.replace("|", r"\|").replace("\\", r"\\")
        return f"|{value}|"


@dataclass
class Attribute(Node):
    name: str
    value: Literal | VariableRef | None

    @property
    def fields(self) -> tuple[str, ...]:
        return ("value",)

    def __str__(self) -> str:
        if not self.value:
            return f"@{self.name}"
        return f"@{self.name}={self.value}"


@dataclass
class Option(Node):
    name: str
    value: Literal | VariableRef

    @property
    def fields(self) -> tuple[str, ...]:
        return ("value",)

    def __str__(self) -> str:
        return f"{self.name}={self.value}"


@dataclass
class FunctionAnnotation(Node):
    name: str
    options: list[Option]

    @property
    def fields(self) -> tuple[str, ...]:
        return ("options",)

    def __str__(self) -> str:
        options = " ".join([str(opt) for opt in self.options])
        if options:
            options = f" {options}"
        return f":{self.name}{options}"


@dataclass
class UnsupportedAnnotation(Node):
    source: str

    def __str__(self) -> str:
        return self.source


class Expression(Node):
    pass


@dataclass
class VariableExpression(Expression):
    arg: VariableRef
    annotation: FunctionAnnotation | UnsupportedAnnotation | None
    attributes: list[Attribute]

    @property
    def fields(self) -> tuple[str, ...]:
        return ("arg", "annotation", "attributes")

    def __str__(self) -> str:
        annotation = f" {self.annotation}" if self.annotation else ""
        attributes = " ".join([str(attr) for attr in self.attributes])
        if attributes:
            attributes = f" {attributes}"
        return f"{{{self.arg}{annotation}{attributes}}}"


@dataclass
class LiteralExpression(Expression):
    arg: Literal
    annotation: FunctionAnnotation | UnsupportedAnnotation | None
    attributes: list[Attribute]

    @property
    def fields(self) -> tuple[str, ...]:
        return ("arg", "annotation", "attributes")

    def __str__(self) -> str:
        annotation = f" {self.annotation}" if self.annotation else ""
        attributes = " ".join([str(attr) for attr in self.attributes])
        if attributes:
            attributes = f" {attributes}"
        return f"{{{self.arg}{annotation}{attributes}}}"


@dataclass
class FunctionExpression(Expression):
    annotation: FunctionAnnotation
    attributes: list[Attribute]

    @property
    def fields(self) -> tuple[str, ...]:
        return ("annotation", "attributes")

    def __str__(self) -> str:
        attributes = " ".join([str(attr) for attr in self.attributes])
        if attributes:
            attributes = f" {attributes}"
        return f"{{{self.annotation}{attributes}}}"


@dataclass
class UnsupportedExpression(Expression):
    annotation: UnsupportedAnnotation
    attributes: list[Attribute]

    @property
    def fields(self) -> tuple[str, ...]:
        return ("annotation", "attributes")

    def __str__(self) -> str:
        attributes = " ".join([str(attr) for attr in self.attributes])
        if attributes:
            attributes = f" {attributes}"
        return f"{{{self.annotation}{attributes}}}"


@dataclass
class Markup(Node):
    kind: TypingLiteral["open", "standalone", "close"]
    name: str
    options: list[Option]
    attributes: list[Attribute]

    @property
    def fields(self) -> tuple[str, ...]:
        return ("options", "attributes")

    def __str__(self) -> str:
        options = " ".join([str(opt) for opt in self.options])
        attributes = " ".join([str(attr) for attr in self.attributes])
        if options:
            options = f" {options}"
        if attributes:
            attributes = f" {attributes}"
        if self.kind == "open":
            return f"{{#{self.name}{options}{attributes}}}"
        if self.kind == "standalone":
            return f"{{#{self.name}{options}{attributes}/}}"
        return f"{{/{self.name}{options}{attributes}}}"


type Pattern = list[str | Expression | Markup]


@dataclass
class CatchallKey(Node):
    value: str | None

    def __str__(self) -> str:
        return "*"


@dataclass
class Variant(Node):
    keys: list[Literal | CatchallKey]
    value: Pattern

    @property
    def fields(self) -> tuple[str, ...]:
        return ("keys", "value")

    def __str__(self) -> str:
        keys = " ".join([str(key) for key in self.keys])
        pattern = "".join([str(part) for part in self.value])
        return f"{keys} {{{{{pattern}}}}}"


# Helper class, not part of the Data Model
@dataclass
class _Matcher:
    selectors: list[Expression]
    variants: list[Variant]


@dataclass
class InputDeclaration(Node):
    name: str
    value: VariableExpression

    @property
    def fields(self) -> tuple[str, ...]:
        return ("value",)

    def __str__(self) -> str:
        return f".input {self.value}"


@dataclass
class LocalDeclaration(Node):
    name: str
    value: Expression

    @property
    def fields(self) -> tuple[str, ...]:
        return ("value",)

    def __str__(self) -> str:
        return f".local {self.name} = {self.value}"


@dataclass
class UnsupportedStatement(Node):
    keyword: str
    body: str | None
    expressions: list[Expression]

    @property
    def fields(self) -> tuple[str, ...]:
        return ("expressions",)

    def __str__(self) -> str:
        body = self.body or ""
        expressions = "\n".join([str(expr) for expr in self.expressions])
        return f".{self.keyword}{body}\n{expressions}"


type Declaration = InputDeclaration | LocalDeclaration | UnsupportedStatement


@dataclass
class PatternMessage(Node):
    declarations: list[Declaration]
    pattern: Pattern

    @property
    def fields(self) -> tuple[str, ...]:
        return ("declarations", "pattern")

    def __str__(self) -> str:
        declarations = "\n".join([str(decl) for decl in self.declarations])
        pattern = "".join([str(part) for part in self.pattern])
        if not declarations:
            return pattern
        return f"{declarations}\n{{{pattern}}}"


@dataclass
class SelectMessage(Node):
    declarations: list[Declaration]
    selectors: list[Expression]
    variants: list[Variant]

    @property
    def fields(self) -> tuple[str, ...]:
        return ("declarations", "selectors", "variants")

    def __str__(self) -> str:
        declarations = "\n".join([str(decl) for decl in self.declarations])
        selectors = " ".join([str(sel) for sel in self.selectors])
        variants = "\n".join([str(var) for var in self.variants])
        if not declarations:
            return f".match {selectors}\n{variants}"
        return f"{declarations}\n.match {selectors}\n{variants}"


type Message = PatternMessage | SelectMessage


class DataModelVisitor:
    """Data model AST visitor.

    Works the same way as the ast.NodeVisitor from the Python stdlib.

    Examples:
        >>> from messageformat2 import Message
        >>> from messageformat2.datamodel import DataModelVisitor
        >>> class VariableVisitor(DataModelVisitor):
        ...     def visit_VariableRef(self, node):
        ...         print(f"${node.name}")
        ...         self.generic_visit(node)
        ...
        >>> message = Message("Hello, {$name}!")
        >>> visitor = VariableVisitor()
        >>> visitor.visit(message.datamodel)
        $name
    """

    def visit(self, node: Node) -> Any:
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: Node) -> Any:
        for name in node.fields:
            if (value := getattr(node, name)) is None:
                continue
            match value:
                case [*items]:
                    for item in items:
                        if isinstance(item, Node):
                            self.visit(item)
                case _:
                    self.visit(value)


class DataModelTransformer(DataModelVisitor):
    """Data model AST transformer.

    Works the same way as the ast.NodeTransformer from the Python stdlib.

    Examples:
        >>> from messageformat2 import Message
        >>> from messageformat2.datamodel import Literal, DataModelTransformer
        >>> class LiteralTransformer(DataModelTransformer):
        ...     def visit_Literal(self, node):
        ...         return Literal(node.value.upper())
        ...
        >>> message = Message("{|foo|}")
        >>> ast = LiteralTransformer().visit(message.datamodel)
        >>> str(ast)
        '{|FOO|}'
    """

    def generic_visit[T: Node](self, node: T) -> T:
        for name in node.fields:
            old_value = getattr(node, name)
            if old_value is None:
                continue
            match old_value:
                case [*items]:
                    new_value = []
                    for item in items:
                        if not isinstance(item, Node):
                            new_value.append(item)
                            continue
                        value = self.visit(item)
                        if isinstance(value, list):
                            new_value.extend(value)
                        elif value is not None:
                            new_value.append(value)
                    setattr(node, name, new_value)
                case _:
                    new_value = self.visit(old_value)
                    if new_value is None:
                        delattr(node, name)
                    else:
                        setattr(node, name, new_value)
        return node


class DataModelValidator(DataModelVisitor):
    def visit_PatternMessage(self, node: SelectMessage) -> None:
        self._check_declarations(node.declarations)
        self.generic_visit(node)

    def visit_SelectMessage(self, node: SelectMessage) -> None:
        self._check_declarations(node.declarations)
        self._check_missing_selector_annotation(node.selectors, node.declarations)
        self._check_variant_key_mismatch(node.selectors, node.variants)
        self._check_missing_fallback_variant(node.variants)
        self.generic_visit(node)

    def visit_Markup(self, node: Markup) -> None:
        self._check_duplicate_options(node.options)
        self.generic_visit(node)

    def visit_FunctionAnnotation(self, node: FunctionAnnotation) -> None:
        self._check_duplicate_options(node.options)
        self.generic_visit(node)

    def _check_declarations(self, declarations: list[Declaration]) -> None:
        self._check_circular_reference(declarations)
        self._check_duplicate_declarations(declarations)
        self._check_implicit_redeclaration(declarations)

    def _check_missing_selector_annotation(self, selectors: list[Expression], declarations: list[Declaration]) -> None:
        for selector in selectors:
            if not self._is_annotated(selector, declarations):
                msg = "Missing selector annotation"
                raise MissingSelectorAnnotation(msg)

    def _is_annotated(self, selector: Expression, declarations: list[Declaration]) -> bool:
        match selector:
            case LiteralExpression(annotation=None):
                return False
            case VariableExpression(annotation=None, arg=VariableRef(name=name)):
                for decl in declarations:
                    if isinstance(decl, UnsupportedStatement) or decl.name != name:
                        continue
                    match decl:
                        case InputDeclaration(value=VariableExpression(annotation=annotation)):
                            return annotation is not None
                        case _:
                            return self._is_annotated(decl.value, declarations)
                return False
        return True

    def _check_variant_key_mismatch(self, selectors: list[Expression], variants: list[Variant]) -> None:
        for variant in variants:
            if len(selectors) != len(variant.keys):
                msg = f'Key count does not match selector count: "{variant}"'
                raise VariantKeyMismatch(msg)

    def _check_missing_fallback_variant(self, variants: list[Variant]) -> None:
        has_fallback = any(all(isinstance(key, CatchallKey) for key in variant.keys) for variant in variants)
        if not has_fallback:
            msg = "Missing fallback variant"
            raise MissingFallbackVariant(msg)

    def _check_circular_reference(self, declarations: list[Declaration]) -> None:
        for decl in declarations:
            match decl:
                case LocalDeclaration(name=name, value=VariableExpression(arg=VariableRef(name=ref))):
                    if name == ref:
                        msg = f"Duplicate declaration: {name}"
                        raise DuplicateDeclaration(msg)

    def _check_duplicate_declarations(self, declarations: list[Declaration]) -> None:
        names = set()
        for decl in declarations:
            if isinstance(decl, UnsupportedStatement):
                continue

            if decl.name in names:
                msg = f"Duplicate declaration: {decl.name}"
                raise DuplicateDeclaration(msg)
            names.add(decl.name)

    def _check_implicit_redeclaration(self, declarations: list[Declaration]) -> None:
        implicit = set()
        for decl in declarations:
            if isinstance(decl, UnsupportedStatement):
                continue

            if decl.name in implicit:
                msg = f"Redeclaration of an implicit variable: {decl.name}"
                raise DuplicateDeclaration(msg)

            match decl.value:
                case (
                    VariableExpression(annotation=FunctionAnnotation() as annotation)
                    | LiteralExpression(annotation=FunctionAnnotation() as annotation)
                    | FunctionExpression(annotation=FunctionAnnotation() as annotation)
                ) if annotation is not None:
                    for opt in annotation.options:
                        match opt.value:
                            case VariableRef(name=name):
                                implicit.add(name)

    def _check_duplicate_options(self, options: list[Option]) -> None:
        options_map = {}
        for opt in options:
            if opt.name in options_map:
                msg = f"Duplicate option name: '{opt.name}'"
                raise DuplicateOptionName(msg)
            options_map[opt.name] = opt.value

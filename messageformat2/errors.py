class MessageFormatError(Exception):
    """Base class for all messageformat2 errors.

    Use this class to catch arbitrary messageformat2 errors.
    """


class ParseError(MessageFormatError):
    """Raised when invalid syntax is encountered during parsing.

    Examples:
        >>> from messageformat2 import Message
        >>> Message("{ Unclosed pattern") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.ParseError: ...
    """


class DataModelError(MessageFormatError):
    """Base class for all messageformat2 data model errors."""


class VariantKeyMismatch(DataModelError):
    """Raised when the number of variant keys does not match the number of selectors.

    Examples:
        >>> from messageformat2 import Message
        >>> Message(".match {$count :integer} 0 1 {{You have no notifications.}}") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.VariantKeyMismatch: ...
    """


class MissingFallbackVariant(DataModelError):
    """Raised when a fallback variant (all catch-all keys) is not provided.

    Examples:
        >>> from messageformat2 import Message
        >>> Message(".match {$count :integer} one {{You have one notification.}}") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.MissingFallbackVariant: Missing fallback variant
    """


class MissingSelectorAnnotation(DataModelError):
    """Raised when a selector annotation is missing.

    Examples:
        >>> from messageformat2 import Message
        >>> Message(".match {$count} * {{You have {$count} notifications.}}") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.MissingSelectorAnnotation: ...
    """


class DuplicateDeclaration(DataModelError):
    """Raised when a variable is declared more than once.

    This includes variables declared as '.input'.

    Examples:
        >>> from messageformat2 import Message
        >>> Message(".input {$count} .local $count = {42} {{Duplicate declaration}}") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.DuplicateDeclaration: ...
    """


class DuplicateOptionName(DataModelError):
    """Raised when an option is declared more than once.

    Examples:
        >>> from messageformat2 import Message
        >>> Message("{42 :integer opt=1 opt=2}") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.DuplicateOptionName: ...
    """


class FormatError(MessageFormatError):
    """Base class for all errors raised during formatting."""


class ResolutionError(FormatError):
    """Raised when a part of the message cannot be determined."""


class UnresolvedVariable(ResolutionError):
    """Raised when a variable cannot be resolved.

    Examples:
        >>> from messageformat2 import Message
        >>> Message("Hello, {$name}!").format() # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.UnresolvedVariable: ...
    """


class UnknownFunction(ResolutionError):
    """Raised when a function is not found.

    Examples:
        >>> from messageformat2 import Message
        >>> Message("{Alice :unknown}").format() # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.UnknownFunction: ...
    """


class UnsupportedExpression(ResolutionError):
    """Raised when an expression uses reserved syntax.

    Examples:
        >>> from messageformat2 import Message
        >>> Message("The value is {!horse}").format() # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.UnsupportedExpression: ...
    """


class UnsupportedStatement(ResolutionError):
    """Raised when the message contains a reserved statement.

    Examples:
        >>> from messageformat2 import Message
        >>> Message(".unknown {$x} .match {$x :string} * {{}}").format() # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.UnsupportedStatement: ...
    """


class InvalidExpression(ResolutionError):
    pass


class OperandMismatch(InvalidExpression):
    pass


class SelectionError(FormatError):
    """Raised when message selection fails."""

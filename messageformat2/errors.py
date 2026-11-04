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
        >>> Message(".input {$count :integer} .match $count 0 1 {{You have no notifications.}}") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.VariantKeyMismatch: ...
    """


class MissingFallbackVariant(DataModelError):
    """Raised when a fallback variant (all catch-all keys) is not provided.

    Examples:
        >>> from messageformat2 import Message
        >>> Message(".input {$count :integer} .match $count one {{You have one notification.}}") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.MissingFallbackVariant: Missing fallback variant
    """


class MissingSelectorAnnotation(DataModelError):
    """Raised when a selector does not reference a declaration with a function.

    Examples:
        >>> from messageformat2 import Message
        >>> Message(".match $count * {{You have {$count} notifications.}}") # doctest: +ELLIPSIS
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


class DuplicateVariant(DataModelError):
    """Raised when the same list of keys is used for more than one variant.

    Literal keys are compared by their string values, so `foo` and `|foo|` are the same key.

    Examples:
        >>> from messageformat2 import Message
        >>> Message(".input {$x :string} .match $x * {{First default}} * {{Second default}}") # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.DuplicateVariant: ...
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


class BadSelector(ResolutionError):
    """Raised when a selector resolves to a value which does not support selection.

    Examples:
        >>> from messageformat2 import Message
        >>> Message(".local $day = {|2024-05-01| :date} .match $day * {{Due {$day}}}").format() # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        messageformat2.errors.BadSelector: ...
    """


class MessageFunctionError(FormatError):
    """Base class for errors raised by (or on behalf of) a function handler.

    Any other exception raised by a custom formatter or selector is wrapped in this error.
    Custom functions can raise one of the subclasses below to signal a specific error.

    A function which can still produce a result despite the error (the spec often says
    "emit a Bad Option error and ignore the option") passes it as `result`: when formatting
    with an `on_error` handler, the error is reported and the result is used instead of a
    fallback value.
    """

    def __init__(self, *args: object, result: object = None) -> None:
        super().__init__(*args)
        self.result = result


class BadOperand(MessageFunctionError):
    """Raised when the operand of a function has the wrong type or format."""


class BadOption(MessageFunctionError):
    """Raised when an option or option value is invalid for a function."""


class BadVariantKey(MessageFunctionError):
    """Raised when a variant key does not match the format expected by the selector function."""


class UnsupportedOperation(MessageFunctionError):
    """Raised when a combination of operand, options or option values is not supported by a function."""


# Backwards-compatible aliases for the pre-spec error names
InvalidExpression = MessageFunctionError
OperandMismatch = BadOperand
SelectionError = BadSelector

from typing import Any

from babel import Locale

from messageformat2.builtins import Formatter, Selector, default_registry
from messageformat2.datamodel import Node
from messageformat2.parser import parse
from messageformat2.runtime import format_message as _format_message


def format_message(
    msg: str,
    inputs: dict[str, Any] | None = None,
    locale: Locale | str | None = None,
    *,
    formatters: dict[str, Formatter] | None = None,
    selectors: dict[str, Selector] | None = None,
) -> str:
    """Format a message.

    Use this function if you only need to format a message once.

    Examples:
        >>> message = Message("Hello, {$name}!")
        >>> message.format({"name": "Alice"})
        'Hello, Alice!'
        >>> message = Message('''\\
        ... .match {$count :integer}
        ... one {{You have one notification}}
        ... *   {{You have {$count} notifications}}''')
        >>> message.format({"count": 3}, "en")
        'You have 3 notifications'

    Args:
        msg: The message to format.
        locale: The locale in which to format the message. Defaults to the system locale.
        inputs: Input variables referenced by the message.
        formatters: Additional formatters.
        selectors: Additional selectors.

    Returns:
        The formatted message.

    Raises:
        ParseError: If the message contains a syntax error.
        DataModelError: If the message contains a semantic error.
        FormatError: If the message cannot be formatted.
    """
    return Message(msg).format(inputs, locale, formatters=formatters, selectors=selectors)


class Message:
    def __init__(self, msg: str):
        """Create a new Message object that can be formatted.

        Use this class if you need to format the same message multiple times as
        the message is only parsed once.

        Args:
            msg: The message.

        Raises:
            ParseError: If the message contains a syntax error.
            DataModelError: If the message contains a semantic error.
        """
        self.msg = msg
        self._ast = parse(msg)

    def format(
        self,
        inputs: dict[str, Any] | None = None,
        locale: Locale | str | None = None,
        *,
        formatters: dict[str, Formatter] | None = None,
        selectors: dict[str, Selector] | None = None,
    ) -> str:
        """Format the message.

        Examples:
            >>> message = Message("Hello, {$name}!")
            >>> message.format({"name": "Alice"})
            'Hello, Alice!'
            >>> message = Message('''\\
            ... .match {$count :integer}
            ... one {{You have one notification}}
            ... *   {{You have {$count} notifications}}''')
            >>> message.format({"count": 3}, "en")
            'You have 3 notifications'

        Args:
            locale: The locale in which to format the message. Defaults to the system locale.
            inputs: Input variables referenced by the message.
            formatters: Additional formatters.
            selectors: Additional selectors.

        Returns:
            The formatted message.

        Raises:
            FormatError: If the message cannot be formatted.
        """
        if locale is None:
            locale = Locale.default()
        elif not isinstance(locale, Locale):
            locale = Locale.parse(locale)
        if inputs is None:
            inputs = {}
        registry = (
            default_registry
            if not formatters and not selectors
            else default_registry.extend(formatters=formatters, selectors=selectors)
        )
        return _format_message(self._ast, locale, inputs, registry)

    @property
    def datamodel(self) -> Node:
        """Return the data model representation of the message.

        Examples:
            >>> message = Message("Hello, {$name}!")
            >>> message.datamodel # doctest: +ELLIPSIS
            PatternMessage(..., pattern=['Hello, ', VariableExpression(arg=VariableRef(name='name'), ...), '!'])
        """
        return self._ast

    def __repr__(self) -> str:
        return f"Message({self.msg})"

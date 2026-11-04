from collections.abc import Callable
from typing import Any

from babel import Locale

from messageformat2.builtins import Formatter, MarkupFormatter, Selector, default_registry
from messageformat2.datamodel import Node
from messageformat2.errors import MessageFormatError
from messageformat2.parser import parse
from messageformat2.runtime import format_message as _format_message


def format_message(  # noqa: PLR0913
    msg: str,
    inputs: dict[str, Any] | None = None,
    locale: Locale | str | None = None,
    *,
    formatters: dict[str, Formatter] | None = None,
    selectors: dict[str, Selector] | None = None,
    markup: MarkupFormatter | None = None,
    on_error: Callable[[MessageFormatError], None] | None = None,
    bidi_isolation: bool = False,
) -> str:
    """Format a message.

    Use this function if you only need to format a message once.

    Examples:
        >>> format_message("Hello, {$name}!", {"name": "Alice"})
        'Hello, Alice!'
        >>> message = Message('''\\
        ... .input {$count :integer}
        ... .match $count
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
        markup: How to format markup (`{#b}...{/b}`). By default markup is formatted as an empty string.
        on_error: Called with each formatting error instead of raising it; the failed placeholder is
            formatted as a fallback value such as `{$name}`.
        bidi_isolation: Whether to isolate placeholders with bidi controls, see `Message.format()`.

    Returns:
        The formatted message.

    Raises:
        ParseError: If the message contains a syntax error.
        DataModelError: If the message contains a semantic error.
        FormatError: If the message cannot be formatted and `on_error` is not given.
    """
    return Message(msg).format(
        inputs,
        locale,
        formatters=formatters,
        selectors=selectors,
        markup=markup,
        on_error=on_error,
        bidi_isolation=bidi_isolation,
    )


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

    def format(  # noqa: PLR0913
        self,
        inputs: dict[str, Any] | None = None,
        locale: Locale | str | None = None,
        *,
        formatters: dict[str, Formatter] | None = None,
        selectors: dict[str, Selector] | None = None,
        markup: MarkupFormatter | None = None,
        on_error: Callable[[MessageFormatError], None] | None = None,
        bidi_isolation: bool = False,
    ) -> str:
        """Format the message.

        Examples:
            >>> message = Message("Hello, {$name}!")
            >>> message.format({"name": "Alice"})
            'Hello, Alice!'
            >>> message.format({"name": "Alice"}, bidi_isolation=True)
            'Hello, \u2068Alice\u2069!'
            >>> errors = []
            >>> message.format({}, on_error=errors.append)
            'Hello, {$name}!'
            >>> errors
            [UnresolvedVariable('Unresolved variable: name')]
            >>> message = Message('''\\
            ... .input {$count :integer}
            ... .match $count
            ... one {{You have one notification}}
            ... *   {{You have {$count} notifications}}''')
            >>> message.format({"count": 3}, "en")
            'You have 3 notifications'

        Args:
            locale: The locale in which to format the message. Defaults to the system locale.
            inputs: Input variables referenced by the message.
            formatters: Additional formatters.
            selectors: Additional selectors.
            markup: How to format markup (`{#b}...{/b}`). By default markup is formatted as an empty string;
                use `messageformat2.builtins.xml_markup` to get XML-ish tags.
            on_error: Called with each formatting error instead of raising it. The failed placeholder is
                formatted as a fallback value (`{$name}`, `{|literal|}` or `{:function}`) and a selector
                which fails only matches the catch-all key `*`.
            bidi_isolation: Whether to isolate placeholders from the surrounding text so that bidirectional
                text displays correctly, following the spec's Default Bidi Strategy: each placeholder whose
                direction is unknown or differs from the message's is wrapped in Unicode isolate controls
                (U+2066-U+2069); numbers and dates are formatted in the direction of the locale, strings and
                values of custom formatters have an unknown direction unless the `u:dir` option is set.
                Off by default, since the controls are invisible but change the string.

        Returns:
            The formatted message.

        Raises:
            FormatError: If the message cannot be formatted and `on_error` is not given.
        """
        if locale is None:
            locale = Locale.default()
        elif not isinstance(locale, Locale):
            locale = Locale.parse(locale)
        if inputs is None:
            inputs = {}
        registry = (
            default_registry
            if not formatters and not selectors and markup is None
            else default_registry.extend(formatters=formatters, selectors=selectors, markup=markup)
        )
        return _format_message(self._ast, locale, inputs, registry, on_error=on_error, bidi_isolation=bidi_isolation)

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

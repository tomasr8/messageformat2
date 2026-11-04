It is possible to write a custom formatter to extend the functionality of the
library. Here's an example of a simple formatter:

```python
from typing import Any
from messageformat2 import format_message

def capitalize(value: Any, locale, options) -> str:
    return value.capitalize()

format_message(
    "{|foo bar| :capitalize}",
    formatters={"capitalize": capitalize}
)
# -> "Foo bar"
```

A formatter function must take exactly 3 arguments:

- `value`: the value passed to the formatter when formatting
- `locale`: the current locale as a `babel.Locale` instance
- `options`: a dictionary containing all the options passed to the formatter.

The return value of this function is converted to string and displayed.

Here's an example using `options`:

```python
def capitalize(value: str, locale, options) -> str:
    if options.get('eachWord') == "yes":
        return value.title()
    return value.capitalize()

format_message(
    "{|foo bar| :capitalize eachWord=yes}",
    formatters={"capitalize": capitalize}
)
# -> "Foo Bar"
```

Any errors during the evaluation of the formatter will be automatically caught
and `messageformat2.errors.MessageFunctionError` will be reraised instead.

```python
from messageformat2.errors import MessageFunctionError

def raise_some_error(value, locale, options) -> str:
    raise ValueError("something went wrong")

try:
    format_message(
        "{foo :raise}",
        formatters={"raise": raise_some_error}
    )
except MessageFunctionError as e:
    print(e)  # -> Exception raised while evaluating formatter :raise
    print(repr(e.__cause__))  # -> ValueError('something went wrong')
```

To signal a specific error, a formatter can raise one of the `MessageFunctionError` subclasses
defined by the spec: `BadOperand` (wrong operand type or format), `BadOption` (invalid option or
option value), `BadVariantKey` (a variant key the selector cannot interpret) or `UnsupportedOperation`.
These are reraised as-is.

If the function can produce a result despite the error (the spec often asks to "emit a Bad Option error and
ignore the option"), pass it as `result`: when the message is formatted with an `on_error` callback
(see [Error handling](errors.md)), the error is reported and the result is used; otherwise the error is raised.

```python
from messageformat2.errors import BadOption

def shout(value, locale, options) -> str:
    result = str(value).upper()
    if options.get("volume", "loud") != "loud":
        raise BadOption("volume must be loud", result=result)
    return result
```

## Annotated operands

If the operand of your formatter is a variable that was already annotated with a function,
`value` is a `messageformat2.builtins.LazyValue` carrying the earlier function's name (`fn_name`),
operand (`value`) and resolved options (`options`). `str(value)` gives the formatted value of the earlier annotation.
It is up to your function to decide which operands it accepts and whether to inherit the earlier options;
raise `BadOperand` if your function cannot use the operand.

```python
from messageformat2.builtins import LazyValue
from messageformat2.errors import BadOperand

def shout(value, locale, options) -> str:
    if isinstance(value, LazyValue):
        if value.fn_name != "string":
            raise BadOperand(f"Cannot shout a :{value.fn_name}")
        value = str(value)
    return str(value).upper()

format_message(
    ".local $name = {alice :string} {{{$name :shout}}}",
    formatters={"shout": shout}
)
# -> "ALICE"
```

## Directionality

The result of a custom formatter has an unknown direction and is isolated with U+2068/U+2069 when the message
is formatted with `bidi_isolation=True` (see [Bidirectional text](../explanation.md#bidirectional-text)).
Return a `FormattedValue` to declare the direction instead, so that a value in the direction of the message
is not isolated:

```python
from messageformat2.builtins import FormattedValue

def shout(value, locale, options) -> FormattedValue:
    return FormattedValue(str(value).upper(), locale.text_direction)
```

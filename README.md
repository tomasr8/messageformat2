

# MessageFormat2

This is a Python implementation of the [Unicode MessageFormat
specification](https://messageformat.unicode.org/).

Unicode MessageFormat (MessageFormat 2.0, MF2) is a new iteration of MessageFormat which aims to be
more expressive and flexible than both MessageFormat 1.0 and, in the context of
Python, gettext.

## Features

The library includes:

- A message parser and a formatter, passing the official
  [test suite](https://github.com/unicode-org/message-format-wg/tree/main/test)
- All default functions described by the
  [spec](https://github.com/unicode-org/message-format-wg/blob/main/spec/functions/README.md)
  (`:string`, `:number`, `:integer`, `:offset`, `:percent`, `:currency`, `:date`, `:time`, `:datetime`)
  and the possibility to write custom formatters/selectors
- Formatting with fallback values and error reporting, optional bidi isolation of placeholders
- Helper classes to inspect and transform the message [data
  model](https://github.com/unicode-org/message-format-wg/blob/main/spec/data-model/README.md)

## Documentation

Documentation is available here: https://messageformat2.readthedocs.io/en/latest/

## Installation

Via pip for Python `>= 3.12`

```sh
pip install messageformat2
```

## Examples

### Simple messages

```python
from messageformat2 import format_message

format_message("Hello, {$name}!", {"name": "Alice"})  # -> "Hello, Alice!"
```

Messages can be reused with different inputs.

```python
from messageformat2 import Message

message = Message("Hello, {$name}!")
message.format({"name": "Alice"})  # -> "Hello, Alice!"
message.format({"name": "Bob"})  # -> "Hello, Bob!"
```

### Built-in formatters

There are several builtin locale-aware formatters available.

```python
from datetime import date
from messageformat2 import Message

message = Message("Today's date is {$today :date}")
today = date(2024, 5, 10)
message.format({"today": today}, locale="en_US")
# -> "Today's date is May 10, 2024"
message.format({"today": today}, locale="en_GB")
# -> "Today's date is 10 May 2024"

Message("{$price :currency currency=EUR}").format({"price": 42}, locale="de")
# -> "42,00\xa0€"
```

### Plural support

MF2 supports pluralization using built-in or custom selectors.

```python
from messageformat2 import Message

msg = Message ("""\
.input {$count :number}
.match $count
one {{You have {$count} notification.}}
*   {{You have {$count} notifications.}}
""")

msg.format({"count": 42}, locale='en_US') # -> "You have 42 notifications."
msg.format({"count": 1}, locale='en_US') # -> "You have 1 notification."
```

### Error handling

By default the first error is raised. To get the spec's fallback behaviour instead (`{$name}` for a
missing variable, etc.) and collect the errors, pass an `on_error` callback:

```python
errors = []
Message("Hello, {$name}!").format({}, on_error=errors.append)  # -> "Hello, {$name}!"
errors  # -> [UnresolvedVariable('Unresolved variable: name')]
```

### Bidirectional text

The spec's *Default Bidi Strategy* (wrapping placeholders in Unicode isolate controls so that mixed-direction
text displays correctly) is available with `bidi_isolation=True`:

```python
Message("Hello, {$name}!").format({"name": "Alice"}, bidi_isolation=True)
# -> "Hello, \u2068Alice\u2069!"
```

Complete documentation is available [here](https://messageformat2.readthedocs.io/en/latest/).

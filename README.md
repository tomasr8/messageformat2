

# MessageFormat2 [![Documentation Status](https://readthedocs.org/projects/messageformat2/badge/?version=latest)](https://messageformat2.readthedocs.io/en/latest/?badge=latest) [![CI](https://github.com/tomasr8/messageformat2/workflows/CI/badge.svg)](https://github.com/tomasr8/messageformat2/workflows/CI/badge.svg) [![Checked with pyright](https://microsoft.github.io/pyright/img/pyright_badge.svg)](https://microsoft.github.io/pyright/)

This is a Python implementation of the [Unicode Message Format 2.0
specification](https://www.unicode.org/reports/tr35/tr35-72/tr35-messageFormat.html).

Message Format 2.0 (MF2) is a new iteration of Message Format which aims to be
more expressive and flexible than both Message Format 1.0 and, in the context of
Python, gettext.

If you would like to learn more about MF2 itself head over to the [Unicode technical
specification](https://www.unicode.org/reports/tr35/tr35-72/tr35-messageFormat.html).

## Features

The library includes:

- A message parser and a formatter
- Several builtin formatters and selectors described by the
  [spec](https://www.unicode.org/reports/tr35/tr35-72/tr35-messageFormat.html#function-registry)
  and the possibility to write custom formatters/selectors
- Helper classes to inspect and transform the message [data
  model](https://www.unicode.org/reports/tr35/tr35-72/tr35-messageFormat.html#interchange-data-model)

## [Documentation](https://messageformat2.readthedocs.io/en/latest/)

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
from datetime import datetime
from messageformat2 import Message

message = Message("Today's date is {$now :date}")
now = datetime.now()
message.format({"now": now}, locale='en_US')
# -> Today's date is 5/10/2024
message.format({"now": now}, locale='en_GB')
# -> Today's date is 10/05/2024
```

### Plural support

MF2 supports pluralization using built-in or custom selectors.

```python
from messageformat2 import Message

msg = Message ("""\
.match {$count :number}
one {{You have {$count} notification.}}
*   {{You have {$count} notifications.}}
""")

msg.format({"count": 42}, locale='en_US') # -> "You have 42 notifications."
msg.format({"count": 1}, locale='en_US') # -> "You have 1 notification."
```

Complete documentation is available [here](https://messageformat2.readthedocs.io/en/latest/).

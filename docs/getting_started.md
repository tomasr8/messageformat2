## Installation

This package is available via `pip` for Python `>= 3.12`:

```sh
pip install messageformat2
```

## Simple messages

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

## Built-in formatters

There are several builtin locale-aware [formatters](builtins.md) available.

```python
from datetime import date
from messageformat2 import Message

message = Message("Today's date is {$today :date}")
today = date(2024, 5, 10)
message.format({"today": today}, locale="en_US")
# -> "Today's date is May 10, 2024"
message.format({"today": today}, locale="en_GB")
# -> "Today's date is 10 May 2024"
```

## Plural support

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

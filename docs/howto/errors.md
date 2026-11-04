# Error handling

Errors might be raised during parsing or during formatting. You can learn more
about MF2 errors
[here](https://github.com/unicode-org/message-format-wg/blob/main/spec/errors.md).

During parsing the following exceptions (or their subclasses) might be raised:

- `messageformat2.errors.ParseError` - for syntax errors
- `messageformat2.errors.DataModelError` - for semantic errors

During formatting the following exception (or its subclasses) might be raised:

- `messageformat2.errors.FormatError`

## Handling parsing errors

```python
from messageformat2.message import Message
from messageformat2.errors import ParseError, DataModelError

try:
    Message("}} invalid syntax")
except ParseError as e:
    print(e)  # -> Invalid character at the start of a simple message: }


try:
    Message("""\
.input {$count :integer}
.match $count
one {{The count is {$count}}}
""")
except DataModelError as e:
    print(e)  # -> Missing fallback variant
```

## Handling formatting errors

```python
from messageformat2.message import Message
from messageformat2.errors import FormatError

msg = Message("Hello, {$name}!")
try:
    msg.format()
except FormatError as e:
    print(e)  # -> Unresolved variable: name
```

## Formatting with fallback values

By default the first formatting error is raised and no output is produced. The spec requires
that a valid message can always be formatted, with
[fallback values](https://github.com/unicode-org/message-format-wg/blob/main/spec/formatting.md#fallback-resolution)
standing in for the parts that failed. Pass an `on_error` callback to get this behaviour: every error is
passed to the callback instead of being raised, and formatting continues.

```python
from messageformat2.message import Message

errors = []
msg = Message("Hello, {$name}! You have {$count :number} messages.")
msg.format({"count": "many"}, on_error=errors.append)
# -> "Hello, {$name}! You have {$count} messages."
errors
# -> [UnresolvedVariable('Unresolved variable: name'), BadOperand("Bad operand: 'many' is not a number")]
```

The fallback value is `{$name}` for a variable, `{|literal|}` for a literal operand and `{:function}` for a
function without an operand. An option whose value cannot be resolved is omitted, and a selector which fails
only matches the catch-all key `*`. Syntax and data model errors are still raised by `Message()`.

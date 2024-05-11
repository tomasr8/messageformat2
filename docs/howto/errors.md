# Error handling

Errors might be raised during parsing or during formatting. You can learn more
about MF2 errors
[here](https://www.unicode.org/reports/tr35/tr35-72/tr35-messageFormat.html#error-handling).

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
    print(e)  # -> Invalid syntax


try:
    Message("""\
.match {$count: integer}
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
    print(e)  # -> Unresolved variable
```

It is possible to write a custom formatter to extend the functionality of the
library. Here's an example of a simple formatter:

```python
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
and `messageformat2.errors.InvalidExpression` will be reraised instead.

```python
from messageformat2.errors import InvalidExpression

try:
    format_message(
        "{foo :raise}",
        formatters={"raise": raise_some_error}
    )
except InvalidExpression as e:
    print(e)
```

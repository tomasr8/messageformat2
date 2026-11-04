It is possible to write a custom selector to be used with the `.match`
statement.

Here's a simple implementation of the `:integer` selector:

```python
from typing import Any

from babel import Locale

from messageformat2 import format_message


def integer_selector(
    value: Any,  # The value passed to the selector while formatting the message
    locale: Locale,  # Babel locale
    options: dict[str, Any],  # Selector options
    keys: list[str],  # Variant keys to be filtered out
) -> list[str]:
    value = int(value)
    select = options.get("select", "plural")

    exact_keys = [key for key in keys if key == str(value)]
    if select == "exact":
        return exact_keys
    form = locale.ordinal_form(value) if select == "ordinal" else locale.plural_form(value)
    return exact_keys + [key for key in keys if key == form]


format_message("""\
.input {$count :integer select=plural}
.match $count
1   {{You have one notification.}}
one {{You have {$count} notification.}}
*   {{You have {$count} notifications.}}""",
    {"count": 1},
    selectors={"integer": integer_selector}
)
# -> "You have one notification."
```

A selector function must take exactly 4 arguments, which are passed by keyword (so they must have these names):

- `value`: the value passed to the selector when formatting
- `locale`: the current locale as a `babel.Locale` instance
- `options`: a dictionary containing all the options passed to the selector
- `keys`: the key from each variant of the match statement (the catch-all `*` is not included)

For example, for this message:

```
.input {$count :integer select=plural}
.match $count
1   {{You have one notification.}}
one {{You have {$count} notification.}}
*   {{You have ???}}
```

The selector would receive as arguments:

- `value=2`
- `locale=babel.Locale("en_US")`
- `options={"select": "plural"}`
- `keys=["1", "one"]`

The return value is another list of keys which is a subset of the passed keys.
Only those keys that match the selector shall be kept. If no keys match the
selector, an empty list should be returned. The keys are returned in
preferential order. `key[0]` should be prefered over `key[1]` and so on.

Specifically for `number` and `integer` selector exact matches (`1`, `2`, ..) are to be prefered over
keyword matches (`one`, `few`, `many`, ..).

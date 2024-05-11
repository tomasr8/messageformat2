It is possible to write a custom selector to be used with the `.match`
statement.

Here's a simple implementation of the `:integer` selector:

```python
def integer_selector(
    value: Any,  # The value passed to the selector while formatting the message
    *,
    locale: Locale,  # Babel locale
    options: dict[str, Any],  # Selector options
    keys: list[str]  # Variant keys to be filtered out
) -> list[str]:
    select = options.get("select", "plural")

    exact_keys = [value] if value in keys else []
    if select == "exact":
        return exact_keys
    if select == "plural":
        form = locale.plural_form(value)
    if select == "ordinal":
        form = locale.ordinal_form(value)
    return exact_keys + keyword_keys


format_message("""\
.match {$count :integer select=plural}
1   {{You have one notification.}}
one {{You have {$count} notification.}}
*   {{You have {$count} notifications.}}""",
    {"count": 1},
    selectors={"integer": integer_selector}
)
# -> You have one notification.
```

A selector function must take exactly 3 arguments:

- `value`: the value passed to the formatter when formatting
- `locale`: the current locale as a `babel.Locale` instance
- `options`: a dictionary containing all the options passed to the formatter.
- `keys`: The key from each variant of the match statement.

For example, for this message:

```python
.match {$count :integer select=plural}
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

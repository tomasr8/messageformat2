The default function registry includes these functions

in line with the [specification](https://github.com/unicode-org/message-format-wg/tree/main/spec/functions)

### `:string`

#### Formatter

As a formatter, this function simply calls `str(value)`.

#### Selector

As a selector, this function selects the exact match among the variant keys
(after NFC normalization of the value).

```python
format_message("""\
.input {$pet :string}
.match $pet
dog {{I have a dog}}
cat {{I have a cat}}
* {{I have a {$pet}}}
""", {"pet": "cat"})
# -> "I have a cat"
```

### `:number`

The operand must be an `int`, `float` or `Decimal` (but not a `bool`), or a string matching the
`number-literal` production of the spec (e.g. `|-1234.5|`, `|1e3|`; `|01|` or `|.5|` are not numbers).
The resolved value of another numeric function (`:number`, `:integer`) is also accepted, in which
case its options are inherited, with the options of the expression taking priority.

#### Formatter

- `signDisplay`
    - auto (default)
    - always
    - exceptZero
    - negative
    - never
- `useGrouping`
    - auto (default)
    - always
    - never
    - min2 (treated as auto)
- `minimumIntegerDigits`
- `minimumFractionDigits`
- `maximumFractionDigits`
- `minimumSignificantDigits`
- `maximumSignificantDigits`
- `numberingSystem` (implementation extension): a Unicode Number System Identifier

The digit options are *digit size options*: small non-negative integers (`0`-`99`).
Not implemented: `trailingZeroDisplay`, `roundingPriority`, `roundingIncrement`, `roundingMode` (these are ignored).

#### Selector

The selector takes the same options as the formatter in addition to:

- `select`
    - plural (default)
    - ordinal
    - exact

`select` must be set by a literal. The selector first tries an exact match between the number and
numeric keys (e.g. `1`), then (unless `select=exact`) matches the CLDR plural or ordinal category of the number
(`zero`, `one`, `two`, `few`, `many`, `other`). Any other key is a `BadVariantKey` error.

### `:integer`

Same as `:number`, but the operand is truncated to an integer. The `minimumFractionDigits`, `maximumFractionDigits`
and `minimumSignificantDigits` options of an annotated operand are discarded.

### `:datetime`

The value must either a `datetime` instance or an ISO8601 string that can be parsed using `datetime.fromisoformat`.

#### Formatter

- `Datestyle`
    - full
    - long
    - medium
    - short (default)
- `timeStyle` (not implemented)
- `weekday`:
    - long
    - short
    - narrow
- `era`:
    - long
    - short
    - narrow
- `year`:
    - numeric
    - 2-digit
- `month`:
    - numeric
    - 2-digit
- `day`:
    - numeric
    - 2-digit
- `hour`:
    - numeric
    - 2-digit
- `minute`:
    - numeric
    - 2-digit
- `second`:
    - numeric
    - 2-digit
- `fractionalSecondDigits`:
    - 1
    - 2
    - 3
- `hourCycle`:
    - h11
    - h12
    - h23
    - h24
- `timeZoneName` (not implemented)

#### Selector

The `:date` selector is not supported currently as it is not required by MF2

### `:date`

The value must either a `datetime` instance or an ISO8601 string that can be parsed using `datetime.fromisoformat`.

#### Formatter

- `style`
    - full
    - long
    - medium
    - short (default)

#### Selector

The `:date` selector is not supported currently as it is not required by MF2

### `:time`

The value must either a `datetime.time` instance

#### Formatter

- `style`
    - full
    - long
    - medium
    - short (default)

#### Selector

The `:time` selector is not supported currently as it is not required by MF2

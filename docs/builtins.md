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
The resolved value of another numeric function (`:number`, `:integer`, `:offset`) is also accepted, in which
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

### `:offset`

Adds or subtracts a small integer from a numeric operand, e.g. to count "other" users:

```python
.input {$likes :integer}
.local $others = {$likes :offset subtract=1}
```

Exactly one of the options must be given:

- `add`
- `subtract`

The formatting options of an annotated operand (e.g. `signDisplay` of `{$likes :integer signDisplay=always}`)
are inherited. `:offset` can also be used as a selector, in which case it behaves like `:number`.

### `:datetime`, `:date`, `:time`

The operand must be a `datetime` (or a `date`/`time` for `:date`/`:time` respectively) or an ISO 8601 date or
datetime string that can be parsed with `datetime.fromisoformat`, e.g. `|2006-01-02|` or `|2006-01-02T15:04:06+01:00|`.
The resolved value of another date/time function is also accepted, in which case its override options
(`timeZone`, `hour12`) are inherited.

The option values below must be set by literals (an option set by a variable is a `BadOption` error).

#### `:datetime`

- `dateFields`
    - weekday
    - day-weekday
    - month-day
    - month-day-weekday
    - year-month-day (default)
    - year-month-day-weekday
- `dateLength`
    - long
    - medium (default)
    - short
- `timePrecision`
    - hour
    - minute (default)
    - second
- `timeZoneStyle`: no time zone is shown unless set
    - long
    - short

#### `:date`

- `fields`: same values as `dateFields` above
- `length`: same values as `dateLength` above

#### `:time`

- `precision`: same values as `timePrecision` above
- `timeZoneStyle`: same values as above

#### Override options

- `timeZone`: `UTC`, `input` (the time zone of the operand, which must then have one), an IANA time zone
  name (`|Europe/Zurich|`) or an offset (`|+01:00|`). A naive `datetime` is interpreted in this time zone,
  an aware one is converted to it.
- `hour12`: `true` or `false` (`:datetime` and `:time` only); the default is locale-dependent.
- `calendar`: not implemented (ignored).

#### Selector

The date/time functions do not support selection, as it is not required by MF2.

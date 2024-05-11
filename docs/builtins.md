The default function registry includes these functions

in line with the specification in the CLDR 45 technical preview

### `:string`

#### Formatter

As a formatter, this functions simply call `str(value)`

#### Selector

As a selector, this function simply selects the exact match among the variant keys

```python
format_message("""\
.match {$pet :string}
dog {{I have a dog}}
cat {{I have a cat}}
* {{I have a {$pet}}}
""", {"pet": "cat"})
# -> "I have a cat"
```

### `:number`

#### Formatter

- `compactDisplay`
    - short (default)
    - long
- notation
    - standard
    - scientific
    - engineering (not implemented)
    - compact
- `numberingSystem`
    valid Unicode Number System Identifier (default is locale-specific)
- `signDisplay` (not implemented)
- `style`
    - decimal (default)
    - percent
- `useGrouping`
    - auto (default)
    - always
    - min2
- `minimumFractionDigits` (not implemented)
- `maximumFractionDigits` (not implemented)

#### Selector

The selector takes the same options as the formatter in addition to:

- `select`
    - plural (default)
    - ordinal
    - exact

The selector does exact string comparison with the variant keys but also keyword comparisons.

### `:integer`

#### Formatter

- `numberingSystem`
    valid Unicode Number System Identifier (default is locale-specific)
- `signDisplay` (not implemented)
- `style`
    - decimal (default)
    - percent
- `useGrouping`
    - auto (default)
    - always
    - min2
- `minimumIntegerDigits` (not implemented)
- `maximumSignificantDigits` (not implemented)

#### Selector

The selector takes the same options as the formatter in addition to:

- `select`
    - plural (default)
    - ordinal
    - exact

The selector does exact string comparison with the variant keys but also keyword comparisons.

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

## Runtime model

All expressions are lazily evaluated at the time of use.
If the same variable is referenced more than once, it will also be evaluated more than once.
Pay attention when providing custom formatters/selectors with side effects:

```python
from messageformat2 import Message

counter = 0

def formatter_with_side_effect(value, locale, options):
    global counter
    counter += 1
    return str(value)

msg = Message("""\
.local $foo = {|foo| :side_effect}
{{{$foo} {$foo}}}
""")
msg.format(formatters={"side_effect": formatter_with_side_effect})
print(counter)  # -> 2
```

## Unannotated variables

A placeholder consisting only of a variable (`{$x}`) is formatted according to the type of its value:
numbers (`int`, `float`, `Decimal`) as if annotated with `:number`, `datetime`, `date` and `time` values with
`:datetime`, `:date` and `:time`. Anything else is formatted with `str()`.
Literals are always strings, so `{|1234.5|}` is formatted verbatim.

## Bidirectional text

Following the spec's *Default Bidi Strategy*, placeholders are wrapped in Unicode isolate controls so that
mixed left-to-right and right-to-left text displays correctly: a value whose direction is unknown (strings,
literals, the results of custom formatters) is wrapped in U+2068 FIRST STRONG ISOLATE … U+2069 POP DIRECTIONAL
ISOLATE, a value whose direction differs from the message's (e.g. a number, which has the direction of the
locale, in a message formatted in an RTL locale) in U+2066 LEFT-TO-RIGHT ISOLATE / U+2067 RIGHT-TO-LEFT ISOLATE.

```python
Message("Hello, {$name}!").format({"name": "Alice"})  # -> "Hello, \u2068Alice\u2069!"
Message("{$n :number} items").format({"n": 3})          # -> "3 items" (same direction, no isolation)
```

The controls are invisible but do change the string, so pass `bidi_isolation="none"` if you compare or
post-process the output. The `u:dir` option sets the direction of a placeholder (`ltr`, `rtl` or `auto`) and
forces its isolation: `{$name :string u:dir=rtl}`. Custom formatters can return a
`messageformat2.builtins.FormattedValue(text, direction)` to declare the direction of their output.

## Function composition

A variable which was annotated with a function can be annotated again, for example in a placeholder.
The function handler then receives the resolved value of the earlier annotation
(a `messageformat2.builtins.LazyValue` carrying the earlier function's name, operand and options) as its operand,
and decides what to do with it. The built-in numeric functions accept each other's resolved values
and inherit their options, with the options of the later expression taking priority:

```python
from messageformat2 import format_message

format_message(".local $x = {42 :number minimumFractionDigits=2 signDisplay=always} {{x = {$x :number minimumFractionDigits=1}}}")
# -> "x = +42.0"
format_message(".local $x = {1.25 :integer} {{x = {$x :number}}}")
# -> "x = 1"
```

whereas e.g. `{$x :date}` would raise `BadOperand`. See [Custom formatters](howto/formatter.md) for how to
handle such operands in your own functions.

## Whitespace

This library implements the [grammar](https://github.com/unicode-org/message-format-wg/blob/main/spec/message.abnf) exactly as specified which includes whitespace.

Whitespace around a complex message (a message containing declarations and/or a match block) is not significant,
so complex messages can be freely indented, e.g. in multiline strings:

```python
from messageformat2 import Message

Message("""
    .input {$count :integer}
    .match $count
    * {{count is {$count}}}
""")
```

Whitespace in a simple message (a message consisting of a single pattern) is always significant
and is part of the message text. Note that the first non-whitespace character of a simple message
cannot be a `.`, so a misspelled keyword (`.imput`) is a syntax error rather than silently becoming text.
To get a pattern which starts with a `.`, use a quoted pattern:

```python
Message("{{.input is not a keyword here}}")
```

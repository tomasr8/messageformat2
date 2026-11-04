## Runtime model

All expressions are lazily evaluated at the time of use.
If the same variable is referenced more than once, it will also be evaluated more than once.
Pay attention when providing custom formatters/selectors with side effects:

```python
counter = 0

def formatter_with_side_effect(value, locale, options):
    nonlocal counter
    counter +=1
    return str(value)

msg = Message("\
.local $foo = {|foo| :side_effect}
{{{$foo} {$foo}}}
")
msg.format(formatters={'side_effect': formatter_with_side_effect})
print(counter)  # -> 2
```

## Function composition

A variable which was annotated with a function can be annotated again, for example in a placeholder.
The function handler then receives the resolved value of the earlier annotation
(a `messageformat2.builtins.LazyValue` carrying the earlier function's name, operand and options) as its operand,
and decides what to do with it. The built-in numeric functions accept each other's resolved values
and inherit their options, with the options of the later expression taking priority:

```python
.local $x = {42 :number minimumFractionDigits=2 signDisplay=always}
{{x = {$x :number minimumFractionDigits=1}}}  # -> "x = +42.0"

.local $x = {1.25 :integer}
{{x = {$x :number}}}  # -> "x = 1"
```

whereas e.g. `{$x :date}` would raise `BadOperand`. See [Custom formatters](howto/formatter.md) for how to
handle such operands in your own functions.

## Whitespace

This library implements the [grammar](https://www.unicode.org/reports/tr35/tr35-72/tr35-messageFormat.html#complete-abnf) exactly as specified which includes whitespace.

Whitespace around a complex message (a message containing declarations and/or a match block) is not significant,
so complex messages can be freely indented, e.g. in multiline strings:

```python
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

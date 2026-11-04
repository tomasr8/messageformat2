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

Composition of functions is only allowed for the same functions:

```python
.local $x {42 :integer}
{{x = {$x :integer}}}
```

This will raise an exception:

```python
.local $x {42 :integer}
{{x = {$x :string}}}
```

Options are merged together with the later options overwritting any earlier options:

```python
.local $date {|2024-05-10| :date style=short}
{{date = {$date :date style=full}}}
```

## Whitespace

This library implements the [grammar](https://www.unicode.org/reports/tr35/tr35-72/tr35-messageFormat.html#complete-abnf) exactly as specified which includes whitespace.

Whitespace around a complex message (a message containing declarations and/or a match block) is not significant,
so complex messages can be freely indented, e.g. in multiline strings:

```python
Message("""
    .match {$count :integer}
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

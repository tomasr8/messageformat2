This part of the project documentation focuses on an
**understanding-oriented** approach. You'll get a
chance to read about the background of the project,
as well as reasoning about how it was implemented.

> **Note:** Expand this section by considering the
> following points:

- Give context and background on your library
- Explain why you created it
- Provide multiple examples and approaches of how
  to work with it
- Help the reader make connections
- Avoid writing instructions or technical descriptions
  here

Invalid syntax
A complex message cannot start with leading whitespace. Such a message is treated as a simple message by the grammar

## Whitespace

This library implements the [grammar](https://www.unicode.org/reports/tr35/tr35-72/tr35-messageFormat.html#complete-abnf) exactly as specified which includes whitespace.
According to the grammar, complex messages (messages containing declarations and/or the match block) cannot have a leading whitespace. For example, this message:

```python
    .match {$count :integer}
* {{count is {$count}}}
```

will be parsed as a simple message (message not containing any declarations/match blocks, only patterns `{...}`). The parsing will fail
because a pattern cannot contain unescaped `{`.

When defining complex messages using multiline strings, don't forget to use a leading `\` to remove the first newline character:

```python
Message("""\  # <- notice the backslash
.match {$count: integer}
* {{count is {$count}}}""")
```

```python
Message(""".match {$count: integer}
* {{count is {$count}}}""")
```

## Computation model

All expressions are lazily evaluated at the time of use. If the same variable if referenced more than once, it will be evaaluated more than once.
IF you have formatters/selectors with side effects be careful.

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

Composition of functions is only allowed for the same functions i.e.

```python
.local $x {42 :integer}
{{x = {$x :integer}}}
```

```python
.local $x {42 :integer}
{{x = {$x :string}}}
```

Options are merged together with the later options overwritting any earlier options

```python
.local $date {|2024-05-10| :date style=short}
{{date = {$date :date style=full}}}
```

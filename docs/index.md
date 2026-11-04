This site contains documentation for the `messageformat2`, a Python library
which implements the [Unicode MessageFormat
specification](https://www.unicode.org/reports/tr35/tr35-messageFormat.html) (LDML 49).

Unicode MessageFormat (MessageFormat 2.0, MF2) is a new iteration of MessageFormat which aims to be
more expressive and flexible than both MessageFormat 1.0 and, in the context of
Python, gettext.

If you would like to learn more about MF2 itself head over to the [Unicode technical
specification](https://www.unicode.org/reports/tr35/tr35-messageFormat.html).

## Features

The `messageformat2` library includes:

- A message parser and a formatter, passing the official
  [test suite](https://github.com/unicode-org/message-format-wg/tree/main/test)
- All default functions described by the
  [spec](https://github.com/unicode-org/message-format-wg/blob/main/spec/functions/README.md)
  (`:string`, `:number`, `:integer`, `:offset`, `:percent`, `:currency`, `:date`, `:time`, `:datetime`)
  and the possibility to write custom formatters/selectors
- Formatting with fallback values and error reporting, optional bidi isolation of placeholders
- Helper classes to inspect and transform the message [data
  model](https://github.com/unicode-org/message-format-wg/blob/main/spec/data-model/README.md)

### Work in progress

- Message extraction and loading - This will be provided once a format for MF2
  [message resources](https://github.com/eemeli/message-resource-wg) is
  standardized.

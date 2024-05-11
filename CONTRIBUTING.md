# Contributing to MessageFormat2

You can help improve this project by either opening issues or submitting pull requests for

- bugs
- differing behaviour between the package and [official specification](https://www.unicode.org/reports/tr35/tr35-72/tr35-messageFormat.html)
- documentation
- implementing missing features (e.g. missing options for formatters)

## Dev setup

Clone the repository and then run this command to install the package in editable mode:

```sh
pip install -e .[dev]
```

### Running tests

```sh
pytest --doctest-modules
```

### Code quality

```sh
pyright tests/ messageformat2/
ruff check tests/ messageformat2/
```

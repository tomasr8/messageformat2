# Unicode MessageFormat test suite

These JSON files are a verbatim copy of the official test suite from
https://github.com/unicode-org/message-format-wg/tree/main/test/tests
(commit `16372a6a02f41728be472a5921ba7c91774edeac`, 2026-10-19) and are run by `tests/test_spec.py`.

To update them:

```sh
git clone --depth 1 https://github.com/unicode-org/message-format-wg.git /tmp/mfwg
cp /tmp/mfwg/test/tests/*.json tests/spec/
cp /tmp/mfwg/test/tests/functions/*.json tests/spec/functions/
```

and update the commit hash above.

Tests tagged with optional features which are not implemented
(`:currency`, `:percent`, `u:dir`, `u:id`) are skipped, see `tests/test_spec.py`.

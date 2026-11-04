from messageformat2.parser import (
    escaped_char,
    markup_start,
    quoted_char,
    reserved_char,
    reserved_escape,
    simple_start_char,
    text_char,
    whitespace,
)


def test_whitespace():
    chars = [" ", "\t", "\r", "\n", "\u3000"]
    for c in chars:
        assert whitespace.match(c) is not None


def test_escaped_char():
    assert escaped_char.match(r"\\") is not None
    assert escaped_char.match(r"\{") is not None
    assert escaped_char.match(r"\|") is not None
    assert escaped_char.match(r"\}") is not None
    assert escaped_char.match(r"\n") is None
    assert escaped_char.match(r"\\\\") is not None


def test_reserved_escape():
    assert reserved_escape.match(r"\\") is not None
    assert reserved_escape.match(r"\{") is not None
    assert reserved_escape.match(r"\|") is not None
    assert reserved_escape.match(r"\}") is not None


def test_simple_start_char():
    chars = [
        "\u0001",
        "\u0008",
        "\u000b",
        "\u000c",
        "\u000e",
        "\u001f",
        "\u0021",
        "\u002d",
        "\u002f",
        "\u003f",
        "\u0041",
        "\u005b",
        "\u005d",
        "\u007a",
        "\u007e",
        "\u2fff",
        "\u3001",
        "\ud7ff",
        "\ue000",
        "\U0010ffff",
        "@",
        "|",
        "a",
        "b",
        "H",
    ]
    for c in chars:
        assert simple_start_char.match(c) is not None
    for c in [".", " ", "\t", "\r", "\n", "\u3000", "{", "}", "\\"]:
        assert simple_start_char.match(c) is None


def test_text_char():
    chars = [
        "\u0001",
        "\u0008",
        "\u000b",
        "\u000c",
        "\u000e",
        "\u001f",
        "\u0021",
        "\u002d",
        "\u002f",
        "\u003f",
        "\u0041",
        "\u005b",
        "\u005d",
        "\u007a",
        "\u007e",
        "\u2fff",
        "\u3001",
        "\ud7ff",
        "\ue000",
        "\U0010ffff",
        " ",
        "\t",
        "\r",
        "\n",
        "\u3000",
        ".",
        "@",
        "|",
    ]
    for c in chars:
        assert text_char.match(c) is not None


def test_quoted_char():
    chars = [
        "\u0001",
        "\u0008",
        "\u000b",
        "\u000c",
        "\u000e",
        "\u001f",
        "\u0021",
        "\u002d",
        "\u002f",
        "\u003f",
        "\u0041",
        "\u005b",
        "\u005d",
        "\u007a",
        "\u007e",
        "\u2fff",
        "\u3001",
        "\ud7ff",
        "\ue000",
        "\U0010ffff",
        " ",
        "\t",
        "\r",
        "\n",
        "\u3000",
        ".",
        "@",
        "{",
        "}",
    ]
    for c in chars:
        assert quoted_char.match(c) is not None


def test_reserved_char():
    chars = [
        "\u0001",
        "\u0008",
        "\u000b",
        "\u000c",
        "\u000e",
        "\u001f",
        "\u0021",
        "\u002d",
        "\u002f",
        "\u003f",
        "\u0041",
        "\u005b",
        "\u005d",
        "\u007a",
        "\u007e",
        "\u2fff",
        "\u3001",
        "\ud7ff",
        "\ue000",
        "\U0010ffff",
        ".",
    ]
    for c in chars:
        assert reserved_char.match(c) is not None


def test_markup_start():
    assert markup_start.match("{#") is not None
    assert markup_start.match("{/") is not None
    assert markup_start.match("{") is None
    assert markup_start.match("#") is None
    assert markup_start.match("/") is None

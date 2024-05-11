from messageformat2.parser import (
    content_char,
    markup_start,
    quoted_char,
    quoted_escape,
    reserved_char,
    reserved_escape,
    simple_start_char,
    text_char,
    text_escape,
    whitespace,
)


def test_whitespace():
    chars = [" ", "\t", "\r", "\n", "\u3000"]
    for c in chars:
        assert whitespace.match(c) is not None


def test_text_escape():
    assert text_escape.match(r"\\") is not None
    assert text_escape.match(r"\{") is not None
    assert text_escape.match(r"\}") is not None


def test_quoted_escape():
    assert quoted_escape.match(r"\\") is not None
    assert quoted_escape.match(r"\|") is not None


def test_reserved_escape():
    assert quoted_escape.match(r"\\") is not None
    assert reserved_escape.match(r"\{") is not None
    assert reserved_escape.match(r"\|") is not None
    assert reserved_escape.match(r"\}") is not None


def test_content_char():
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
        "a",
        "b",
        "H",
    ]
    for c in chars:
        assert content_char.match(c) is not None


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
        " ",
        "\t",
        "\r",
        "\n",
        "\u3000",
        "@",
        "|",
        "a",
        "b",
        "H",
    ]
    for c in chars:
        assert simple_start_char.match(c) is not None


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

# def test_whitespace():
#     chars = [" ", "\t", "\r", "\n", "\u3000"]
#     for c in chars:
#         assert whitespace.match(c)


# def test_text_escape():
#     assert text_escape.match(r"\\")
#     assert text_escape.match(r"\{")
#     assert text_escape.match(r"\}")


# def test_quoted_escape():
#     assert quoted_escape.match(r"\\")
#     assert quoted_escape.match(r"\|")


# def test_reserved_escape():
#     assert quoted_escape.match(r"\\")
#     assert reserved_escape.match(r"\{")
#     assert reserved_escape.match(r"\|")
#     assert reserved_escape.match(r"\}")


# def test_content_char():
#     chars = [
#         "\u0001", "\u0008", "\u000B", "\u000C", "\u000E", "\u001F", "\u0021",
#         "\u002D", "\u002F", "\u003F", "\u0041", "\u005B", "\u005D", "\u007A",
#         "\u007E", "\u2FFF", "\u3001", "\uD7FF", "\uE000", "\U0010FFFF",
#         "a", "b", 'H'
#     ]
#     for c in chars:
#         assert content_char.match(c)


# def test_simple_start_char():
#     chars = [
#         "\u0001", "\u0008", "\u000B", "\u000C", "\u000E", "\u001F", "\u0021",
#         "\u002D", "\u002F", "\u003F", "\u0041", "\u005B", "\u005D", "\u007A",
#         "\u007E", "\u2FFF", "\u3001", "\uD7FF", "\uE000", "\U0010FFFF", " ",
#         "\t", "\r", "\n", "\u3000", "@", "|", "a", "b", 'H'
#     ]
#     for c in chars:
#         assert simple_start_char.match(c)


# def test_text_char():
#     chars = [
#         "\u0001", "\u0008", "\u000B", "\u000C", "\u000E", "\u001F", "\u0021",
#         "\u002D", "\u002F", "\u003F", "\u0041", "\u005B", "\u005D", "\u007A",
#         "\u007E", "\u2FFF", "\u3001", "\uD7FF", "\uE000", "\U0010FFFF", " ",
#         "\t", "\r", "\n", "\u3000", ".", "@", "|"
#     ]
#     for c in chars:
#         assert text_char.match(c)


# def test_quoted_char():
#     chars = [
#         "\u0001", "\u0008", "\u000B", "\u000C", "\u000E", "\u001F", "\u0021",
#         "\u002D", "\u002F", "\u003F", "\u0041", "\u005B", "\u005D", "\u007A",
#         "\u007E", "\u2FFF", "\u3001", "\uD7FF", "\uE000", "\U0010FFFF", " ",
#         "\t", "\r", "\n", "\u3000", ".", "@", "|", "{", "}"
#     ]
#     for c in chars:
#         assert quoted_char.match(c)


# def test_reserved_char():
#     chars = [
#         "\u0001", "\u0008", "\u000B", "\u000C", "\u000E", "\u001F", "\u0021",
#         "\u002D", "\u002F", "\u003F", "\u0041", "\u005B", "\u005D", "\u007A",
#         "\u007E", "\u2FFF", "\u3001", "\uD7FF", "\uE000", "\U0010FFFF", "."
#     ]
#     for c in chars:
#         assert reserved_char.match(c)


# def test_markup_start():
#     assert markup_start.match("{#")
#     assert markup_start.match("{/")
#     assert not markup_start.match("{")
#     assert not markup_start.match("#")
#     assert not markup_start.match("/")

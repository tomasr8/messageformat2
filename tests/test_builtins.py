import pytest

from messageformat2 import Message
from messageformat2.errors import BadOperand, BadSelector


def test_string_selection():
    message = ".input {$s :string} .match $s |1| {{one}} dog {{dog}} * {{other}}"
    assert Message(message).format({"s": "1"}) == "one"
    assert Message(message).format({"s": 1}) == "one"
    assert Message(message).format({"s": "dog"}) == "dog"
    assert Message(message).format({"s": "cat"}) == "other"


def test_string_selection_is_nfc_normalized():
    message = ".local $x = {D\u0323\u0307 :string} .match $x \u1e0c\u0307 {{Right}} * {{Wrong}}"
    assert Message(message).format() == "Right"


def test_string_errors():
    with pytest.raises(BadOperand):
        Message("{:string}").format()
    with pytest.raises(BadSelector):
        Message(".local $d = {|2024-05-01| :date} .match $d * {{The due date is {$d}}}").format()

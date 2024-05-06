from messageformat2 import format_message as _, register_function


register_function("date", lambda value: "2024-06-07")
register_function("integer", formatter=lambda value: int(value), selector=lambda value, keys: ("1", "one"))
register_function("integer", selector=lambda value, keys: ("1", "one"))


_("Hello, World!")
# => "Hello, World!"
_("Hello, {$name}!", name="Alice")
# => "Hello, Alice!"
_(
    """\
.match {$count :integer}
one {{You have {$count} notification.}}
few {{You have {$count} notifications.}}
many {{You have many notifications.}}""",
    inputs={"count": 42},
    registry={"integer": lambda value: ("1", "one")},
)
# => "You have 42 notifications."

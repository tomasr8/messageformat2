The `Message` class has a `datamodel` property which gives you access to the
message data model which is based on the [MF2
spec](https://www.unicode.org/reports/tr35/tr35-72/tr35-messageFormat.html#interchange-data-model).
The data model nodes are documented [here](/datamodel).

There are two classes to work with the datamodel - `DataModelVisitor` &
`DataModelTransformer`.

## Inspecting the data model

All the data model nodes have implemented `__str__` and `__repr__` for easier
debugging and inspection.

```python
from messageformat2 import Message
from messageformat2.datamodel import dump

msg = Message("Hello, {$name}!")
dump(msg.datamodel)  # -> 'Hello, {$name}!'
# Same as calling .dump()
str(msg.datamodel)  # -> 'Hello, {$name}!'
repr(msg.datamodel)  # -> "PatternMessage(declarations=[], pattern=['Hello, ', VariableExpression(arg=VariableRef(name='name'), annotation=None, attributes=[]), '!'])"
```

## Walking the data model

Here is how you can walk the parsed data model syntax tree:

```python
from messageformat2 import Message
from messageformat2.datamodel import DataModelVisitor

class VariableVisitor(DataModelVisitor):
    def visit_VariableRef(self, node):
        print(f"${node.name}")
        self.generic_visit(node)

message = Message("Hello, {$name}!")
visitor = VariableVisitor()
visitor.visit(message.datamodel)
# -> "$name"
```

## Transforming the data model

Use the transformer class to modify the data model:

```python
from messageformat2 import Message
from messageformat2.datamodel import Literal, DataModelTransformer

class LiteralTransformer(DataModelTransformer):
    def visit_Literal(self, node):
        return Literal(node.value.upper())

message = Message("{|foo|}")
ast = LiteralTransformer().visit(message.datamodel)
str(ast)
# -> "{|FOO|}"
```

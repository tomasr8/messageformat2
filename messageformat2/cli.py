import ast
import hashlib
from pathlib import Path
from typing import Any

import click

import messageformat2


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True)
@click.pass_context
def cli(ctx: Any, version: bool) -> None:  # noqa: FBT001
    if ctx.invoked_subcommand is None:
        if version:
            click.echo(messageformat2.__version__)
        else:
            click.echo(ctx.get_help())


@cli.command()
@click.argument("filename", type=click.Path(exists=True))
def extract(filename: Path) -> None:
    """Extract messages."""
    filename = Path(filename)

    class MessageExtractor(ast.NodeVisitor):
        def __init__(self) -> None:
            super().__init__()
            self.messages = []

        def visit_Call(self, node: ast.Call) -> None:
            match node:
                case ast.Call(func=ast.Name(id="_"), args=[ast.Constant(value=message), *_]):
                    self.messages.append(message)
            self.generic_visit(node)

    files = filename.rglob("*.py") if filename.is_dir() else [filename]

    extractor = MessageExtractor()
    for f in files:
        source = f.read_text()
        tree = ast.parse(source)
        extractor.visit(tree)

    output = ""
    for message in extractor.messages:
        msg_id = hashlib.sha256(message.encode()).hexdigest()
        output += f"{msg_id} = {message}\n\n"
    click.echo(output)

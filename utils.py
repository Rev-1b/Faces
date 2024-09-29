import click
import sys


def safe_prompt(text, **kwargs):
    response = click.prompt(text, **kwargs)
    if response.lower() == 'exit':
        click.echo("Программа завершена.")
        sys.exit(0)
    return response


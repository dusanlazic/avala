import click
from .main import main as server_main
from .main import initialize_workspace
from .main import test_setup
from .workers.persister import main as persister_main
from .workers.submitter import main as submitter_main


@click.group()
def cli():
    pass


@cli.command()
def server():
    server_main()


@cli.command()
def persister():
    persister_main()


@cli.command()
def submitter():
    submitter_main()


@cli.command()
def init():
    initialize_workspace()


@cli.command()
def test():
    test_setup()


if __name__ == "__main__":
    cli()

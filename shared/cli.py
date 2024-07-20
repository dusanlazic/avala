import click
from server.main import main as server_main
from server.workers.persister import main as persister_main
from server.workers.submitter import main as submitter_main
from client.main import main as client_main
from client.test import attack


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
def client():
    client_main()


@cli.command()
@click.argument("script")
@click.argument("target")
@click.argument("service", required=False)
def test(script, target, service):
    attack(script, target, service)


if __name__ == "__main__":
    cli()

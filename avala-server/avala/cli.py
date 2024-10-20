import click


def show_banner():
    """
    Shows the Avala banner. Needs to be called before any imports to ensure
    the banner is shown before any other output.
    """
    print(
        """\033[32;1m
      db 
     ;MM:
    ,V^MM. 7MM""Yq.  ,6"Yb.  `7M""MMF',6"Yb.  
   ,M  `MM `MM   j8 8)   MM    M  MM 8)   MM  
   AbmmmqMA MM""Yq.  ,pm9MM   ,P  MM  ,pm9MM  
  A'     VML`M   j8 8M   MM . d'  MM 8M   MM  
.AMA.   .AMMA.mmm9' `Moo9^Yo8M' .JMML`Moo9^Yo.
\033[0m"""
    )


@click.group()
def cli():
    pass


@cli.command()
def server():
    show_banner()
    from .main import main as server_main

    server_main()


@cli.command()
def persister():
    from .workers.persister import main as persister_main

    persister_main()


@cli.command()
def submitter():
    from .workers.submitter import main as submitter_main

    submitter_main()


@cli.command()
def init():
    from .initialization import initialize_workspace

    initialize_workspace()


@cli.command()
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
def test(verbose):
    from .setup_tests import main as tests_main

    tests_main(verbose=verbose)


if __name__ == "__main__":
    cli()

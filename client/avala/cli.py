import importlib.util
import io
import json
import os
import sys
from types import ModuleType
from typing import Any

import click

from .logging import colorize
from .main import Avala


def _import_module_from_path(path: str) -> ModuleType:
    """Import a Python module from a filesystem path."""
    path = os.path.abspath(path)
    if os.path.isdir(path):
        init_path = os.path.join(path, "__init__.py")
        if not os.path.exists(init_path):
            raise FileNotFoundError(f"No __init__.py found in directory: {path}")
        module_name = os.path.basename(path)
        spec = importlib.util.spec_from_file_location(module_name, init_path)
    else:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        module_name = os.path.splitext(os.path.basename(path))[0]
        spec = importlib.util.spec_from_file_location(module_name, path)

    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from path: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def _find_avala_instance(mod: ModuleType) -> Any:
    """Return an object in the module that is an instance of Avala."""
    for _, obj in vars(mod).items():
        if obj is None:
            continue
        if isinstance(obj, Avala):
            return obj
    raise AttributeError(
        "Could not find an instance of 'Avala' in the imported module. "
        "Please ensure your file defines an Avala instance."
    )


def _load_avala(path: str | None = None) -> Any:
    """
    Load an Avala instance from:
    - the given --path (file or package directory), or
    - './app.py' by default.
    """
    target = path or os.path.join(os.getcwd(), "app.py")
    mod = _import_module_from_path(target)
    return _find_avala_instance(mod)


def _stdin_has_data() -> bool:
    return not sys.stdin.isatty()


def _require_avala(ctx: click.Context) -> Any:
    obj: Context | None = getattr(ctx, "obj", None)  # type: ignore[assignment]
    if obj is None or obj.avala is None:
        tried = getattr(obj, "module_path", os.path.join(os.getcwd(), "app.py")) if obj else "app.py"
        message = [
            "No Avala instance available.",
            f"Tried to import: {tried}",
        ]
        if obj and obj.load_error:
            message.append(f"Cause: {obj.load_error}")
        message.append(
            "\nTips:\n"
            "  - Ensure your module defines an Avala instance at module scope.\n"
            "  - Use --path to point to a different file, e.g. --path ./hello.py\n"
            "  - Run 'avl init' to scaffold a client."
        )
        raise click.ClickException("\n".join(message))
    return obj.avala


class Context:
    def __init__(
        self,
        avala: Avala,
        module_path: str,
        load_error: str | None = None,
    ) -> None:
        self.avala = avala
        self.module_path = module_path
        self.load_error = load_error


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--path",
    "path_",
    type=click.Path(exists=False, dir_okay=True, file_okay=True, readable=True, path_type=str),
    default=None,
    help="Path to a Python file (e.g. ./hello.py) or package that exports an Avala instance. Defaults to ./app.py.",
)
@click.pass_context
def avl(ctx: click.Context, path_: str | None = None) -> None:
    """
    Avala CLI utility.
    Uses an Avala instance from ./app.py. Use --path to point to a different file or package directory.
    """
    module_path = os.path.abspath(path_ or os.path.join(os.getcwd(), "app.py"))
    try:
        avala = _load_avala(path_)
        ctx.obj = Context(avala=avala, module_path=module_path)
    except Exception as e:
        ctx.obj = Context(avala=None, module_path=module_path, load_error=str(e))  # type: ignore[arg-type]
        return


@avl.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """
    Guided initialization for a new Avala client (creates app.py and exploit directory).
    """
    protocol = click.prompt("protocol", default="http")
    host = click.prompt("host", default="localhost")
    port = click.prompt("port", default=2024, type=int)
    name = click.prompt("name", default="anon")
    password = click.prompt("password", default="", hide_input=True)
    redis_url = click.prompt("redis url", default="")
    exploit_dir = click.prompt("exploit directory", default="sploits")

    os.makedirs(exploit_dir, exist_ok=True)

    args = [
        f'host="{host}"',
        f"port={port}",
        f'name="{name}"',
        f'password="{password}"',
    ]
    if protocol:
        args.append(f'protocol="{protocol}"')
    if redis_url:
        args.append(f'redis_url="{redis_url}"')
    args_str = ",\n    ".join(args)
    app_content = f"""from avala import Avala

avl = Avala(
    {args_str},
)

avl.register_directory("{exploit_dir}")

if __name__ == "__main__":
    avl.run()
"""

    app_path = "app.py"
    if os.path.exists(app_path):
        overwrite = click.confirm(f"⚠️  '{app_path}' already exists. Overwrite?", default=False)
        if not overwrite:
            click.echo("❌ Initialization cancelled.")
            return

    with open(app_path, "w", encoding="utf-8") as f:
        f.write(app_content)

    click.echo("\n🚀 Initialization complete. Run 'avl run' to run Avala.")


@avl.command()
@click.pass_context
def run(ctx: click.Context) -> None:
    """
    Runs Avala client in production mode.
    """
    avala = _require_avala(ctx)
    avala.update_directory_paths(ctx.obj.module_path)
    avala.run()


@avl.command()
@click.pass_context
def services(ctx: click.Context) -> None:
    """
    Displays all service names based on flag IDs.
    """
    avala = _require_avala(ctx)
    avala.suppress_logs = True
    avala.connect()

    for name in sorted(avala.get_services()):
        click.echo(name)


@avl.command()
@click.argument("service", required=False)
@click.argument("target", required=False)
@click.argument("tick_index", required=False, type=int)
@click.pass_context
def flag_ids(ctx: click.Context, service: str | None, target: str | None, tick_index: int | None) -> None:
    """
    Filters and lists flag IDs.
    """
    avala = _require_avala(ctx)
    avala.suppress_logs = True
    avala.connect()

    if service is None:
        click.echo(json.dumps(avala.get_flag_ids().serialize()))
    elif service and target is None:
        click.echo(json.dumps((avala.get_flag_ids() / service).serialize()))
    elif service and target and tick_index is None:
        click.echo(json.dumps((avala.get_flag_ids() / service / target).serialize()))
    elif service and target and tick_index is not None:
        click.echo((avala.get_flag_ids() / service / target / tick_index).value)


@avl.command()
@click.pass_context
def exploits(ctx: click.Context) -> None:
    """
    Displays aliases of all found exploits.
    """
    avala = _require_avala(ctx)
    avala.suppress_logs = True
    avala.update_directory_paths(ctx.obj.module_path)
    avala.connect()

    for exploit_alias, is_draft in avala.list_exploits():
        draft_marker = " (draft)" if is_draft else ""
        click.echo(f"{colorize(exploit_alias)}{draft_marker}")


@avl.command()
@click.argument("alias", required=True)
@click.pass_context
def launch(ctx: click.Context, alias: str) -> None:
    """
    Launches attacks using an exploit with specified alias.
    """
    avala = _require_avala(ctx)
    avala.suppress_logs = True
    avala.update_directory_paths(ctx.obj.module_path)
    avala.connect()

    avala.run_exploit(alias)


@avl.command()
@click.pass_context
def submit(ctx: click.Context) -> None:
    """
    Extracts flags from text (stdin or interactive paste) and sends them for submission.
    """
    avala = _require_avala(ctx)
    avala.suppress_logs = True
    avala.connect()

    if _stdin_has_data():
        content = sys.stdin.read()
    else:
        click.echo("Paste content containing the flags and press Ctrl-D/Ctrl-Z when done:")
        # Read until EOF (Ctrl-D/Ctrl-Z)
        buf = io.StringIO()
        try:
            for line in sys.stdin:
                buf.write(line)
        except KeyboardInterrupt:
            pass
        content = buf.getvalue()

    if not content.strip():
        raise click.UsageError("No input provided. Pipe or paste content containing flags.")

    flags = avala.match_flags(content)
    click.echo(f"Found {len(flags)} unique flag(s):")
    for flag in flags:
        click.echo(flag)

    avala.submit_flags(flags)


def main() -> None:
    avl(prog_name="avl")


if __name__ == "__main__":
    main()

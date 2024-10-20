import shutil
from pathlib import Path

from avala_shared.logs import logger


def initialize_workspace():
    """
    Initializes the workspace in the current working directory by creating starter
    configuration files and scripts.
    """
    logger.info("Initializing workspace...")
    source_code_dir = Path(__file__).resolve().parent
    initialization_dir = source_code_dir / "files"
    workspace_dir = Path.cwd()

    for item in initialization_dir.iterdir():
        if item.name == "__pycache__":
            continue

        destination = workspace_dir / item.name
        if destination.exists():
            logger.info(
                "⏩ Skipping creating {item_name} as it already exists.",
                item_name=item.name,
            )
            continue
        shutil.copy2(item, destination)
        logger.info("✅ Created {item_name}.", item_name=item.name)

    logger.success(
        """🎉 Workspace initialized. Next steps:

 <b>1.</> 📝 <strike>Run <b>avl init</> to initialize your server workspace.</>
 <b>2.</> 🔧 Configure the server by editing <b>server.yaml</b>.
 <b>3.</> 🧩 Implement the flag submission logic in <b>submitter.py</b>.
 <b>4.</> 🧩 Implement the flag ID fetching logic in <b>flag_ids.py</b>.
 <b>5.</> 📝 Run <b>avl test</> to ensure everything is set up correctly.
 <b>6.</> 🐳 Edit <b>compose.yaml</> to fit your infrastructure.
 <b>7.</> 🚀 Run <b>docker compose up -d</> to run everything.
 <b>8.</> 🎉 Happy hacking!
        """
    )

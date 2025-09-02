For improved exploit development experience, it's recommended to install a lightweight **Avala** extension for Visual Studio Code. It adds "Run" button above your exploit function definition allowing you to run an exploit immediately from VS Code.

Clicking "Run" button will open an integrated terminal and run `avl launch [exploit alias]`. The same terminal will be reused for any subsequent exploit runs.

!!! warning

    At the moment, running exploits through VS Code is possible only if your client script is named `app.py`.


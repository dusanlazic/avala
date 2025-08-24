The recommended way to install **Avala** is via **pip** within a Python virtual environment. This practice helps to manage dependencies and avoid conflicts with other dependencies on your system.

## Create virtual environment

A virtual environment is a self-contained directory that holds a specific version of Python and any installed packages.

1. **Create the virtual environment**: From your terminal, navigate to an empty directory where you will keep your exploits, and run the following command. The `venv` module creates a new virtual environment in a folder named `venv` within your current directory.

    ```sh
    python3 -m venv venv
    ```

2. **Activate the virtual environment**: To use the virtual environment, you need to activate it. You'll know it's active when the name of the environment (e.g. `(venv)`) appears at the beginning of your terminal prompt, or by running `which python` to see if it points to the Python executable within your virtual environment.

    ```sh
    source venv/bin/activate
    ```

## Install Avala library

Once your virtual environment is created and activated, you can install the library using **pip**. The package is named `avala-ad` on the Python Package Index (PyPI).

```sh
pip install avala-ad
```

## Connect to the server

To configure Avala client, you just need to provide connection parameters for your Avala server.

In your current directory, create a Python file of arbitrary name (e.g. `client.py`) and create an instance of `Avala`. Provide it your own connection parameters.

```py title="client.py"
from avala import Avala

avl = Avala(
    host="avala.hakuj.me",
    port=2024,
    name="your nickname, can be any",
    password="your server password"
)

avl.start()
```

Running the script should connect to the server and display server configuration. It will also warn you that no exploit directories are registered.

!!! info  "TODO"
    asciinema replay of running the server

## Register exploit directories

Avala client needs to know where the exploit scripts will be located at. Create a directory of arbitrary name in your current directory (e.g. `exploits`) and register it.

```py title="client.py" hl_lines="10"
from avala import Avala

avl = Avala(
    host="avala.hakuj.me",
    port=2024,
    name="your nickname, can be any",
    password="your server password"
)

avl.register_directory("exploits")

avl.start()
```

From now on, you can start writing exploits inside your `exploits` directory.

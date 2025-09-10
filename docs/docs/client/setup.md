The recommended way to install **Avala** is via **pip** within a Python virtual environment. This practice helps to manage dependencies and avoid conflicts with other dependencies on your system.

## Create virtual environment

A virtual environment is a self-contained directory that holds a specific version of Python and any installed packages.

1. **Create the virtual environment**: From your terminal, navigate to an empty directory where you will keep your exploits, and run the following command. The `venv` module creates a new virtual environment in a folder named `venv` within your current directory.

    ```console
    $ python3 -m venv venv
    ```

2. **Activate the virtual environment**: To use the virtual environment, you need to activate it. You'll know it's active when the name of the environment (e.g. `(venv)`) appears at the beginning of your terminal prompt, or by running `which python` to see if it points to the Python executable within your virtual environment.

    ```console
    $ source venv/bin/activate
    (venv) $ 
    ```

## Install Avala library

Once your virtual environment is created and activated, you can install the library via **pip**. The package is named `avala-ad` on the Python Package Index (PyPI).

```console
$ pip install avala-ad
```

## Connect to the server

!!! tip
    You can also set up Avala client interactively via `avl init`. See [CLI reference](./cli.md#avl-init).

In your current directory, create a Python file named `app.py` and create an instance of `Avala`. Provide it your own connection parameters.

```py title="app.py"
from avala import Avala

avl = Avala(
    protocol="http",
    host="avala.hakuj.me",
    port=2024,
    name="your nickname, can be any",
    password="your server password"
)

if __name__ == "__main__":
    avl.run()
```

Running the script should connect to the server and display its configuration. It will also warn you that no exploit directories are registered yet. 

You can also run Avala client using the CLI by running `avl run`. For using the CLI, refer to [CLI reference](./cli.md). 

<div
  data-asciinema
  data-src="/avala/assets/demos/connect.cast"
  data-cols="113"
  data-rows="18"
></div>

## Register exploit directories

Avala client needs to know where the exploit scripts will be located. Create a directory with a custom name (e.g. `sploits`) in your current directory and register it.

```py title="app.py" hl_lines="11"
from avala import Avala

avl = Avala(
    protocol="http",
    host="avala.hakuj.me",
    port=2024,
    name="your nickname, can be any",
    password="your server password"
)

avl.register_directory("sploits")

if __name__ == "__main__":
    avl.run()
```

If already running the client, stop it and rerun it so the changes take effect. Avala will now scan and pick up exploits in any files in `sploits` directory.

<div
  data-asciinema
  data-src="/avala/assets/demos/run.cast"
  data-cols="126"
  data-rows="28"
></div>

## Redis cache (optional)

To support advanced features such as [blob storage](./exploit.md#store-parameter), fallback flag store and skipping successful attacks to reduce resource usage, you can run a Redis instance and connect your Avala client.

You can spin up a Redis instance using Docker:

```console
$ docker run -d --name avala-client-redis -p 6379:6379 --restart always redis
```

Pass the connection string to the `Avala` instance:

```py hl_lines="7"
avl = Avala(
    protocol="http",
    host="avala.hakuj.me",
    port=2024,
    name="your nickname, can be any",
    password="your server password",
    redis_url="redis://localhost:6379/0",
)
```

This will allow you to use:

- [Blob storage](./exploit.md#store-parameter) – Lets you persist any data between multiple attacks.
- Fallback flag store – Keeps unsubmitted flags locally while the Avala server is down and sends them as soon as the server comes online.
- Skipping successful attacks – Keeps a list of attacks that have returned a flag, so they don't run twice. Attacks are identified by the hash of the exploit alias and flag ID value. This is disabled if `draft` is set to `True`.

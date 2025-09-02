After installing Avala, you'll have access to the `avl` CLI utility. This guide serves as a quick reference for its commands.

## Discovery

By default, `avl` command will try to import `app.py` in the current working directory and look for an instance of `Avala`. To import a file other than `app.py`, use `--path` flag to specify a different path.

```console
$ avl --path hello run
```

The rest of this guide assumes the file is named `app.py` and omits the `--path` flag.

## `avl init`

Creates an `app.py` client script and an exploit directory in the current working directory based on user inputs. Serves as a guided interactive way of setting up the client.

```console
$ avl init
protocol [http]: http
host [localhost]: avala.hakuj.me
port [2024]: 2024
name [anon]: s4ndu
password []: 
redis url []:
exploit directory [sploits]: sploits

🚀 Initialization complete. Run 'avl run' to run Avala.
```

## `avl run`

Runs Avala client in production mode.

## `avl services`

Displays all service names based on flag IDs.

```console
$ avl services
foo
bar
baz
qux
```

## `avl flag_ids`

Filters and lists flag IDs. You can narrow down the results by providing a service name, target host, and/or tick index. Pipe output to `jq` to make large outputs easier to read. 

`avl flag_ids [service] [target] [tick index]`

```console
$ avl flag_ids
<entire flag_ids json>

$ avl flag_ids foobar | jq
{
  <...>
  "10.10.42.1": [...],
  "10.10.43.1": [
    "lorem",
    "ipsum",
    "dolor",
    "sit",
    "amet"
  ],
  "10.10.44.1": [...],
  <...>
}

$ avl flag_ids foobar "10.10.43.1"
["lorem", "ipsum", "dolor", "sit", "amet"]

$ avl flag_ids foobar "10.10.43.1" 2
dolor
```

## `avl exploits`

Displays aliases of all found exploits.

```console
$ avl exploits
alpha
bravo
charlie (dev)
delta
```

## `avl launch`

Launches attacks using an exploit with specified alias.

```console
$ avl launch alpha
TODO: Running exploits output
```

## `avl submit`

Extracts flags from text and sends them for submission. 

```console
$ avl submit
Paste content containing the flags:
```

```console
$ echo "surroundingtext FLAG_3B37DF144CE4A83566BB surroundingtext" | avl submit
```

```console
$ avl submit < response.txt
```
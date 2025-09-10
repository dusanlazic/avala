After installing Avala, you'll have access to the `avl` CLI utility. This guide serves as a quick reference for its commands.

## Discovery

By default, the `avl` command will try to import `app.py` in the current working directory and look for an instance of `Avala`. To import a file other than `app.py`, use `--path` flag to specify a different path.

```console
$ avl --path ./hello.py run
```

The rest of this guide assumes the file is named `app.py` and omits the `--path` flag.

## `avl init`

Creates an `app.py` client script and an exploit directory in the current working directory based on user inputs. Serves as a guided interactive way of setting up the client.

<div
  data-asciinema
  data-src="/avala/assets/demos/init.cast"
  data-cols="100"
  data-rows="18"
></div>

## `avl run`

Runs Avala client in production mode.

<div
  data-asciinema
  data-src="/avala/assets/demos/run.cast"
  data-cols="126"
  data-rows="28"
></div>

## `avl services`

Displays all service names based on flag IDs.

```console
$ avl services
history
none
own
pay
prepare
security
wish
```

## `avl flag-ids`

Filters and lists flag IDs. You can narrow down the results by providing a service name, target host, and/or tick index. Pipe output to `jq` to make large outputs easier to read. 

`avl flag-ids [service] [target] [tick index]`

<div
  data-asciinema
  data-src="/avala/assets/demos/flagids.cast"
  data-cols="126"
  data-rows="28"
></div>

## `avl exploits`

Displays aliases of all found exploits.

```console
$ avl exploits
wish
wish_team_188 (draft)
wish_experimental (draft)
history_1
history_2
security.testing (draft)
all_at_once
```

## `avl launch`

Launches attacks using an exploit with specified alias.

`avl launch <exploit alias>`

<div
  data-asciinema
  data-src="/avala/assets/demos/launch.cast"
  data-cols="126"
  data-rows="28"
></div>

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

<script src="https://cdn.jsdelivr.net/npm/asciinema-player@3.5.0/dist/bundle/asciinema-player.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/asciinema-player@3.5.0/dist/bundle/asciinema-player.min.css">

After installing Avala, you'll have access to the `avl` CLI utility. This guide serves as a quick reference for its commands.

## Discovery

By default, `avl` command will try to import `app.py` in the current working directory and look for an instance of `Avala`. To import a file other than `app.py`, use `--path` flag to specify a different path.

```console
$ avl --path ./hello.py run
```

The rest of this guide assumes the file is named `app.py` and omits the `--path` flag.

## `avl init`

Creates an `app.py` client script and an exploit directory in the current working directory based on user inputs. Serves as a guided interactive way of setting up the client.

<div id="init-demo"></div>
<script>
  AsciinemaPlayer.create('/avala/assets/demos/init.cast', document.getElementById('init-demo'), {
      cols: 100,
      rows: 18,
      idleTimeLimit: 2
  });
</script>

## `avl run`

Runs Avala client in production mode.

<div id="run-2-demo"></div>
<script>
  AsciinemaPlayer.create('/avala/assets/demos/run.cast', document.getElementById('run-2-demo'), {
      cols: 126,
      rows: 28,
      idleTimeLimit: 2
  });
</script>

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

<div id="flag-ids-demo"></div>
<script>
  AsciinemaPlayer.create('/avala/assets/demos/flagids.cast', document.getElementById('flag-ids-demo'), {
      cols: 126,
      rows: 28,
      idleTimeLimit: 2
  });
</script>

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

<div id="launch-2-demo"></div>
<script>
  AsciinemaPlayer.create('/avala/assets/demos/launch.cast', document.getElementById('launch-2-demo'), {
      cols: 126,
      rows: 28,
      idleTimeLimit: 2
  });
</script>

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

After installing Avala, you'll have access to the `avl` CLI utility. This guide serves as a quick reference for its commands.

## Discovery

By default, `avl` command will try to import `app.py` in the current working directory and look for an instance of `Avala`. To import a file other than `app.py`, use `--path` flag to specify a different path.

```console
$ avl --path ./hello.py run
```

The rest of this guide assumes the file is named `app.py` and omits the `--path` flag.

## `avl init`

Creates an `app.py` client script and an exploit directory in the current working directory based on user inputs. Serves as a guided interactive way of setting up the client.

```console
$ avl init
protocol [http]: https
host [localhost]: avala.hakuj.me
port [2024]: 2024
name [anon]: s4ndu
password []: 
redis url []:
exploit directory [sploits]: sploits

🚀 Initialization complete. Run 'avl run' to run Avala.
$ avl run

      db
     ;MM:
    ,V^MM. 7MM""Yq.  ,6"Yb.  `7M""MMF',6"Yb.
   ,M  `MM `MM   j8 8)   MM    M  MM 8)   MM
   AbmmmqMA MM""Yq.  ,pm9MM   ,P  MM  ,pm9MM
  A'     VML`M   j8 8M   MM . d'  MM 8M   MM
.AMA.   .AMMA.mmm9' `Moo9^Yo8M' .JMML`Moo9^Yo.

[23:54:23] SUCCESS  ✅ Connected to Avala server at https://avala.hakuj.me:2024 as s4ndu.
[23:54:23] INFO     Flag format: ENO[A-Za-z0-9+/=]{48}
[23:54:23] INFO     Tick duration: 60.0 seconds
[23:54:23] INFO     Time of the first tick: 2025-09-03 20:30:00+02:00
[23:54:23] INFO     📂 Registered exploit directories: sploits
[23:54:23] WARNING  ⚠️  No exploits loaded.
^C
[23:54:29] INFO     🙌 Thanks for using Avala!
```

## `avl run`

Runs Avala client in production mode.

```console
$ avl run

      db
     ;MM:
    ,V^MM. 7MM""Yq.  ,6"Yb.  `7M""MMF',6"Yb.
   ,M  `MM `MM   j8 8)   MM    M  MM 8)   MM
   AbmmmqMA MM""Yq.  ,pm9MM   ,P  MM  ,pm9MM
  A'     VML`M   j8 8M   MM . d'  MM 8M   MM
.AMA.   .AMMA.mmm9' `Moo9^Yo8M' .JMML`Moo9^Yo.

[22:50:47] SUCCESS  ✅ Connected to Avala server at http://avala.hakuj.me:2024 as s4ndu.
[22:50:47] INFO     Flag format: ENO[A-Za-z0-9+/=]{48}
[22:50:47] INFO     Tick duration: 60.0 seconds
[22:50:47] INFO     Time of the first tick: 2025-09-03 20:30:00+02:00
[22:50:47] INFO     📂 Registered exploit directories: exploits
[22:50:47] INFO     📥 Loaded 5 exploits: alpha*, bravo*, charlie*, delta, echo*
[22:50:47] INFO     ⏰ Exploit delta (batch 1/2) will run at 22:50:50.
[22:50:47] INFO     ⏰ Exploit delta (batch 2/2) will run at 22:50:55.
```

## `avl services`

Displays all service names based on flag IDs.

```console
$ avl services
foo
bar
baz
qux
```

## `avl flag-ids`

Filters and lists flag IDs. You can narrow down the results by providing a service name, target host, and/or tick index. Pipe output to `jq` to make large outputs easier to read. 

`avl flag-ids [service] [target] [tick index]`

```console
$ avl flag-ids
<entire flag_ids json>

$ avl flag-ids foobar | jq
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

$ avl flag-ids foobar "10.10.43.1"
["lorem", "ipsum", "dolor", "sit", "amet"]

$ avl flag-ids foobar "10.10.43.1" 2
dolor
```

## `avl exploits`

Displays aliases of all found exploits.

```console
$ avl exploits
alpha (draft)
bravo (draft)
charlie (draft)
delta
echo (draft)
```

## `avl launch`

Launches attacks using an exploit with specified alias.

```console
$ avl launch alpha
[22:49:50] INFO     🚀 Launching exploit alpha (batch 1/1)...
[22:49:50] INFO     🚩 Enqueued 1/1 flags from 10.10.221.1 via alpha. ENOa354f4fc256fd7ea207b12b8dab1b6997309cec6e3283dd...
[22:49:50] INFO     🚩 Enqueued 1/1 flags from 10.10.101.1 via alpha. ENO7345b273162b30b9da7e141c6bacae89d8f664db04fe1a9...
[22:49:50] INFO     🚩 Enqueued 1/1 flags from 10.10.201.1 via alpha. ENOb1508613cd3dfa0c2ffd49562e3973528eaea78bfa918d5...
[22:49:50] INFO     🚩 Enqueued 1/1 flags from 10.10.173.1 via alpha. ENOd4445975d6ea241863a1000ae03105a094d665ab53aa797...
[22:49:50] INFO     🚩 Enqueued 1/1 flags from 10.10.13.1 via alpha. ENOb38346cc5c2375807885c7197e88fb5e56378e0d3e27616...
...
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

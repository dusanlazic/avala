## `service` <small>required</small> { #service data-toc-label="service" }

`str`

Name of the service attacked by the exploit. Run `avl services` to see the names of available services.

## `draft`

`bool`

Exclude the exploit when running Avala in production mode. Useful for testing and debugging exploits when running manually. Defaults to `False`.

## `alias`

`str | None`

Alias used for exploit identification, logging and as a key for [tracking repeated flag IDs](./setup.md#redis-cache-optional). If not provided, Avala will set it to `<module name>.<function name>`. Defaults to `None`.

## `targets`

`Iterable[str] | TargetingStrategy`

IP addresses or hostnames of the targeted teams, or a targeting strategy. Defaults to `TargetingStrategy.AUTO`.

### `TargetingStrategy`

Targeting strategy that can be used as an alternative to specifying a collection of targets in the exploit configuration.

- `TargetingStrategy.AUTO` **(default)** – Selects all available hosts, excluding your own team and the NOP team.
- `TargetingStrategy.NOP_TEAM` – Selects the hosts of the NOP team.
- `TargetingStrategy.OWN_TEAM` – Selects the hosts of your own team.

## `skip`

`Iterable[str] | None`

IP addresses or hostnames to skip when attacking. Hosts of the NOP team and own team are skipped regardless of this setting. To include NOP team and own team hosts, use `include`. Defaults to `None`.

## `include`

`Iterable[str] | None`

Additional IP addresses or hostnames to include when attacking. Can be used to include hosts that are skipped by default (NOP team and own team). Defaults to `None`.

## `flag_id_scope`

`FlagIdScope`

TODO

### `FlagIdScope`

TODO

## `delay`

`int | float | timedelta`

Delay in seconds to wait before starting the first attack, defaults to 0 (`timedelta(seconds=0)`). Useful when running multiple exploits and need a way to prevent them from running at the same time, which could lead to excessive CPU, memory or network usage.

## `batching`

`Batching`

TODO

### `Batching`

TODO

## `timeout`

`int | float | timedelta`

Timeout in seconds after which the exploit will be terminated if it hangs or takes too long to complete, defaults to `timedelta(seconds=15)`.

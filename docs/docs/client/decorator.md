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

`TargetingStrategy` can be used as an alternative to specifying a collection of targets.

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

Scope of the `flag_ids` parameter. Can be narrowed down to a single tick (service / target / tick), or a single target (service / target). Defaults to `FlagIdScope.SINGLE`.

- `FlagIdScope.SINGLE_TICK` **(default)** – `flag_ids` object will represent flag IDs relevant to a single service, target, and tick. If using [Redis cache](./setup.md#redis-cache-optional), each flag ID that successfully returns a flag will be tracked, allowing Avala client to skip the attacks that are using the same flag ID (based on exploit alias, target host and flag id value). This is the recommended and optimized approach.
- `FlagIdScope.LAST_N_TICKS` – `flag_ids` object will contain a list of flag IDs relevant to a single service, target, and the last N ticks. In most cases, not necessary and can be inefficient due to performing redundant attacks.

## `delay`

`int | float | timedelta`

Delay in seconds to wait before starting the first attack, defaults to 0 (`timedelta(seconds=0)`). Useful when running multiple exploits and need a way to prevent them from running at the same time, which could lead to excessive CPU, memory or network usage.

## `batching`

`Batching`

See [Optimizing with batching](./exploit.md#optimizing-with-batching) section.

## `timeout`

`int | float | timedelta`

Timeout in seconds after which the exploit will be terminated if it hangs or takes too long to complete, defaults to `timedelta(seconds=15)`.

---
hide:
- toc
---

The `avala.yaml` file is the primary configuration file for your Avala server. It is where you define tick duration and flag format, fine-tune flag ID fetching and flag submission, configure authorization parameters and connection parameters to database and message queue. 

Create a file named `avala.yaml` in your current directory and paste the following content. Adjust the parameters in each section as necessary to configure Avala based on your competition's rulebook and preferences.

---

```yaml title="avala.yaml"
#
#       db 
#      ;MM:
#     ,V^MM. 7MM""Yq.  ,6"Yb.  `7M""MMF',6"Yb.  
#    ,M  `MM `MM   j8 8)   MM    M  MM 8)   MM  
#    AbmmmqMA MM""Yq.  ,pm9MM   ,P  MM  ,pm9MM  
#   A'     VML`M   j8 8M   MM . d'  MM 8M   MM  
# .AMA.   .AMMA.mmm9' `Moo9^Yo8M' .JMML`Moo9^Yo.
#
# Configuration file for the Avala server.
# 
# Follow the instructions in the comments to configure the server according to the
# competition's rulebook and your preferences.
#
# Game settings - adjust these according to the competition's rulebook.
game:
  # Duration of each game tick in seconds.
  tick_duration: 60

  # Regular expression pattern for matching flags.
  # Note: If given in rulebook, remove ^ and $ from the pattern to match flags 
  # anywhere in your output, not just at the beginning and end of text.
  flag_format: "CTF[A-Za-z0-9+\/=]{48}"

  # IP addresses or hostnames of your team's vulnerable machines (vulnboxes).
  # There is usually just a single machine per team, but some competitions may have more.
  # These hosts will be excluded from the attacks unless specified otherwise.
  own_team_hosts: 
    - 10.10.43.1 # Example Linux machine 1
    - 10.10.43.2 # Example Linux machine 2
    - 10.10.43.3 # Example Windows machine

  # IP addresses or hostnames of your team's vulnerable machines (vulnboxes).
  # There is usually just a single machine per team, but some competitions may have more.
  # These hosts will be excluded from the attacks unless specified otherwise.
  nop_team_hosts: 
    - 10.10.1.1 # Example Linux machine 1
    - 10.10.1.2 # Example Linux machine 2
    - 10.10.1.3 # Example Windows machine

  # IP addresses or hostnames of the opponent teams.
  # There is usually just a single machine per team, but some competitions may have more.
  # Make sure to include ALL hosts that belong to the opponent teams.
  opp_team_hosts:
    - 10.10.2.1
    - 10.10.2.2
    - 10.10.2.3
    - 10.10.3.1
    - 10.10.3.2
    - 10.10.3.3
    - 10.10.4.1
    - 10.10.4.2
    - 10.10.4.3
    - 10.10.5.1
    - 10.10.5.2
    - 10.10.5.3
    - 10.10.6.1
    - 10.10.6.2
    - 10.10.6.3

  # Time-to-live (TTL) of a flag in seconds. Sometimes it's given in ticks.
  # If not specified, leave it to at least 5 ticks.
  flag_ttl: 300

  # Time when the game starts in ISO 8601 format. Example: 2024-08-11T10:00:00+01:00
  game_starts_at: 2024-08-11T10:00:00+01:00

  # Duration of the grace period before the networks open. Specified in hours, minutes, and seconds.
  networks_open_after: 1:00:00

  # Duration of the game. Specified in hours, minutes, and seconds.
  game_ends_after: 8:00:00

# Flag submission configuration
submitter:
  # Path to the submitter script. If running Avala in Docker, you likely don't need to change this.
  script_path: /etc/avala/submitter.py

  # Number of retries if flag submission fails with an error.
  retries: 5

  # If submitting in batches, set interval or per_tick, and batch_size.
  # Duration in seconds between submitting two batches of flags.
  # interval: 5
  # OR
  # Number of batches to submit during a single tick (interval will be calculated based on this value).
  # per_tick: 5
  # Maximum size of a batch of flags. Think of HTTP request size, game server limitations and similar
  # factors to avoid submitting a batch that's too large.
  # batch_size: 50

  # If submitting in a stream, just uncomment the setting below.
  # stream: true

  # [Experimental] Spawn a new thread for each call to the submit function. Not recommended
  # if using persistent context in a thread-unsafe way. Disabled by default.
  # threading: true

# Flag IDs fetching
flag_ids:
  # Path to the flag IDs fetching script. If running Avala in Docker, you likely don't need to change this.
  script_path: /etc/avala/flag_ids.py

  # Maximum number of attempts to fetch the flag IDs.
  # This is added to mitigate game-server latency issues. In case of failure,
  # the last fetched flag IDs will be reused.
  retries: 5

  # Interval (in seconds) between retrying to fetch flag IDs.
  interval: 2

# Server access configuration
server:
  # Hostname or IP address to bind to (0.0.0.0 for all interfaces).
  host: 0.0.0.0

  # Port number for the server to listen on.
  # Make sure this port is open and not blocked by any firewall rules.
  port: 2024

  # Password for authorizing clients and allowing dashboard access.
  # It's recommended to use a strong password.
  # https://www.random.org/strings/?num=1&len=32&digits=on&upperalpha=on&loweralpha=on&format=plain
  password: avalarocks

  # Enable serving the dashboard (frontend app) at the root (/) URL.
  # Leave this to true to simplify the setup process.
  dashboard: true

  # List of allowed domains for Cross-Origin Resource Sharing (CORS).
  # Enable this if you're serving the frontend from a different domain.
  # If you have dashboard: true set above, you likely don't need this.
  # cors:
  #   - http://hakuj.me
  #   - https://hakuj.me

# Database connection settings
# If running via Docker compose, ensure that the parameters and the hostname match 
# those in compose.yaml. 
#
# If you have any additional connection parameters, use query object. Note that the
# database driver is "postgresql+asyncpg".
database:
  name: avala
  user: admin
  password: admin
  host: postgres
  port: 5432
  # query:
  #   ssl: disable

# RabbitMQ connection settings
# If running via Docker compose, ensure that the parameters and the hostname match 
# those in compose.yaml.
rabbitmq:
  user: guest
  password: guest
  host: rabbitmq
  port: 5672
  management_port: 15672
```

## Next steps

After configuring Avala via `avala.yaml` file, in your directory you should have the following:

```
server-workspace/
├── avala.yaml
├── flag_ids.py
└── submitter.py
```

Next step is writing the flag ID fetching script.

- [x] [Create an empty directory on your server](./index.md) ✅
- [x] [Write the **submitter** script](./submitter.md) ✅
- [x] [Write the **flag IDs fetching** script](./flag-ids.md) ✅
- [x] [Configure the Avala server](./configuration.md) ✅
- [ ] [Launch all containers using Docker Compose](./launching.md) 👈

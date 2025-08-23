To run the entire infrastructure, a pre-configured `compose.yaml` file is provided. The file defines the following services:

- `avala-server`: Core server component that orchestrates all operations.
- `avala-subimtter`: Component responsible for submitting flags. It can be configured to run multiple instances (replicas) to handle high volume of flags, which is useful when submitting in streams.
- `rabbitmq`: Message broker that handles the flow of flags from the server to the submitters.
- `postgres`: Database used for storing flags, their statuses, responses and historical data.


## Docker compose file

Create a file named `compose.yaml` in your current directory and paste the content below. The `compose.yaml` file typically requires only minor adjustments, primarily for:

- **Credentials**: You should update the access credentials for RabbitMQ and PostgreSQL. Make sure these credentials, along with hostnames, ports, and other connection parameters, match the settings in your `avala.yaml` file.
- **Time zone**: The time zone is set to `Europe/Belgrade`, which may need to be adjusted to match your location.
- **Docker image**: The services are configured to use images from Docker Hub. If your images have different names or are hosted on a different registry, you'll need to update the `image` field accordingly.
- **Volumes**: The configuration uses Docker volumes to persist data for RabbitMQ and PostgreSQL. Ensure these are correctly set up if you are not using Docker's default volume management.

```yaml
services:
  avala-server:
    image: avala-server
    ports:
      - "2024:2024"
    depends_on:
      rabbitmq:
        condition: service_healthy
      postgres:
        condition: service_started
    restart: always
    environment:
      TZ: Europe/Belgrade
    tty: true
    volumes:
      - ./avala.yaml:/etc/avala/avala.yaml:ro
      - ./flag_ids.py:/etc/avala/flag_ids.py:ro
    
  avala-submitter:
    image: avala-submitter
    depends_on:
      rabbitmq:
        condition: service_healthy
      postgres:
        condition: service_started
    restart: always
    environment:
      TZ: Europe/Belgrade
    tty: true
    volumes:
      - ./avala.yaml:/etc/avala/avala.yaml:ro
      - ./submitter.py:/etc/avala/submitter.py:ro
    deploy:
      replicas: 1
  
  rabbitmq:
    image: rabbitmq:management
    ports:
      - 5672:5672
      - 15672:15672
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    healthcheck:
      test: rabbitmq-diagnostics check_port_connectivity
      interval: 1s
      timeout: 3s
      retries: 30
    restart: always
    tty: true
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq

  postgres:
    image: postgres:alpine
    ports:
      - 5432:5432
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: admin
      POSTGRES_DB: avala
    tty: true
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  rabbitmq-data:
    driver: local
  postgres-data:
    driver: local
```

## Launching

In your directory you should have the following:

```
server-workspace/
├── avala.yaml
├── compose.yaml
├── flag_ids.py
└── submitter.py
```

Launching all containers is done using the following command:

```sh
docker compose up -d
```

After your containers are up, you can access the dashboard via `http://<your hostname>:2024/` (assuming that you're using the default port 2024). Upon opening the page you will be prompted for a username and a password. The password is the one you set in `avala.yaml`, while the username can be anything. 

To confirm the system is working, manually submit a test flag. If the submitted flag appears in the database with the correct status and server response, the setup is successful. If not, check the container logs for errors.

### Other commands

If you need to restart a service, run the following:

```sh
docker compose restart avala-submitter
```

To shut down the infrastructure temporarily:

```sh
docker compose down
```

To destroy the infrastructure and clean up the volumes completely:

```sh
docker compose down -v
```

## Next steps

- [x] [Create an empty directory on your server](./index.md) ✅
- [x] [Write the **submitter** script](./submitter.md) ✅
- [x] [Write the **flag IDs fetching** script](./flag-ids.md) ✅
- [x] [Configure the Avala server](./configuration.md) ✅
- [x] [Launch all containers using Docker Compose](./launching.md) ✅

Now that your Avala server is running, you're ready to install the Avala client and start writing exploits. 🚀

- [ ] [Setup Avala client](../client/index.md) 👈

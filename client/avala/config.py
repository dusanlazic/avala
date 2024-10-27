from pathlib import Path

DOT_DIR_PATH = Path(".avala")


class ConnectionConfig:
    def __init__(
        self,
        protocol: str = "http",
        host: str = "localhost",
        port: int = 2024,
        username: str = "anon",
        password: str | None = None,
    ) -> None:
        self.protocol = protocol
        self.host = host
        self.port = port
        self.username = username
        self.password = password

        self.raise_for_invalid()

    def raise_for_invalid(self):
        if self.protocol not in ["http", "https"]:
            raise ValueError("Invalid protocol")
        if not isinstance(self.host, str):
            raise ValueError("Invalid host")
        if not isinstance(self.port, int) or self.port < 1 or self.port > 65535:
            raise ValueError("Invalid port")
        if not isinstance(self.username, str) or len(self.username) > 20:
            raise ValueError("Invalid username")
        if self.password is not None and not isinstance(self.password, str):
            raise ValueError("Invalid password")

from dataclasses import dataclass, field


@dataclass
class MachineMount:
    volume: str
    encrypted: bool = True
    path: str = "/home/jovyan/student_data"


@dataclass
class MachineService:
    http_options: dict
    autostart: bool = True
    autostop: str = "off"
    concurrency: dict[str, str|int] = field(
        default_factory=lambda: {
            "type": "connections",
            "hard_limit": 30,
            "soft_limit": 20,
        }
    )
    internal_port: str = "8888"
    force_https: bool = True
    min_machines_running: int = 0
    ports: list[dict] = field(
        default_factory=lambda: [
            {"port": 80, "handlers": ["http"]},
            {"port": 443, "handlers": ["tls", "http"]},
        ]
    )
    protocol: str = "tcp"


@dataclass
class MachineConfig:
    image: str
    env: dict[str, str]
    services: list[MachineService]
    mounts: list[MachineMount]
    auto_destroy: bool = True
    guest: dict = field(
        default_factory=lambda: {"cpu_kind": "shared", "cpus": 1, "memory_mb": 512}
    )
    init: dict[str, str|int] = field(
        default_factory=lambda: {
            "swap_size_mb": 512,
        }
    )
    restart: dict[str, str|int] = field(
        default_factory=lambda: {"max_retries": 3, "policy": "on-failure"}
    )


@dataclass
class MachineCreate:
    name: str
    config: MachineConfig
    region: str = "ams"

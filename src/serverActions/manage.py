#!/usr/bin/env python3
"""
Jupyter Lab Provisioning Script for Fly.io

This script creates and manages Jupyter Lab instances on Fly.io for students.
It uses the Fly Machines API directly to create and manage the instances.
Zero external dependencies - uses only the standard library.
"""

from __future__ import annotations

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import asdict
from typing import Dict
from pathlib import Path
from enum import Enum
import platform

try:
    sys.path.append(Path(__file__).parent.parent.as_posix())
    from serverActions.models import (
        MachineCreate,
        MachineConfig,
        MachineMount,
        MachineService,
    )
except Exception as e:
    print(e)
    print("[Χ] Could not load modules into path")
    sys.exit(1)

essential_keys = [
    "FLY_ORGANIZATION",
    "BASE_DOMAIN",
    "JUPYTER_IMAGE",
    "FLY_API_TOKEN",
    "APP_NAME",
]


class Color(str, Enum):
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    ERRORRED = "\033[91m"
    ENDC = "\033[0m"
    UNDERLINE = "\033[4m"


class Command(str, Enum):
    LIST = "list"
    SPIN = "spin"
    SHUTDOWN = "shutdown"
    DELETE = "delete"


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class CliCommand(str, Enum):
    LIST = "list"
    PROVISION = "provision"
    STOP = "stop"
    START = "start"
    DELETE = "delete"
    BATCH = "batch"


def pretty_print(contents: str, color: Color = Color.OKGREEN) -> None:
    print(f"{color.value}{contents}{Color.ENDC.value}")


def make_api_request(
    method: HTTPMethod,
    path: str,
    data: Dict[str, str] | None = None,
    headers: Dict[str, str] | None = None,
) -> Dict[str, str]:
    """Makes an API request to Fly.io Machines API"""
    if not headers:
        headers = dict()
        headers["Authorization"] = f"Bearer {FLY_API_TOKEN}"
        headers["Content-Type"] = "application/json"

    url = f"https://{FLY_API_HOST}{path}"

    request = urllib.request.Request(
        url=url,
        data=json.dumps(data).encode("utf-8") if data else None,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request) as response:
            if response.getcode() not in [200, 201, 204]:
                return {
                    "status": response.getcode(),
                    "error": response.read().decode("utf-8"),
                }
            return {
                "status": response.getcode(),
                "data": (
                    json.loads(response.read().decode("utf-8"))
                    if response.getcode() != 204
                    else None
                ),
            }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            error_json = json.loads(error_body)
            return {"status": e.code, "error": error_json}
        except:
            return {"status": e.code, "error": error_body}
    except Exception as e:
        return {"status": 500, "error": str(e)}


def create_volume(student_id: str) -> str | None:
    data = {"region": "ams", "name": f"vol_{student_id}", "size_gb": 1}
    result = make_api_request(
        "POST",
        f"/v1/apps/{APP_NAME}/volumes",
        data=data,
        headers=common_headers,
    )

    if result["status"] not in [200, 201]:
        pretty_print(
            f"Failed to create volume: \n[Status:{result['status']}] {result.get('error', 'Unknown error')}",
            Color.ERRORRED,
        )
        return

    try:
        return result["data"]["id"]
    except KeyError as e:
        pretty_print(e, Color.ERRORRED)
        return


def create_machine(student_id: str, volume_id: str) -> Dict[str, str] | None:
    """Create a new machine for the app"""
    machine_config = MachineConfig(
        image=JUPYTER_IMAGE,
        env={"STUDENT_ID": student_id},
        mounts=[MachineMount(volume=volume_id)],
        services=[
            MachineService(
                internal_port=INTERNAL_PORT,
                http_options={
                    "idle_timeout": IDLE_TIMEOUT,
                    "h2_backend": True,
                },
            )
        ],
    )
    data = MachineCreate(name=f"{FLY_APP_PREFIX}{student_id}", config=machine_config)

    result = make_api_request(
        "POST",
        f"/v1/apps/{APP_NAME}/machines",
        data=asdict(data),
        headers=common_headers,
    )

    if result["status"] not in [200, 201]:
        pretty_print(
            f"Failed to create machine: \n[Status:{result['status']}] {result.get('error', 'Unknown error')}",
            Color.ERRORRED,
        )
        return

    return {"instance_id": result["data"]["instance_id"]}


def provision_jupyter(student_id: str):
    """Provision a new Jupyter Lab instance for a student"""
    app_exists = make_api_request("GET", f"/v1/apps/{APP_NAME}", headers=common_headers)

    if app_exists["status"] != 200:
        pretty_print(
            f"Failed to get information about machines; app = {APP_NAME}",
            Color.ERRORRED,
        )
        return

    pretty_print(f"[X] Creating new Jupyter instance for student: {student_id}")

    volume_id: str | None = create_volume(student_id)
    if not volume_id:
        return

    create_machine(student_id, volume_id)

    pretty_print(f"[X] Successfully deployed Jupyter instance for {student_id}")
    pretty_print(
        f"\tAccess URL: https://{APP_NAME}.{BASE_DOMAIN}/lab?token={student_id}",
        Color.UNDERLINE,
    )

    config_dir = Path(__file__).parent / f".fly-configs/{student_id}"
    config_dir.mkdir(parents=True, exist_ok=True)

    access_info = {
        "student_id": student_id,
        "url": f"https://{APP_NAME}.{BASE_DOMAIN}/lab?token={student_id}",
    }

    with open(config_dir / "access.json", "+a") as f:
        json.dump(access_info, f, indent=2)


def get_machines():
    """Get all machines for an app"""
    result = make_api_request("GET", f"/v1/apps/{APP_NAME}/machines")

    if result["status"] != 200:
        return list()

    return result["data"]


def main():
    parser = argparse.ArgumentParser(
        description="Manage Jupyter Lab instances on Fly.io"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    provision_parser = subparsers.add_parser(
        CliCommand.PROVISION.value, help="Provision a new Jupyter instance"
    )
    provision_parser.add_argument("student_id", help="Student identifier")
    provision_parser.add_argument(
        "--resources",
        dest="resource_limit",
        default="standard",
        choices=["standard", "high"],
        help="Resource allocation",
    )

    terminate_parser = subparsers.add_parser(
        CliCommand.STOP.value, help="Stop a Jupyter instance"
    )
    terminate_parser.add_argument("student_id", help="Student identifier")

    start_parser = subparsers.add_parser(
        CliCommand.START.value, help="Start a Jupyter instance"
    )
    start_parser.add_argument("student_id", help="Student identifier")

    delete_parser = subparsers.add_parser(
        CliCommand.DELETE.value, help="Delete a Jupyter instance"
    )
    delete_parser.add_argument("student_id", help="Student identifier")

    subparsers.add_parser(CliCommand.LIST.value, help="List all Student instances")

    batch_parser = subparsers.add_parser(
        CliCommand.BATCH.value, help="Provision multiple instances from a CSV file"
    )
    batch_parser.add_argument(
        "file", help="CSV file with student_id,enrolled_date,resource_limit format"
    )

    args = parser.parse_args()

    match args.command:
        case CliCommand.PROVISION.value:
            provision_jupyter(args.student_id)
        case CliCommand.STOP.value:
            raise NotImplementedError
        case CliCommand.START.value:
            raise NotImplementedError
        case CliCommand.DELETE.value:
            raise NotImplementedError
        case CliCommand.LIST.value:
            import pprint

            pprint.pprint(get_machines())
        case CliCommand.BATCH.value:
            raise NotImplementedError

        case _:
            parser.print_help()


def run_system_checks() -> bool:
    major, minor, _ = platform.python_version_tuple()
    if int(major) != 3 and int(minor) < 9:
        pretty_print("[X] Python 3.10 or later is required", Color.ERRORRED)
        return False
    env_file = Path(__file__).parent.parent.parent / ".env"
    if not env_file.exists():
        pretty_print("[X] .env file not found", Color.ERRORRED)
        return False
    with open(env_file.as_posix(), "r") as f:
        for line in f.readlines():
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            key, value = line.split("=", 1)
            if key not in essential_keys:
                continue
            os.environ[key] = value
    if not all(os.environ.get(key) for key in essential_keys):
        pretty_print("[X] Missing required environment variables", Color.ERRORRED)
        return False
    return True


if __name__ == "__main__":
    if not run_system_checks():
        sys.exit(1)
    FLY_ORGANIZATION = os.environ.get("FLY_ORGANIZATION", "")
    BASE_DOMAIN = os.environ.get("BASE_DOMAIN", "")
    JUPYTER_IMAGE = os.environ.get("JUPYTER_IMAGE", "")
    VOLUME_SIZE = os.environ.get("VOLUME_SIZE", "1")
    FLY_API_TOKEN = os.environ.get("FLY_API_TOKEN", "")
    FLY_API_HOST = os.environ.get("FLY_API_HOST", "api.machines.dev")
    FLY_APP_PREFIX = os.environ.get("FLY_APP_PREFIX", "jupyter-")
    APP_NAME = os.environ.get("APP_NAME", "")
    try:
        INTERNAL_PORT = int(os.environ.get("INTERNAL_PORT", "8888"))
        IDLE_TIMEOUT = int(os.environ.get("IDLE_TIMEOUT", "300"))
    except ValueError:
        pretty_print(
            "[X] Invalid value for INTERNAL_PORT or IDLE_TIMEOUT", Color.ERRORRED
        )
        sys.exit(1)

    common_headers = {
        "User-Agent": "Fidiaitera-Provision/0.1",
        "Authorization": f"Bearer {FLY_API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        main()
    except NotImplementedError:
        pretty_print("[X] Command not implemented", Color.ERRORRED)
        sys.exit(1)

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
import secrets
import json
import argparse
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict
from pathlib import Path
from enum import Enum
import time
import platform


FLY_ORGANIZATION = os.environ.get("FLY_ORGANIZATION", "")
BASE_DOMAIN = os.environ.get("BASE_DOMAIN", "")
JUPYTER_IMAGE = os.environ.get("JUPYTER_IMAGE", "")
VOLUME_SIZE = os.environ.get("VOLUME_SIZE", "10")
FLY_API_TOKEN = os.environ.get("FLY_API_TOKEN", "")
FLY_API_HOST = os.environ.get("FLY_API_HOST", "api.machines.dev")
FLY_APP_PREFIX = os.environ.get("FLY_APP_PREFIX", "jupyter-")


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
        headers = {}

    if not FLY_API_TOKEN:
        pretty_print(
            "Error: FLY_API_TOKEN environment variable not set", Color.ERRORRED
        )
        pretty_print("Please set it with your Fly.io API token", Color.ERRORRED)
        sys.exit(1)

    headers["Authorization"] = f"Bearer {FLY_API_TOKEN}"
    headers["Content-Type"] = "application/json"

    url = f"https://{FLY_API_HOST}{path}"

    request = urllib.request.Request(
        url=url,
        data=json.dumps(data).encode("utf-8") if data else None,
        headers=headers,
        method=method.value,
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


def create_app(app_name) -> None:
    """Create a new Fly.io app"""
    data = {"name": app_name, "org_slug": FLY_ORGANIZATION}

    result = make_api_request("POST", "/v1/apps", data)

    if result["status"] not in [200, 201]:
        pretty_print(
            f"Failed to create app: {result.get('error', 'Unknown error')}",
            Color.ERRORRED,
        )
        sys.exit(1)

    return


def create_volume(app_name, volume_name, size_gb) -> None:
    """Create a volume for the app"""
    data = {
        "name": volume_name,
        "size_gb": int(size_gb),
        "region": "iad",
        "encrypted": True,
    }

    result = make_api_request("POST", f"/v1/apps/{app_name}/volumes", data)

    if result["status"] not in [200, 201]:
        pretty_print(
            f"Failed to create volume: {result.get('error', 'Unknown error')}",
            Color.ERRORRED,
        )
        sys.exit(1)

    time.sleep(2)
    return


def create_machine(app_name, jupyter_token, student_id):
    """Create a new machine for the app"""
    data = {
        "name": f"{FLY_APP_PREFIX}instance",
        "region": "iad",  # Default region, can be made configurable
        "config": {
            "image": JUPYTER_IMAGE,
            "env": {
                "JUPYTER_TOKEN": jupyter_token,
                "STUDENT_ID": student_id,
            },
            "services": [
                {
                    "ports": [
                        {"port": 80, "handlers": ["http"]},
                        {"port": 443, "handlers": ["tls", "http"]},
                    ],
                    "protocol": "tcp",
                    "internal_port": 8888,
                    "concurrency": {
                        "type": "connections",
                        "hard_limit": 25,
                        "soft_limit": 20,
                    },
                }
            ],
            "mounts": [{"volume": "user_data", "path": "/home/jovyan/work"}],
        },
    }

    result = make_api_request("POST", f"/v1/apps/{app_name}/machines", data)

    if result["status"] not in [200, 201]:
        pretty_print(
            f"Failed to create machine: {result.get('error', 'Unknown error')}",
            Color.ERRORRED,
        )
        sys.exit(1)

    return


def provision_jupyter(student_id: str, app_name: str):
    """Provision a new Jupyter Lab instance for a student"""
    jupyter_token = secrets.token_urlsafe()
    result = make_api_request("GET", f"/v1/apps/{app_name}")

    if result["status"] == 200:
        pretty_print(f"[X] Instance for {student_id} already exists", Color.WARNING)
        pretty_print(
            f"\tAccess URL: https://{app_name}.{BASE_DOMAIN}/lab?token={jupyter_token}",
            Color.UNDERLINE,
        )
        return

    pretty_print(f"[X] Creating new Jupyter instance for student: {student_id}")

    create_app(app_name)
    create_volume(app_name, "user_data", VOLUME_SIZE)
    create_machine(app_name, jupyter_token, student_id)

    pretty_print(f"[X] Successfully deployed Jupyter instance for {student_id}")
    pretty_print(
        f"\tAccess URL: https://{app_name}.{BASE_DOMAIN}/lab?token={jupyter_token}",
        Color.UNDERLINE,
    )

    config_dir = Path(__file__).parent / f".fly-configs/{student_id}"
    config_dir.mkdir(parents=True, exist_ok=True)

    access_info = {
        "student_id": student_id,
        "app_name": app_name,
        "url": f"https://{app_name}.{BASE_DOMAIN}/lab?token={jupyter_token}",
        "token": jupyter_token,
    }

    with open(config_dir / "access.json", "w") as f:
        json.dump(access_info, f, indent=2)


def get_machines(app_name: str):
    """Get all machines for an app"""
    result = make_api_request("GET", f"/v1/apps/{app_name}/machines")

    if result["status"] != 200:
        return list()

    return result["data"]


def terminate_jupyter(student_id: str, app_name: str):
    """Stop a student's Jupyter instance"""

    machines = get_machines(app_name)
    if not machines:
        pretty_print(f"No running machines found for {student_id}", Color.ERRORRED)
        return

    for machine in machines:
        machine_id = machine["id"]
        result = make_api_request(
            "POST", f"/v1/apps/{app_name}/machines/{machine_id}/stop"
        )

        if result["status"] not in [200, 204]:
            pretty_print(
                f"Failed to stop machine {machine_id} for {student_id}", Color.ERRORRED
            )

        pretty_print(f"Successfully stopped machine {machine_id} for {student_id}")


def start_jupyter(student_id: str, app_name: str):
    """Start a previously created but stopped Jupyter instance"""

    app_result = make_api_request("GET", f"/v1/apps/{app_name}")
    if app_result["status"] != 200:
        pretty_print(f"No instance found for {student_id}", Color.ERRORRED)
        return

    machines = get_machines(app_name)

    if machines:
        for machine in machines:
            if machine["state"] != "started":
                machine_id = machine["id"]
                result = make_api_request(
                    "POST", f"/v1/apps/{app_name}/machines/{machine_id}/start"
                )

                if result["status"] not in [200, 204]:
                    pretty_print(
                        f"Failed to start machine {machine_id} for {student_id}",
                        Color.ERRORRED,
                    )

                pretty_print(
                    f"Successfully started machine {machine_id} for {student_id}"
                )

    else:
        config_dir = Path(__file__).parent / f".fly-configs/{student_id}"
        access_file = config_dir / "access.json"

        if access_file.exists():
            with open(access_file, "r") as f:
                access_info = json.load(f)
                jupyter_token = access_info.get("token", secrets.token_urlsafe())
                create_machine(app_name, jupyter_token, student_id)
                pretty_print(f"Successfully recreated machine for {student_id}")
        else:
            jupyter_token = secrets.token_urlsafe()
            create_machine(app_name, jupyter_token, student_id)
            pretty_print(f"Created new machine for {student_id} with new token")


def delete_jupyter(student_id, app_name: str):
    """Completely remove a student's Jupyter instance"""

    confirm = input(
        f"{Color.WARNING}Are you sure you want to delete the instance for {student_id}? (y/N): {Color.ENDC}"
    )
    if confirm.lower() != "y":
        pretty_print("Operation canceled", Color.WARNING)
        return

    result = make_api_request("DELETE", f"/v1/apps/{app_name}")

    if result["status"] not in [200, 204]:
        pretty_print(
            f"Failed to delete instance for {student_id}: {result.get('error', 'Unknown error')}",
            Color.ERRORRED,
        )
    pretty_print(f"Successfully deleted instance for {student_id}")


def list_instances():
    """List all Jupyter instances"""
    result = make_api_request("GET", "/v1/apps")

    if result["status"] != 200:
        pretty_print("Failed to list apps", Color.ERRORRED)
        return

    apps = result["data"]
    jupyter_instances = [app for app in apps if app["name"].startswith(FLY_APP_PREFIX)]

    if not jupyter_instances:
        pretty_print("No Jupyter instances found", Color.WARNING)
        return

    pretty_print("Jupyter instances:")
    for instance in jupyter_instances:
        student_id = instance["name"].replace(FLY_APP_PREFIX, "")

        machines = get_machines(instance["name"])
        status = "unavailable"
        if machines:
            status = machines[0]["state"]

        pretty_print(
            f"Student: {student_id}, App: {instance['name']}, Status: {status}",
            Color.UNDERLINE,
        )


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
            provision_jupyter(
                args.student_id,
                args.course_id,
                args.resource_limit,
                f"{FLY_APP_PREFIX}{student_id}",
            )
        case CliCommand.STOP.value:
            terminate_jupyter(args.student_id, f"{FLY_APP_PREFIX}{student_id}")
        case CliCommand.START.value:
            start_jupyter(args.student_id, f"{FLY_APP_PREFIX}{student_id}")
        case CliCommand.DELETE.value:
            delete_jupyter(args.student_id, f"{FLY_APP_PREFIX}{student_id}")
        case CliCommand.LIST.value:
            list_instances()
        case CliCommand.BATCH.value:
            with open(args.file, "r") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        parts = line.strip().split(",")
                        if len(parts) < 2:
                            pretty_print(
                                f"Invalid line format: {line.strip()}", Color.ERRORRED
                            )
                            continue
                        student_id = parts[0]
                        resource_limit = parts[2] if len(parts) > 2 else "standard"
                        pretty_print(f"Provisioning for {student_id}")
                        provision_jupyter(student_id, f"{FLY_APP_PREFIX}{student_id}")

        case _:
            parser.print_help()


if __name__ == "__main__":
    major, minor, _ = platform.python_version_tuple()
    if int(major) != 3 and int(minor) < 9:
        pretty_print("[X] Python 3.9 or later is required", Color.ERRORRED)
        sys.exit(1)
    if not (FLY_ORGANIZATION and BASE_DOMAIN and JUPYTER_IMAGE and FLY_API_TOKEN):
        pretty_print("[X] Missing required environment variables", Color.ERRORRED)
        sys.exit(1)
    main()

from __future__ import annotations

import argparse
import ipaddress
import socket
from dataclasses import dataclass


DEFAULT_HOST = "127.0.0.1"
DEFAULT_LAN_HOST = "0.0.0.0"
DEFAULT_PORT = 8765
DEFAULT_PREFERRED_INPUT = "aux"
LOCAL_HOSTNAMES = {"localhost"}


@dataclass(frozen=True)
class RuntimeConfig:
    host: str
    port: int
    lan_enabled: bool
    preferred_input: str

    @property
    def local_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def lan_url(self, lan_ip: str) -> str:
        return f"http://{lan_ip}:{self.port}"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Logitech Z407 Remote Control Server")
    parser.add_argument("--ip", type=str, default=None, help="Host IP to bind to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to bind to (default: {DEFAULT_PORT})")
    parser.add_argument("--lan", action="store_true", help="Expose the web app to other devices on the local network")
    parser.add_argument(
        "--preferred-input",
        choices=("aux", "usb", "bluetooth"),
        default=DEFAULT_PREFERRED_INPUT,
        help="Input source to emphasize in the UI",
    )
    return parser


def build_runtime_config(argv: list[str] | None = None) -> RuntimeConfig:
    args = build_arg_parser().parse_args(argv)
    host = args.ip
    lan_enabled = args.lan

    if host is None:
        host = DEFAULT_LAN_HOST if args.lan else DEFAULT_HOST
    elif not _is_loopback_host(host):
        lan_enabled = True

    return RuntimeConfig(
        host=host,
        port=args.port,
        lan_enabled=lan_enabled,
        preferred_input=args.preferred_input,
    )


def _is_loopback_host(host: str) -> bool:
    if host.casefold() in LOCAL_HOSTNAMES:
        return True

    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return _is_ipv4_loopback_shorthand(host)


def _is_ipv4_loopback_shorthand(host: str) -> bool:
    parts = host.split(".")
    if not 1 <= len(parts) <= 4:
        return False

    try:
        octets = [int(part, 10) for part in parts]
    except ValueError:
        return False

    return all(0 <= octet <= 255 for octet in octets) and octets[0] == 127


def get_lan_ip() -> str:
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        if s is not None:
            s.close()

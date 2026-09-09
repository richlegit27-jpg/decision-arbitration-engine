from __future__ import annotations

import socket

from nova_backend.tools.base import NovaTool


class PortCheckTool(NovaTool):

    name = "port_check"
    description = "Checks whether a local TCP port is open."
    category = "system"

    capabilities = [
        "port inspection",
        "local server detection",
    ]

    risk_level = "low"
    requires_confirmation = False

    def run(
        self,
        port: int,
        host: str = "127.0.0.1",
        timeout: float = 1.0,
        **kwargs,
    ):

        try:

            port = int(port)

            with socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM,
            ) as sock:

                sock.settimeout(
                    float(timeout)
                )

                result = sock.connect_ex(
                    (host, port)
                )

            return {
                "ok": True,
                "host": host,
                "port": port,
                "open": result == 0,
            }

        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
            }

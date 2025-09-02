"""Helper script to install Hecate as a systemd service.

Running this script writes a small systemd unit file that ensures the
``autostart.py`` watcher boots with the operating system and restarts if the
process crashes.  It requires root privileges on Linux systems with systemd.

Usage::

    sudo python install_service.py

After running, the service is enabled and started immediately.  Subsequent
reboots will automatically launch Hecate via ``autostart.py``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from textwrap import dedent


SERVICE_NAME = "hecate"


def main() -> None:
    cwd = os.path.abspath(os.path.dirname(__file__))
    python = sys.executable
    autostart = os.path.join(cwd, "autostart.py")

    service_path = f"/etc/systemd/system/{SERVICE_NAME}.service"
    service_contents = dedent(
        f"""
        [Unit]
        Description=Hecate self-start service
        After=network.target

        [Service]
        Type=simple
        WorkingDirectory={cwd}
        ExecStart={python} {autostart}
        Restart=always
        RestartSec=5

        [Install]
        WantedBy=multi-user.target
        """
    ).strip()

    try:
        with open(service_path, "w") as fh:
            fh.write(service_contents)
        print(f"Wrote service file to {service_path}")
        subprocess.run(["systemctl", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "enable", SERVICE_NAME], check=False)
        subprocess.run(["systemctl", "start", SERVICE_NAME], check=False)
        print("Service enabled and started. Hecate will auto-start on boot and restart on crash.")
    except PermissionError:
        print("Permission denied. Run this script as root to install the service.")


if __name__ == "__main__":
    main()


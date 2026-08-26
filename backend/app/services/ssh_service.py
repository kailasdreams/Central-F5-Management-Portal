"""
SSH service for F5 devices.
Two modes:
  1. Interactive shell (used by the WebSocket CLI terminal - xterm.js on the frontend)
  2. One-shot structured command execution (tmsh command runner)
"""
import socket
import paramiko
from typing import Optional


class SSHServiceError(Exception):
    pass


def open_shell_channel(host: str, port: int, username: str, password: str,
                        term: str = "xterm", cols: int = 120, rows: int = 32) -> tuple:
    """Opens an interactive SSH shell channel. Returns (client, channel).
    Caller is responsible for closing both."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host, port=port, username=username, password=password,
            timeout=10, banner_timeout=10, auth_timeout=10, look_for_keys=False,
            allow_agent=False,
        )
    except (paramiko.AuthenticationException, paramiko.SSHException, socket.error) as e:
        raise SSHServiceError(f"SSH connection to {host}:{port} failed: {e}")

    channel = client.invoke_shell(term=term, width=cols, height=rows)
    channel.settimeout(0.0)
    return client, channel


def run_command(host: str, port: int, username: str, password: str, command: str,
                 timeout: int = 20) -> str:
    """One-shot command execution (e.g. a single tmsh command). Not for interactive use."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host, port=port, username=username, password=password,
            timeout=10, banner_timeout=10, auth_timeout=10, look_for_keys=False,
            allow_agent=False,
        )
        # F5 SSH login shell is tmsh by default; -c passes a single command
        # through the bash utility login for reliability across device configs.
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        return out if out else err
    except (paramiko.AuthenticationException, paramiko.SSHException, socket.error) as e:
        raise SSHServiceError(f"SSH command execution on {host}:{port} failed: {e}")
    finally:
        client.close()


def tail_log_file(host: str, port: int, username: str, password: str,
                   log_path: str, lines: int = 500, timeout: int = 20) -> str:
    """Tails a log file on the F5 device (e.g. /var/log/ltm)."""
    safe_lines = int(lines)
    command = f"tail -n {safe_lines} {log_path}"
    return run_command(host, port, username, password, command, timeout=timeout)

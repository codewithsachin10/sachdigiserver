import os
import pty
import fcntl
import termios
import struct
import signal
import subprocess
import asyncio
import uuid
from typing import Dict, Any
from datetime import datetime

# Global store for active PTY sessions
# Format: { session_id: { "master_fd": int, "pid": int, "name": str, "created_at": str, "cwd": str } }
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

def get_shell_command():
    for sh in ["/bin/bash", "/bin/sh"]:
        if os.path.exists(sh):
            return sh
    return "/bin/sh"

def create_terminal_session(name: str = "Host Terminal", cwd: str = "/app") -> Dict[str, Any]:
    session_id = str(uuid.uuid4())[:8]
    master_fd, slave_fd = pty.openpty()

    # Set non-blocking on master_fd
    fl = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    # Determine start directory (fallback to /app if invalid)
    start_dir = cwd if os.path.isdir(cwd) else "/app"
    shell = get_shell_command()

    # Set initial window size (80x24)
    try:
        winsize = struct.pack("HHHH", 24, 80, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
    except Exception:
        pass

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["PS1"] = "\\[\\033[01;32m\\]sachdeploy\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\]\\$ "

    # Spawn shell subprocess attached to PTY slave
    proc = subprocess.Popen(
        [shell, "-i"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        cwd=start_dir,
        env=env,
        preexec_fn=os.setsid
    )

    # Close slave_fd in parent process so EOF works correctly when child exits
    os.close(slave_fd)

    session_data = {
        "id": session_id,
        "name": name,
        "master_fd": master_fd,
        "pid": proc.pid,
        "created_at": datetime.now().strftime("%H:%M:%S"),
        "cwd": start_dir
    }
    ACTIVE_SESSIONS[session_id] = session_data
    return session_data

def list_terminal_sessions():
    # Prune dead sessions first
    dead_ids = []
    for sid, data in ACTIVE_SESSIONS.items():
        try:
            # Check if process still running
            os.kill(data["pid"], 0)
        except OSError:
            dead_ids.append(sid)
    
    for sid in dead_ids:
        kill_terminal_session(sid)
        
    return [
        {
            "id": data["id"],
            "name": data["name"],
            "created_at": data["created_at"],
            "cwd": data.get("cwd", "/app")
        }
        for data in ACTIVE_SESSIONS.values()
    ]

def kill_terminal_session(session_id: str):
    if session_id not in ACTIVE_SESSIONS:
        return False
    data = ACTIVE_SESSIONS.pop(session_id)
    try:
        os.killpg(os.getpgid(data["pid"]), signal.SIGTERM)
    except Exception:
        try:
            os.kill(data["pid"], signal.SIGKILL)
        except Exception:
            pass
    try:
        os.close(data["master_fd"])
    except Exception:
        pass
    return True

def resize_terminal_session(session_id: str, cols: int, rows: int):
    if session_id not in ACTIVE_SESSIONS:
        return False
    master_fd = ACTIVE_SESSIONS[session_id]["master_fd"]
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
        return True
    except Exception as e:
        print(f"[Terminal] Resize error on session {session_id}: {e}")
        return False

async def read_pty_loop(websocket, master_fd: int):
    """Asynchronous loop reading from PTY master FD and sending to WebSocket"""
    loop = asyncio.get_event_loop()
    while True:
        try:
            # Use run_in_executor or non-blocking read
            data = await loop.run_in_executor(None, _read_fd_safe, master_fd)
            if data:
                await websocket.send_text(data.decode("utf-8", errors="replace"))
            else:
                await asyncio.sleep(0.02)
        except Exception as e:
            break

def _read_fd_safe(fd: int):
    try:
        return os.read(fd, 4096)
    except (BlockingIOError, InterruptedError):
        return None
    except OSError:
        return None

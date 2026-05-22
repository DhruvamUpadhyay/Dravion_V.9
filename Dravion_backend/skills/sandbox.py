"""
DRAVION v.9 — Code Execution Sandbox

Safe execution of Python and shell code from chat:
  - Subprocess-isolated Python execution
  - 30-second timeout
  - Output capture (stdout + stderr)
  - No file system destruction allowed
"""
import subprocess
import tempfile
import os
from datetime import datetime
from core.logger import log

BLOCKED_PATTERNS = [
    "os.remove", "os.unlink", "shutil.rmtree", "os.rmdir",
    "rm -rf", "del /f", "format c:", "mkfs",
    "subprocess.call", "exec(", "eval(",
    "__import__('os').system",
]


def execute_python(code: str, timeout: int = 30) -> str:
    """Execute Python code in an isolated subprocess."""
    # Safety check
    for pattern in BLOCKED_PATTERNS:
        if pattern in code:
            return f"Blocked: dangerous pattern '{pattern}' detected. I won't run destructive code, Boss."

    log.info("sandbox_exec", lang="python", code_len=len(code))

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(code)
        tmp.close()

        result = subprocess.run(
            ["python", tmp.name],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir(),
        )

        output = result.stdout.strip()
        errors = result.stderr.strip()

        if result.returncode == 0:
            return output if output else "(executed successfully, no output)"
        else:
            return f"Error (exit {result.returncode}):\n{errors}\n{output}".strip()

    except subprocess.TimeoutExpired:
        return f"Execution timed out after {timeout}s. Code may have an infinite loop."
    except Exception as e:
        return f"Execution failed: {e}"
    finally:
        try:
            os.unlink(tmp.name)
        except:
            pass


def execute_shell(command: str, timeout: int = 15) -> str:
    """Execute a shell command with safety checks."""
    lower = command.lower()
    for pattern in ["rm -rf", "del /f /s", "format ", "mkfs", "dd if="]:
        if pattern in lower:
            return f"Blocked: destructive command pattern '{pattern}'. Not happening, Boss."

    log.info("sandbox_shell", cmd=command[:60])

    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout.strip() or result.stderr.strip() or "(no output)")
        return output[:3000]
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s."
    except Exception as e:
        return f"Shell execution failed: {e}"

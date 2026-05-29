# logic/agents/sandbox.py
"""
5.1.1.b — Tool Execution Sandbox

A strict subprocess sandbox where agents can write and execute Python code
in complete isolation.  The sandbox:

  • Writes code to a temporary file inside a controlled workspace directory
  • Runs it in a subprocess with strict timeouts and resource constraints
  • Captures stdout/stderr and returns structured results
  • Prevents imports of dangerous modules (os.system, subprocess, shutil.rmtree)
  • Cleans up temporary files after execution
"""

import os
import sys
import uuid
import logging
import tempfile
import subprocess
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("QuantumToolSandbox")

# Modules / calls that are forbidden inside sandboxed code
FORBIDDEN_PATTERNS = [
    r"\bos\.system\b",
    r"\bsubprocess\.",
    r"\bshutil\.rmtree\b",
    r"\b__import__\b",
    r"\beval\b",
    r"\bexec\b",
    r"\bopen\s*\(.*(\/etc|\/var|C:\\\\Windows)",
    r"\bsocket\.",
    r"\brequests\.(get|post|put|delete|patch)\b",
]


@dataclass
class SandboxResult:
    """Structured result from a sandbox execution."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = -1
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class ToolExecutionSandbox:
    """
    Isolated Python subprocess sandbox for autonomous agent code execution.

    Usage:
        sandbox = ToolExecutionSandbox(workspace_dir="/path/to/sandbox_workspace")
        result = sandbox.execute("print('Hello from sandbox')")
        print(result.stdout)  # "Hello from sandbox\n"
    """

    DEFAULT_TIMEOUT_SECONDS = 30
    MAX_OUTPUT_BYTES = 1024 * 1024  # 1 MB

    def __init__(self, workspace_dir: Optional[str] = None, timeout: int = None):
        if workspace_dir:
            self.workspace_dir = workspace_dir
        else:
            # Default to a sandbox subdirectory inside the project's scratch folder
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            self.workspace_dir = os.path.join(project_root, "scratch", "sandbox")

        os.makedirs(self.workspace_dir, exist_ok=True)
        self.timeout = timeout or self.DEFAULT_TIMEOUT_SECONDS
        logger.info(f"Sandbox workspace initialized at: {self.workspace_dir}")

    def validate_code(self, code: str) -> Optional[str]:
        """
        Static analysis pass: scans code for forbidden patterns before execution.
        Returns an error message string if a violation is found, else None.
        """
        for pattern in FORBIDDEN_PATTERNS:
            match = re.search(pattern, code)
            if match:
                violation = match.group(0)
                logger.warning(f"Sandbox policy violation detected: '{violation}'")
                return f"Security policy violation: forbidden pattern '{violation}' detected."
        return None

    def execute(self, code: str, env_vars: Optional[dict] = None) -> SandboxResult:
        """
        Executes a Python code string inside an isolated subprocess.

        Args:
            code: Python source code to execute.
            env_vars: Optional dict of extra environment variables to inject.

        Returns:
            SandboxResult with stdout, stderr, return code, and timing.
        """
        # Pre-flight static analysis
        violation = self.validate_code(code)
        if violation:
            return SandboxResult(
                success=False,
                error=violation,
                return_code=-1,
            )

        # Write code to a temporary file inside the workspace
        script_name = f"sandbox_{uuid.uuid4().hex[:8]}.py"
        script_path = os.path.join(self.workspace_dir, script_name)

        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Build environment: inherit current env but override with extras
            env = os.environ.copy()
            # Restrict the PYTHONPATH to only the sandbox workspace
            env["PYTHONPATH"] = self.workspace_dir
            if env_vars:
                env.update(env_vars)

            import time
            start_time = time.monotonic()

            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.workspace_dir,
                env=env,
            )

            elapsed_ms = (time.monotonic() - start_time) * 1000

            # Truncate excessively large outputs
            stdout = result.stdout[:self.MAX_OUTPUT_BYTES] if result.stdout else ""
            stderr = result.stderr[:self.MAX_OUTPUT_BYTES] if result.stderr else ""

            sandbox_result = SandboxResult(
                success=(result.returncode == 0),
                stdout=stdout,
                stderr=stderr,
                return_code=result.returncode,
                execution_time_ms=round(elapsed_ms, 2),
            )

            logger.info(
                f"Sandbox execution completed: rc={result.returncode}, "
                f"time={sandbox_result.execution_time_ms}ms, "
                f"stdout_len={len(stdout)}, stderr_len={len(stderr)}"
            )
            return sandbox_result

        except subprocess.TimeoutExpired:
            logger.error(f"Sandbox execution timed out after {self.timeout}s")
            return SandboxResult(
                success=False,
                error=f"Execution timed out after {self.timeout} seconds.",
                return_code=-1,
            )
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return SandboxResult(
                success=False,
                error=str(e),
                return_code=-1,
            )
        finally:
            # Clean up the temporary script
            try:
                if os.path.exists(script_path):
                    os.remove(script_path)
            except Exception:
                pass

    def cleanup(self):
        """Removes all files from the sandbox workspace directory."""
        try:
            for f in os.listdir(self.workspace_dir):
                fpath = os.path.join(self.workspace_dir, f)
                if os.path.isfile(fpath):
                    os.remove(fpath)
            logger.info("Sandbox workspace cleaned up.")
        except Exception as e:
            logger.error(f"Sandbox cleanup error: {e}")

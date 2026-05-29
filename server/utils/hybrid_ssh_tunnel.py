# utils/hybrid_ssh_tunnel.py
import os
import sys
import platform
import logging
import subprocess
import threading
from typing import Optional

logger = logging.getLogger("QuantumSSHTunnel")

class HybridSSHTunnel:
    """
    7.1.2 Hybrid SSH Tunneling Engine
    Primary: Uses paramiko and sshtunnel for native port forwarding and remote execution.
    Fallback: Spawns plink.exe (Windows) or native ssh (Unix) invisibly via subprocess.
    """
    def __init__(self, host: str, user: str, password: str = None, key_file: str = None, port: int = 22):
        self.host = host
        self.user = user
        self.password = password
        self.key_file = key_file
        self.port = port
        
        self.forwarder = None
        self.ssh_client = None
        self._fallback_process = None

    def start_tunnel(self, remote_bind_addresses: list, local_bind_addresses: list) -> bool:
        """
        Starts the port forwarding tunnel.
        remote_bind_addresses: list of tuples, e.g., [("127.0.0.1", 5432), ("127.0.0.1", 6379), ("127.0.0.1", 5000)]
        local_bind_addresses: list of tuples, e.g., [("127.0.0.1", 5432), ("127.0.0.1", 6379), ("127.0.0.1", 5050)]
        """
        success = self._start_native_sshtunnel(remote_bind_addresses, local_bind_addresses)
        if not success:
            logger.warning("Native SSHTunnel failed. Falling back to subprocess tunneling...")
            success = self._start_fallback_tunnel(remote_bind_addresses, local_bind_addresses)
        return success

    def _start_native_sshtunnel(self, remote_bind_addresses: list, local_bind_addresses: list) -> bool:
        try:
            from sshtunnel import SSHTunnelForwarder
            import paramiko

            connect_kwargs = {}
            if self.key_file:
                connect_kwargs["pkey"] = paramiko.RSAKey.from_private_key_file(self.key_file)
            elif self.password:
                connect_kwargs["password"] = self.password

            self.forwarder = SSHTunnelForwarder(
                (self.host, self.port),
                ssh_username=self.user,
                ssh_password=self.password,
                ssh_pkey=self.key_file,
                remote_bind_addresses=remote_bind_addresses,
                local_bind_addresses=local_bind_addresses
            )
            self.forwarder.start()
            logger.info(f"Native SSHTunnel started successfully. Active bindings: {self.forwarder.local_bind_ports}")
            
            # Keep a raw paramiko client available for God Mode execution/SFTP
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(self.host, port=self.port, username=self.user, **connect_kwargs)
            logger.info("Paramiko SSHClient connected successfully for remote execution.")
            
            return True
        except ImportError:
            logger.error("sshtunnel or paramiko module not installed.")
        except Exception as e:
            logger.error(f"Failed to start native SSHTunnel: {e}")
        return False

    def _start_fallback_tunnel(self, remote_bind_addresses: list, local_bind_addresses: list) -> bool:
        # Build the forwarding arguments: -L local_port:remote_host:remote_port
        forward_args = []
        for local, remote in zip(local_bind_addresses, remote_bind_addresses):
            forward_args.extend(["-L", f"{local[1]}:{remote[0]}:{remote[1]}"])

        cmd = []
        if platform.system() == "Windows":
            from server.utils.path_utils import get_resource_path
            plink_path = get_resource_path("resources/plink.exe")
            if not plink_path.exists():
                logger.error(f"Fallback failed: plink.exe not found at {plink_path}")
                return False
            # Batch mode (-batch), no prompt, SSH (-ssh), no pty (-N)
            cmd = [str(plink_path), "-ssh", "-batch", "-N"]
            if self.password:
                cmd.extend(["-pw", self.password])
            if self.key_file:
                cmd.extend(["-i", self.key_file])
            cmd.extend([f"{self.user}@{self.host}", "-P", str(self.port)])
            cmd.extend(forward_args)
        else:
            # Native Unix SSH fallback
            cmd = ["ssh", "-N", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
            if self.key_file:
                cmd.extend(["-i", self.key_file])
            cmd.extend([f"{self.user}@{self.host}", "-p", str(self.port)])
            cmd.extend(forward_args)
            
            # Note: Unix ssh via subprocess doesn't natively accept password args securely without sshpass
            # It expects keys. We proceed assuming key_file is provided.

        try:
            logger.info(f"Executing fallback tunnel subprocess: {' '.join(cmd)}")
            # Suppress windows console and output
            creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            self._fallback_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL, 
                creationflags=creationflags
            )
            # Give it a second to fail if auth is wrong
            import time
            time.sleep(1.0)
            if self._fallback_process.poll() is not None:
                logger.error("Fallback tunnel process terminated prematurely.")
                return False
            
            logger.info("Fallback tunnel process started successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to start fallback tunnel subprocess: {e}")
            return False

    def execute_remote_command(self, command: str) -> dict:
        """7.1.2.a Native Paramiko Execution. Returns exit_status, stdout, stderr."""
        if not self.ssh_client:
            return {"error": "Native SSHClient not connected. Subprocess fallback mode does not support dynamic remote execution.", "success": False}
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            out_str = stdout.read().decode('utf-8')
            err_str = stderr.read().decode('utf-8')
            return {
                "success": exit_status == 0,
                "exit_status": exit_status,
                "stdout": out_str,
                "stderr": err_str
            }
        except Exception as e:
            return {"error": str(e), "success": False}

    def sftp_get(self, remote_path: str, local_path: str) -> bool:
        """7.1.2.a Native Paramiko SFTP download."""
        if not self.ssh_client:
            return False
        try:
            sftp = self.ssh_client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            return True
        except Exception as e:
            logger.error(f"SFTP Get failed: {e}")
            return False

    def stop_tunnel(self):
        if self.forwarder:
            self.forwarder.stop()
            self.forwarder = None
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
        if self._fallback_process:
            self._fallback_process.terminate()
            self._fallback_process = None
        logger.info("HybridSSHTunnel shut down.")

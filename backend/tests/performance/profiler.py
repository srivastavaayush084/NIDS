import os
import platform
import time
from typing import Any, Dict, Optional
import psutil


class SystemProfiler:
    """
    Measures CPU, memory RSS/VMS, and thread/process resource consumption.
    """

    def __init__(self, target_pid: Optional[int] = None):
        self.pid = target_pid or os.getpid()
        self.process = psutil.Process(self.pid)
        # Prime CPU percent measurement
        self.process.cpu_percent(interval=None)

    def sample_resource_usage(self) -> Dict[str, Any]:
        """Sample current CPU and memory consumption of the monitored process."""
        try:
            mem_info = self.process.memory_info()
            cpu_pct = self.process.cpu_percent(interval=0.05)
            num_threads = self.process.num_threads()
            return {
                "pid": self.pid,
                "cpu_percent": round(cpu_pct, 2),
                "memory_rss_mb": round(mem_info.rss / (1024 * 1024), 2),
                "memory_vms_mb": round(mem_info.vms / (1024 * 1024), 2),
                "num_threads": num_threads,
            }
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_environment_info() -> Dict[str, Any]:
        """Collect detected host environment characteristics."""
        mem = psutil.virtual_memory()
        return {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "cpu_physical_cores": psutil.cpu_count(logical=False),
            "cpu_logical_cores": psutil.cpu_count(logical=True),
            "total_ram_gb": round(mem.total / (1024**3), 2),
            "available_ram_gb": round(mem.available / (1024**3), 2),
            "python_version": platform.python_version(),
        }

from ..serialization import Serializable
from dataclasses import dataclass
from rich import print


@dataclass
class ExecutionStatus(Serializable):
    userTime: float = 0
    sysTime: float = 0
    cpuPercent: int = 0
    wallClock: float = 0
    maxResidentSize: float = 0

    def display(self):
        print(f"Status:")
        print(f"""  time  : {self.wallClock:.4f} s ({self.cpuPercent}% CPU)
  memory: {self.maxResidentSize / 1024:.4f} MB""")

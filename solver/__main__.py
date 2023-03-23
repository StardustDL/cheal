import sys
from pathlib import Path

from .connection import ConnectionState
from .pod import PodManager
from .generator import NetworkGenerator

def main(buildScript: str):
    pods = PodManager()
    state = ConnectionState(pods)
    gen = NetworkGenerator()
    exec(buildScript, {
        "pods": pods,
        "state": state,
        "gen": gen,
    })
    from .solver import HealingSolver
    print(HealingSolver(state).compile().solve())

if __name__ == "__main__":
    assert len(sys.argv) == 2, "Must have a file argument."
    file = Path(sys.argv[1])
    assert file.is_file(), "Must have a file argument."
    main(file.read_text())
import sys
from pathlib import Path

from .connection import ConnectionState
from .pod import PodManager
from .generator import RandomConnectionStateGenerator

def main(buildScript: str):
    pods = PodManager()
    state = ConnectionState(pods)
    gen = RandomConnectionStateGenerator()
    exec(buildScript, {
        "pods": pods,
        "state": state,
        "gen": gen,
    })
    state.display()
    from .solver import CIPMultipleBatchSolver
    solver = CIPMultipleBatchSolver()
    solution = solver.solve(state)
    solution.display()

if __name__ == "__main__":
    assert len(sys.argv) == 2, "Must have a file argument."
    file = Path(sys.argv[1])
    assert file.is_file(), "Must have a file argument."
    main(file.read_text())
import sys
import time
from pathlib import Path
from rich import print
import json


def main(buildScript: str):
    from .model.connection import ConnectionState
    from .model.network import Network, NetworkTopo, FreezedNetwork, Device, DeviceInterface
    from .model.pod import Pod, PodConfig, PodContainer
    from .model.solution import Solution, Batch
    from .generator import RandomConnectionStateGenerator, ProbabilityConnectionStateGenerator

    stateToSolve: ConnectionState = None

    def submit(state: ConnectionState):
        nonlocal stateToSolve
        stateToSolve = state

    exec(buildScript, locals())
    assert stateToSolve is not None
    stateToSolve.display()
    print("-" * 50)

    from .solver import CIPMultipleBatchSolver
    solver = CIPMultipleBatchSolver()
    start = time.time()
    solution = solver.solve(stateToSolve)
    end = time.time()
    print(f"Solved in {end - start:.2f} seconds")
    print("-" * 50)

    solution.display()

def bug():
    from .model.connection import ConnectionState
    state = ConnectionState()
    state.load(json.loads(Path("./bug.json").read_text()))
    from .solver import CIPMultipleBatchSolver
    solver = CIPMultipleBatchSolver()
    solution = solver.solve(state)
    solution.display()


if __name__ == "__main__":
    assert len(sys.argv) == 2, "Must have a file argument."
    file = Path(sys.argv[1])
    assert file.is_file(), "Must have a file argument."
    main(file.read_text())

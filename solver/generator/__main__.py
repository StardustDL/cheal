import sys
from pathlib import Path
from rich import print
import json

def main(buildScript: str):
    from ..model.connection import ConnectionState
    from ..model.network import Network, NetworkTopo, FreezedNetwork, Device, DeviceInterface
    from ..model.pod import Pod, PodConfig, PodContainer
    from ..model.solution import Solution, Batch
    from ..generator import RandomConnectionStateGenerator, ProbabilityConnectionStateGenerator

    stateToSolve: ConnectionState = None

    def submit(state: ConnectionState):
        nonlocal stateToSolve
        stateToSolve = state

    exec(buildScript, locals())
    assert stateToSolve is not None
    print(json.dumps(stateToSolve.dump()))

if __name__ == "__main__":
    assert len(sys.argv) == 2, "Must have a file argument."
    file = Path(sys.argv[1])
    assert file.is_file(), "Must have a file argument."
    main(file.read_text())

from pathlib import Path
import sys
import json

if __name__ == "__main__":
    assert len(sys.argv) == 2, "Must have a file argument."
    file = Path(sys.argv[1])
    assert file.is_file(), "Must have a file argument."
    
    from ..model.connection import ConnectionState
    state = ConnectionState()
    state.load(json.loads(file.read_text()))

    from . import CIPMultipleBatchSolver
    solver = CIPMultipleBatchSolver()

    solution = solver.solve(state)
    
    print(json.dumps(solution.dump()))

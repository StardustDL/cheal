import subprocess
import sys
import time
from pathlib import Path
from rich import print
import json

import click


class AliasedGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        matches = [x for x in self.list_commands(ctx)
                   if x.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail(f"Too many matches: {', '.join(sorted(matches))}")

    def resolve_command(self, ctx, args):
        # always return the full command name
        _, cmd, args = super().resolve_command(ctx, args)
        assert cmd is not None, "Command is None."
        return cmd.name, cmd, args


def execute(module: str, *args: str):
    from .model import ExecutionStatus

    status = ExecutionStatus()

    result = subprocess.run(["/usr/bin/time", "-v", "python", "-m", module, *args],
                            capture_output=True, text=True, encoding="utf-8", timeout=600)
    output = result.stdout.strip()
    stats = result.stderr.strip()
    if result.returncode != 0:
        print(stats)
        result.check_returncode()
    for line in stats.splitlines():
        line = line.strip()
        if line.startswith("User time (seconds):"):
            status.userTime = float(line.split(':')[1].strip())
        if line.startswith("System time (seconds):"):
            status.sysTime = float(line.split(':')[1].strip())
        if line.startswith("Percent of CPU this job got:"):
            status.cpuPercent = int(line.split(
                ':')[1].strip().removesuffix("%"))
        if line.startswith("Elapsed (wall clock) time (h:mm:ss or m:ss):"):
            time = line.removeprefix(
                "Elapsed (wall clock) time (h:mm:ss or m:ss): ").strip()
            minute, second = map(float, time.split(":"))
            status.wallClock = minute * 60 + second
        if line.startswith("Maximum resident set size (kbytes):"):
            status.maxResidentSize = int(line.split(':')[1])
    return output, status


@click.group(cls=AliasedGroup)
@click.pass_context
def main(ctx=None):
    pass


@main.command()
@click.argument("file", type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, path_type=Path))
def generate(file: Path):
    output, status = execute("solver.generator", str(file))
    from .model.connection import ConnectionState
    data = ConnectionState()
    data.load(json.loads(output))
    data.status = status
    print(json.dumps(data.dump()))


@main.command()
@click.argument("file", type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, path_type=Path))
def solve(file: Path):
    output, status = execute("solver.solver", str(file))
    from .model.solution import Solution
    data = Solution()
    data.load(json.loads(output))
    data.status = status
    print(json.dumps(data.dump()))


@main.command()
@click.argument("file", type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, path_type=Path))
def state(file: Path):
    from .model.connection import ConnectionState
    data = ConnectionState()
    data.load(json.loads(file.read_text()))
    data.display()


@main.command()
@click.argument("file", type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True, path_type=Path))
def solution(file: Path):
    from .model.solution import Solution
    data = Solution()
    data.load(json.loads(file.read_text()))
    data.display()


if __name__ == "__main__":
    main()

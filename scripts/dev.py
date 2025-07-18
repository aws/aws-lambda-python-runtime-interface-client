#!/usr/bin/env python3
import argparse
import subprocess
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd, check=True):
    print(f"\n$ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(cmd, shell=isinstance(cmd, str), check=check)
    if result.returncode != 0 and check:
        sys.exit(result.returncode)


def init():
    print("Initializing environment")
    run(["poetry", "install"])


def test():
    print("Running tests")
    run(["poetry", "run", "pytest", "tests"])


def lint():
    print("Running lint checks")
    run(["poetry", "run", "flake8", "awslambdaric"])
    run(["poetry", "run", "pylint", "awslambdaric"])
    run(["poetry", "run", "black", "--check", "awslambdaric"])
    run(["poetry", "run", "bandit", "-r", "awslambdaric"])


def clean():
    print("Cleaning build and cache files")
    patterns = ["__pycache__", "*.pyc", "*.pyo", ".pytest_cache", ".mypy_cache"]
    for pattern in patterns:
        for path in ROOT.rglob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()


def build():
    print("Building package")
    run(["poetry", "build"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Development command-line tool")
    parser.add_argument("command", choices=["init", "test", "lint", "clean", "build"])
    args = parser.parse_args()

    globals()[args.command]()

#!/usr/bin/env python3
import argparse
import subprocess
import shutil
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def run(cmd, check=True, env=None):
    print(f"\n$ {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(cmd, shell=isinstance(cmd, str), check=check, env=env)
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

    for folder in ["dist", "build", "awslambdaric.egg-info"]:
        dir_path = ROOT / folder
        if dir_path.exists():
            shutil.rmtree(dir_path)

def build():
    print("Building package")
    env = os.environ.copy()
    if sys.platform.startswith("linux"):
        env["BUILD"] = "true"
    run([sys.executable, "setup.py", "sdist", "bdist_wheel"], env=env)

def local_test():
    print("Running local tests")
    # will be implemented later using RIE

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Development command-line tool")
    parser.add_argument("command", choices=["init", "test", "lint", "clean", "build", "local-test"])
    args = parser.parse_args()
    commands = {
    "init": init,
    "test": test,
    "lint": lint,
    "clean": clean,
    "build": build,
    "local-test": local_test,
}

commands[args.command]()


#!/usr/bin/env python3
import argparse
import subprocess
import shutil
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def run(cmd, check=True, env=None):
    print("\n$ {}".format(' '.join(cmd) if isinstance(cmd, list) else cmd))
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
    print("Running linters")
    run(["poetry", "run", "ruff", "check", "awslambdaric/", "tests/"])


def format_code():
    print("Formatting code")
    run(["poetry", "run", "black", "awslambdaric/", "tests/"])


def clean():
    print("Cleaning build artifacts")
    dirs_to_remove = ["build", "dist", "*.egg-info"]
    for pattern in dirs_to_remove:
        for path in ROOT.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print("Removed directory: {}".format(path))
            elif path.is_file():
                path.unlink()
                print("Removed file: {}".format(path))


def build():
    print("Building package")
    env = os.environ.copy()
    if os.getenv("BUILD") == "true":
        env["BUILD"] = "true"
    run([sys.executable, "setup.py", "sdist", "bdist_wheel"], env=env)


def main():
    parser = argparse.ArgumentParser(description="Development scripts")
    parser.add_argument("command", choices=[
        "init", "test", "lint", "format", "clean", "build"
    ])
    
    args = parser.parse_args()
    
    command_map = {
        "init": init,
        "test": test,
        "lint": lint,
        "format": format_code,
        "clean": clean,
        "build": build,

    }
    
    command_map[args.command]()


if __name__ == "__main__":
    main()


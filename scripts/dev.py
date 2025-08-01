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
    run(["poetry", "run", "ruff", "format", "awslambdaric/", "tests/"])


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
    
    # Set BUILD=true on Linux for native compilation
    import platform
    if platform.system() == "Linux":
        env["BUILD"] = "true"
    elif os.getenv("BUILD") == "true":
        env["BUILD"] = "true"
        
    run([sys.executable, "setup.py", "sdist", "bdist_wheel"], env=env)


def build_container():
    print("Building awslambdaric wheel in container")
    run(["./scripts/build-container.sh"])


def test_rie():
    print("Testing with RIE using pre-built wheel")
    run(["./scripts/test-rie.sh"])

def check_docstr():
    print("Checking docstrings")
    run(["poetry", "run", "ruff", "check", "--select", "D", "--ignore", "D105", "awslambdaric/"])


def main():
    parser = argparse.ArgumentParser(description="Development scripts")
    parser.add_argument("command", choices=[
        "init", "test", "lint", "format", "clean", "build", "build-container", "test-rie",
        "check-docstr"
    ])
    
    args = parser.parse_args()
    
    command_map = {
        "init": init,
        "test": test,
        "lint": lint,
        "format": format_code,
        "clean": clean,
        "build": build,
        "build-container": build_container,
        "test-rie": test_rie,
        "check-docstr": check_docstr,
    }
    
    command_map[args.command]()


if __name__ == "__main__":
    main()


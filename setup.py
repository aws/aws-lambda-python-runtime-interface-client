import os
import platform
import sys
from subprocess import check_call, check_output
from setuptools import Extension, setup, find_packages

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tomli"])
        import tomli as tomllib

def get_metadata():
    with open("pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    
    poetry_config = pyproject["tool"]["poetry"]
    return {
        "name": poetry_config["name"],
        "version": poetry_config["version"],
        "description": poetry_config["description"],
        "author": poetry_config["authors"][0] if poetry_config["authors"] else "",
        "license": poetry_config["license"],
        "python_requires": poetry_config["dependencies"]["python"],
        "install_requires": [
            f"{pkg}{version}" if not version.startswith("^") and not version.startswith("~") else f"{pkg}>={version[1:]}"
            for pkg, version in poetry_config["dependencies"].items()
            if pkg != "python"
        ]
    }

def get_curl_extra_linker_flags():
    if platform.system() != "Linux" or os.getenv("BUILD") != "true":
        return []
    check_call(["./scripts/preinstall.sh"])
    cmd = ["./deps/artifacts/bin/curl-config", "--static-libs"]
    curl_config = check_output(cmd).decode("utf-8").strip()
    return curl_config.split(" ")[1:]

def get_runtime_client_extension():
    if platform.system() != "Linux" and os.getenv("BUILD") != "true":
        print("Native extension build skipped on non-Linux.")
        return []
    return [Extension(
        "runtime_client",
        ["awslambdaric/runtime_client.cpp"],
        extra_compile_args=["--std=c++11"],
        library_dirs=["deps/artifacts/lib", "deps/artifacts/lib64"],
        libraries=["aws-lambda-runtime", "curl"],
        extra_link_args=get_curl_extra_linker_flags(),
        include_dirs=["deps/artifacts/include"],
    )]

metadata = get_metadata()

setup(
    name=metadata["name"],
    version=metadata["version"],
    description=metadata["description"],
    author=metadata["author"],
    license=metadata["license"],
    packages=find_packages(),
    python_requires=metadata["python_requires"],
    install_requires=metadata["install_requires"],
    ext_modules=get_runtime_client_extension(),
)

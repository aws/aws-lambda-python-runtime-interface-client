import sys
from setuptools import setup, find_packages

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
            f"{pkg}{version}" if isinstance(version, str) and not version.startswith("^") and not version.startswith("~") else f"{pkg}>={version[1:] if isinstance(version, str) else version}"
            for pkg, version in poetry_config["dependencies"].items()
            if pkg != "python" and not isinstance(version, dict)
        ]
    }

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
)

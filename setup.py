"""
Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import os
import platform
from subprocess import check_call, check_output
from setuptools import Extension, find_packages, setup

def get_curl_extra_linker_flags():
    if platform.system() != "Linux" or os.getenv("BUILD") != "true":
        return []
    check_call(["./scripts/preinstall.sh"])
    cmd = ["./deps/artifacts/bin/curl-config", "--static-libs"]
    curl_config = check_output(cmd).decode("utf-8").replace("\n", "")
    flags = curl_config.split(" ")[1:]
    return flags

def get_runtime_client_extension():
    if platform.system() != "Linux" and os.getenv("BUILD") != "true":
        print("The native runtime_client only builds on Linux. Skipping its compilation.")
        return []
    runtime_client = Extension(
        "runtime_client",
        ["awslambdaric/runtime_client.cpp"],
        extra_compile_args=["--std=c++11"],
        library_dirs=["deps/artifacts/lib", "deps/artifacts/lib64"],
        libraries=["aws-lambda-runtime", "curl"],
        extra_link_args=get_curl_extra_linker_flags(),
        include_dirs=["deps/artifacts/include"],
    )
    return [runtime_client]

def readme():
    try:
        with open("README.md", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

setup(
    name="awslambdaric",
    version="3.0.2",
    description="AWS Lambda Runtime Interface Client for Python",
    long_description=readme(),
    long_description_content_type="text/markdown",
    author="Amazon Web Services",
    url="https://github.com/aws/aws-lambda-python-runtime-interface-client",
    packages=find_packages(exclude=("tests", "tests.*", "docs", "examples", "versions")),
    python_requires=">=3.9",
    install_requires=[
        "simplejson>=3.20.1",
        "snapshot-restore-py>=1.0.0",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    ext_modules=get_runtime_client_extension(),
    test_suite="tests",
)

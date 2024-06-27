"""
Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import io
import os
import platform
from subprocess import check_call, check_output
from setuptools import Extension, find_packages, setup


def get_curl_extra_linker_flags():
    # We do not want to build the dependencies during packaging
    if platform.system() != "Linux" or os.getenv("BUILD") == "true":
        return []

    # Build the dependencies
    check_call(["./scripts/preinstall.sh"])

    # call curl-config to get the required linker flags
    cmd = ["./deps/artifacts/bin/curl-config", "--static-libs"]
    curl_config = check_output(cmd).decode("utf-8").replace("\n", "")

    # It is expected that the result of the curl-config call is similar to
    # "/tmp/pip-req-build-g9dlug7g/deps/artifacts/lib/libcurl.a -lidn2"
    # we want to return just the extra flags
    flags = curl_config.split(" ")[1:]

    return flags


def get_runtime_client_extension():
    if platform.system() != "Linux" and os.getenv("BUILD") != "true":
        print(
            "The native runtime_client only builds on Linux. Skipping its compilation."
        )
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


def read(*filenames, **kwargs):
    encoding = kwargs.get("encoding", "utf-8")
    sep = kwargs.get("sep", os.linesep)
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)

setup(
    packages=find_packages(
        exclude=("tests", "tests.*", "docs", "examples", "versions")
    ),
    ext_modules=get_runtime_client_extension(),
    test_suite="tests",
)

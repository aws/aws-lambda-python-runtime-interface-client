"""
Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""

import io
import os
import platform
from subprocess import check_call, check_output
from setuptools import Extension, find_packages, setup


def read(*filenames, **kwargs):
    encoding = kwargs.get("encoding", "utf-8")
    sep = kwargs.get("sep", os.linesep)
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)


def read_requirements(req="base.txt"):
    content = read(os.path.join("requirements", req))
    return [
        line for line in content.split(os.linesep) if not line.strip().startswith("#")
    ]


setup(
    name="awslambdaric",
    version="1.0.0",
    author="Amazon Web Services",
    description="AWS Lambda Runtime Interface Client for Python",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/aws/aws-lambda-python-runtime-interface-client",
    packages=find_packages(
        exclude=("tests", "tests.*", "docs", "examples", "versions")
    ),
    install_requires=read_requirements("base.txt"),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    test_suite="tests",
)

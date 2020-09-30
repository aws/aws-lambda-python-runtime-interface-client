#!/bin/sh
# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
set -e

ARTIFACTS_DIR=$(pwd)/deps/artifacts

if [ "$(uname)" = "Darwin" ]; then
    echo "aws-lambda-cpp does not build on OS X. Skipping the preinstall step."
else
    if [ -x "$(command -v cmake3)" ]; then
        CMAKE=cmake3
    elif [ -x "$(command -v cmake)" ]; then
        CMAKE=cmake
    else
        echo 'Error: cmake is not installed.' >&2
        exit 1
    fi

    cd deps
    . ./versions

    rm -rf ./curl-curl-$CURL_VERSION
    rm -rf ./aws-lambda-cpp-$AWS_LAMBDA_CPP_RELEASE

    # unpack dependencies
    tar xzf ./curl-$CURL_VERSION.tar.gz && \
    tar xzf ./aws-lambda-cpp-$AWS_LAMBDA_CPP_RELEASE.tar.gz

    (
        # Build Curl
        cd curl-curl-$CURL_VERSION && \
            ./buildconf && \
            ./configure \
                --prefix "$ARTIFACTS_DIR" \
                --disable-shared \
                --without-ssl \
                --without-zlib && \
            make && \
            make install
    )

    (
        # Build aws-lambda-cpp
        mkdir -p ./aws-lambda-cpp-$AWS_LAMBDA_CPP_RELEASE/build && \
            cd ./aws-lambda-cpp-$AWS_LAMBDA_CPP_RELEASE/build

        $CMAKE .. \
                -DCMAKE_CXX_FLAGS="-fPIC" \
                -DCMAKE_INSTALL_PREFIX="$ARTIFACTS_DIR" \
                -DENABLE_LTO=$ENABLE_LTO \
                -DCMAKE_MODULE_PATH="$ARTIFACTS_DIR"/lib/pkgconfig && \
            make && make install
    )
fi
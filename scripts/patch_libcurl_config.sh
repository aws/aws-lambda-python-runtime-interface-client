#!/bin/bash
# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.

set -x

(
    cd deps
    . versions
    LIBCURL="curl-${CURL_MAJOR_VERSION}.${CURL_MINOR_VERSION}.${CURL_PATCH_VERSION}"
    tar -xf "curl-${CURL_MAJOR_VERSION}.${CURL_MINOR_VERSION}.${CURL_PATCH_VERSION}.tar.gz" --no-same-owner && \
    cd $LIBCURL && \
    patch -p1 < ../patches/libcurl-configure-template.patch && \
    cd - && \
    tar -czvf "curl-${CURL_MAJOR_VERSION}.${CURL_MINOR_VERSION}.${CURL_PATCH_VERSION}.tar.gz" $LIBCURL --no-same-owner
)
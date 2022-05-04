#!/bin/bash
# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
set -e

cd deps
source versions

# Clean up old files
rm -f aws-lambda-cpp-*.tar.gz && rm -f curl-*.tar.gz

# Grab Curl
wget -c "https://github.com/curl/curl/releases/download/curl-${CURL_MAJOR_VERSION}_${CURL_MINOR_VERSION}_${CURL_PATCH_VERSION}/curl-${CURL_MAJOR_VERSION}.${CURL_MINOR_VERSION}.${CURL_PATCH_VERSION}.tar.gz"

# Grab aws-lambda-cpp
wget -c https://github.com/awslabs/aws-lambda-cpp/archive/v$AWS_LAMBDA_CPP_RELEASE.tar.gz -O - | tar -xz

## Apply patches to aws-lambda-cpp
(
  cd aws-lambda-cpp-$AWS_LAMBDA_CPP_RELEASE && \
    patch -p1 < ../patches/aws-lambda-cpp-add-xray-response.patch && \
    patch -p1 < ../patches/aws-lambda-cpp-posting-init-errors.patch && \
    patch -p1 < ../patches/aws-lambda-cpp-make-the-runtime-client-user-agent-overrideable.patch && \
    patch -p1 < ../patches/aws-lambda-cpp-make-lto-optional.patch && \
    patch -p1 < ../patches/aws-lambda-cpp-add-content-type.patch
)

## Pack again and remove the folder
tar -czvf aws-lambda-cpp-$AWS_LAMBDA_CPP_RELEASE.tar.gz aws-lambda-cpp-$AWS_LAMBDA_CPP_RELEASE --no-same-owner && \
  rm -rf aws-lambda-cpp-$AWS_LAMBDA_CPP_RELEASE

#!/bin/bash
# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
set -x

cd deps
source versions

# Clean up old files
rm -f aws-lambda-cpp-*.tar.gz && rm -f curl-*.tar.gz


LIBCURL="curl-${CURL_MAJOR_VERSION}.${CURL_MINOR_VERSION}.${CURL_PATCH_VERSION}"

# Grab Curl
wget -c "https://github.com/curl/curl/releases/download/curl-${CURL_MAJOR_VERSION}_${CURL_MINOR_VERSION}_${CURL_PATCH_VERSION}/$LIBCURL.tar.gz" -O - | tar -xz
(
  cd  $LIBCURL && \
  patch -p1 < ../patches/libcurl-configure-template.patch
)

tar -czf $LIBCURL.tar.gz $LIBCURL --no-same-owner && rm -rf $LIBCURL

# Grab aws-lambda-cpp
wget -c https://github.com/awslabs/aws-lambda-cpp/archive/v$AWS_LAMBDA_CPP_RELEASE.tar.gz -O - | tar -xz

## Apply patches to aws-lambda-cpp
(
  cd aws-lambda-cpp-$AWS_LAMBDA_CPP_RELEASE && \
    patch -p1 < ../patches/aws-lambda-cpp-add-xray-response.patch && \
    patch -p1 < ../patches/aws-lambda-cpp-posting-init-errors.patch && \
    patch -p1 < ../patches/aws-lambda-cpp-make-the-runtime-client-user-agent-overrideable.patch && \
    patch -p1 < ../patches/aws-lambda-cpp-make-lto-optional.patch && \
    patch -p1 < ../patches/aws-lambda-cpp-add-content-type.patch && \
    patch -p1 < ../patches/aws-lambda-cpp-add-tenant-id.patch
)

## Pack again and remove the folder
tar -czf aws-lambda-cpp-$AWS_LAMBDA_CPP_RELEASE.tar.gz aws-lambda-cpp-$AWS_LAMBDA_CPP_RELEASE --no-same-owner && \
  rm -rf aws-lambda-cpp-$AWS_LAMBDA_CPP_RELEASE

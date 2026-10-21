#!/bin/bash
# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
set -x

cd deps
source versions

# Clean up old files
rm -f curl-*.tar.gz


LIBCURL="curl-${CURL_MAJOR_VERSION}.${CURL_MINOR_VERSION}.${CURL_PATCH_VERSION}"

# Grab Curl
wget -c "https://github.com/curl/curl/releases/download/curl-${CURL_MAJOR_VERSION}_${CURL_MINOR_VERSION}_${CURL_PATCH_VERSION}/$LIBCURL.tar.gz" -O - | tar -xz
(
  cd  $LIBCURL && \
  patch -p1 < ../patches/libcurl-configure-template.patch
)

tar -czf $LIBCURL.tar.gz $LIBCURL --no-same-owner && rm -rf $LIBCURL



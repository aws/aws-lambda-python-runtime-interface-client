#!/bin/sh
# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
set -e

ARTIFACTS_DIR=$(pwd)/deps/artifacts

if [ "$(uname)" = "Darwin" ]; then
    echo "aws-lambda-cpp does not build on OS X. Skipping the preinstall step."
    exit 0
fi

download() {
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL -o "$2" "$1"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$2" "$1"
    else
        echo 'Error: need curl or wget to fetch dependencies.' >&2
        exit 1
    fi
}

cd deps
. ./versions

CURL_VERSION="${CURL_MAJOR_VERSION}.${CURL_MINOR_VERSION}.${CURL_PATCH_VERSION}"

rm -rf "./curl-$CURL_VERSION"

# unpack and build curl from the vendored source tarball
tar xzf "./curl-$CURL_VERSION.tar.gz" --no-same-owner

(
    # Build Curl
    cd "curl-$CURL_VERSION" && \
        ./buildconf && \
        ./configure \
            --prefix "$ARTIFACTS_DIR" \
            --disable-shared \
            --without-ssl \
            --with-pic \
            --without-zlib \
            --without-ngtcp2 \
            --without-nghttp3 && \
        make && \
        make install
)


if ! command -v gpg >/dev/null 2>&1; then
    echo 'Error: gpg is required to verify the aws-lambda-cpp release artifact.' >&2
    exit 1
fi

case "$(uname -m)" in
    x86_64)        RELEASE_ARCH="x86_64" ;;
    aarch64|arm64) RELEASE_ARCH="aarch64" ;;
    *)
        echo "Error: unsupported architecture '$(uname -m)' for aws-lambda-cpp." >&2
        exit 1
        ;;
esac

ALC_VERSION="$AWS_LAMBDA_CPP_RELEASE"
ALC_TAG="v${ALC_VERSION}"
ALC_REPO_URL="https://github.com/awslabs/aws-lambda-cpp"
ALC_RELEASE_URL="${ALC_REPO_URL}/releases/download/${ALC_TAG}"
ALC_SIGNING_KEY_URL="https://raw.githubusercontent.com/awslabs/aws-lambda-cpp/${ALC_TAG}/signing-public-key.asc"
LIB_ASSET="libaws-lambda-runtime-${RELEASE_ARCH}.a"

echo "Fetching prebuilt aws-lambda-cpp ${ALC_VERSION} for ${RELEASE_ARCH}"

WORKDIR=$(mktemp -d)

download "${ALC_RELEASE_URL}/${LIB_ASSET}"     "${WORKDIR}/${LIB_ASSET}"
download "${ALC_RELEASE_URL}/${LIB_ASSET}.asc" "${WORKDIR}/${LIB_ASSET}.asc"
download "${ALC_RELEASE_URL}/SHA256SUMS"       "${WORKDIR}/SHA256SUMS"
download "${ALC_RELEASE_URL}/SHA256SUMS.asc"   "${WORKDIR}/SHA256SUMS.asc"
download "${ALC_SIGNING_KEY_URL}"              "${WORKDIR}/signing-key.asc"

GNUPGHOME_DIR=$(mktemp -d)
gpg --homedir "$GNUPGHOME_DIR" --batch --quiet --import "${WORKDIR}/signing-key.asc"
gpg --homedir "$GNUPGHOME_DIR" --batch --verify "${WORKDIR}/${LIB_ASSET}.asc" "${WORKDIR}/${LIB_ASSET}"
gpg --homedir "$GNUPGHOME_DIR" --batch --verify "${WORKDIR}/SHA256SUMS.asc"   "${WORKDIR}/SHA256SUMS"
rm -rf "$GNUPGHOME_DIR"

# Cross-check the checksum too (defence in depth; SHA256SUMS is itself signed).
(cd "$WORKDIR" && grep "${LIB_ASSET}\$" SHA256SUMS | sha256sum -c -)

mkdir -p "$ARTIFACTS_DIR/lib" "$ARTIFACTS_DIR/include"
cp "${WORKDIR}/${LIB_ASSET}" "$ARTIFACTS_DIR/lib/libaws-lambda-runtime.a"

download "${ALC_REPO_URL}/archive/refs/tags/${ALC_TAG}.tar.gz" "${WORKDIR}/src.tar.gz"
tar -xzf "${WORKDIR}/src.tar.gz" -C "$WORKDIR" "aws-lambda-cpp-${ALC_VERSION}/include"
cp -R "${WORKDIR}/aws-lambda-cpp-${ALC_VERSION}/include/." "$ARTIFACTS_DIR/include/"

rm -rf "$WORKDIR"

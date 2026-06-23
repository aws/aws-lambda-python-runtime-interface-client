#!/bin/bash
# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Run a single integration test locally.
# Usage: run-local.sh <distro> <distro_version> <runtime_version>

set -euo pipefail

if (( $# != 3 )); then
    echo "usage: run-local.sh <distro> <distro_version> <runtime_version>"
    echo "  e.g. run-local.sh alpine 3.20 3.13"
    exit 1
fi

DISTRO="$1"
DISTRO_VERSION="$2"
RUNTIME_VERSION="$3"
TEST_NAME="ric-integ-test"
SCRATCH_DIR=".scratch"

trap 'docker rm -f "${TEST_NAME}-app" "${TEST_NAME}-tester" 2>/dev/null || true; docker network rm "${TEST_NAME}-net" 2>/dev/null || true; rm -rf "$SCRATCH_DIR"' EXIT

mkdir -p "$SCRATCH_DIR"

ARCHITECTURE=$(arch)
if [[ "$ARCHITECTURE" == "x86_64" ]]; then
    RIE="aws-lambda-rie"
elif [[ "$ARCHITECTURE" == "aarch64" ]]; then
    RIE="aws-lambda-rie-arm64"
else
    echo "Architecture $ARCHITECTURE is not currently supported."
    exit 1
fi

tar -xvf tests/integration/resources/${RIE}.tar.gz --directory "$SCRATCH_DIR"

DOCKERFILE="tests/integration/docker/Dockerfile.echo.${DISTRO}"
TMPFILE="$SCRATCH_DIR/Dockerfile.tmp"
cp "$DOCKERFILE" "$TMPFILE"
if [[ "$DISTRO" == "alpine" ]]; then
    echo "RUN apk add curl" >> "$TMPFILE"
fi
echo "COPY ${SCRATCH_DIR}/${RIE} /usr/bin/${RIE}" >> "$TMPFILE"

echo "Building image for ${DISTRO} ${DISTRO_VERSION} / python ${RUNTIME_VERSION}..."
docker build . \
    -f "$TMPFILE" \
    -t ric-test \
    --build-arg RUNTIME_VERSION="${RUNTIME_VERSION}" \
    --build-arg DISTRO_VERSION="${DISTRO_VERSION}" \
    --build-arg ARCHITECTURE="${ARCHITECTURE}"

# Determine python location
case "$DISTRO" in
    alpine|debian) PYTHON_LOCATION="/usr/local/bin/python" ;;
    amazonlinux2|amazonlinux2023) PYTHON_LOCATION="/usr/local/bin/python3" ;;
    ubuntu) PYTHON_LOCATION="/usr/bin/python${RUNTIME_VERSION}" ;;
    *) echo "Unknown distro: $DISTRO"; exit 1 ;;
esac

echo "Running integration test..."
docker network create "${TEST_NAME}-net"

docker run \
    --detach \
    --name "${TEST_NAME}-app" \
    --network "${TEST_NAME}-net" \
    --entrypoint="" \
    ric-test \
    sh -c "/usr/bin/${RIE} ${PYTHON_LOCATION} -m awslambdaric app.handler"

sleep 2

docker run \
    --name "${TEST_NAME}-tester" \
    --env "TARGET=${TEST_NAME}-app" \
    --network "${TEST_NAME}-net" \
    --entrypoint="" \
    ric-test \
    sh -c 'curl -sS -X POST "http://${TARGET}:8080/2015-03-31/functions/function/invocations" -d "{}" --max-time 10'

ACTUAL="$(docker logs --tail 1 "${TEST_NAME}-tester" | xargs)"
EXPECTED="success"
echo "Response: ${ACTUAL}"
if [ "$ACTUAL" != "$EXPECTED" ]; then
    echo "FAIL: expected '${EXPECTED}', got '${ACTUAL}'"
    docker logs "${TEST_NAME}-app" 2>&1 || true
    exit 1
fi
echo "PASS"

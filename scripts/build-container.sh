#!/bin/bash
set -euo pipefail

TAG=${TAG:-latest}
PYTHON_VERSION=${PYTHON_VERSION:-3.9}

echo "Building awslambdaric wheel for Python ${PYTHON_VERSION}..."

echo "Building wheel in container..."
docker build \
    --build-arg PYTHON_VERSION="${PYTHON_VERSION}" \
    -f Dockerfile.build \
    -t "awslambdaric-builder:${TAG}" \
    .

echo "Extracting built wheel..."
mkdir -p build-artifacts

docker run --rm -v $(pwd)/build-artifacts:/output awslambdaric-builder:${TAG} /bin/sh -c "
    cp /home/build/dist/*.whl /output/
    echo 'Wheel copied to build-artifacts/'
    ls -la /output/
"

echo "Build complete! Wheel is available in build-artifacts/"
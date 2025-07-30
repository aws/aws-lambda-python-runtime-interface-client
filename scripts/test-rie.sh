#!/bin/bash
set -euo pipefail

DOCKERFILE="Dockerfile.rie"

echo "Starting RIE test setup..."

# Check if build artifacts exist
if [ ! -d "build-artifacts" ] || [ -z "$(ls -A build-artifacts/*.whl 2>/dev/null)" ]; then
    echo "No build artifacts found. Please run 'make build-container' first."
    exit 1
fi

echo "Building test Docker image..."
docker build \
    -f "${DOCKERFILE}" \
    -t awslambdaric-rie-test .

echo "Starting test container on port 9000..."
echo ""
echo "Test with:"
echo "curl -XPOST \"http://localhost:9000/2015-03-31/functions/function/invocations\" -d '{\"message\":\"test\"}'"
echo ""

docker run -it -p 9000:8080 \
    --rm awslambdaric-rie-test
#!/bin/bash
# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.

set -euo pipefail

CODEBUILD_IMAGE_TAG="${CODEBUILD_IMAGE_TAG:-al2/x86_64/standard/3.0}"

function usage {
    >&2 echo "usage: test_one.sh buildspec_yml os_distribution distro_version runtime_version [env]"
    >&2 echo "Runs one buildspec version combination from a build-matrix buildspec."
    >&2 echo "Required:"
    >&2 echo "  buildspec_yml          Used to specify the CodeBuild buildspec template file."
    >&2 echo "  os_distribution        Used to specify the OS distribution to build."
    >&2 echo "  distro_version         Used to specify the distro version of <os_distribution>."
    >&2 echo "  runtime_version        Used to specify the runtime version to test on the selected <distro_version>."
    >&2 echo "Optional:"
    >&2 echo "  env                    Additional environment variables file."
}

function pull_with_retry() {
    local image="$1"
    local max_retries=3
    local wait=10
    for attempt in $(seq 1 $max_retries); do
        if docker pull "$image"; then
            return 0
        fi
        >&2 echo "Docker pull attempt $attempt/$max_retries failed. Retrying in ${wait}s..."
        sleep $wait
        wait=$((wait * 2))
    done
    >&2 echo "Failed to pull $image after $max_retries attempts."
    return 1
}

main() {
    if (( $# != 3 && $# != 4)); then
        >&2 echo "Invalid number of parameters."
        usage
        exit 1
    fi

    set -x
    BUILDSPEC_YML="$1"
    OS_DISTRIBUTION="$2"
    DISTRO_VERSION="$3"
    RUNTIME_VERSION="$4"
    EXTRA_ENV="${5-}"

    CODEBUILD_TEMP_DIR=$(mktemp -d codebuild."$OS_DISTRIBUTION"-"$DISTRO_VERSION"-"$RUNTIME_VERSION".XXXXXXXXXX)
    trap 'rm -rf $CODEBUILD_TEMP_DIR' EXIT

    # Create an env file for codebuild_build.
    ENVFILE="$CODEBUILD_TEMP_DIR/.env"
    if [ -f "$EXTRA_ENV" ]; then
        cat "$EXTRA_ENV" > "$ENVFILE"
    fi
    {
        echo ""
        echo "OS_DISTRIBUTION=$OS_DISTRIBUTION"
        echo "DISTRO_VERSION=$DISTRO_VERSION"
        echo "RUNTIME_VERSION=$RUNTIME_VERSION"
    }  >> "$ENVFILE"
    
    ARTIFACTS_DIR="$CODEBUILD_TEMP_DIR/artifacts"
    mkdir -p "$ARTIFACTS_DIR"

    # Pre-pull the CodeBuild local agent image with retries to handle ECR rate limits.
    pull_with_retry "public.ecr.aws/codebuild/local-builds:latest"

    # Run CodeBuild local agent.
    "$(dirname "$0")"/codebuild_build.sh \
        -i "$CODEBUILD_IMAGE_TAG" \
        -a "$ARTIFACTS_DIR" \
        -e "$ENVFILE" \
        -b "$BUILDSPEC_YML"
}

main "$@"

#!/bin/bash
# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Run a docker command, retrying when it fails (e.g. public.ecr.aws throttling
# the base image pulls with "429 Too Many Requests").
# Usage: docker-retry.sh <command> [args...]

set -uo pipefail

# Ladder of base wait times (in seconds) between successive attempts.
# Default: 1 min, 2 min, 5 min — 4 attempts total (initial + 3 retries).
# public.ecr.aws rate-limit windows recover on a minute-scale timer, so short
# exponential backoff tends to exhaust its budget before the slot reopens.
IFS=' ' read -r -a DELAYS <<< "${RETRY_DELAYS:-60 120 300}"
JITTER_MAX="${RETRY_JITTER_MAX:-30}"
MAX_ATTEMPTS=$(( ${#DELAYS[@]} + 1 ))

if (( $# == 0 )); then
    >&2 echo "usage: docker-retry.sh <command> [args...]"
    exit 2
fi

attempt=1
while true; do
    "$@"
    status=$?
    if (( status == 0 || attempt >= MAX_ATTEMPTS )); then
        exit "$status"
    fi

    # Base delay from the ladder + additive jitter in [0, JITTER_MAX] so
    # concurrent shards don't retry in the exact same second.
    base=${DELAYS[$((attempt - 1))]}
    jitter=$(( RANDOM % (JITTER_MAX + 1) ))
    delay=$(( base + jitter ))

    >&2 echo "docker-retry: '$*' failed (exit ${status}); attempt ${attempt}/${MAX_ATTEMPTS}, retrying in ${delay}s (${base}s + ${jitter}s jitter)."
    sleep "$delay"
    attempt=$(( attempt + 1 ))
done

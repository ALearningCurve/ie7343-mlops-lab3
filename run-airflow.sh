#!/bin/bash
trap 's=$?; echo "$0: Error on line "$LINENO": "$BASH_COMMAND""; exit $s' ERR
set -Eeuo pipefail

docker compose up --build
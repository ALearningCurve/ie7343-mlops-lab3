#!/bin/bash
trap 's=$?; echo "$0: Error on line "$LINENO": "$BASH_COMMAND""; exit $s' ERR
set -Eeuo pipefail


# Remove existing .env file if it exists
rm -f .env
rm -rf ./logs ./plugins ./config
touch .env

# Stop and remove containers, networks, and volumes
docker compose down -v

# Create required Airflow directories
mkdir -p ./logs ./plugins ./config

# Write the current user's UID into .env
echo "AIRFLOW_UID=$(id -u)" > .env

# Run airflow CLI to show current config
docker compose run --rm airflow-cli airflow config list


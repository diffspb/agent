#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SANDBOX_ROOT="${SANDBOX_ROOT:-/tmp/simple-agent-sandbox}"
SANDBOX_SEED_REPO_DIR="${SANDBOX_SEED_REPO_DIR:-datasets/sandbox_repos/demo_python_app}"
AGENT_EMAIL="${AGENT_EMAIL:-agent@example.com}"
GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-Simple Agent Sandbox}"

case "${SANDBOX_SEED_REPO_DIR}" in
  /*) SEED_REPO_DIR="${SANDBOX_SEED_REPO_DIR}" ;;
  *) SEED_REPO_DIR="${PROJECT_ROOT}/${SANDBOX_SEED_REPO_DIR}" ;;
esac

if [[ ! -d "${SEED_REPO_DIR}" ]]; then
  echo "Seed repo directory not found: ${SEED_REPO_DIR}" >&2
  exit 1
fi

if [[ -z "${SANDBOX_ROOT}" || "${SANDBOX_ROOT}" == "/" ]]; then
  echo "Unsafe SANDBOX_ROOT: ${SANDBOX_ROOT}" >&2
  exit 1
fi

rm -rf "${SANDBOX_ROOT}"
mkdir -p "${SANDBOX_ROOT}/repo" "${SANDBOX_ROOT}/workspaces"

cp -R "${SEED_REPO_DIR}/." "${SANDBOX_ROOT}/repo/"

git -C "${SANDBOX_ROOT}/repo" init -b main >/dev/null
git -C "${SANDBOX_ROOT}/repo" config user.name "${GIT_AUTHOR_NAME}"
git -C "${SANDBOX_ROOT}/repo" config user.email "${AGENT_EMAIL}"
git -C "${SANDBOX_ROOT}/repo" add .
git -C "${SANDBOX_ROOT}/repo" commit -m "Initial sandbox seed" >/dev/null

printf 'Sandbox reset complete\n'
printf '  root: %s\n' "${SANDBOX_ROOT}"
printf '  repo: %s\n' "${SANDBOX_ROOT}/repo"
printf '  workspaces: %s\n' "${SANDBOX_ROOT}/workspaces"

#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

fail() {
    echo "$1" >&2
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="PDF Analyzer" --text="$1" || true
    elif [[ "$(uname -s)" == "Darwin" ]]; then
        osascript -e 'display alert "PDF Analyzer" message "Start Docker Desktop, then open Start Lab again."' || true
    fi
    exit 1
}
command -v docker >/dev/null 2>&1 || fail "Install Docker Engine and Compose on Linux, or Docker Desktop on Windows/macOS. See README.md for installation steps."
docker compose version >/dev/null 2>&1 || fail "Docker Compose is required. On Kali install docker-compose; on macOS update Docker Desktop. See README.md."
if ! docker info >/dev/null 2>&1; then
    # A newly granted group membership may not be active in this desktop session yet.
    if [[ "$(uname -s)" == "Linux" && "${PDF_LAB_GROUP_RETRY:-0}" != "1" ]] \
        && command -v sg >/dev/null 2>&1 \
        && [[ " $(id -nG "$(id -un)") " == *" docker "* ]]; then
        printf -v restart_command 'env PDF_LAB_GROUP_RETRY=1 bash %q' "$PWD/Start Lab.sh"
        exec sg docker -c "$restart_command"
    fi
    fail "Docker is unavailable. On Kali start the docker service and log out/back in after joining the docker group. On macOS start Docker Desktop. See README.md."
fi
echo "Preparing PDF Analyzer. The first start downloads the lab tools; later starts use the saved lab."
docker compose up -d --build --wait --wait-timeout 180 || fail "The lab could not start. Check the output above for build errors or an occupied port."
lab_url="http://localhost:${LAB_PORT:-8080}"
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$lab_url" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
    open "$lab_url"
fi
echo "PDF Analyzer is ready: $lab_url. Import your dataset through Lab setup in the web app."

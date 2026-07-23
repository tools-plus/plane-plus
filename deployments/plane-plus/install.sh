#!/bin/bash
set -e

# Plane Plus — Self-Hosted Installer
# Usage: curl -sSL <release-url>/install.sh | bash
#   or:  ./setup.sh [install|start|stop|restart|upgrade|logs|backup]

SCRIPT_DIR=$PWD
INSTALL_DIR=$PWD/plane-app
DOCKER_FILE_PATH=$INSTALL_DIR/docker-compose.yml
DOCKER_ENV_PATH=$INSTALL_DIR/plane.env

GH_REPO=eyriehq/plane-plus
RELEASE_DOWNLOAD_URL="https://github.com/$GH_REPO/releases/download"
FALLBACK_DOWNLOAD_URL="https://raw.githubusercontent.com/$GH_REPO/main/deployments/infrawatch"

export APP_RELEASE=${APP_RELEASE:-latest}

OS_NAME=$(uname)

# ─── Docker Compose detection ──────────────────────────────────────────────

if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

# ─── Helpers ───────────────────────────────────────────────────────────────

function print_header() {
    clear
    echo ""
    echo "  ╔═╗┬  ┌─┐┌┐┌┌─┐  ╔═╗┬  ┬ ┬┌─┐"
    echo "  ╠═╝│  ├─┤│││├┤   ╠═╝│  │ │└─┐"
    echo "  ╩  ┴─┘┴ ┴┘└┘└─┘  ╩  ┴─┘└─┘└─┘"
    echo ""
}

function getEnvValue() {
    local key=$1 file=$2
    [ -f "$file" ] && grep -q "^$key=" "$file" && grep "^$key=" "$file" | cut -d'=' -f2
}

function updateEnvFile() {
    local key=$1 value=$2 file=$3
    if grep -q "^$key=" "$file" 2>/dev/null; then
        if [ "$OS_NAME" == "Darwin" ]; then
            sed -i '' "s|^$key=.*|$key=$value|g" "$file"
        else
            sed -i "s|^$key=.*|$key=$value|g" "$file"
        fi
    else
        echo "$key=$value" >> "$file"
    fi
}

function checkLatestRelease() {
    # Try stable release first
    local latest=$(curl -sSL "https://api.github.com/repos/$GH_REPO/releases/latest" | grep -o '"tag_name": "[^"]*"' | sed 's/"tag_name": "//;s/"//g')
    if [ -n "$latest" ]; then
        echo "$latest"
        return
    fi
    # Fall back to most recent release (including prereleases)
    latest=$(curl -sSL "https://api.github.com/repos/$GH_REPO/releases" | grep -o '"tag_name": "[^"]*"' | head -1 | sed 's/"tag_name": "//;s/"//g')
    if [ -n "$latest" ]; then
        echo "No stable release found, using prerelease: $latest" >&2
        echo "$latest"
        return
    fi
    echo "No releases found" >&2
    exit 1
}

function downloadFile() {
    local filename=$1 dest=$2
    local url="$RELEASE_DOWNLOAD_URL/$APP_RELEASE/$filename"

    local response=$(curl -sSL -w "HTTPSTATUS:%{http_code}" "$url?$(date +%s)")
    local body=$(echo "$response" | sed -e 's/HTTPSTATUS\:.*//g')
    local status=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')

    if [ "$status" -eq 200 ]; then
        echo "$body" > "$dest"
        return 0
    fi

    # Fallback to raw GitHub
    url="$FALLBACK_DOWNLOAD_URL/$filename"
    response=$(curl -sSL -w "HTTPSTATUS:%{http_code}" "$url?$(date +%s)")
    body=$(echo "$response" | sed -e 's/HTTPSTATUS\:.*//g')
    status=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')

    if [ "$status" -eq 200 ]; then
        echo "$body" > "$dest"
        return 0
    fi

    echo "Failed to download $filename (HTTP $status)" >&2
    return 1
}

# ─── Core Functions ────────────────────────────────────────────────────────

function install() {
    echo "Installing Plane Plus..."
    echo ""

    # Resolve "latest" to actual latest release version
    if [ "$APP_RELEASE" == "latest" ]; then
        echo "Checking for latest release..."
        APP_RELEASE=$(checkLatestRelease)
        echo "Latest release: $APP_RELEASE"
        echo ""
    fi

    mkdir -p "$INSTALL_DIR/archive"
    mkdir -p "$INSTALL_DIR/data"

    # Archive existing files
    local ts=$(date +%s)
    [ -f "$DOCKER_FILE_PATH" ] && mv "$DOCKER_FILE_PATH" "$INSTALL_DIR/archive/$ts.docker-compose.yml"

    # Download compose and env
    downloadFile "docker-compose.yml" "$DOCKER_FILE_PATH" || exit 1
    downloadFile "variables.env" "$INSTALL_DIR/variables-upgrade.env" || exit 1

    # Backup and sync env
    if [ -f "$DOCKER_ENV_PATH" ]; then
        cp "$DOCKER_ENV_PATH" "$INSTALL_DIR/archive/$ts.env"
        cp "$DOCKER_ENV_PATH" "$INSTALL_DIR/plane.env.bak"
    fi

    mv "$INSTALL_DIR/variables-upgrade.env" "$DOCKER_ENV_PATH"

    # Restore user values from backup (except APP_RELEASE — use the downloaded version)
    if [ -f "$INSTALL_DIR/plane.env.bak" ]; then
        while IFS= read -r line; do
            [[ -z "$line" || "$line" == \#* ]] && continue
            local key=$(echo "$line" | cut -d'=' -f1)
            [ "$key" == "APP_RELEASE" ] && continue
            local value=$(getEnvValue "$key" "$INSTALL_DIR/plane.env.bak")
            [ -n "$value" ] && updateEnvFile "$key" "$value" "$DOCKER_ENV_PATH"
        done < "$DOCKER_ENV_PATH"
    fi

    # Use APP_RELEASE from downloaded env (stamped at build time), fallback to env var
    local downloaded_release=$(getEnvValue "APP_RELEASE" "$DOCKER_ENV_PATH")
    if [ -n "$downloaded_release" ] && [ "$downloaded_release" != "latest" ]; then
        APP_RELEASE="$downloaded_release"
    fi
    updateEnvFile "APP_RELEASE" "$APP_RELEASE" "$DOCKER_ENV_PATH"

    # Pull images
    echo "Pulling images..."
    $COMPOSE_CMD -f "$DOCKER_FILE_PATH" --env-file="$DOCKER_ENV_PATH" pull --quiet
    echo ""
    echo "Installation complete. Run './setup.sh start' to start services."
    echo ""
}

function startServices() {
    echo "Starting Plane Plus..."
    $COMPOSE_CMD -f "$DOCKER_FILE_PATH" --env-file="$DOCKER_ENV_PATH" up -d --quiet-pull

    # Wait for migrator
    local migrator_id=$($COMPOSE_CMD -f "$DOCKER_FILE_PATH" ps -q migrator 2>/dev/null)
    if [ -n "$migrator_id" ]; then
        echo -n "  Waiting for database migration..."
        while docker inspect --format='{{.State.Status}}' "$migrator_id" 2>/dev/null | grep -q "running"; do
            echo -n "."
            sleep 2
        done
        local exit_code=$(docker inspect --format='{{.State.ExitCode}}' "$migrator_id" 2>/dev/null)
        if [ "$exit_code" -ne 0 ]; then
            echo " FAILED"
            echo "  Migration failed. Check logs: ./setup.sh logs migrator"
            exit 1
        fi
        echo " done"
    fi

    # Wait for API
    local api_id=$($COMPOSE_CMD -f "$DOCKER_FILE_PATH" ps -q api 2>/dev/null)
    if [ -n "$api_id" ]; then
        echo -n "  Waiting for API..."
        local elapsed=0
        while ! docker exec "$api_id" python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/', timeout=3)" > /dev/null 2>&1; do
            echo -n "."
            sleep 2
            elapsed=$((elapsed + 2))
            if [ $elapsed -gt 120 ]; then
                echo " timeout (API may still be starting)"
                break
            fi
        done
        [ $elapsed -le 120 ] && echo " ready"
    fi

    source "$DOCKER_ENV_PATH" 2>/dev/null
    echo ""
    echo "  Plane Plus is running at ${WEB_URL:-http://localhost}"
    echo ""
}

function stopServices() {
    echo "Stopping services..."
    $COMPOSE_CMD -f "$DOCKER_FILE_PATH" --env-file="$DOCKER_ENV_PATH" down
}

function restartServices() {
    stopServices
    startServices
}

function upgrade() {
    local current=$APP_RELEASE
    local latest=$(checkLatestRelease)

    echo "Current: $current"
    echo "Latest:  $latest"

    if [ "$current" == "$latest" ]; then
        echo "Already on latest version."
        exit 0
    fi

    read -p "Upgrade to $latest? [y/N]: " confirm
    [[ ! "$confirm" =~ ^[Yy]$ ]] && exit 0

    export APP_RELEASE=$latest
    stopServices
    install
    echo "Upgrade complete. Run './setup.sh start' to start services."
}

function viewLogs() {
    local service=$1
    if [ -z "$service" ]; then
        echo "Usage: ./setup.sh logs <service>"
        echo "Services: web, space, admin, live, api, worker, beat-worker, migrator, proxy, plane-db, plane-redis, plane-mq, plane-minio"
        exit 1
    fi
    $COMPOSE_CMD -f "$DOCKER_FILE_PATH" --env-file="$DOCKER_ENV_PATH" logs -f "$service"
}

function backupData() {
    local ts=$(date +"%Y%m%d-%H%M")
    local backup_dir="$INSTALL_DIR/backup/$ts"
    mkdir -p "$backup_dir"

    echo "Backing up data to $backup_dir..."

    for svc_dir in postgres redis rabbitmq minio; do
        if [ -d "$INSTALL_DIR/data/$svc_dir" ]; then
            echo "  Backing up $svc_dir..."
            tar -czf "$backup_dir/$svc_dir.tar.gz" -C "$INSTALL_DIR/data" "$svc_dir"
        fi
    done

    # Backup env
    cp "$DOCKER_ENV_PATH" "$backup_dir/plane.env"

    echo ""
    echo "Backup complete: $backup_dir"
}

# ─── Main ──────────────────────────────────────────────────────────────────

# Load existing config
if [ -f "$DOCKER_ENV_PATH" ]; then
    APP_RELEASE=$(getEnvValue "APP_RELEASE" "$DOCKER_ENV_PATH")
    APP_RELEASE=${APP_RELEASE:-latest}
fi

print_header

case "${1:-}" in
    install)  install ;;
    start)    startServices ;;
    stop)     stopServices ;;
    restart)  restartServices ;;
    upgrade)  upgrade ;;
    logs)     viewLogs "$2" ;;
    backup)   backupData ;;
    *)
        echo "Usage: ./setup.sh <command>"
        echo ""
        echo "Commands:"
        echo "  install   Download and set up Plane"
        echo "  start     Start all services"
        echo "  stop      Stop all services"
        echo "  restart   Restart all services"
        echo "  upgrade   Upgrade to latest release"
        echo "  logs      View logs (./setup.sh logs <service>)"
        echo "  backup    Backup data volumes"
        echo ""
        ;;
esac

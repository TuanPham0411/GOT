#!/bin/bash
# First migration from the two existing systemd apps to the verified Docker stack.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo 'Run with sudo.' >&2; exit 1; }
release_dir="$(realpath "${1:?Pass the tested release directory}")"
revision="${2:?Pass the exact tested Git commit SHA}"
[[ "$revision" =~ ^[0-9a-f]{40}$ ]] || { echo 'Full Git SHA required.' >&2; exit 1; }
cd "$release_dir"
base=/opt/thienha-platform
stage_config="$base/config/stage.env"
[ -r "$stage_config" ]
systemctl is-active --quiet thienha-home
systemctl is-active --quiet game-of-thien
python3 deploy/smoke.py
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup="$base/backups/$stamp"
state="$base/state/production-$stamp"
install -d -m 0700 "$backup" "$base/config"
cp -a /etc/systemd/system/thienha-home.service /etc/systemd/system/game-of-thien.service "$backup/"
cp -a /etc/thienha-home.env "$backup/"
cp -a /etc/cloudflared/config.yml "$backup/cloudflared-config.yml"
printf '%s\n' "$revision" > "$backup/revision"
production_config="$base/config/production.env"
rollback() {
    result=$?
    trap - ERR
    echo 'Cutover failed; stopping Docker production and restoring original services.' >&2
    if [ -f "$production_config" ]; then
        docker compose --env-file "$production_config" -p thienha-production -f compose.platform.yaml stop || true
    fi
    systemctl enable thienha-home game-of-thien || true
    systemctl start thienha-home game-of-thien || true
    exit "$result"
}
trap rollback ERR
systemctl stop thienha-home game-of-thien
python3 deploy/snapshot_data.py /home/sika1/thienha-home/data "$backup/portal-data" --legacy-files /home/sika1/thienha-home/files
cp -a "$backup/portal-data" "$state"
chown -R 10001:10001 "$state"
cat > "$production_config" <<EOF
PORTAL_ENV_FILE=/etc/thienha-home.env
PORTAL_DATA_DIR=$state
PORTAL_PORT=5050
GOT_PORT=5000
PORTAL_IMAGE=thienha-portal:$revision
GOT_IMAGE=got-game:$revision
APP_REVISION=$revision
EOF
chmod 0600 "$production_config"
docker compose --env-file "$stage_config" -p thienha-stage -f compose.platform.yaml stop
docker compose --env-file "$production_config" -p thienha-production -f compose.platform.yaml up -d --no-build --wait --wait-timeout 180
python3 deploy/smoke.py --portal http://127.0.0.1:5050 --game http://127.0.0.1:5000
systemctl disable thienha-home game-of-thien
systemctl enable docker
ln -sfn "$release_dir" "$base/current"
printf '%s\n' "$revision" > "$base/current-revision"
trap - ERR
echo "Cutover passed. Private rollback snapshot: $backup"

#!/usr/bin/env bash
# Push templates/dashboard.liquid into the LaraPaper dashboard plugin and re-render it.
#
# Run it on the machine where LaraPaper's containers run (laptop, or the VPS after `git pull`):
#   server/larapaper/scripts/push-template.sh                # local compose file
#   COMPOSE_FILE=compose.prod.yml server/larapaper/scripts/push-template.sh   # on the VPS
#
# The plugin uuid is a secret (it is the webhook URL): it is read from DASHBOARD_PLUGIN_UUID in the
# environment or in server/larapaper/.env, never from the repo.
# The previous markup is saved to server/larapaper/backups/ (gitignored) before replacing it.
set -euo pipefail
cd "$(dirname "$0")/.."

uuid="${DASHBOARD_PLUGIN_UUID:-}"
if [[ -z "$uuid" && -f .env ]]; then
  uuid="$(grep -E '^DASHBOARD_PLUGIN_UUID=' .env | tail -1 | cut -d= -f2- | tr -d '"'"'"' ')"
fi
if [[ -z "$uuid" ]]; then
  echo "DASHBOARD_PLUGIN_UUID is not set (environment or server/larapaper/.env)" >&2
  exit 1
fi

mkdir -p backups
stamp="$(date +%Y%m%d-%H%M%S)"

docker compose exec -T app sh -c 'cat > /tmp/dashboard.liquid' < templates/dashboard.liquid
docker compose exec -T -e UUID="$uuid" app php artisan tinker --execute='
$p = App\Models\Plugin::where("uuid", getenv("UUID"))->firstOrFail();
file_put_contents("/tmp/dashboard.previous.liquid", (string) $p->render_markup);
$new = file_get_contents("/tmp/dashboard.liquid");
$changed = md5((string) $p->render_markup) !== md5($new);
$p->render_markup = $new;
$p->current_image = null;
$p->save();
foreach (App\Models\PlaylistItem::where("plugin_id", $p->id)->pluck("id") as $id) {
    App\Jobs\RenderPlaylistItemImageJob::dispatchSync($id, true);
}
$p->refresh();
echo ($changed ? "template updated" : "template unchanged") . ", rendered: " . ($p->current_image ?? "(none)") . PHP_EOL;
' < /dev/null
docker compose exec -T app cat /tmp/dashboard.previous.liquid < /dev/null > "backups/dashboard.$stamp.liquid"
echo "previous markup saved to server/larapaper/backups/dashboard.$stamp.liquid"

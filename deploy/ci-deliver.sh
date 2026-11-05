#!/usr/bin/env bash
set -euo pipefail
operation=${1:?stage or promote}
[[ "$operation" == stage || "$operation" == promote ]]
[[ "$IMAGE_DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]
[[ "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]
private_dir=$(mktemp -d)
trap 'rm -rf "$private_dir"' EXIT
chmod 700 "$private_dir"
printf '%s\n' "$DEPLOY_KEY" > "$private_dir/key"
printf '%s\n' "$DEPLOY_KNOWN_HOSTS" > "$private_dir/known_hosts"
chmod 600 "$private_dir/key" "$private_dir/known_hosts"
printf '%s\n' "$REGISTRY_TOKEN" | ssh -i "$private_dir/key" \
  -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$private_dir/known_hosts" \
  mia-deploy@vps-7c516158.vps.ovh.net "$operation $IMAGE_DIGEST $GITHUB_SHA"
printf '\n%s: `%s`\n' "$operation" "$IMAGE_DIGEST" >> "$GITHUB_STEP_SUMMARY"

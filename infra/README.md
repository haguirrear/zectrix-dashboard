# infra/: the droplet, its firewall, the Cloudflare tunnel and DNS (OpenTofu)

One `tofu apply` creates:

| Provider | Resources |
|---|---|
| Tailscale | a single-use, pre-approved auth key tagged `tag:server` (valid 1 day) |
| DigitalOcean | your SSH key, the droplet (Ubuntu 24.04, 2 GB, `cloud-init.yaml` as user data), a firewall with **no inbound rules** |
| Cloudflare | the tunnel, its routing (`public_hostname` → `http://caddy:80`), the proxied DNS record for `public_hostname` |

Not managed here, on purpose:
- **Tailscale policy** (tag owner, access rules): the provider would replace the whole policy file. Edit it in the admin console.
- **What runs on the droplet** (LaraPaper, Docker volumes): OpenTofu doesn't see inside the droplet. See `docs/deploy-vps.md`.

## State

The state lives in `infra/terraform.tfstate` on your machine, encrypted with `state_passphrase`
(OpenTofu state encryption). Git ignores it. Keep the passphrase in your password manager and back up the
encrypted file anywhere. If you lose either, the resources keep running, but OpenTofu forgets them
and you'd have to `tofu import` each one.

## One-time setup

1. **OpenTofu** 1.8 or newer (`tofu version`).
2. **Tailscale admin console:**
   - Access controls: add the tag owner (and see `docs/deploy-vps.md` for access rules):
     ```json
     "tagOwners": { "tag:server": ["autogroup:admin"] },
     ```
   - DNS: enable MagicDNS and HTTPS Certificates.
   - Settings → Trust credentials (OAuth clients) → new client with the **Auth Keys: write** scope and tag
     `tag:server`. Note the client ID and secret.
3. **DigitalOcean:** API → Generate New Token, custom scopes: droplet, ssh_key, firewall, tag
   (create/read/update/delete), plus read for regions, sizes, image, actions.
4. **Cloudflare:** My Profile → API Tokens → Create Custom Token:
   - Account → Cloudflare Tunnel → Edit
   - Zone → DNS → Edit, limited to your domain

   Note the Account ID and Zone ID from your domain's Overview page.
5. **SSH key** just for this server:
   ```zsh
   ssh-keygen -t ed25519 -C "apps-vps" -f ~/.ssh/id_ed25519_apps_vps
   ```
6. **Variables:**
   ```zsh
   cp infra/terraform.tfvars.example infra/terraform.tfvars
   ```
   ```zsh
   chmod 600 infra/terraform.tfvars
   ```
   Fill it in. `admin_ssh_public_key` is the line in `~/.ssh/id_ed25519_apps_vps.pub`. To keep the
   passphrase out of the file, delete its line and set it per shell instead: `read -rs TF_VAR_state_passphrase && export TF_VAR_state_passphrase`.

## Create

```zsh
cd infra
```
```zsh
tofu init
```
```zsh
tofu plan -out=apply.tfplan
```
Check the plan: 7 resources to add, nothing to change or destroy.
```zsh
tofu apply apply.tfplan
```

Then follow `docs/deploy-vps.md` from "First login". The tunnel token for the droplet's
`server/larapaper/.env`:
```zsh
tofu output -raw tunnel_token
```

## Later changes

- Always `tofu plan` first. A line saying `must be replaced` on the droplet means its disk would be
  destroyed; `prevent_destroy` makes such a plan fail on purpose.
- User data, image and SSH key changes are ignored after creation (they only matter at first boot).
- Bumping provider versions: edit `versions.tf`, then `tofu init -upgrade` and commit `.terraform.lock.hcl`.

provider "digitalocean" {
  token = var.do_token
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

provider "tailscale" {
  oauth_client_id     = var.tailscale_oauth_client_id
  oauth_client_secret = var.tailscale_oauth_client_secret
  tailnet             = "-" # the tailnet the OAuth client belongs to
}

# ---- Tailscale: a single-use key the droplet joins with at first boot ----------------------
# The tag:server owner and the access rules stay in the admin console (this provider would
# overwrite the whole policy file). See README.md.
resource "tailscale_tailnet_key" "droplet" {
  reusable            = false
  ephemeral           = false
  preauthorized       = true
  expiry              = 86400 # 1 day: enough to create the droplet, worthless afterwards
  tags                = ["tag:server"]
  description         = "${var.droplet_name} droplet first boot"
  recreate_if_invalid = "never" # once used it is invalid by design; don't make a new one each apply
}

# ---- DigitalOcean ---------------------------------------------------------------------------
resource "digitalocean_ssh_key" "admin" {
  name       = "${var.droplet_name}-admin"
  public_key = var.admin_ssh_public_key
}

resource "digitalocean_droplet" "apps" {
  name       = var.droplet_name
  image      = var.image
  region     = var.region
  size       = var.size
  ipv6       = true
  monitoring = true # DigitalOcean's metrics agent: memory and disk graphs in the control panel
  backups    = var.do_backups
  tags       = [var.droplet_name]

  # Only root gets this key from DigitalOcean, and root login is off; the admin user gets it from
  # cloud-init. Without any key, DigitalOcean emails a root password instead.
  ssh_keys = [digitalocean_ssh_key.admin.fingerprint]

  user_data = templatefile("${path.module}/cloud-init.yaml", {
    ADMIN_USER    = var.admin_user
    ADMIN_SSH_KEY = var.admin_ssh_public_key
    VPS_HOSTNAME  = var.droplet_name
    TS_AUTHKEY    = tailscale_tailnet_key.droplet.key
  })

  lifecycle {
    # Replacing the droplet destroys its disk, Docker volumes included. To really delete it,
    # remove this line first.
    prevent_destroy = true
    # These only matter at creation; changing them later must not replace the droplet.
    ignore_changes = [user_data, ssh_keys, image]
  }
}

# No inbound rules at all: Tailscale and cloudflared only make outbound connections.
resource "digitalocean_firewall" "apps" {
  name        = "${var.droplet_name}-no-inbound"
  droplet_ids = [digitalocean_droplet.apps.id]

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

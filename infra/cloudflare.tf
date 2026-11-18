# Cloudflare Tunnel: public_hostname -> tunnel -> cloudflared on the droplet -> caddy:80.
# Remotely managed (config_src = "cloudflare"): the routing lives here, and cloudflared only needs
# the tunnel token (output tunnel_token -> TUNNEL_TOKEN in server/larapaper/.env on the droplet).

resource "cloudflare_zero_trust_tunnel_cloudflared" "apps" {
  account_id = var.cloudflare_account_id
  name       = var.droplet_name
  config_src = "cloudflare"
}

resource "cloudflare_zero_trust_tunnel_cloudflared_config" "apps" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.apps.id

  config = {
    ingress = [
      {
        # Caddy on the compose network does the allow-list and the webhook token check.
        hostname = var.public_hostname
        service  = "http://caddy:80"
      },
      {
        # Required catch-all: anything else that reaches this tunnel.
        service = "http_status:404"
      },
    ]
  }
}

# The subdomain: a proxied CNAME to the tunnel. Cloudflare answers for it; the droplet's IP is
# never published.
resource "cloudflare_dns_record" "public" {
  zone_id = var.cloudflare_zone_id
  name    = var.public_hostname
  type    = "CNAME"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.apps.id}.cfargotunnel.com"
  proxied = true
  ttl     = 1 # automatic (required for proxied records)
  comment = "Cloudflare Tunnel to the ${var.droplet_name} droplet (managed by OpenTofu, infra/)"
}

data "cloudflare_zero_trust_tunnel_cloudflared_token" "apps" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.apps.id
}

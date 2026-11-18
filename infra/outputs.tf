output "ssh" {
  description = "Log in over Tailscale once the droplet shows up in your tailnet."
  value       = "ssh -i ~/.ssh/<your key> ${var.admin_user}@${var.droplet_name}"
}

output "public_url" {
  description = "Base URL for the device (APP_URL) and the webhook senders."
  value       = "https://${var.public_hostname}"
}

output "droplet_ipv4" {
  description = "Public IP. Nothing listens on it (no inbound firewall rules); for reference only."
  value       = digitalocean_droplet.apps.ipv4_address
}

output "tunnel_id" {
  value = cloudflare_zero_trust_tunnel_cloudflared.apps.id
}

output "tunnel_token" {
  description = "TUNNEL_TOKEN for server/larapaper/.env on the droplet: tofu output -raw tunnel_token"
  value       = data.cloudflare_zero_trust_tunnel_cloudflared_token.apps.token
  sensitive   = true
}

# ---- Secrets: set them in terraform.tfvars (gitignored) or TF_VAR_* environment variables ----

variable "state_passphrase" {
  description = "Encrypts the state and plan files (16+ characters). Keep it in your password manager."
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.state_passphrase) >= 16
    error_message = "state_passphrase must be at least 16 characters."
  }
}

variable "do_token" {
  description = "DigitalOcean API token (droplet, ssh_key, firewall scopes)."
  type        = string
  sensitive   = true
}

variable "cloudflare_api_token" {
  description = "Cloudflare API token: Account > Cloudflare Tunnel: Edit, Zone > DNS: Edit for your zone."
  type        = string
  sensitive   = true
}

variable "tailscale_oauth_client_id" {
  description = "Tailscale OAuth client with the auth_keys scope and tag:server."
  type        = string
  sensitive   = true
}

variable "tailscale_oauth_client_secret" {
  description = "Secret of the Tailscale OAuth client."
  type        = string
  sensitive   = true
}

# ---- Not secret, but personal: also in terraform.tfvars ----

variable "admin_user" {
  description = "Your login on the droplet (sudo)."
  type        = string
  validation {
    condition     = can(regex("^[a-z_][a-z0-9_-]{0,31}$", var.admin_user)) && !contains(["root", "apps"], var.admin_user)
    error_message = "admin_user must be a valid Linux user name and not root or apps."
  }
}

variable "admin_ssh_public_key" {
  description = "The one line of your PUBLIC key file (~/.ssh/<name>.pub), never the private key."
  type        = string
  validation {
    condition     = can(regex("^(ssh-ed25519|ecdsa-sha2-nistp[0-9]+|ssh-rsa|sk-ssh-ed25519@openssh.com|sk-ecdsa-sha2-nistp256@openssh.com) [A-Za-z0-9+/=]+( [^\"\\n]*)?$", var.admin_ssh_public_key))
    error_message = "admin_ssh_public_key must be a single public key line (ssh-ed25519 AAAA... comment) without quotes."
  }
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID (dashboard: your domain > Overview > API section)."
  type        = string
}

variable "cloudflare_zone_id" {
  description = "Zone ID of your domain (same Overview page)."
  type        = string
}

variable "public_hostname" {
  description = "Public name of the dashboard server, a subdomain of your Cloudflare domain, e.g. paper.example.com."
  type        = string
}

# ---- Defaults you can override ----

variable "droplet_name" {
  description = "Droplet name, hostname and Tailscale machine name."
  type        = string
  default     = "apps"
  validation {
    condition     = can(regex("^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", var.droplet_name))
    error_message = "droplet_name must be lowercase letters, digits and dashes."
  }
}

variable "region" {
  description = "DigitalOcean region slug."
  type        = string
  default     = "nyc3"
}

variable "size" {
  description = "Droplet size: 2 GB RAM, because LaraPaper renders with headless Chromium."
  type        = string
  default     = "s-1vcpu-2gb"
}

variable "image" {
  description = "Droplet image. Only used when the droplet is created (changes are ignored afterwards)."
  type        = string
  default     = "ubuntu-24-04-x64"
}

variable "do_backups" {
  description = "DigitalOcean weekly droplet backups (+20% of the droplet price)."
  type        = bool
  default     = false
}

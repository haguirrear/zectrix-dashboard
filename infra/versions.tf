terraform {
  # OpenTofu, not Terraform: the state encryption below is an OpenTofu feature (1.8+ for variables).
  required_version = ">= 1.8.0"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.108"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.29.0" # v5 minors have renamed fields before; bump deliberately
    }
    tailscale = {
      source  = "tailscale/tailscale"
      version = "~> 0.30.0"
    }
  }

  # The state holds the Tailscale auth key, the droplet's user data and the tunnel token, so it is
  # encrypted on disk with a passphrase you keep in your password manager. Losing the passphrase
  # means losing the state (the resources keep running; see README.md).
  encryption {
    key_provider "pbkdf2" "passphrase" {
      passphrase = var.state_passphrase
    }
    method "aes_gcm" "default" {
      keys = key_provider.pbkdf2.passphrase
    }
    state {
      method   = method.aes_gcm.default
      enforced = true
    }
    plan {
      method   = method.aes_gcm.default
      enforced = true
    }
  }
}

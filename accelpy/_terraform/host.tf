/*
Pre-existing hosts: Common configuration
*/

locals {
  # IP addresses, defined in user_override
  host_ip = []

  # Needs password to to sudo
  ask_sudo_pass = true

  # Remote user, defined in user_override
  remote_user = ""

  # Coma separated list of IP addresses
  host_ip_str = join(",", local.host_ip)

  # Does not require a specific driver
  provider_required_driver = ""

  # Will use the OS already installed on host
  remote_os = ""

  # Return input IP adresses as output
  host_public_ip  = local.host_ip
  host_private_ip = local.host_ip
}

resource "null_resource" "cluster" {
  provisioner "local-exec" {
    # Configure using Ansible
    command = local.require_provisioning ? "${local.ansible} -i '${local.host_ip_str},'" : "cd"
  }
}

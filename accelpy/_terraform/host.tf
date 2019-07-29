/*
Pre-existing hosts: Common configuration
*/

locals {
  # Coma separated list of IP addresses
  host_ip_str = join(",", local.host_ip)

  # Does not require a specific driver
  provider_required_driver = ""

  # Will use the OS already installed on host
  remote_os = ""
}

resource "null_resource" "cluster" {
  provisioner "local-exec" {
    # Configure using Ansible
    command = local.require_provisioning ? "${local.ansible} -i '${local.host_ip_str}'" : "cd"
  }
}

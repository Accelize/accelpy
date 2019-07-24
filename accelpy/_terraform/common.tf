/*
Common configuration
*/

terraform {
  required_version = ">= 0.12"
}

# Ansible executable path

variable "ansible" {
  type        = string
  default     = "ansible-playbook"
  description = "ansible-playbook command."
}
locals {

  # Ansible Remote python to use: Python3 except on CentOS 7
  ansible_python = local.remote_os == "centos_7" ? "/usr/bin/python" : "/usr/bin/python3"

  # Ansible-playbook CLI with disabling SSH host key checking and ensuring using a fixed Python version
  ansible = "ANSIBLE_REMOTE_USER=${local.remote_user} ${var.ansible} playbook.yml -e 'ansible_python_interpreter=${local.ansible_python}' -u ${local.remote_user} --private-key ${local.ssh_key_private_path} --extra-vars 'accelize_drm_driver_name=${local.accelize_drm_driver_name}' --extra-vars 'os_hardening=${local.os_hardening}' --extra-vars 'ssh_hardening=${local.ssh_hardening}'"
}

# Host FPGA configuration

variable "fpga_count" {
  type        = string
  default     = "1"
  description = "Number of required FPGA devices."
}

# Host VM image

variable "package_vm_image" {
  type        = string
  default     = ""
  description = "Host image to use if already existing"
}

locals {
  require_provisioning = var.package_vm_image == "" ? true : false
}

# Host ressources name

variable "host_name" {
  default     = "application"
  type        = string
  description = "Host name of this configuration."
}

variable "host_provider" {
  default     = ""
  type        = string
  description = "Provider name."
}

locals {
  # Name prefix for all resources
  prefix = "accelize_"

  # Name used for all provider resources
  name            = "${local.prefix}${var.host_name}"
  provider_params = split(",", var.host_provider)
  provider_name   = local.provider_params[0]
}

# Host IP Addresses

output "host_public_ip" {
  value = local.host_public_ip
}

output "host_private_ip" {
  value = local.host_private_ip
}

# Host user

output "remote_user" {
  value = local.remote_user
}

# Host OS

locals {
  # Remote OS to use (Default to latest Ubuntu LTS)
  remote_os = "ubuntu_bionic"

  # Enable OS security hardening
  os_hardening = "false"

  # Enable SSH security hardening
  ssh_hardening = "false"
}

# User public IP Address

locals {
  current_ip = "${chomp(data.http.public_ip.body)}/32"
}

data "http" "public_ip" {
  url = "https://api.ipify.org"
}

# Firewall configuration

variable "firewall_rules" {
  type = list(object({
    direction  = string,
    start_port = number,
    end_port   = number,
    protocol   = string
  }))
  default     = []
  description = "Host firewall rules."
}


locals {
  # Default Firewall rules
  default_firewall_rules = [
    # Always require SSH access from current IP
    { direction  = "ingress",
      start_port = 22,
      end_port   = 22,
      protocol   = "tcp",
    ip_range = local.current_ip },

    # Allow all egress connections, Required to setup host using Ansible
    { direction  = "egress",
      start_port = 0,
      end_port   = 0,
      protocol   = "all",
    ip_range = "0.0.0.0/0" },
  ]

  # User specified IP range to allow
  firewall_ip_ranges = []

  # Computed firewall rules
  firewall_rules = concat([for item in setproduct(var.firewall_rules, [for ip in concat(local.firewall_ip_ranges, [local.current_ip]) : { ip_range = ip }]) : merge(item...)], local.default_firewall_rules)
}

output "firewall_rules" {
  # Output Firewall rules
  value = local.firewall_rules
}

# SSH Key pair

locals {
  # Key pair name in provider
  ssh_key_name = ""
  # User provided private key PEM file path
  ssh_key_pem = ""
  # True if require to generated a new key pair
  ssh_key_generated = local.ssh_key_name == "" && local.ssh_key_pem == ""
  # Public key string in OpenSSH format
  ssh_key_public = local.ssh_key_generated ? tls_private_key.ssh_key_generated[0].public_key_openssh : data.tls_public_key.ssh_key_pem[0].public_key_openssh
  # Private key string in PEM format
  ssh_key_private = local.ssh_key_generated ? tls_private_key.ssh_key_generated[0].private_key_pem : data.tls_public_key.ssh_key_pem[0].private_key_pem
  # Path to private key in PEM format
  ssh_key_private_path = local.ssh_key_generated ? local_file.ssh_key_generated_pem[0].filename : local.ssh_key_pem
}

data "tls_public_key" "ssh_key_pem" {
  # Load provided private key
  count           = local.ssh_key_pem != "" ? 1 : 0
  private_key_pem = local.ssh_key_pem != "" ? file(local.ssh_key_pem) : ""
}

resource "tls_private_key" "ssh_key_generated" {
  # Generate a new key pair
  count     = local.ssh_key_generated ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "local_file" "ssh_key_generated_pem" {
  # Save generated private key
  count    = local.ssh_key_generated ? 1 : 0
  content  = tls_private_key.ssh_key_generated[0].private_key_pem
  filename = "${path.module}/ssh_private.pem"
  provisioner "local-exec" {
    command = "chmod 600 ${self.filename}"
  }
}

output "host_ssh_private_key" {
  # Path to private key to use
  value = local.ssh_key_private_path
}

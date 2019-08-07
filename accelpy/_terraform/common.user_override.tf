/* Common user configuration */

locals {
  # Resources prefix
  # ================
  #
  # By default, all resources are prefixed "accelize_".
  # Change the following value to change this prefix.
  prefix = "accelize_"

  # Firewall/Security group IP ranges to allow
  # ==========================================
  #
  # By default, only the current machine can access to the application host
  # Add IP ranges to the following list to allow them to access to the host.
  firewall_ip_ranges = []

  # Ansible configuration
  # =====================
  #
  # Ansible require Python preinstalled on hosts.
  #
  # By default, Ansible should autodetect the Python insterpreter to use, but
  # in case of failure, it is possible to define the interpreter to use
  # like "/usr/bin/python3" (Python 3) or "/usr/bin/python" (Python 2).
  #
  # Uncomment and fill this value with the Python path to use with Ansible:
  /*
  ansible_python = "auto"
  */

  # By default a password may or may not be asked to connect ssh and sudo on the
  # remote host.
  # It is possible to force Ansible to ask for passwords by uncommenting
  # the following value:
  /*
  require_ask_pass = true
  */
}

/* Common user configuration */

# Resources prefix
# ================
#
# By default, all resources are prefixed "accelize_".
# Change the following value to change this prefix.
locals {
  prefix = "accelize_"
}

# Firewall/Security group IP ranges to allow
# ==========================================
#
# By default, only the current machine can access to the application host
# Add IP ranges to the following list to allow them to access to the host.
locals {
  firewall_ip_ranges = []
}

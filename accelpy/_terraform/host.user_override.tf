/* Pre-existing hosts user configuration */

locals {
  # Host lists
  # ==========
  #
  # It is possible to provision one or more remote machine by providing their
  # IP addresses
  #
  # Fill with the list of hosts IP addresses
  host_ip = ["1.2.3.4"]

  # SSH connection
  # ==============
  #
  # A key pair is required to access the instance using SSH.
  #
  # Fill with the private key PEM file path to use
  ssh_key_pem = ""

  # Fill with the user name to use to connect to SSH
  remote_user = "user"

}

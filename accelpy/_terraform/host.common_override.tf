/*
Pre-existing hosts: Common configuration override
*/

locals {
  # Always requires an user provided SSH key
  ssh_key_generated = false
}

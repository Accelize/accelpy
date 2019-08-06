/*
Amazon Web Service: Common configuration
*/

# AWS creadential, by default use Terraform autodetection
provider "aws" {
  region = local.provider_params[1]
}

# FPGA instance types

locals {
  # Define instance type based on required FPGA count
  instances_types = {
    "1" = "f1.2xlarge"
    "2" = "f1.4xlarge"
    "8" = "f1.16xlarge"
  }
  instance_type = [for fpga_count, type in local.instances_types : type if fpga_count >= var.fpga_count][0]

  # AWS use its specific FPGA driver
  provider_required_driver = "aws_f1"

  # AMI Information for supported OS
  ami_users = {
    "centos_7"      = "centos"
    "ubuntu_bionic" = "ubuntu"
    "ubuntu_xenial" = "ubuntu"
  }
  ami_owners = {
    "centos_7"      = "679593333241"
    "ubuntu_bionic" = "099720109477"
    "ubuntu_xenial" = "099720109477"
  }
  ami_names = {
    "centos_7"      = "CentOS Linux 7 x86_64 HVM EBS *"
    "ubuntu_bionic" = "ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-*"
    "ubuntu_xenial" = "ubuntu/images/ebs-ssd/ubuntu-xenial-16.04-amd64-server-*"
  }

  # Use CentOS 7 because the only one that wrok with AWS FPGA driver
  remote_os = "centos_7"

  # AWS AMI does not require ssh/become password by default
  require_ask_pass = false
}

# Instance image and sudo user name

data "aws_ami" "image" {
  most_recent = true
  owners      = [local.ami_owners[local.remote_os]]

  filter {
    name   = "name"
    values = [local.ami_names[local.remote_os]]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  remote_user = local.ami_users[local.remote_os]
  ami         = var.package_vm_image != "" ? var.package_vm_image : data.aws_ami.image.id
}

# Security group

resource "aws_security_group" "security_group" {
  name = local.name

  dynamic "ingress" {
    for_each = [for rule in local.firewall_rules : rule if rule.direction == "ingress"]
    content {
      from_port   = ingress.value.start_port
      to_port     = ingress.value.end_port
      protocol    = ingress.value.protocol == "all" ? "-1" : ingress.value.protocol
      cidr_blocks = [ingress.value.ip_range]
    }
  }

  dynamic "egress" {
    for_each = [for rule in local.firewall_rules : rule if rule.direction == "egress"]
    content {
      from_port   = egress.value.start_port
      to_port     = egress.value.end_port
      protocol    = egress.value.protocol == "all" ? "-1" : egress.value.protocol
      cidr_blocks = [egress.value.ip_range]
    }
  }
}

# Instance profile with minimum FPGA requierements

locals {
  policy = <<EOF
{
  "Version": "2012-10-17", "Statement": [
    {"Sid": "AllowDescribeFpgaImages",
     "Effect": "Allow",
     "Action": ["ec2:DescribeFpgaImages"],
     "Resource": ["*"]}
  ]
}
EOF

}

resource "aws_iam_instance_profile" "instance_profile" {
  name = local.name
  role = aws_iam_role.role.name
}

resource "aws_iam_role" "role" {
  name = local.name

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17", "Statement": {
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"}
}
EOF

}

resource "aws_iam_role_policy" "role_policy" {
  name   = local.name
  role   = aws_iam_role.role.id
  policy = local.policy
}


# SSH key

resource "aws_key_pair" "key_pair" {
  # Require to create a new key pair if no key pair name provided
  count      = local.ssh_key_name == "" ? 1 : 0
  key_name   = local.name
  public_key = local.ssh_key_public
}

locals {
  key_name = local.ssh_key_name != "" ? local.ssh_key_name : aws_key_pair.key_pair[0].key_name
}

# Instance

locals {
  # If True, use spot instance, else, use on-demand instance
  spot_instance = true
}

resource "aws_instance" "instance" {
  # Use on-demand instance
  count = local.spot_instance ? 0 : 1

  # Common configuration
  ami                  = local.ami
  instance_type        = local.instance_type
  iam_instance_profile = aws_iam_instance_profile.instance_profile.name
  security_groups      = [aws_security_group.security_group.name]
  key_name             = local.key_name
  tags = {
    Name = local.name
  }
  root_block_device {
    volume_size = local.root_volume_size
  }

  # On-demand specific configuration
  instance_initiated_shutdown_behavior = "terminate"

  # Configure remote machine
  provisioner "remote-exec" {
    # Wait until instance ready (Use "cd" command as it should work on any OS)
    inline = ["cd"]
    connection {
      host        = self.public_ip
      type        = "ssh"
      user        = local.remote_user
      private_key = local.ssh_key_private
    }
  }
  provisioner "local-exec" {
    # Configure using Ansible
    command = local.require_provisioning ? "${local.ansible} -i '${self.public_ip},'" : "cd"
  }
}

resource "aws_spot_instance_request" "instance_spot" {
  # Use spot instance
  count = local.spot_instance ? 1 : 0

  # Common configuration
  ami                  = local.ami
  instance_type        = local.instance_type
  iam_instance_profile = aws_iam_instance_profile.instance_profile.name
  security_groups      = [aws_security_group.security_group.name]
  key_name             = local.key_name
  tags = {
    Name = local.name
  }
  root_block_device {
    volume_size = local.root_volume_size
  }

  # Spot specific configuration
  spot_type            = "one-time"
  wait_for_fulfillment = true
  provisioner "local-exec" {
    # "tags" apply to spot instance request and needs to be applied to instance
    # https://github.com/terraform-providers/terraform-provider-aws/issues/32
    command = "aws ec2 create-tags --resources ${self.spot_instance_id} --tags Key=Name,Value=${local.name}"
  }

  # Configure remote machine
  provisioner "remote-exec" {
    # Wait until instance ready (Use "cd" command as it should work on any OS)
    inline = ["cd"]
    connection {
      host        = self.public_ip
      type        = "ssh"
      user        = local.remote_user
      private_key = local.ssh_key_private
    }
  }
  provisioner "local-exec" {
    # Configure using Ansible
    command = local.require_provisioning ? "${local.ansible} -i '${self.public_ip},'" : "cd"
  }
}

locals {
  # Output Instance IP addresses
  host_public_ip  = local.spot_instance ? aws_spot_instance_request.instance_spot[0].public_ip : aws_instance.instance[0].public_ip
  host_private_ip = local.spot_instance ? aws_spot_instance_request.instance_spot[0].private_ip : aws_instance.instance[0].private_ip
}

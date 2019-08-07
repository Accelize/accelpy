/* Amazon Web Service user configuration */

# Credentials
# ===========
#
# Terraform should autodetect access key on user machine if possible, but it
# is also possible to specify them directly.
# For more information: https://www.terraform.io/docs/providers/aws/index.html

# To use specified credential, uncomment and fill your credentials informations.
/*
provider "aws" {
  # Insert your credentials information below this line

  # Do not override region, it is autogenerated
  region = local.region
}
*/

# SSH key pair
# ============
#
# A key pair is required to access the instance using SSH.
#
# By default, a new SSH key pair is generated. It is possible to use an existing
# AWS EC2 key pair or use an existing private key.

# To use AWS EC2 key pair, uncomment and fill with the AWS key pair name to use.
/*
locals {
  # AWS EC2 key pair name
  ssh_key_name = "my_key_pair"
  # Path to the private key PEM file matching to to the EC2 key pair
  ssh_key_pem = "~/.ssh/id_rsa"
}
*/

# To define the private key to use, uncomment and fill with the private key PEM
# file path.
/*
locals {
  ssh_key_pem = "~/.ssh/id_rsa"
}
*/

# Instance profile IAM role policy
# ==================================
#
# By default, only the minimum access to use FPGA is granted to the instance.
# It is possible to modify the policy to give more access to the instance.
#
# Note that "DescribeFpgaImages" is mandatory to program FPGA devices.
#
# The below example gives access to all S3 buckets.
#
# Uncomment and fill with the required policy document.
/*
locals {
  policy = <<EOF
{
  "Version": "2012-10-17", "Statement": [
    {"Sid": "AllowDescribeFpgaImages",
     "Effect": "Allow",
     "Action": ["ec2:DescribeFpgaImages"],
     "Resource": ["*"]},

    {"Sid": "AllowS3Access",
     "Effect": "Allow",
     "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket",
                "s3:ListAllMyBuckets"],
     "Resource": ["arn:aws:s3:::*"]}
  ]
}
EOF
}
*/

# Spot instance
# =============
#
# By default, spot instances are used to reduce cost. But any spot instance can
# be terminated by AWS without advice at any time.
#
# Set following value to "true" to enable spot instances
# and "false" to disable it
locals {
  spot_instance = true
}

# Root volume size
# ================
#
# It is possible to define the size of the root volume of instances.
#
# Uncomment and fill with the required size in GiB:
/*
locals {
  root_volume_size = "10"
}
*/

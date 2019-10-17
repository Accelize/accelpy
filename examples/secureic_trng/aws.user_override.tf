/* Amazon Web Service user configuration */

# Instance profile IAM role policy
# ==================================
#
# Allow logging on Cloudwatch

locals {
  policy = <<EOF
{
  "Version": "2012-10-17", "Statement": [
    {"Sid": "AllowDescribeFpgaImages",
     "Effect": "Allow",
     "Action": ["ec2:DescribeFpgaImages"],
     "Resource": ["*"]},

    {"Sid": "AllowCloudwatchLogging",
     "Effect": "Allow",
     "Action": ["logs:CreateLogGroup", "logs:CreateLogStream",
                "logs:PutLogEvents", "logs:DescribeLogStreams"],
     "Resource": ["*"]}
  ]
}
EOF
}

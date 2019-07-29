FROM centos:7
SHELL ["/bin/bash", "-c"]

# This dockerfile create an image containning:
# - AWS FPGA runtimes
# - Xilinx XRT runtimes (For AWS)
# - An "appuser" user with "fpgauser" group

RUN yum install -y epel-release && \
yum install -y \
    gcc \
    git \
    make \
    sudo && \
git clone https://github.com/aws/aws-fpga /tmp/aws-fpga --depth 1 && \
source /tmp/aws-fpga/sdk_setup.sh && \
yum erase -y \
    gcc \
    git \
    make \
    sudo && \
curl -s https://s3.amazonaws.com/aws-fpga-developer-ami/1.6.0/Patches/XRT_2018_3_RC3_Patch1/xrt_201830.2.1.0_7.6.1810-xrt.rpm -o /tmp/xrt_201830.2.1.0_7.6.1810-xrt.rpm && \
curl -s https://s3.amazonaws.com/aws-fpga-developer-ami/1.6.0/Patches/XRT_2018_3_RC3_Patch1/xrt_201830.2.1.0_7.6.1810-aws.rpm -o /tmp/xrt_201830.2.1.0_7.6.1810-aws.rpm && \
yum install -y /tmp/xrt_201830.2.1.0_7.6.1810-xrt.rpm && \
yum install -y /tmp/xrt_201830.2.1.0_7.6.1810-aws.rpm && \
rm -Rf /tmp/* && \
rm -rf /var/cache/yum/* && \
groupadd -g 1001 fpgauser && \
useradd -mN -u 1001 -g fpgauser appuser

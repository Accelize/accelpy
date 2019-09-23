FROM centos:7
SHELL ["/bin/bash", "-c"]

# This dockerfile create an image containning:
# - AWS FPGA runtimes
# - Xilinx XRT runtimes (For AWS)
# - Accelize DRM library (C/C++)
# - Extra RPM repositories: EPEL, Accelize
# - "appuser" user (UID = 1001)
# - "fpgauser" group (GID = 1001)

RUN curl -L https://accelize.s3.amazonaws.com/rpm/accelize_stable.repo -o /etc/yum.repos.d/accelize_stable.repo && \
yum install -y epel-release && \
yum install -y \
    gcc \
    libaccelize-drm \
    make \
    sudo && \
mkdir -p /tmp/aws-fpga && \
export AWS_FPGA_RELEASE=$(curl -s https://api.github.com/repos/aws/aws-fpga/releases/latest | grep tag_name | cut -d '"' -f 4) && \
curl -L https://github.com/aws/aws-fpga/archive/$AWS_FPGA_RELEASE.tar.gz | tar xz -C /tmp/aws-fpga --strip-components=1 && \
source /tmp/aws-fpga/sdk_setup.sh && \
yum erase -y sudo && \
yum install -y https://s3.amazonaws.com/aws-fpga-developer-ami/1.7.0/Patches/XRT_2019_1_RC2/xrt_201910.2.2.0_7.6.1810-xrt.rpm && \
yum install -y https://s3.amazonaws.com/aws-fpga-developer-ami/1.7.0/Patches/XRT_2019_1_RC2/xrt_201910.2.2.0_7.6.1810-aws.rpm && \
rm -rf /tmp/* && \
rm -rf /var/cache/yum/* && \
groupadd -g 1001 fpgauser && \
useradd -mN -u 1001 -g fpgauser appuser

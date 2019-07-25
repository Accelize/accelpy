FROM accelize/base:centos_7-aws_f1

RUN yum install -y \
    yum-utils \
    epel-release && \
yum-config-manager --add-repo https://accelize.s3.amazonaws.com/rpm/accelize_stable.repo && \
yum install -y python36-accelize-drm && \
rm -rf /var/cache/yum/*

EXPOSE 8080
COPY app_server.py .
CMD ["./app_server.py"]

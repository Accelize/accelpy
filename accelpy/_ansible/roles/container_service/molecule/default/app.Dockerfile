FROM accelize/base:centos_7-aws_f1

RUN yum install -y python36 && \
rm -rf /var/cache/yum/*

EXPOSE 8080
COPY app_server.py .
CMD ["./app_server.py"]

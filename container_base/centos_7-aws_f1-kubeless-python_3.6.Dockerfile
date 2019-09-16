FROM accelize/base:centos_7-aws_f1

# This dockerfile create an Kubeless runtime image containning:
# - Content from as "centos_7-aws_f1"
# - Kubeless Python 3.6 runtime
# - Accelize DRM library Python

RUN yum install -y \
    python36-pip \
    python36-accelize-drm && \
pip3 install -U --prefix='/usr' --no-cache-dir \
    bottle==0.12.13 \
    cherrypy==8.9.1 \
    wsgi-request-logger \
    prometheus_client && \
ln -s /usr/bin/pip3 /usr/bin/pip && \
curl -L https://raw.githubusercontent.com/kubeless/runtimes/master/stable/python/kubeless.py -o /kubeless.py && \
mkdir -p /kubeless && \
rm -rf /var/cache/yum/*

WORKDIR /
EXPOSE 8080
# USER 1001 # Disabled because currently AWS FPGA absolutely requires root
CMD ["python3", "/kubeless.py"]

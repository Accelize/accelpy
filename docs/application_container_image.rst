Container images
================

Prerequisites
-------------

To use applications, you need to create a Docker container image and push it on
a registry like Docker-Hub. Following links from Docker
documentation can help to start with container images:

* `Develop with Docker <https://docs.docker.com/develop>`_
* `Repositories <https://docs.docker.com/docker-hub/repos>`_


.. note:: All required FPGA runtime libraries must be installed in the image.
          Even if accelpy install required drivers on the host, host runtime
          libraries cannot be accessed from the container directly.

Accelize base images
-------------------

Accelize provides some container base images that can be used as base to create
your own container images.

Theses base images features:

* Pre-installed FPGA runtime libraries.
* A preconfigured non-root user named `appuser` with group `fpgauser`.

Theses base images can be found on
`Docker-hub <https://cloud.docker.com/repository/docker/accelize/base>`_.

Tu use base image, add them to the `FROM` command of your image `Dockerfile`:

.. code-block:: dockerfile
    :caption: Example with the Centos 7 image with AWS F1 instances driver

    FROM accelize/base:centos_7-aws_f1

Often, it is not possible to use Accelize base images (Example if you want use
a more specific image like a Nginx or FFMPEG one). In this cases, the base image
can still help you to configure your own image by looking the Dockerfile.

Dockerfile of each base image can be found in the `container_base` directory of
the accelpy GitHub repository.

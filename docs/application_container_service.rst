Container Service
=================

The application is a container infinitely running in background.

The application manager is a systemd service that run the container once on
boot.

Prerequisites
-------------

To create this kind of application, you need to create a Docker container image
and push it on a registry like Docker-Hub. Following links from Docker
documentation can help to start with container images:

* `Develop with Docker <https://docs.docker.com/develop>`_
* `Repositories <https://docs.docker.com/docker-hub/repos>`_

Container configuration
-----------------------

The container is started with following extra environment variables that can be
used from the containerized application:

* `FPGA_SLOTS`: Coma separated list of FPGA slots numbers where the application
  bitstream is programmed.

Container image
---------------

The container image must fit following requirements:

* The container `ENTRYPOINT`/`CMD` must run the application as an infinitely
  running application.
* All required FPGA runtime libraries must be installed in the image.
  Even if accelpy install required drivers on the host, host runtime
  libraries cannot be accessed from the container directly.

.. TODO: Disabled, experimental
    * The container must not tries to manage the programmed FPGA bitstream.
      accelpy program the FPGA prior to run the application.
    * The application must be run by an user different than root with UID 1001 and
      GID 1001. If not using Accelize base image, the following Dockerfile code
      example show how to create such user (with name `appuser` and group name
      `fpgauser`):

    .. code-block:: dockerfile

        RUN groupadd -g 1001 fpgauser && \
        useradd -mN -u 1001 -g fpgauser appuser
        USER appuser

.. note:: If `accelize_drm` `use_service` is set to `false` in the application
          definition file, the application must handle the Accelize DRM itself
          using the Accelize DRM library.

Accelize base images
~~~~~~~~~~~~~~~~~~~~

Accelize provides some container base images that can be used as base to create
your own container images.

Theses base images features:

* Pre-installed FPGA runtime libraries.

.. TODO: Disabled, experimental
    * A preconfigured non-root user named `appuser`.  Use this user to run your
      application to help mitigate against vulnerabilities.

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

How it work
-----------

This section explain how the application is handled on the host.

Application start
~~~~~~~~~~~~~~~~~

The application is managed by two systemd services:

* The Accelize DRM service: This service ensure that the FPGA is ready to use by
  programming it with the application specified bitstream, and provides the
  design licensing.
* The Accelize container service: This service start the container once the
  Accelize DRM service is ready. Once this service is started, the application
  should be ready to use.

.. note:: To ensure immutability and ensure the software in the container match
          with the FPGA bitstream, the image last version available is not
          pulled when the container is run. The version started is always the
          version pulled on the host creation.

.. TODO: Disabled, experimental
    Container FPGA Access
    ~~~~~~~~~~~~~~~~~~~~~

    The container FPGA access is not straightforward:

    * By default, the container cannot access to the FPGA.
    * It is possible to give "privileged" access to a Docker container but this also
      give a full root host access to it: This is a security issue.
    * Currently, there is no ready and easy to use solution to provides FPGA access
      to Docker that are supported by FPGA vendors and Docker.

    To give the container access to the FPGA but not break the security, the
    following solution is used:

    * The container is run "rootless" with Podman. That mean that the container is
      run by an unprivileged user instead of root.
    * The unprivileged user is member of the FPGA user group generated when
      installing FPGA driver and libraries. This allow this user to access to the
      FPGA (Using an Udev rule).
    * Paths that are owned by the FPGA user group are mounted to the container to
      ensure application can access to the FPGA.

    With this, the container can securely access to the FPGA and not more.

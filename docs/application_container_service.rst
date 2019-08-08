Container Service
=================

The application is a container infinitely running in background.

The application manager is a systemd service that run the container once on
boot.

Application definition
----------------------

This application type support the following package types:

* `container_image`: A container image.
* `vm_image`: An image of an already provisioned virtual machine.

Example snippet of application definition file:

.. code-block:: yaml

   application:
     name: my_application
     version: 1.0.2
     type: container_service

   package:
     name: my_docker_account/my_image
     type: container_image

Variables
~~~~~~~~~

This application support following variables:

* `rootless`: Enable rootless mode (See below).
* `privileged`: In non rootless mode, force the use of the container privileged
  mode.

Container configuration
-----------------------

See :doc:`application_container_image` for common container requirements.

The container `ENTRYPOINT`/`CMD` must run the application as an infinitely
running application.

The container is started with following extra environment variables that can be
used from the containerized application:

* `FPGA_SLOTS`: Coma separated list of FPGA slots numbers where the application
  bitstream is programmed.

Rootless mode
-------------

The rootless mode use Podman instead of Docker to run the container as
unprivileged user instead of root. This improve the security.

The rootless mode can be enabled in the application definition with the
`rootless` variable:

.. code-block:: yaml

    application:
      name: my_application
      version: 1.0.2
      type: container_service
      variables:
        # Enable rootless mode
        rootless: true

To run in rootless mode, the container also needs to fit the following
requirement:

* The application must be run by an user different than root with UID 1001 and
  GID 1001. If not using Accelize base image, the following Dockerfile code
  example show how to create such user (with name `appuser` and group name
  `fpgauser`):

.. code-block:: dockerfile
    :caption: From a common base image:

    RUN groupadd -g 1001 fpgauser && \
    useradd -mN -u 1001 -g fpgauser appuser
    USER appuser

.. code-block:: dockerfile
    :caption: From the Accelize base image (User already exists)

    USER appuser

Security notice
---------------

Except in rootless mode, depending on the configuration, the container may be
run in `privileged` mode to have FPGA access. This means that the container run
as `root` on your host.

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

Rootless mode
~~~~~~~~~~~~~

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

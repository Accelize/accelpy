Application definition
======================

The application definition is a YAML file that define the application to
deploy.

This file needs to be written by the application vendor following the
specification detailed below.

To check the definition file content use the `lint` command:

.. code-block:: bash

    accelpy lint path/to/application.yml

Specification
-------------

This specification define all YAML file sections and its content

`application` section
~~~~~~~~~~~~~~~~~~~~~

This section define base information about the application.

This section is a mapping of following key, values pairs:

* `product_id` (string): **Required**. Product ID linked to the application.
  The product ID can be found with the related product in your Accelize vendor
  account on `Accelize portal <https://portal.accelize.com/>`_.
* `version` (string): **Required**. Version of the application in
  `semantic versioning format <https://semver.org>`_.
* `type` (string): **Required**. Application type. The application type is used
  to filter configuration and use correct Ansible roles to deploy the
  application. For more information on each application type, see the
  "application type" section of the right menu. Predefined application types
  are: `container_service`, `kubernetes_node`.
* `variables` (mapping of strings): Application type specific variables. See the
  application type documentation for more information.

Example:

.. code-block:: yaml

    application:
      product_id: my_product_id
      version: 1.0.2
      type: container_service
      variables:
        var1: 1
        var2: 2

`package` section
~~~~~~~~~~~~~~~~~

This section define how the application is packaged and how to install it.

This section is a mapping of following key, values pairs:

* `type` (string): **Required**. Package type. Each application type support a
     limited subset of package types. Predefined package types are:

    * `container_image`: A Docker or OCI container image.
    * `kubernetes_deployment`: URL to a Kubernetes deployment or pod
      YAML or JSON file.
    * `vm_image`: A virtual machine image. Can be an ID, or an URL
      depending the provider in use. Using a virtual machine image disable the
      Ansible provisioning. An image can be created from any other configuration
      using `accelpy build`.

* `name` (string): **Required**. The name or ID of the package to install.
* `version` (string): The version of the package to install. If not specified,
  use the last version available.
* `repository` (string): Package repository. If not specified, use following
  default repository for specified package `type`:

  * `container_image`: `docker.io` (https://hub.docker.com/ registry)

Example:

.. code-block:: yaml

    package:
      type: container_image
      name: httpd

`firewall_rules` section
~~~~~~~~~~~~~~~~~~~~~~~~

This section define firewall rules to apply to the application host to allow
user access to the application.

Depending the environment, Firewall may refer to security group.

This section is a list of firewall rule.

If this section is empty or not specified no external inbound access will be
allowed to the application.

Each rule is a mapping of following key, values pairs:

* `start_port` (integer): **Required**. Start port range to allow.
* `end_port` (integer): **Required**. End port range to allow.
* `protocol` (string): Protocol to allow. Can be `tcp`, `udp` or `all`.
  `tcp` if not specified.
* `direction` (string): Direction to allow. Can be `ingress` or `egress`.
  `ingress` if not specified.

.. note:: The IP range is specified at infrastructure level (In Terraform
          configuration)and is not part of the application definition.

Example:

.. code-block:: yaml

    firewall_rules:
      - start_port: 1000
        end_port: 1000
        protocol: tcp
        direction: ingress
      - start_port: 1001
        end_port: 1100
        protocol: udp
        direction: ingress

`fpga` section
~~~~~~~~~~~~~~

The FPGA section define all information required to configure the FPGA
device(s).

* `driver` (string): The FPGA driver to use. If not specified, default to the
  Linux Kernel driver or the provider specific driver.
  Possible values : `aws_f1` (AWS F1 instances only), `xilinx_xrt` (Xilinx XRT).
* `image` (string or list of string): **Required**. The FPGA bitstream image to
  use to program the FPGA. Depending the provider this can be an ID, a path or
  an URL. If multiple FPGA are required, must be a list of FPGA bitstream (One
  for each FPGA slot).
  Possibles values: AGFI (AWS F1 instances), URL to a *.xclbin* file
  (Xilinx XRT).
* `driver_version` (string): The version of the FPGA driver to use. If not
  specified, use the latest version available.
* `count` (int): The number of FPGA devices required to run the application.
  If not specified, default to `1`.

Example:

.. code-block:: yaml

    fpga:
        image: path/to/my/image

`accelize_drm` section
~~~~~~~~~~~~~~~~~~~~~~

This section define the DRM service configuration.

* `use_service` (bool): If `true`, use the Accelize DRM service to handle the
  Accelize DRM. If `false`, the application must handle the DRM itself
  using the Accelize DRM library (See
  `Accelize documentation <https://www.accelize.com/docs>`_). `false` if not
  specified.
* `conf` (mapping of strings): Content of Accelize DRM `conf.json`
  (YAML or JSON formatted).

.. code-block:: yaml
   :caption: Passing the Accelize DRM conf.json: YAML formatted

    accelize_drm:
      conf:
        licensing:
          url: https://master.metering.accelize.com
        drm:
          frequency_mhz: 125
          drm_ctrl_base_addr: 0
        design:
          boardType: ISV custom data

.. code-block:: yaml
   :caption: Passing the Accelize DRM conf.json: JSON formatted

    accelize_drm:
      conf: {
        "licensing": {
          "url": "https://master.metering.accelize.com"
        },
        "drm": {
          "frequency_mhz": 125,
           "drm_ctrl_base_addr": 0,
        },
      }

.. warning:: To use the Accelize DRM service, the application must not tries to
             manage the programmed FPGA bitstream. The service will program the
             FPGA itself before licensing it.

.. note:: The *boardType* key of the *design* section of the configuration file
          is dynamically set to the provider used at runtime.

Provider specific override
~~~~~~~~~~~~~~~~~~~~~~~~~~

The definition file allow to override some values for a specific provider.

Each provider specified by override require to match to the definition
specification independently. Providing a working default configuration is not
mandatory.

Example:

.. code-block:: yaml

    package:
      # The container image will be used by default
      type: container_image
      name: httpd

      # This override replace the package type and name for AWS provider on
      # specified regions
      aws,eu-west-1,f1:
        type: vm_image
        name: ami-01010101010

      aws,eu-west-2:
        type: vm_image
        name: ami-10101010101

    fpga:
      # The Xilinx XRT driver will always be used because not overridden
      driver: xilinx_xrt

      # Different FPGA image are used for each AWS region, and the driver
      # used on AWS need to be specified:
      aws,eu-west-1,f1:
        image: agfi-01010101010
        driver: aws_f1

      aws,eu-west-2:
        image: agfi-10101010101
        driver: aws_f1

      # This specify the image to use on a bare metal host with a specific kind
      # of FPGA board
      host,xilinx_u200_xdma_201820_1:
         image: https://my_domain.com/my_fpga_image.xclbin
         driver_version: 2018.3

      # No default FPGA image is provided. The application can only be used on
      # other providers.

AWS EC2
=======

The utility is shipped with an AWS example that provision the application on
a single EC2 instance.

.. warning:: AWS EC2 currently only support FPGA properly with the following
             software configuration:

             * CentOS 7
             * Xilinx XRT 2018.3 2.1.0

Region selection
----------------

AWS require to select a region when provisioning and creating an image.

The region selection is done with the provider parameter by specifying it in
the format: `aws,region`.

By example to use the `eu-west-1` region:

.. code-block:: bash

    accelpy init -a my_app -p aws,eu-west-1

.. note:: In the application definition file, the AWS provider require also
          to be specified with the region. This allow to specify different AMI
          or AFI image for each regions.

Infrastructure Configuration
----------------------------

The example is also provided with a default Terraform override file that
allow to easily :

* Configure AWS credential (Note that Terraform can autodetect them in most
  cases)
* Configure SSH Key to use: The generated SSH key (Default), an AWS EC2 existing
  key pair or a key pair from a private key file.
* Disable or enable Spot instances to reduce cost (Enabled by default).
* Configure the instance profile IAM role policy.
* Configure resource name prefix.

:download:`aws.user_override.tf <../accelpy/_terraform/aws.user_override.tf>`.

To use this file, download it in `~/.accelize` and edit it to fit your needs.
The next provisioning will use your settings automatically.

Image creation Configuration
----------------------------

If AWS credentials cannot be detected in current machine, it is required to add
them into the Packer configuration using the following file:

:download:`aws.user_override.json <../accelpy/_packer/aws.user_override.json>`.

To use this file, download it in `~/.accelize` and edit it to fit your needs.
The next provisioning will use your settings automatically.

Image generation
----------------

When generating an image with the `build` function, an AMI is generated in
the specified region.

.. note:: The utility will never delete generated AMI.

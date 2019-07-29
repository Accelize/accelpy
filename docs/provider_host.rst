FPGA Host
=========

The utility is shipped with an examples to provision one or more existing
FPGA hosts thought SSH.

board selection
---------------

To correctly provision an host, the FPGA board typ is required.

The board type selection is done with the provider parameter by specifying it in
the format: `host,board_type`.

Configuration
-------------

The example is also provided with a default Terraform override file that
allow to easily :

* IP addresses of machines to provision.
* SSH key to use to provision.
* SSH username to use to provision.

:download:`host.user_override.tf <../accelpy/_terraform/host.user_override.tf>`.

To use this file, download it in `~/.accelize` and edit it to fit your needs.
The next provisioning will use your settings automatically.

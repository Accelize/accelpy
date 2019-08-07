Getting Started
===============

Requirements
------------

* Linux, but may also work on any other Unix based OS.
* Python >= 3.6

.. note:: The Windows support is not planned because it is not supported by
          Ansible.

Installation
------------

The installation is performed using Pip:

.. code-block:: bash

    pip3 install accelpy

To enable bash autocompletion, add the following line in your `~/.bashrc`:

.. code-block:: bash

    eval "$(register-python-argcomplete accelpy)"

.. note:: Ansible is installed automatically by Pip.

          HashiCorp utilities (Terraform & Packer) are managed automatically by
          accelpy. It ensures that the version used is up to date, downloads and
          installs the tool if necessary after checking its signature and
          integrity.

Application definition
----------------------
The utility require an application definition to know details of the application
to deploy.

It is possible to load an existing one from the Accelize platform, or to write
your custom application definition. See :doc:`application_definition`.

Infrastructure provision
------------------------

This section explain all required steps to provision the infrastructure.

All examples are performed using the command line interface of the utility.

The command line interface provides help that can be accessed with the
`--help` / `-h` option:

.. code-block:: bash

    accelpy --help

Configuration initialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The configuration is created using the `init` command, this command support
following options:

* `--name`/`-n`: The name of the configuration. If not name is provided to the
  configuration, a random name is generated.
* `--application` / `-a`: Always required. Path to the application definition
  file of the application to provision.
* `--provider` / `-p`: Name of the provider to where provision the application.
  You can find some provider examples in the "Provider examples" section of
  the right menu.
* `--user_config` / `-c`: Path to an extra configuration directory that may be
  used to override default configuration. The `~/.accelize` folder is always
  loaded as extra user configuration directory.

.. code-block:: bash

    accelpy init -n my_app -a my_app -p my_provider -c my_config_dir

.. note:: For futures calls, the utility automatically select the last
          configuration used. It is possible to select the
          configuration to use with the `--name`/`-n` argument.

It is possible list existing configurations with the `list` function:

.. code-block:: bash

    accelpy list

Provision
~~~~~~~~~

The provisioning is performed using Terraform and Ansible.

Before applying the infrastructure, it is recommanded to use `plan` to see what
will be provisioned, this output
`Terraform plan <https://www.terraform.io/docs/commands/plan.html>`_ command
result:

.. code-block:: bash

    accelpy plan

To really provision the infrastructure, use `apply`:

.. code-block:: bash

    accelpy apply

Once your infrastructure is not needed, use `destroy` to delete all provisioned
resources:

.. code-block:: bash

    accelpy destroy


To also remove the configuration if not required, use the `--delete`/`-d`
option with `destroy`:

.. code-block:: bash

    accelpy destroy -d


Image generation & immutable infrastructure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, host are provisioned based on a generic OS image and software is
installed using Ansible. This allow to easily setup a new infrastructure or
developing the application. But this is not recommanded in production.

Using an immutable infrastructure in production ensure that all host in the
environment are the same and are based on a stable and tested software stack.

The utility allow to easily create this kind of environment by providing the
feature of creating image/snapshot of the configuration.

This feature is performed using Packer.

To create an image, simply use the `build` command:

.. code-block:: bash

    accelpy build

This command return as artifact the generated image. This image needs to be
added to the application definition to be automatically used on next
infrastructure provisioning use. This can be done by editing the YAML file or
automatically using the `--update_application` argument:

.. code-block:: bash

    accelpy build --update_application

.. warning:: As side effect, the `--update_application` resets the YAML
             configuration file format and removes all comments inside it.

Always using the same host image to generate new hosts ensure immutability, but
don't forget to regularly regenerate the image and host that use it to ensure
system software are up to date and keep them secure.

SSH connection
~~~~~~~~~~~~~~

It is possible to connect application host using SSH using information returned
by the utility.

Example with OpenSSH:

.. code-block:: bash

    ssh -Yt -i $(accelpy ssh_private_key) $(accelpy ssh_user)@$(accelpy public_ip)

.. note:: By default, the utility generate a new SSH key for each configuration,
          but it is possible to configure it to use an existing key.


Python library usage
--------------------

The utility can also be used as a Python library.

The host configuration is managed with the `accelpy.Host` class:

.. code-block:: python

    from accelpy import Host

    # The Host class instantiation is equivalent to the CLI "init" function
    host = Host(name="my_app", application="my_app", provider="my_provider"
                user_config="my_config_dir")

    # CLI equivalent functions are proposed as host instance methods
    # Example with "apply" and "destroy".
    host.apply()
    host.destroy()

    # CLI equivalent information are proposed as host instance properties
    public_ip = host.public_ip

The `accelpy.Host` class can be used as context manager, this can be
used by example to create short lived host for a specific operation:

.. code-block:: python

    from accelpy import Host

    with Host(application="my_app", provider="my_provider",

                # Enable automatic destruction of the infrastructure on exit
                destroy_on_exit=True,

                # Enable clean up of the generated configuration on exit
                keep_config=False

                ) as host:

         # Provision the infrastructure
         host.apply()

         # Do some stuff on the infrastructure...

     # The infrastructure is destroyed and configuration cleaned up on context
     # manager exit

It is possible to iterate over existing configuration with the
`accelpy.iter_hosts` function:

.. code-block:: python

    from accelpy import iter_hosts

    # This example Print IP addresses of all existing hosts
    for host in iter_hosts():
        print(host.public_ip)

configuration
-------------

The utility is done to allow easy and extensible configuration of the host.

Default configuration are provided for some providers and applications types.
Theses configuration can be used with only minor modifications and are the
recommanded way to start using this utility.

You can find some provider examples in the "Provider examples" section of the
right menu.

It is also possible to modify the configuration or completely replace it. This
requires to have a minimal knowledge in tools used as backend
(Terraform, Ansible & Packer), but also allow you to user all of their power.
To see how to override the configuration, see :doc:`configuration`.

Overview
========

*accelpy* is an FPGA accelerated applications provisioning utility.

The aim of this utility is to provision the cloud or on-prem infrastructure and
configures it to run the application.

The philosophy behind the utility is to help to leverage software industry
standard solutions and frameworks instead of reinventing the wheel for FPGA
accelerated applications.

The utility is based on the powerful industry approved tools
`Ansible <https://www.ansible.com>`_, `Terraform <https://www.terraform.io>`_,
& `Packer <https://www.packer.io>`_. This allows the utility to support a very
wide variety of cloud of on-prem providers and support an to be very
configurable.

By default, it can deploy Docker containers based services, but can perform
many more with configuration.

Features
--------

Provision in the multi-Cloud
    *accelpy* can provision infrastructure on any provider that
    `Terraform support <https://www.terraform.io/docs/providers/>`_ and create
    software configuration images on any provider that
    `Packer support <https://www.packer.io/docs/builders/index.html>`_.

Provision an immutable infrastructure
    Once the application is ready, *accelpy* allow creating an image of it for
    all required provider and then use this image to deploy an immutable
    infrastructure.

Don't care about the FPGA requirements
    *accelpy* configure the host with required FPGA drivers and ensure the FPGA
    bitstream is loaded before starting the application.

Configure and scale as you need
    *accelpy* provides default infrastructure configuration that can be
    extended or overridden as needs allowing all possibilities of *Ansible*,
    *Terraform* and *Packer* tools.

    This allows generating the scalable infrastructure that fit your needs.

Protect your FPGA application
    *accelpy* is integrated into the
    `Accelize solution <https://www.accelize.com/>`_ and provides all
    the tools to provision application protected by the
    `Accelize DRM <https://www.accelize.com/docs>`_.

Containerize your application
    *accelpy* allow to package the software part of your application as a
    *Docker* container image and a single YAML configuration file.

Run without configuration
    *accelpy* provides default ready to use configuration to immediately
    provision a single host infrastructure on a subset of providers.

Use and integrate it easily
    *accelpy* can be operated using the command line interface or the Python
    API.

Deploy application on secure host that follow DevOps good practices
    The default configurations provided with *accelpy* are done with DevOps
    good practices and enhanced security in mind.
    `DevSec hardening baselines <https://dev-sec.io/>`_ can also be easily
    enabled in your deployment.

Be free to use it as you want
    *accelpy* generate a configuration for your application that can then be
    used without the utility itself as part of your own provisioning project.

    The entire project is open source and based on open source tools.

Documentation
=============
.. toctree::
   :maxdepth: 2
   :caption: User Guide

   getting_started
   configuration
   application_definition
   application_container_image
   cli_help
   api
   changes

.. toctree::
   :maxdepth: 2
   :caption: Application types

   application_ansible_role
   application_container_service
   application_kubernetes_node

.. toctree::
   :maxdepth: 2
   :caption: Providers

   provider_aws
   provider_host

.. toctree::
   :maxdepth: 2
   :caption: Applications examples

   example_kubeless_function

.. toctree::
   :maxdepth: 2
   :caption: Accelize links

   GitHub project page <https://github.com/Accelize/accelpy>
   PyPI project page <https://pypi.org/project/accelpy>
   Accelize Website <https://www.accelize.com>
   Contact us <https://www.accelize.com/contact-us>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Ansible role
============

The setup of the application is performed by one or more Ansible role.

Si allow to fully configure the host as wish.

Application definition
----------------------

This application type support the following package types:

* `ansible_role`: A role available on Ansible Galaxy or in a local subdirectory
  named `roles`.
* `vm_image`: An image of an already provisioned virtual machine.

Example snippet of application definition file:

.. code-block:: yaml

   application:
     name: my_application
     version: 1.0.2
     type: ansible_role

   package:
     - name: ansible_galaxy_namespace.role_name
       type: ansible_role
     - name: ansible_galaxy_namespace.role_name
       type: ansible_role

.. note:: Any application definition published using `accely push` require that
          roles are available on `Ansible Galaxy <https://galaxy.ansible.com>`_.

Variables
~~~~~~~~~

This application support any variables. All variables will be available in
Ansible roles.

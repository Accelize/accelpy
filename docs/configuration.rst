Configuration
=============

This section explain how to configure the utility and leveraging all the power
of Terraform, Ansible and Packer with generated configuration.

The configuration provides following features to allow this:

* Default configuration: Default configuration that can be used as base of more
  complex configuration.
* Configuration overriding: Mechanism to override configuration files.
* Configuration filtering: A mechanism to help to manage many configuration at
  once and select relevant configuration files on runtime.

Default configuration
---------------------

Default configuration are provided for some providers and applications types.
Theses configuration can be used with only minor modifications and are the
recommanded way to start using this utility.

You can find some provider examples in the "Provider examples" section of the
right menu.

Configuration files overriding
------------------------------

This feature allow to override the default configuration provided for
Terraform, Ansible and Packer by the utility.

When running, the utility search for configuration files to use in following
directories (in that order)):

* accelpy provided default configuration directories.
* Users home Accelize directory (`~/*.accelize`)
* Current working directory.
* User provided directory using `user_config` argument.

For each filename, the utility keep the last seen only.

By example: If a `common.tf` file exists in both default configuration and
current working directory. The one from the current working directory is used
and the one from the default configuration is ignored.

Configuration filtering
-----------------------

The feature allow to select configuration to include based on filenames.

Filenames are also filtered using their names, only files that match following
pasterns are imported to the configuration.

With the filter name equal to `common`, the provider name or the application
type. Files that starts with the filter name after being split by `.` are kept
in the configuration.

Tool specific configuration handling
------------------------------------

This section detail how is handled the configuration of each tool. This help to
understand how to override the configuration.

Terraform
~~~~~~~~~

Terraform is used to deploy the infrastructure.

The Terraform configuration is a set of files written in Terraform configuration
language (Ending by `.tf`, `.tfvars`, `.tf.json` or `.tfvars.json`).

Each file that match the name filtering are linked to the configuration
directory.

Terraform then combine theses files itself to generate its configuration.

The use of Terraform overrides files (Ending with `override.tf` is recommanded
to override parts of the configuration without the need of rewrite the whole
file that contain the part to override. The utility provides some overrides
files to easily customize some common cases (Files ending with
`.user_override.tf`)

An override file is available to easily set provider independent options:

:download:`common.user_override.tf <../accelpy/_terraform/common.user_override.tf>`.

Finally, variables from user and application are added to a variable definition
file (`generated.auto.tfvars.json`)

Ansible
~~~~~~~

Ansible is used to install required software on the infrastructure created by
Terraform.

The Ansible configuration is split in two parts:

* The playbook file (`playbook.yml`) that is used as base for the configuration.
* Ansible roles that contain the detail of the configuration.

First, the playbook file is copied from source directories to the configuration
directory.

Then, the utility search for roles in the `roles` sub directory of sources
directories. Roles that match name filtering are linked in the `roles`
subdirectory of the configuration directory and added in the playbook file.

Dependencies found in the `meta/main.yml` or roles are managed automatically:

*  Local dependencies are linked to th `roles` subdirectory of the configuration
   directory.
*  Dependencies from Ansible Galaxy are automatically downloaded.

It is possible to override Ansible variables to change software provisioning
behavior.

An override file is available to easily set common options:

:download:`common.user_override.yml <../accelpy/_ansible/common.user_override.yml>`.

Packer
~~~~~~

Packed is used to create an image of the software configuration created by
Ansible. This allow Terraform to deploy this image instead of fully
reconfiguring the infrastructure with Ansible. This allow to deploy the
infrastructure in a immutable way and reduce provisioning time.

The Packer configuration is a single `template.json` and packer does not support
any kind of overriding.

For this reason, the following mechanism is used:

* A base `template.json` is provided by the utility.
* Any `.json` files that match the naming filtering found in source directories
  are merged in the base template file (The merge is done in files alphabetical
  order)

Like for Terraform, some `.user_override.json` files are provided to easily
replace some common variables of the template file.

From this a single `template.json` is generated in the configuration directory.

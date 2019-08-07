Kubernetes Node
===============

The application is one or more preconfigured Kubernetes Nodes with a master
node.

.. note:: Currently the application provision only the application as a single
          node/master.

Application definition
----------------------

This application type support the following package types:

* `kubernetes_deployment`: A Kubernetes pod or deployment.
* `vm_image`: An image of an already provisioned virtual machine.

Example snippet of application definition file:

.. code-block:: yaml

   application:
     name: my_application
     version: 1.0.2
     type: kubernetes_node

   package:
     name: url_to_my_deployment_yaml
     type: kubernetes_deployment


Container configuration
-----------------------

See :doc:`application_container_image` for common container requirements.

Pod and Deployments configuration
---------------------------------

Kubernetes use
`devices plugins <https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/>`_
to manage FPGA resources.

Pods and deployment requires to specify resource limits to allow the use of
FPGA devices. Here is a basic examples of pods that require a FPGA device
for its container:

.. code-block:: yaml

    apiVersion: v1
    kind: Pod
    metadata:
      name: my_application_pod
    spec:
      containers:
        - name: my_container
          image: my_docker_account/my_image
          resources:
            limits:
              my_fpga_board_type: 1

Each device plugin may require the add of extra options to work.
The FPGA board type value also depend on the device plugin.
See relevant device plugins documentation for more information:

* `Xilinx boards <https://github.com/Xilinx/FPGA_as_a_Service/tree/master/k8s-fpga-device-plugin/trunk>`_
* `AWS F1 <https://github.com/Xilinx/FPGA_as_a_Service/tree/master/k8s-fpga-device-plugin/trunk/aws>`_

Security notice
---------------

Depending on the device plugin requirements, the container may run
in `privileged` mode to have FPGA access. This means that the container run as
`root` on your host.

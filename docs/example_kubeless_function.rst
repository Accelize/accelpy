Kubeless function
=================

This example show how to deploy a `Kubeless <https://kubeless.io>`_ Python
function on AWS F1 with Accelpy.

Kubeless require Kubernetes to run, we will use the
:doc:`application_kubernetes_node` Accelpy application type to deploy it.

Kubernetes configuration
------------------------

This application requires to creates some Kubernetes configuration files that
requires to be hosted online (By example on a GitHub repository)

* A `kubeless` namespace is required to install Kubeless.

.. code-block:: yaml
    :caption: kubeless-namespace.yml

    ---
    kind: Namespace
    apiVersion: v1
    metadata:
      name: kubeless
      labels:
        name: kubeless

* The function to run needs to be configured as a Kubernetes object to allow
  the specification of FPGA requirements:

  * `kubeless.yml <https://github.com/kubeless/kubeless/releases>`_: The YAML
    that install Kubeless itself. This one is already hosted and ready to use on
    Github.
  * A specific deployment spec that define resources limits, and in the AWS case
    `privileged`, root user and volume options.
  * A specific Kubeless runtime that contain FPGA required libraries (AWS FPGA
    runtime & Xilinx XRT)

.. code-block:: yaml
    :caption: my-function.yml

    ---
    apiVersion: kubeless.io/v1beta1
    kind: Function
    metadata:
      name: my-function
      namespace: default
      label:
        function: my-function
    spec:
      # We require a custom runtime to handle additional FPGA libraries
      runtime: python_fpga3.6
      handler: my-function.list
      deployment:
        spec:
          template:
            spec:
              # This part handles FPGA container requirements
              containers:
                # Define FPGA resource limits
                - resources:
                    limits:
                      xilinx.com/fpga-xilinx_aws-vu9p-f1-04261818_dynamic_5_0-0: 1
                # Add Extra AWS F1 requirements
                  securityContext:
                    privileged: true
                    runAsUser: 0
                    runAsGroup: 0
                  volumeMounts:
                    - name: sys
                      mountPath: /sys
              volumes:
              - name: sys
                hostPath:
                  path: /sys
      function-content-type: text
      # Here is the code of the Python function to run
      function: |
        def list(event, context):
            from subprocess import run, PIPE, STDOUT
            return run(['/opt/xilinx/xrt/bin/awssak', 'list'],
                       stderr=STDOUT, stdout=PIPE, universal_newlines=True).stdout


Application definition
----------------------

Accelpy require the following application definition to run the function.

.. code-block:: yaml
    :caption: my-function-application.yml

    ---
    application:
      product_id: my-function
      type: kubernetes_node
      version: 1.0.0

    firewall_rules:
      # We need to allow access to the Kubernetes node in the AWS security group
      # For this example, we will simply enable all NodePort ports.
      - start_port: 30000
        end_port: 32767
        protocol: tcp
        direction: ingress

    fpga:
      # AGFI that correspond to the FPGA image of the function
      image: agfi-071909cc191313a51
      count: 1

    package:
      # Previously defined Kubernetes configuration YAML
      # The order is important: namespace, Kubeless
      - type: kubernetes_yaml
        name: https://raw.githubusercontent.com/Accelize/accelpy/master/examples/kubeless_function/kubeless-namespace.yml
      - type: kubernetes_yaml
        name: https://github.com/kubeless/kubeless/releases/download/v1.0.4/kubeless-v1.0.4.yaml
      # Note: We can't add the function yaml here, Kubeless requires
      #       configuration first


Provision a master/node with Accelpy
------------------------------------

Provisioning a master/node instance allow to test the application on a
disposable Kubernetes infrastructure.

To provision, simply run following commands:

.. code-block:: bash

    accelpy init -a my-function-application.yml -p aws,eu-west-1,f1 -n my-function
    accelpy apply -n my-function

Once the instance is ready, it is required to configure Kubeless to use a
specific runtime image for Python3.6:

.. code-block:: bash

    kubectl edit -n kubeless configmap kubeless-config

Then, add in "data.runtime-images":

.. code-block:: json

    {
      "ID": "python_fpga",
      "depName": "requirements.txt",
      "fileNameSuffix": ".py",
      "versions": [
        {
          "images": [
            {
              "command": "pip install --prefix=$KUBELESS_INSTALL_VOLUME -r $KUBELESS_DEPS_FILE",
              "image": "accelize/base:centos_7-aws_f1-kubeless-python_3.6",
              "phase": "installation"
            },
            {
              "env": {
                "PYTHONPATH": "$(KUBELESS_INSTALL_VOLUME)/lib/python3.6/site-packages:$(KUBELESS_INSTALL_VOLUME)"
              },
              "image": "accelize/base:centos_7-aws_f1-kubeless-python_3.6",
              "phase": "runtime"
            }
          ],
          "name": "python_fpga36",
          "version": "3.6"
        }
      ]
    }

Reload the Kubeless controller to apply change
.. code-block:: bash

    kubectl delete pod -n kubeless -l kubeless=controller

Create a node image with Accelpy
--------------------------------

Since our application is now ready and fully working in master/node, time is
ready to push it in production on our existing Kubernetes infrastructure on AWS.

It is possible to pass some variables to Ansible to specify the join
command that will automatically join the node to an existing Kubernetes
infrastructure. This can be done with the user override file:

.. code-block:: yaml
    :caption: ~/.accelize/common.user_override.yml

    ---
    # Add join command from your master, you can get it with kubeadm
    # command: "kubeadm token create --print-join-command"
    kubernetes_join_command: join command

.. note:: Using the override file is not the only way to execute the join
          command on the node instance. It is also possible to execute it on
          node instantiation (By example with the "cloud init" / "user data"
          provided by some cloud providers).

Then we run accelpy to build an image of the node and add its AMI to the
application definition.

.. code-block:: bash

    accelpy init -a my-function-application.yml -p aws,eu-west-1,f1 -n my-function_node
    accelpy build -n my-function_node -u
    accelpy destroy -d

The AMI can now be used in any Kubernetes infrastructure on AWS.
Once some F1 nodes are running based on the image, it is possible to run the
Kubeless function on it by running following commands on the master node:

.. code-block:: bash

    # AWS FPGA device plugin installation
    kubectl apply -f https://raw.githubusercontent.com/Xilinx/FPGA_as_a_Service/master/k8s-fpga-device-plugin/trunk/aws/aws-fpga-device-plugin.yaml

    # Kubeless installation
    export RELEASE=$(curl -s https://api.github.com/repos/kubeless/kubeless/releases/latest | grep tag_name | cut -d '"' -f 4)
    kubectl create namespace kubeless
    kubectl apply -f https://github.com/kubeless/kubeless/releases/download/$RELEASE/kubeless-$RELEASE.yaml

    # [Optional] Kubeless CLI installation
    export OS=$(uname -s| tr '[:upper:]' '[:lower:]')
    curl -OL https://github.com/kubeless/kubeless/releases/download/$RELEASE/kubeless_$OS-amd64.zip
    unzip kubeless_$OS-amd64.zip
    sudo mv bundles/kubeless_$OS-amd64/kubeless /usr/bin/
    rm kubeless_$OS-amd64.zip

    # Runtime deployment (Do same config change as in
    # "Provision a master/node with Accelpy") section
    kubectl edit -n kubeless configmap kubeless-config
    kubectl delete pod -n kubeless -l kubeless=controller

    # Function deployment
    kubectl apply -f https://raw.githubusercontent.com/Accelize/accelpy/master/examples/kubeless_function/my-function.yml

    # [Optional] Call the function with Kubeless CLI
    kubeless function call my-function

    # [Optional] Create a proxy to the API server
    kubectl proxy -p 8080 &

    # [Optional] Call the function trough the proxy
    curl -L localhost:8080/api/v1/namespaces/default/services/my-function:http-function-port/proxy/

Your FPGA function is now working with Kubeless on AWS.

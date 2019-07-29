Kubernetes Node
===============

The application is one or more preconfigured Kubernetes Nodes with a master
node.

.. notes:: Currently the application provision only the application as a single
           node/master.

Container configuration
-----------------------

See :doc:`application_container_image` for common container requirements.

The container `ENTRYPOINT`/`CMD` must run the application as an infinitely
running application.

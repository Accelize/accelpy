# coding=utf-8
"""Application tests"""
import pytest


def mock_application(source_dir, override=None):
    """
    Mock Application

    Args:
        source_dir (py.path.local): Source directory.
        override (dict): Dict with update content.

    Returns:
        py.path.local: Application path.
    """
    from accelpy._yaml import yaml_write

    application = source_dir.join('application.yml')

    content = {
        'application': {
            'product_id': 'my_product_id',
            'version': '1.0.0'
        },
        'package': [{
            'type': 'container_image',
            'name': 'my_image'
        }],
        'fpga': {
            'image': 'image'
        },
        'accelize_drm': {
            'conf': {
                'drm': {}
            }
        }
    }
    if override:
        content.update(override)

    yaml_write(content, application)

    return application


def test_lint(tmpdir):
    """
    Test application definition file lint

    Args:
        tmpdir (py.path.local) tmpdir pytest fixture
    """
    from accelpy._application import Application
    from accelpy.exceptions import ConfigurationException

    # Mock yaml definition file
    yml_file = tmpdir.join('application.yml')

    # Test: Load valid file
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  - type: container_image
    name: my_container_image
    version: 1.0.0

    # Override of value in provider
    my_provider:
      type: vm_image
      name: my_vm_image

firewall_rules:
  - start_port: 1000
    end_port: 1000
    protocol: tcp
    direction: ingress
  - start_port: 1001
    end_port: 1100
    protocol: tcp
    direction: egress

fpga:
  # Mandatory value only in provider
  my_provider:
    image: my_fpga_image
""")
    app = Application(yml_file)

    # Test: __getitem__
    assert app['application']['product_id'] == 'my_product_id'

    # Test section _node
    assert isinstance(app['firewall_rules'], list)
    assert isinstance(app['application'], dict)

    # Test: get
    assert app['fpga']['image'] is None
    assert app['my_provider']['fpga']['image'] == ['my_fpga_image']
    assert app['package'][0]['type'] == 'container_image'
    assert app['my_provider']['package'][0]['type'] == 'vm_image'

    # Test: save
    app['package'][0]['my_provider']['name'] = 'another_image'
    app.save()
    assert Application(
        yml_file)['my_provider']['package'][0]['name'] == 'another_image'

    # Test: provider
    assert app.providers == {'my_provider'}

    # Test: Load valid file with missing not mandatory section
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  - type: container_image
    name: my_container_image

fpga:
  image: image
""")
    app = Application(yml_file)
    assert app['firewall_rules'] == []

    # Test: Load file with inferred list section from mapping
    yml_file.write("""
    application:
      product_id: my_product_id
      version: 1.0.0

    package:
      type: container_image
      name: my_container_image

    fpga:
      image: image
    """)
    app = Application(yml_file)
    assert app['package'][0]['type'] == 'container_image'

    # Test: Provider with reserved name
    yml_file.write("""
    application:
      product_id: my_product_id
      version: 1.0.0

    package:
      - type: container_image
        name: my_container_image

    fpga:
      image: image
      application:
        image: image
    """)
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: Missing or empty package section
    yml_file.write("""
    application:
      product_id: my_product_id
      version: 1.0.0

    package: []

    fpga:
      image: image
    """)
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    yml_file.write("""
    application:
      product_id: my_product_id
      version: 1.0.0

    fpga:
      image: image
    """)
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: Load bad section type
    yml_file.write("""
application:
  - product_id: my_product_id
    version: 1.0.0

package:
  - type: container_image
    name: my_container_image

fpga:
  image: image
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: Missing mandatory value in default keys
    yml_file.write("""
application:
  product_id: my_product_id

package:
  # Missing image
  - type: container_image

fpga:
  image: image
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: Missing mandatory value in provider keys
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  # Missing image
  - my_provider:
      type: container_image

fpga:
  image: image
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: Value not in list
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  - type: container_image
    name: my_container_image

firewall_rules:
  - start_port: 1000
    end_port: 1000
    protocol: tcp
    # No a known direction
    direction: no_direction

fpga:
  image: image
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: Bad value type
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  - type: container_image
    name: my_container_image

fpga:
  image: image
  # Count should be an int
  count: "1"
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: Bad value type in list
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  - type: container_image
    name: my_container_image

fpga:
  image:
    - image_slot0
    - 1
  count: 1
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: List of values
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  - type: container_image
    name: my_container_image

fpga:
  image:
    - image_slot0
    - image_slot1
  count: 1
""")
    Application(yml_file)

    # Test: Auto list conversion
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  - type: container_image
    name: my_container_image

fpga:
  image: image_slot0
  count: 1
""")
    Application(yml_file)

    # Test: top level list bad value
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  - type: container_image
    name: my_container_image

fpga:
  image: 1
  count: 1
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: Extra section should not raise
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  - type: container_image
    name: my_container_image

fpga:
  image: image
  
extra_section:
  extra_key: value
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: Extra key should raise
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  - type: container_image
    name: my_container_image

fpga:
  image: image
  extra_key: value
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: Extra key should raise in provider
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  - type: container_image
    name: my_container_image

fpga:
  image: image
  my_provider:
    extra_key: value
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: Value does not match regex
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0.0.0

package:
  - type: container_image
    name: my_container_image

fpga:
  image: image
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)


@pytest.mark.require_csp
def test_web_service_integration():
    """
    Test web service integration.
    """
    from accelpy._common import request
    from accelpy._application import Application
    from random import randint

    # Use dev environment
    request_endpoint = request._endpoint
    request._endpoint = 'https://master.devmetering.accelize.com'

    product_id = 'accelize.com/accelpy/ci'
    version = f'{randint(0, 255)}.{randint(0, 255)}.{randint(0, 255)}'
    application = f'{product_id}:{version}'

    definition = dict(
        application=dict(
            product_id=product_id, type='container_service', version=version),
        fpga=dict(image='nothing'),
        package=dict(name='nothing', type='container_image'),
        accelize_drm=dict(use_service=False))

    try:
        scr_app = Application(definition)

        # Test: push
        scr_app.push()

        # Test: Get
        srv_app = Application.from_id(application)
        assert scr_app._definition == srv_app._definition

        # Test: List
        assert product_id in Application.list()

        # Test: List with prefix
        assert product_id in Application.list('accelize.com/accelpy')

        # Test: List version
        assert version in Application.list_versions(product_id)

        # Test: List version with prefix
        assert version in Application.list_versions(
            product_id, version.split('.', 1)[0])

        # Test: Delete
        Application.delete(application)
        assert version not in Application.list_versions(product_id)

    finally:
        try:
            Application.delete(application)
        except Exception:
            pass
        request._endpoint = request_endpoint

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
        'package': {
            'type': 'container_image',
            'name': 'my_image'
        },
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
  type: container_image
  name: my_container_image
  version: 1.0.0

  # Override of value in environment
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
  # Mandatory value only in environment
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
    assert app.get('fpga', 'image') is None
    assert app.get('fpga', 'image', 'my_provider') == ['my_fpga_image']
    assert app.get('package', 'type') == 'container_image'
    assert app.get('package', 'type', 'my_provider') == 'vm_image'

    # Test: save
    app['package']['name'] = 'another_image'
    app.save()
    assert Application(yml_file)['package']['name'] == 'another_image'

    # Test: environment
    assert app.environments == {'my_provider'}

    # Test: Load valid file with missing not mandatory section
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
    assert app['firewall_rules'] == []

    # Test: Load bad section type
    yml_file.write("""
application:
  - product_id: my_product_id
    version: 1.0.0

package:
  type: container_image
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
  type: container_image

fpga:
  image: image
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: Missing mandatory value in environment keys
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  # Missing image
  my_provider:
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
  type: container_image
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
  type: container_image
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
  type: container_image
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
  type: container_image
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
  type: container_image
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
  type: container_image
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
  type: container_image
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
  type: container_image
  name: my_container_image

fpga:
  image: image
  extra_key: value
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)

    # Test: Extra key should raise in environment
    yml_file.write("""
application:
  product_id: my_product_id
  version: 1.0.0

package:
  type: container_image
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
  type: container_image
  name: my_container_image

fpga:
  image: image
""")
    with pytest.raises(ConfigurationException):
        Application(yml_file)
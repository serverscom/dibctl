Pytest tests
---

Dibctl may use py.test as test framework. Usage of testinfra plugin is highly recommended, but not mandatory.

All pytest tests follows generic rules for py.test. If any test failed, dibctl will return error for test results.

Tests, written for pytest, may use set of fixtures with information about instance and image under test.

List of available fixtures:
- flavor - information about flavor used to run test instance.
- flavor_meta - meta information for flavor
- ips - list of all ips  on all interfaces of instance
- ips_v4 - list of all IPv4 addresses on all interfaces
- ips_v6 - same as above with IPv6 addresses
- main_ip - single value with IPv4, selected according to main_nic_regexp.
- network - additional information about all interfaces, including expected MAC addresses, subnets, etc.
- ssh - information about ssh connection to test instance. Includes main ip, path to the private key, username to connect to instance
- ssh_backend - prepared testinfra backed to the instance.
- environment_variables - environment_variables from image config.
- port - information about ip/port, used to server availability prior to test

flavor fixture
---
Flavor fixture is a copy of 'flavor' object from novaclient. It contains:
- flavor.id - flavor id
- flavor.name - flavor name
- flavor.disk - disk size (in GB)
- flavor.mem - memory size (in MB)
- flavor.vcpus - amount of VCPUs

flavor_meta fixture
---
It is a dict with key:value structure, containing all metadata for flavor used to start test instance.

ips
---
It is a list of all (IPv4 and IPv6) addresses allocated by neutron/nova. Does not include any floatingIPs.

ips_v4
---
It is a list of all IPv4 addresses on allocated by neutron/nova. Does not include any floatingIPs.

ips_v6
---
It is a list of all IPv6 addresses on allocated by neutron/nova. Does not include any floatingIPs.

main_ip
---
It's a single unicode string containing IPv4 address which was choosen as main_ip according to main_nic_regexp (or  it single ip if instance has one interface with one IP address)

network
---
It contains result of nova.instance.interface_list() call.

ssh
---
It's a dictionary with following elements:
- ip
- private_key_file
- key_name
- username (may be None if none was specified in the image configuration)

ssh_backend
---
It's a testinfra ssh backend

environment_variables
---
It's a dictionary from environment_variables section of tests section of image config.

port
---
It's a dictionary. It contains information about port, used to check connection to instance prior running tests.
Contains:
- ip (main ip) - unicode string
- port (int)
- timeout (int) - expected maximum timeout
- delay (float) - who long was wait process before instance replied on the given port

nova
---
A fixture to have access to nova client (python-novaclient) with established credentials to
openstack.

glance
---
Fixture returns configured glance client (python-glanceclient) with established session.

image_info
---
Glance metadata of the instance's boot image.

image_config
---
Dictionary of current image configuration items from `image.yaml`.

console_output
---
Text full console log of an instance, stored by OpenStack.
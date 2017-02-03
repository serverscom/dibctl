Dibctl
------

Dibctl is an automation software indendent to help with configuring
diskimage-builder, maintain, test and upload images in consistent way.

This readme is under construction, as well, as software itself.


Image lifecycle
---------------

BUILD -> TEST -> UPLOAD -> OBSOLETE -> ROTATE


Configuration
-------------
There are three important conceptions in Dibctl:
images, test environments and upload environments.
Each of them have separate configuration file.

## Images.yaml
This file describes how to build image, which
name and medata it should have in glance during upload,
which *test_environment* to use to test this image,
which tests should be ran during test stage.

## test.yaml
This file describes test environments. They may be
referenced by images in `image.yaml`, or forced to
be used during test from command line.
It contains all openstack information for test
purposes:
- Where to upload image for test (OS credentials)
  (images are upload for test independently from
   actual 'upload' stage)
- Which flavor, network(s), etc to use

## upload.yaml
This file contains configuration for upload.
Each entry describes credentials and connection
options for one openstack installation.

During upload image uploaded to a given upload
environemnt with metadata, name and properties
specified in the images.yaml.


Configs
-------

Images config (yaml):
```
imagelabel:
  filename: name of the image
  glance:
    name: 'Image Name x86_64'
    properties:
      - key: value
      - key: value
    public: true/false  # default true
    share_with_tenants:
     - tenant_name1 # some_private_tenant may be omitted, tenant from command line will be used, tenant_name
     - tenant_name2
  dib:
    environment_variables:
      key: value
      key2: value2
    cli_options:
     - option1
     - option2
    elements:
     - element1
     - element2
     environment_variables:
       name1: value1
       name2: value2
  tests:
    environment_name: name_of_environment
    wait_for_port: 22  # default (if not specified), 22
    port_wait_timeout: 61  #default (if not specified), 61
    config:
      key1: value1
      key2: value2  # goes to environment variables for tests
    tests_list:
     - dir1
     - dir2
     - dir3/test3.py
```

test environments config:
```
environmentname:
  os_auth_url:
  os_tenant_name:
  os_username:
  os_password:
  flavor: name
  main_nic_regexp: regexp1
  nics:
   - net-id1
   - net-id2
   - net-id3
```

Image lifecycle
---------------

BUILD -> TEST -> UPLOAD -> OBSOLETE -> ROTATE

BUILD: produce image file
TEST: upload file to the test (private) account, start instance in test environment, run tests against image, report status
UPLOAD: upload to given installation and obsolete images of the same name with prefix
ROTATE: delete unused obsolete images from given installation

Command line
------------

By default dibctl will search config in:

- current directory: (images.yaml, test\_environments.yaml)
- current directory: dibctl/images.yaml, dibctl/test\_evnironments.yaml
- /etc/dibctl/images.yaml dibctl/test\_environments.yaml

Alternative name may be passed via command line (--images-config, --test-environments-config)

* `dibctl build imagelabel [-o filename] [--images-config images.yaml]`
  Build given image

* `dibctl test imagelabel [-i filename] [--images-config images.yaml] [--test-environments-config env.yaml] [--upload-only] [--use-existing-image uuid] [--force-test-env env-name]`

Upload image to test tenant and spawn instance, run tests against this instance. Return -1 if test failed, or 0 if tests passed.
If no filename supplied, 'filename' form images.yaml is used. os\_tenant\_name, os\_password, os\_auth\_url, os\_username may
be overrided via environment variables, and may be ommited in config


* `dibctl upload imagelabel [-i filename] [--images-config images.yaml] [--no-obsolete]`

Upload image to a given environment with properties and name from images.yaml
Old images with same name (in the same tenant) would be renamed to 'Obsolete (oldname)' and marked with property.

* `dibctl mark-obsolete uuid [uuid, ...]`
Obsolete given image name (rename and mark it with property)

* `dibctl rotate ["Image Name 1" "Image Name 2" ...]`

Rotate (remove) unused obsolete images with given name (if no name given, all unused obsolete images are processed)
Requires administrative permissions to find if image is unused or not.


Dibctl uses environment variables for Openstack credentials (except for the tests where it uses credentials from test-environments.yaml).
It uses standard names for environment variables:
```
OS_USERNAME
OS_PASSWORD
OS_TENANT_NAME
OS_AUTH_URL
```

For test command dibctl prioritize environment configuration with exception of OS_PASSWORD,
which have higher priority over configuration file.

Examples
--------


images.yaml for normal Ubuntu:
```
xenial-servers.com:
  filename: xenial-servers.com.img.qcow2
  glance:
    name: 'Ubuntu 16.04 Xenial (x86_64)'
    properties:
     - display_priority: 4
     - allowed_flavors: "[3,4,5,6]"
    public: True
 dib:
   environment_variables:
      DIB_APT_REPO: mirror.servers.com
      DIB_NTP: 192.168.8.8
   elements:
    - ubuntu
    - deb-servers.com
 tests:
     environment_variables:
      key1: value1
     environment_name: normal-servers.com
     tests_list:
      - type: tests/servers.com.d/
      - type: tests/debian-based/
```

images.yaml for Centos7 with GPU for private tenant
```
centos7-nvidia-servers.com:
 filename: centos7-nvidia-servers.com.img.qcow2
 glance:
   name: 'Customized Centos 7 (x86_64) with NVIDIA driver'
   properties:
     - display_priority: 9
     - allowed_flavors: "[333, 666]"
     - display_type: gpu
   public: False
   share_with_tenant:
     - 3344
     - demotenant
  dib:
    environment_variables:
      DIB_APT_REPO: vip-tenant.own.repo.com
      DIB_NTP: 192.168.8.8
    elements:
     - ubuntu
     - deb-servers.com
     - nvidia
     - tenant_3344_tweaks
  tests:
    environment_name: gpu-servers.com
    environment_variables:
      ssh_username: cloud-user
    tests_list:
     - pytest: tests/servers.com.d/
     - pytest: tests/debian-based/
     - shell: tests/deb-nvidia/
     - pytest: tests/tenant_3344_tweaks.sh
```

Windows image (without dib elements, can not be build, may be tested and uploaded)
```
windows-servers.com:
  filename: windows-magic-artifact.img.qcow2
  glance:
    name: 'Windows 2016 Server'
    properties:
     - display_priority: 1
     - allowed_flavors: "[5,6,7]"
     - isolate_os: windows
     - requires_ssh_key: true
     - windows12: true
    public: True
 dib:
   tests:
     environment_name: windows-servers.com
     tests_list:
      - tests/windows-tests/
```
test-environments.yaml
```
normal-servers.com:
 os_auth_url: http://keystone.p:35357/v2.0
 os_tenant_name: for-image-tests
 os_username: image-rotate
 os_password: Kid5ilagfees
 flavor: c281fb70-a751-11e6-a10e-17fb4e159f14
 main_nic_regexp: /internet/
 nics:
  - 1c4ac9c0-a751-11e6-a31d-fbc010cadaa1
  - d38091ca-a751-11e6-acb0-935b96e35464
  - 271550fa-a751-11e6-ac66-db994dd5c8b2
gpu-servers.com:
 os_auth_url: http://keystone.p:35357/v2.0
 os_tenant_name: for-image-tests
 os_username: image-rotate
 # no os_password here
 flavor: dd533d60-1335-4257-b07a-5d018b1e06bd
 main_nic_regexp: internet
 nics:
  - 1c4ac9c0-a751-11e6-a31d-fbc010cadaa1
  - 271550fa-a751-11e6-ac66-db994dd5c8b2
windows-servers.com:
 os_auth_url: http://keystone.p:35357/v2.0
 os_tenant_name: for-image-tests
 os_username: image-rotate
 # no os_password here
 flavor: 01660ce6-a752-11e6-8165-db95f7e4f53f
 nics:
  - 1c4ac9c0-a751-11e6-a31d-fbc010cadaa1
```

Command line
------------
```
dibctl build centos7-nvidia-servers.com
dibctl test centos7-nvidia-servers.com
OS_TENANT_NAME=public_images \
 OS_USERNAME=image-rotate \
 OS_PASSWORD="yu9Grag" \
 OS_AUTH_URL=http://keystone.p:35357/v2.0 \
 dibctl upload centos7-nvidia-servers.com

OS_TENANT_NAME=demotenant \
 OS_USERNAME=superadmin \
 OS_PASSWORD="qwerty" \
 OS_AUTH_URL=http://keystone.p:35357/v2.0 \
 dibctl rotate

OS_PASSWORD=4WredOlOced dibctl test windows-servers.com -i mywindows.img.qcow2

OS_TENANT_NAME=public_images \
 OS_USERNAME=image-rotate \
 OS_PASSWORD="yu9Grag" \
 OS_AUTH_URL=http://keystone.p:35357/v2.0 \
 dibctl upload windows-servers.com -i mywindows.img.qcow2

OS_TENANT_NAME=public_images \
 OS_USERNAME=image-rotate \
 OS_PASSWORD="yu9Grag" \
 OS_AUTH_URL=http://keystone.p:35357/v2.0 \
 dibctl mark-obsolete "Ubuntu Karmic x86_64"

```

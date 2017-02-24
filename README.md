Dibctl
------

Dibctl is a software for image build, testing and  uploading.
It uses diskimage-builder to build images, pytest and testinfra
to test them and provide a consistent way to upload tested images
to multiple Openstack installations.

Dibctl uses configuration files to how to build image, which name
it should have after upload, what properties (if any) should be
set for a given image. Image configuration file also provide list
of tests for each image, plus name of environment where tests should
happen.

Other configuration file, test.yaml contains information how to
run test instance: region authorization url, credentials, flavor,
network list, availability zone, security groups and other nova
parameters.

Third configuration file provides upload configuration for
arbitrary amount of openstack regions.

*This readme is under construction, as well, as software itself.*

Element is not image
--------------------

Diskimage-builder is very nice way to build custom images from elements.
One need to supply few pieces to diskimage-builder to get image:
- few enviroment variables for diskimage-builder itself
- few very inconsistent and cryptic variables for used elements
- some command line arguments for diksimage-builder
- list of elements used to build image

Resulting command line is a 'golden artifact' - you need to keep it
somewhere.

After an image was build, you can upload it to your Glance. You need
to provide few more pieces of information:
- Image name
- Credentials for Glance
- Additional meta you need to set up on image (`hw_property`, etc)

This adds few more lines to the 'golden artifact'.

Normally one wants to test image before uploading. It should, at least,
be able to boot and accept ssh key.

One may create a simple script to boot and test it:

This adds few more lines:
- credential to spawn instance
- flavor id
- nics net-id
- security group name

If one have more than one image with more than one configuration
for testing, this brings up complexity even higher.

Dibctl was created to solve this problems. It provides consistent
way to describe images, test and upload enviroments, relations
between image and tests, way to ensure that images are fully functional
(outside of usual scope of 'I can log in').
Examples of test preshipped with dibctl:
- Does instance resize rootfs up to flavor limits at first boot?
- Does it recieves IP addresses on all attached interfaces?
- Does DNS set up properly?
- Does hostname match the name of the instance?
- Does instance still work after reboot?

Outside of main scope dibctl gives one more nice feature: image-transfer,
which can copy image from one glance to another while preserving every propery,
ownership and share information (tenant-name based).

Key concepts
------------

Dibctl uses following conceptions:
- label (for image and environment) - internal 'name' for a given image or environemnt to
use in command line. Add entries in dibctl configuration have label, or 'namelabel'.
- image: set of attirbutes to build and test image. Images are described in images.yaml file.
- test instance: Instance used for testing image. Instance is created at test time and
  removed afterwards. Dibctl creates custom SSH key for each test.
- test image: image uploaded for testing. Dibctl uses separate upload stage for testing and
  actual 'upload to procution'. Test images normally uploaded to specific project and are
  not public. Production images are normally public (or upload to selected tenant and shared
  with specific tenants). Test image is removed after test (succesfull or not).
- test environemnt: set of attributes and variables describing how upload test image and
  how to boot test instance. Every image references to test environement by it's label.
  They are listed in tests.yaml
- upload environemnts: Those are describes how and where upload images for production use.
  Uploaded images are subjected to optional 'obsoletion' stage (see Obsoletion part below),
  which happens automatically every time image is uploaded or manually.


Image lifecycle
---------------

`BUILD -> TEST -> UPLOAD -> OBSOLETE -> ROTATE`

## Build stage
It uses information from corresponding entry in images.yaml to execute diskimage-builder.
'filename' option specify target filename.
dibctl translates diskimage-builder exit codes
(it exits with same exit code as diskimage-builder).

## Test stage
At this stage image should be build. Dibctl uses information from entry in images.yaml
to find image file for testing ('filename'), and than uses `environment_name` to
find correspoinding test environment in tests.yaml. Then it upload image, creates new ssh key,
spawns instance accoring to test environments settings, and executing tests
in `tests_list` section of image configuration. Those tests recieve information about
instance (IP addresses, network settings, hostname, flavor, etc), perform instance validation.
If all tests passes successfully, dibctl sets exit code to 0, otherwise error returned.
Regardless of the test results all test-time objects in Openstack are removed: test image,
test instance, ssh key. User may use `--keep-failed-image` and `--keep-failed-instance` to
keep them for closer investigation.

*not implemented yet*
By using --shell dibctl may be instructed to open ssh shell to test machine when tests failed.
After that shell is closed, instance (and all other pieces of test) are removed.


## Upload stage
At the upload stage image is uploaded to specified installation with specific settings
for publication. All image-specific things (properties, tags, etc) from images.yaml
are used during this stage, as well, as settings from upload.yaml (See variable ordering
to see override rules).

After upload done, it triggers *obosoletion stage* if obsoletion is stated in
upload configuration.

## Obsolete stage
Obsolete image: If image is in the same tenant and have same glance name as freshly uploaded,
it is obsolete. Obsoleted images recieve specific rename pattern (usually adds 'Obsolete ' before
name), and specific set of properties.

Obsoletion may be performed manually by using 'obsolete' command.

## Rotation stage
If obsolete image is no longer used by any instances in region it's called unused obsoleted
image and may be removed. That is done by 'rotate' command.

Please note, rotation requires administrative privilege (dibctl needs to see all instances
in the region). Normally it's performed periodically by administrator itself, without
delegating this job to CI/cron.

Installation
------------
You need to have following packages installed:
- diskimage-builder
- novaclient
- glanceclient
- keystoneauth1

Important notice: at this moment diskimage-builder package
in debian & ubuntu is very, very old (1.0). You need
to upgrade it al least to 1.9 to have working images.

Please use pip version or rebuild package
if you have own CI/buildfarm.

If you want to use python-based test you need:
- pytest
- pytest-timeout
- pytest-testinfra (it's new and it may be not in your distro yet)

TODO: set up ppa with dependencies

Configuration
-------------

Dibctl may use system-wide configuration files
(/etc/dibctl/) or local configuration files (./dibctl).
Local configuration files usually used within
git repository, containing custom image and enviroment
configs, custom diskimage-builder elements and
custom tests.

## Configuration file prioriy
Dibctl stops searching file as soon as file is found.
Each file is searched independently
(f.e. /etc/dibctl/images.yaml and ./dibctl/test.yaml)

Lookup order:

- `./` (config file in the current directory)
- `./dibctl` (config file in the dibctl directory in the current directory)
- `/etc/dibctl` (system-wide configs)

Configuration file names:
- `images.yaml`
- `test.yaml` (test environments)
- `upload.yaml` (upload environments)

If one uses pytest-based tests, than tox.ini and other
pytest-related configuration files may influence tests
discovery.

### `images.yaml`
This file describes how to build image, which
name and properties it should have in Glance during upload,
which *test_environment* to use to test this image,
which tests should be ran during test stage.

### `test.yaml`
This file describes test environments. They may be
referenced by images in `image.yaml`, or forced to
be used during test from command line.
It contains all openstack information for test
purposes:
- Where to upload image for test (OS credentials)
  (images are upload for test independently from
   actual 'upload' stage)
- Which flavor, network(s), etc to use

### `upload.yaml`
This file contains configuration for upload.


Variable ordering
-----------------
When dibctl performs tests or uploads it combines
information from `images.yaml` and correspoding
environment config (`test.yaml` or `upload.yaml`).

Each of that file may contains `glance` section.
Normally all image-specific variables should
be kept in the `images.yaml` config file,
but under certain circumstances it may be desirable
to override/change them for a given location.
Most noticable and common are timeout settings
(for remote/slow regions) and `glance_endpoint`
to help deal with complicated intra-extra-net
endpoints.

Special riority rules for `glance` section:
- `api_version` - environment have priority over image
- `upload_timeout` - used a max of all available values
- `properties` - merged. If there are same properties in
   the images config and in environement config,
   environments have priority over image.
- `tags` - merged (this is a simple list)
- `endpoint` - environment have priority over image

For all other variables image has priority over
environment (please see `smart_join_glance_config`
function for up to date information).

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

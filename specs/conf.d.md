Conf.d support
--------------

Production use of dibctl shows that current configuration scheme for images,
tests and uploads in hard to maintain. Average image configuration is about
40 lines long. With ~10 images it's a 400 lines config, which is hard to navigate
and manage. Additionally, images, grouped in one file, prevents seamless
merge of independent changes for different images.

Preposition
===========

Add support for conf.d style configurations. Each top-level element of the list
(image, test, upload) may be placed in a separate file. Global configuration
is still honored (for example, there is no need for splitting upload.yaml, so far,
so it can be left alone as a single file).

Proposed structure
==================
Old search structures will be left intact. New search pathes:

First:
- `./images.d/*.yaml`
- `./test.d/*.yaml`
- `./upload.d/*.yaml`

Second:
- `./dibctl/images.d/*.yaml`
- `./dibctl/test.d/*.yaml`
- `./dibctl/upload.d/*.yaml`

Last:
- `/etc/dibctl/images.d/*.yaml`
- `/etc/dibctl/test.d/*.yaml`
- `/etc/dibctl/upload.d/*.yaml`


Joining instead of override
===========================
As those are independent files, we need to change the way configuration files are
loaded. Old approach used `first win` approach: seach continued until config found.
(separately for each config).

New approach will use 'merge' strategy, that means that we'll start from least
priority and will merge/override from configs with higher priority.

Each config contains hashtable (dictionary), and merge policy for those will
be:
- For new elements: add to hashtable
- For conflicting labels (keys) - override

New lookup rules (for images, test/upload follow the same pattern):
- `/etc/dibctl/images.yaml`
- `/etc/dibctl/images.d/*.yaml` (alphabetical order)
- `./dibctl/images.yaml`
- `./dibctl/images.d/*.yaml` (alphabetical order)
- `./images.yaml`
- `./images.d/*.yaml` (alphabetical order)

If user uses --images-config it will be used without searching other options.

Each entry in configuration files will have a separate validation
(big changes in validate sequence).

When element is overrided there going to be notification of override.

Refactoring process
===================

* create `read_validate_and_merge_config` function
* Change `read_and_validate_config` function to use it.
* change `set_conf_name` info discovery code (yield configs)
* Change schema and the moment of validation.
[somewhere in between] Change validate command to work on per-config basis
* Update documentation
* Create test cases for doctests
* Create at least one or two cases with superseeding

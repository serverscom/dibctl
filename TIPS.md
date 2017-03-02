How to debug images
-------------------

There are few moments when you find your image does not work. It's normal, and fixing it is a way to
make image works.

This file describes few debugging techniques for different types of failures.

Instance can't spawn
====================
1. Check if you have your own `OS_*` credentials in shell environment. They override
test.yaml/upload.yaml settings.
2. Check if you can spawn instance with same settings.

Instance spawns but become ERROR
================================

This is your Openstack issue. Check logs. Often this is 'No valid hosts found'.
Check if you are using proper flavor, availability\_zone (if you use them).

One of possible mistakes: specified 'net-id' network is full and there are no
free IP left.

Instance become active but there is no connection
=================================================
1. Enable devuser in the `dib.elements` section for image config
2. Set user, password and passwordless sudo (in the `dib.environment_variables`):
```
      DIB_DEV_USER_PWDLESS_SUDO: yes
      DIB_DEV_USER_USERNAME: dibdebug
      DIB_DEV_USER_PASSWORD: joj0quilUst
```
3. Rebuild image
4. Repeat test with --keep-failed-instance

It will fail again, but now you can log into instance via console and see why
it didn't recieve IP (or have trouble with SSH).

(!) Do not forget to remove devuser element and rebuild image after you done, otherwise
your clients/users would be really upset to find unknown user with password and sudo
in their systems.

Common reasons:
1. No cloud-init or no proper data-source for cloud-init.
2. Security groups (which prevents incoming connection by default)
3. Incorrect networks (local network instead of 'internet')
4. Wrong port settings
5. `wait_for_port` timeout is too short (common mistake for baremetal instances - they usually take more time to boot)

Instance failing tests
======================

Use `--shell` option to get shell to failed instance and inspect it.
If you want to keep instance after you log out of the shell, use `exit 42`.


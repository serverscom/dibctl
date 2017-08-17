HOWTO
-----

Add a new test
--------------
1. copy test.yaml.secret to test.yaml
2. copy upload.yaml.secret to upload.yaml
3. Add new test
4. Run `./clear_creds.py` script

Updating existing test
----------------------
1. copy test.yaml.secret to test.yaml
2. copy upload.yaml.secret to upload.yaml
3. Remove it's cassete from cassetes directory
4. Check your test instruction (in test docstring)
5. Update your configs
6. Run test
7. Run `./clear_creds.py` script


New users
---------
If you want just to run tests - use `py.test`.

If you want to update cassettes, then you need
a well configured Openstack. Some tests
require special policy.json - check docstrings
for details
1. Copy dibctl/test.yaml into test.yaml
2. Copy dibctl/upload.yaml into upload.yaml
3. Fill credentials with actual openstack credentials
   in both files
4. VERY CAREFULY read docstring for test. Some tests
   need to be updated in parallel, some require to
   update test code (uuids) after cassette run,
   some require manual preparation of installation
   (mostly rotate command).
4. Remove correponding cassettes
5. Run tests in a proper order (`py.test ... -k`)
6. Run `./clear\_creds.py`

Please be careful not to send your '.secret' files
into git.

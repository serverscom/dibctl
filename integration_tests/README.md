Here are integration tests. They record once actual interaction with actual
external servers (Openstack only at this moment) and reply it every time
test run.

Those interactions are written in 'cassettes' directory.

Other aspects of tests (pytest, shell, socket (`wait_for_port` function), time.sleep)
are mocked according to tested scenario.

How to record new interaction
-----------------------------
Please note, you need to be very careful about updating those tests:
- If you run tests against broken Openstack, those changes would be
recorded.
- Any passwords and tokens will be recorded as well. If you commit them
to git, they would become publicly available. I usually replace them in
cassettes after recording session before commit.

1. You can change record mode with special environment variable `VCR_RECORD_MODE`.
It can be:
- 'none' (default mode every test is run with).
- 'once'
- 'new\_episodes'
- 'all'

2. You need to remove (rename `integration_tests/*.yaml` files)

3. You need to place real configuration files into /etc/dibctl or
   in `integration_tests/dibctl` folder. By agreement fake configs are
   stored in `integration_tests`, and real one in `integration_tests/dibctl`
   and later should not be committed to git.

4. Update tests if needed (tests usually specify some uuids or image names).

5. Run tests from `integration_tests`. This will write/update cassettes
in `integration_tests/secret_cassettes` directory.

6. Copy cassettes to `integration_tests/secret_cassettes` and replace all
passwords and tokens.

7. Copy configs into `integration_tests` and replace passwords.

8. Bump 'expires' for token  in cassette(at leat for few years ahead, please),
otherwise tests would fail with message: CannotOverwriteExistingCassetteException: No match for the request (<Request (POST) https://auth.servers.nl01.cloud.servers.com:5000/v2.0/tokens>) was found. Can't overwrite existing cassette 

9. Change (fake passwords, etc) in cassettes and in fake configs should match.

10. Review changes before committing them!

Those modes are described in the pyVCR documentation:
https://vcrpy.readthedocs.io/en/latest/usage.html

Configuration
-------------
There is a bit of a problem with dibctl Configuration for those
tests. They should use actual configs, but at the same time
I don't want to disclose my passwords in git. At the same time
I want to have (fake) passwords in configuration to match (fake) passwords
in cassettes.

This done by using two sets of configuration files: 'fake' (public) are stored
in `integration_tests`, real one stored in 'integration_tests/dibctl'.
If VCR_RECORD_MODE is not none,
cassettes location changed into `secret_cassettes` (and this location,
together with integration_tests/*.yaml files is hidden by .gitignore).

After recording is done one need manually copy files (do not forget to
replace passwords and tokens with fake ones) from `secret_cassettes` into
`cassettes` and update configuration files in `integration_tests/dibctl`.

For now this is done manually, may be I write some script to fix this later.

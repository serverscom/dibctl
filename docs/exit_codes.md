Exit codes
----------
0 - everything is fine (success)
1 - generic unspecified error (if it annoy you, report bug for case and I'll add code)

10 - dibctl config not found or there is an error in config
11 - dibctl couldn't find requested item in configuration files (image, environment, etc)
12 - Not enough credentials in configuration file or environment to continue
18 - preprocessing during image upload has failed (exit code for cmdline is not zero)
20 - Authorization failure from keystone
50 - Glance return 'HTTPNotFoundError', which usually means that uuid in --use-existing-image is not found in Glance
60 - Nova returns BadRequest (unfortunately there is no way to distinct between codes)
70 - Instance become ERROR after creation
71 - Timeout while waiting for port (after instance become ACTIVE).
80 - Some tests have failed.

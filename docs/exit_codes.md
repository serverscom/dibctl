Exit codes
----------
0 - everything fine (success)
1 - generic unspecified error (if it annoy you, report bug for case and I'll add code)

10 - dibctl config not found or there is an error in config
11 - dibctl couldn't find requested item in configuration files (image, environment, etc)
12 - There is not enough information to connect to openstack (there is no login/password neither in configs nor environment variables).
50 - Glance return 'HTTPNotFoundError', which usually means that uuid in --use-existing-image is not found in Glance
60 - Nova returns BadRequest (unfortunately there is no way to distinct between codes)
71 - Timeout while waiting for port (after instance become ACTIVE).

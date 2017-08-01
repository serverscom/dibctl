External commands
-------------------------

There was a request to add external test and upload
features into dibctl.

Dibctl is tightly linked with Openstack. Live images
for distributions couldn't be tested and uploaded
by means of openstack, but build process may be performed
by DIB. To unify build process it's convenient to
keep image description (environment variables, elements)
inside the configuration as Openstack Images.

## Proposed solution
Add full set of external commands:
- External build
- External test
- External upload

Each of them would be able to replace (add to in case of
  external_tests) native workflow with single external command.

### external build
external build will be called instead of dib. If there are
external build and dib sections, dib section would be called
first, and external_build later. This should allow to build
image by DIB, but tweak image later. This is slightly different
from preprocessing option for upload, as preprocessing should
be performed after tests. external_build should produce new
image which would require new tests.

External build may produce more then one artifact out of build
process, therefore, there should be section for artifact processing (see corresponding blueprint, there is none at
the moment of this blueprint creation).

### external_tests
External tests are applied alongside with normal 'tests'
section. As tests shouldn't modify original image,
order of execution is not important. For now I plan to execute
external tests prior to native, but this could change in the future.

External tests are executed consecutively, end rely on
return code. By default code 0 is 'success', and any other
return (exit) code is 'failure'. It's possible to change
expected exit code ranges, but I'll leave this function
unimplemented for now. (i.e. 0 is 'ok', any other is 'bad').

Both external_build and external_tests are placed inside
image.yaml (external_tests does not need for test_environment).

### external_upload
External upload is very different from tests and build,
as one upload excludes other (If someone wants to upload
image to more then one region two calls of dibctl with different region names should be used).
This would require additional check into config load
section.

Preprocessing would happen for both types of upload before
upload itself.

## Interpolation

All cmdlines for all three external commands will be
interpolated with list of variables (not defined yet) in
the same way as cmdline for preprocessing.

Note: if preprocessing was performed, it will change
output_filename variable to a new name (for external_upload).

## Implementation details
1. Add options into configuration files.
2. Refactor interpolation code away from 'preprocess' module.
3. Create a generic 'external_commands' module to handle
   preprocess, external_build, external_tests and external_upload.
4. Create stable set of variables and rules for their modification after interpolation.
5. Make current dib call conditional without fail (if no dib section)
5. Add external_build code after dib processing
6. Made existing tests conditional (without fail)
7. Add special handling for '--keep*' options
8. Add special handling for 'shell' command
9. Add external_tests code after normal tests.
10. Add external_upload code into upload command.
11. Incorporate changes into user documentation

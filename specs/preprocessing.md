# Conversion before upload

We need some way to perform conversion of images prior upload into some regions.

## Configuration details

There is a new section in upload.yaml, with name 'preprocessing'.
It is similar to dib section for images.yaml and describes how to convert.
It can contain few variables:
- cmdline - contains command line with substitutions, using .format() function of python.
  (I need to think about explicit list of variables for substitution to avoid chaos).
- input\_filename - name of file before processing
- output\_filename - name of file after processing
- use\_existing - use file with output\_name if it is exist. (if use\_existing is false, existing file will be removed and processing performend as mandatory stage)
- delete\_processed\_after\_upload - self-descripting.

Variables for substitution:

- 'input\_filename'
- 'output\_filename'
- 'container\_format'
- 'disk\_format'

## Implementation  details
If there is a preprocessing section, it will be used before upload.
Module (akin to dib.py) for calling and processing errors.

Need to take in account caching and changes in output\_name.


## PROBLEM

As we change format we need to change upload options for image. I think we need to add glance section and use smart merge (with priority from upload section) to allow
overrides in image properties (especially, format).

## Format
Now format is hardcoreded, so we need to have format specs in glance section. Normally it should be in image, but can be overriden by preprocessing.
add new variables `disk_format` and `container_format` into glance section

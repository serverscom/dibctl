Rotate feautre has been planned from very start but I have no time to deal with it.

# Feautre description
When new image is uploaded, images with same name are marked as 'obsolete' by using a name prefix
("Obsolete ") and adding meta 'obsolete' to image.

We do this to keep images available until all instances which had been started from this image, finally,
have been removed or reubilded from other images. (Reason why we do this is too complicated, it is
related to '\_base' thing in nova-compute and a way how instances migrages)

To get list of all instances which uses given image we need escalated priveleges (admin priveleges)
as we need to look to other tenants instances list.

Escalated priveleges is a main reason why rotate is separate command from 'upload', as we can happily
upload and mark old image obsolete without peeking in other tenants instances list.

# Workflow
I see two ways to use rotate command:
- administrative console (dibctl rotate regionname), where command is run by operator with
  own set of OS\_\* environemnt variables.
- special job in Jenkins where those credentials are passed in secure manner (more secure than
  default login/password for image upload).

# How it works
1. Get all instance (nova list --all)
2. Get all obsolete images (images with obsolete meta, name is ignored)
3. Filter images such there is instance with 'base\_image\_ref' pointing to it.
4. Remove all such images

# Command line options
--dry-run should just print candidates for removal without actual deletion.


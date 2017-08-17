#!/usr/bin/python
'''
    This script cleanup credentials:
    - replaces passwords with word 'password'
    - replaces usernames with name 'username'

    It cleanup test.yaml and upload.yaml files.

    Non cleaned files (originals) are moved to .secret:
    - test.yaml -> test.yaml.secret
    - upload.yaml -> upload.yaml.secret

    Cleared copies stored in dibctl:
    - dibctl/test.yaml
    - dibctl/upload.yaml

    Addtitionally it checks all cassetess for found passwords
    and usernames in all cassettes. They shouldn't be there.
'''
import yaml
import os

CFG_LIST = ('test.yaml', 'upload.yaml')
pw_replacements = []
un_replacements = []
CASSETTES_LOCATION = 'cassettes'
PUBLIC_CONFIG_LOCATION = 'dibctl'

for cfgname in CFG_LIST:

    obj = yaml.load(open(cfgname, 'r'))

    for e in obj:
        if 'username' in obj[e]['keystone']:
            un_replacements.append(obj[e]['keystone']['username'])
            obj[e]['keystone']['username'] = "username"

        if 'password' in obj[e]['keystone']:
            pw_replacements.append(obj[e]['keystone']['password'])
            obj[e]['keystone']['password'] = "password"
        if 'tenant_name' in obj[e]['keystone']:
            obj[e]['keystone']['tenant_name'] = "pyvcr"
    open(os.path.join(PUBLIC_CONFIG_LOCATION, cfgname), 'w').write(
        yaml.dump(obj)
    )
    os.rename(cfgname, cfgname + '.secret')
print("Cleared passwords: %s\nCleared usernames: %s" % (
    pw_replacements,
    un_replacements
))


def check_location(location, pw_list):
    for f in os.listdir(location):
        path = os.path.join(location, f)
        cassette = open(path, 'r').read()
        for item in pw_list:
            if cassette.find(item) != -1:
                print("CRITICAL!!!! Found password %s in %s" % (
                    item, path
                ))


check_location(CASSETTES_LOCATION, pw_replacements)
check_location(PUBLIC_CONFIG_LOCATION, pw_replacements)

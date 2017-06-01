#!/usr/bin/python
import sys
import yaml
import os

in_name = sys.argv[1]
out_name = sys.argv[2]
cassette = sys.argv[3]
pw_replacements = []
un_replacements = []

obj = yaml.load(file(in_name, 'r'))

for e in obj:
    if 'username' in obj[e]['keystone']:
        un_replacements.append(obj[e]['keystone']['username'])
        obj[e]['keystone']['username'] = "username"
    
    if 'password' in obj[e]['keystone']:
        pw_replacements.append(obj[e]['keystone']['password'])
        obj[e]['keystone']['password'] = "password"

file(out_name, 'w').write(yaml.dump(obj))

path = cassette
rd = file(path, 'r').read()
for item in pw_replacements:
    new_data = rd.replace(item, 'password', 99999)
for item in un_replacements:
    new_data = new_data.replace(item, 'username', 99999)
os.rename(path, path + '.old')
file(path, 'w').write(new_data)

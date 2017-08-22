#!/usr/bin/python
import os
import yaml
import jsonschema

'''Config support for dibctl'''


class ConfigError(ValueError):
    pass


class ConfigNotFound(ConfigError):
    pass


class InvaidConfigError(ConfigError):
    pass


class NotFoundInConfigError(KeyError):
    pass


SCHEMA_UUID = {
    "type": "string",
    "pattern": "^[a-fA-F0-9]{8}-"
               "[a-fA-F0-9]{4}-"
               "[a-fA-F0-9]{4}-"
               "[a-fA-F0-9]{4}-"
               "[a-fA-F0-9]{12}$"
}
SCHEMA_TIMEOUT = {'type': 'integer', "minimum": 0}
SCHEMA_PORT = {'type': 'integer', 'minimum': 1, 'maximum': 65535}
SCHEMA_PATH = {'type': 'string', 'pattern': '^(/)?([^/\0]+(/)?)+$'}
SCHEMA_KEYSTONE = {}
SCHEMA_GLANCE = {
    "type": "object",
    "properties": {
        'api_version': {
            'type': 'integer',
            'minimum': 1,
            'maximum': 1  # PIN to version 1. Remove when v2 is introduced
        },
        "name": {"type": "string"},
        "upload_timeout": SCHEMA_TIMEOUT,
        "properties": {  # it's a name, 'properties'
            "type": "object"
        },
        "container_format": {'type': 'string'},
        "disk_format": {'type': 'string'},
        "endpoint": {"type": "string"},
        "public": {"type": "boolean"},
        "min_disk": {
            "type": "integer",
            "minimum": 0
        },
        "min_ram": {
            "type": "integer",
            "minimum": 0
        },
        "protected": {"type": "boolean"}
    },
    "additionalProperties": False
    # "required": ["name"]  # TODO reintroduce it back
}
SCHEMA_KEYSTONE = {
    'type': 'object',
    'properties': {
        'api_version': {
            'type': 'integer',
            'minimum': 2,
            'maximum': 3
        },
        'username': {'type': 'string'},
        'user': {'type': 'string'},
        'os_username': {'type': 'string'},
        'password': {'type': 'string'},
        'os_password': {'type': 'string'},
        'pass': {'type': 'string'},
        'tenant': {'type': 'string'},
        'tenant_name': {'type': 'string'},
        'os_tenant_name': {'type': 'string'},
        'project': {'type': 'string'},
        'project_name': {'type': 'string'},
        'os_project': {'type': 'string'},
        'os_project_name': {'type': 'string'},
        'url': {'type': 'string'},
        'auth_url': {'type': 'string'},
        'os_auth_url': {'type': 'string'},
        'user_domain': {'type': 'string'},
        'user_domain_id': {'type': 'string'},
        'tenant_domain': {'type': 'string'},
        'tenant_domain_id': {'type': 'string'},
        'project_domain_id': {'type': 'string'},
        'project_domain': {'type': 'string'}
    },
    "additionalProperties": False
}
SCHEMA_VERSION = {
    'type': 'string',
    'pattern': '\d+\.\d+\.\d+'
}
SCHEMA_EXTERNAL_COMMAND = {
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'cmdline': {'type': 'string'}
        },
        'required': ['cmdline']
    }

}


class Config(object):

    DEFAULT_CONFIG_NAME = None  # should be overriden in subclasses
    CONFIG_SEARCH_PATH = ["./", "./dibctl/", "/etc/dibctl/"]
    CONF_D_NAME = None   # should be overriden in subclasses
    D_SUFFIX = '.yaml'

    SCHEMA = {  # each subclass should provide own schema
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "minItem": 1
    }

    def __init__(self, mock_config, filename=None):
        '''
            This class shound't be called directly
            in actual code, but may be used as
            mock for configs without need to 'read' files
        '''
        self.config = mock_config
        self.config_file = filename
        self.config_list = [filename]

    def common_init(self, config_file=None):
        self.config_file = self.set_conf_name(config_file)
        print("Using %s" % self.config_file)
        self.config = self.read_and_validate_config(self.config_file)

    def merge_config_snippet(self, snippet, snippet_filename):
        for key in snippet:
            if key in self.config:
                print("Warning, %s redefines %s" % (snippet_filename, snippet))
            self.config[key] = snippet[key]
        print("%s is merged %s elememnts" % (snippet_filename, len(snippet)))

    def add_config(self, config_filename):
        '''
            Merge new piece of config from file into existing config
        '''
        snippet_content = yaml.load(open(config_filename), 'r')
        try:
            jsonschema.validate(snippet_content, self.ELEMENT_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            error_message = "There is an error in the file '%s': %s" % (
                config_filename, e.message
            )
            raise InvaidConfigError(error_message)
        self.config_list.append(config_filename)

    def gather_snippets(self, directory):
        content = [os.path.join(directory, f) for f in os.listdir(directory)]
        files = filter(os.path.isfile, content)
        files.sort()
        return files

    def find_all_configs(self):
        for basepath in reversed(self.CONFIG_SEARCH_PATH):  # FIX THIS AFTER REFACTORING !!!!
            candidate = os.path.join(basepath, self.DEFAULT_CONFIG_NAME)
            if os.path.isfile(candidate):
                yield candidate
            dot_d_dir = os.path.join(basepath, self.CONF_D_NAME)
            if os.path.isdir(dot_d_dir):
                for snippet in self.gather_snippets(dot_d_dir):
                    yield snippet

    def read_and_validate_config(self, name):
        content = yaml.load(open(name, "r"))
        try:
            jsonschema.validate(content, self.SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            error_message = "There is an error in the file '%s': %s" % (
                name, e.message
            )
            raise InvaidConfigError(error_message)
        return content

    def set_conf_name(self, forced_name):
        if forced_name:
            if os.path.isfile(forced_name):
                    return forced_name
            else:
                raise ConfigNotFound("%s is not a config file" % forced_name)
        for location in self.CONFIG_SEARCH_PATH:
            candidate = os.path.join(location, self.DEFAULT_CONFIG_NAME)
            if os.path.isfile(candidate):
                return candidate

        raise ConfigNotFound("Unable to file %s in %s" % (
            self.DEFAULT_CONFIG_NAME, ", ".join(self.CONFIG_SEARCH_PATH))
        )

    def get(self, label, default_value=None):
        path = label.split('.')
        position = self.config
        for element in path[:-1]:
            position = position.get(element, {})
        retval = position.get(path[-1], default_value)
        if type(retval) == dict:
            return Config(retval, self.config_file)
        else:
            return retval

    def __getitem__(self, label):
        try:
            path = label.split('.')
            position = self.config
            for element in path[:-1]:
                position = position[element]
            retval = position[path[-1]]
            if type(retval) is dict:
                return Config(retval, self.config_file)
            else:
                return retval
        except KeyError:
            raise NotFoundInConfigError(
                "Unable to find '%s' in %s" % (label, self.config_file)
            )

    def items(self):
        return self.config.items()

    def __iter__(self):
        return self.config.iteritems()

    def iteritems(self):
        return self.config.iteritems()

    def __contains__(self, key):
        try:
            self.__getitem__(key)
            return True
        except NotFoundInConfigError:
            return False

    def __eq__(self, item):
        return self.config == item

    def __str__(self):
        return str(self.config)

    def __repr__(self):
        return "Config(" + repr(self.config) + ")"

    def __nonzero__(self):
        return bool(self.config)

    def __len__(self):
        return len(self.config)


class ImageConfig(Config):

    DEFAULT_CONFIG_NAME = "images.yaml"
    CONF_D_NAME = 'images.d'
    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "patternProperties": {
            ".+": {
                "type": "object",
                "properties": {
                    "filename": SCHEMA_PATH,
                    "dib": {
                        "type": "object",
                        "properties": {
                            "min_version": SCHEMA_VERSION,
                            "max_version": SCHEMA_VERSION,
                            "environment_variables": {
                                "type": "object"
                            },
                            "elements": {
                                "type": "array",
                                "uniqueItems": True,
                                "items": {
                                    "type": "string"
                                },
                                "minItems": 1
                            },
                            'cli_options': {
                              'type': 'array',
                              'uniqueItems': True,
                              "items": {
                                  "type": "string"
                              },
                              "minItems": 1
                            }

                        },
                        "required": ["elements"],
                        "additionalProperties": False
                    },
                    "glance": SCHEMA_GLANCE,
                    "nova": {
                        "type": "object",
                        "properties": {
                            "create_timeout": SCHEMA_TIMEOUT,
                            "active_timeout": SCHEMA_TIMEOUT,
                            "keypair_timeout": SCHEMA_TIMEOUT,
                            "cleanup_timeout": SCHEMA_TIMEOUT
                        },
                        "additionalProperties": False
                    },
                    "tests": {
                        "type": "object",
                        "properties": {
                            "ssh": {
                                "type": "object",
                                "properties": {
                                    "username": {"type": "string"},
                                    "port": SCHEMA_PORT
                                },
                                "additionalProperties": False,
                                "required": ["username"]
                            },
                            "wait_for_port": SCHEMA_PORT,
                            "port_wait_timeout": {"type": "number"},
                            "environment_name": {"type": "string"},
                            "environment_variables": {"type": "object"},
                            "tests_list": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "shell": SCHEMA_PATH,
                                        "pytest": SCHEMA_PATH,
                                        "timeout": SCHEMA_TIMEOUT
                                    },
                                    "additionalProperties": False
                                }
                            }
                        }
                    },
                    'external_tests': SCHEMA_EXTERNAL_COMMAND,
                    "external_build": SCHEMA_EXTERNAL_COMMAND
                },
                "required": ["filename"]
            }
        }
    }

    def __init__(self, config_file=None, override_filename=None):
        self.common_init(config_file)
        if override_filename:
            for img_key in self.config:
                self.config[img_key].update(filename=override_filename)


class EnvConfig(Config):
    def __init__(self, config_file=None):
        self.common_init(config_file)


class TestEnvConfig(EnvConfig):
    DEFAULT_CONFIG_NAME = "test.yaml"
    CONF_D_NAME = 'test.d'
    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "patternProperties": {
            ".+": {
                "type": "object",
                "properties": {
                    'keystone': SCHEMA_KEYSTONE,
                    'nova': {
                        'type': 'object',
                        'properties': {
                            # 'api_version': {"type": number}
                            'flavor': {"type": "string"},
                            'flavor_id': {"type": "string"},
                            "nics": {
                                "type": "array",
                                'minItems': 1,
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'net_id': SCHEMA_UUID,
                                        'fixed_ip': {'type': 'string'}
                                    },
                                    'required': ['net_id'],
                                    "additionalProperties": False
                                }
                            },
                            'main_nic_regexp': {'type': 'string'},
                            'config_drive': {'type': 'boolean'},
                            'availability_zone': {'type': 'string'},
                            "create_timeout": SCHEMA_TIMEOUT,
                            "active_timeout": SCHEMA_TIMEOUT,
                            "keypair_timeout": SCHEMA_TIMEOUT,
                            "cleanup_timeout": SCHEMA_TIMEOUT,
                            "userdata": {"type": "string"},
                            "userdata_file": SCHEMA_PATH
                        },
                        "additionalProperties": False,
                        'oneOf': [
                            {"required": ['flavor']},
                            {"required": ['flavor_id']}
                        ]
                    },
                    'glance': SCHEMA_GLANCE,
                    'neutron': {'type': 'object'},
                    'ssl_insecure': {'type': 'boolean'},
                    'ssl_ca_path': SCHEMA_PATH,
                    'disable_warnings': {'type': 'boolean'},
                    'tests': {
                        'type': 'object',
                        'properties': {
                            'port_wait_timeout': SCHEMA_TIMEOUT,
                            "environment_variables": {"type": "object"}
                        },
                        'additionalProperties': False
                    }
                },
                "required": ['keystone', 'nova'],
                "additionalProperties": False
            }
        }
    }


class UploadEnvConfig(EnvConfig):
    DEFAULT_CONFIG_NAME = "upload.yaml"
    CONF_D_NAME = 'upload.d'
    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "patternProperties": {
            ".+": {
                "type": "object",
                "properties": {
                    'keystone': SCHEMA_KEYSTONE,
                    'glance': SCHEMA_GLANCE,
                    'ssl_insecure': {'type': 'boolean'},
                    'ssl_ca_path': SCHEMA_PATH,
                    'disable_warnings': {'type': 'boolean'},
                    'preprocessing': {
                        'type': 'object',
                        'properties': {
                            'cmdline': {'type': 'string'},
                            'output_filename': {'type': 'string'},
                            'use_existing': {'type': 'boolean'},
                            'delete_processed_after_upload': {
                                'type': 'boolean'
                            }
                        },
                        'additionalProperties': False,
                        'required': ['cmdline', 'output_filename']
                    },
                    'external_upload': SCHEMA_EXTERNAL_COMMAND
                },

                "additionalProperties": False
            }
        }
    }


def get_max(config1, config2, path, default_value):
    value1 = config1.get(path, None)
    value2 = config2.get(path, None)
    guess = max(value1, value2)
    if guess is None:
        return default_value
    else:
        return guess

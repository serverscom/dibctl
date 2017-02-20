#!/usr/bin/python
import os
import yaml
import jsonschema

'''Config support for dibctl'''


class ConfigError(ValueError):
    pass


class ConfigNotFound(ConfigError):
    pass


class NotFoundInConfigError(ConfigError):
    pass


SCHEMA_TIMEOUT = {'type': 'integer', "minimum": 0}
SCHEMA_PORT = {'type': 'integer', 'minimum': 1, 'maximum': 65535}
SCHEMA_PATH = {'type': 'string'}
SCHEMA_KEYSTONE = {}
SCHEMA_GLANCE = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "upload_timeout": SCHEMA_TIMEOUT,
        "properties": {  # it's a name, 'properties'
            "type": "object"
        },
        "endpoint": {"type": "string"},
        "public": {"type": "boolean"}

    }
    # "required": ["name"]  # TODO reintroduce it back
}
SCHEMA_KEYSTONE = {
    'type': 'object',
    'properties': {
        'api_version': {
            'type': 'integer',
            'minimum': 2,
            'maximum': 3
        },  # add oneOf
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
        'tenant_domain_id': {'type': 'string'}
    }
}


class Config (object):

    DEFAULT_CONFIG_NAME = None  # should be overrided in subclasses
    CONFIG_SEARCH_PATH = ["./", "./dibctl/", "/etc/dibctl/"]

    SCHEMA = {  # each subclass should provide own schema
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "minItem": 1
    }

    def __init__(self, config_file=None, overrides={}):
        self.config_file = self.set_conf_name(config_file)
        print("Using %s" % self.config_file)
        self.config = self.read_and_validate_config(self.config_file)
        self._apply_overrides(**overrides)

    @staticmethod
    def append(d, key, value):
        if value:
            d[key] = value

    def _apply_overrides(self):
        raise TypeError("This method should not be called")

    def read_and_validate_config(self, name):
        content = yaml.load(open(name, "r"))
        jsonschema.validate(content, self.SCHEMA)
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

        raise ConfigNotFound("Unable to file %s in %s" % (self.DEFAULT_CONFIG_NAME, self.CONFIG_SEARCH_PATH))

    def get(self, label):
        try:
            obj = self.config[label]
        except KeyError:
            raise NotFoundInConfigError("Unable to find '%s' in %s" % (label, self.config_file))
        return obj


class ImageConfig(Config):

    DEFAULT_CONFIG_NAME = "images.yaml"  # TODO RENAME TO iamge.yaml
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
                            "environment_variables": {
                                "type": "object"
                            },
                            "elements": {
                                "type": "array",
                                "uniqueItems": True
                            }

                        },
                        "required": ["elements"]
                    },
                    "glance": SCHEMA_GLANCE,
                    "tests": {
                        "type": "object",
                        "properties": {
                            "ssh": {
                                "type": "object",
                                "properties": {
                                    "username": {"type": "string"},
                                    "port": SCHEMA_PORT
                                },
                                "required": ["username"]
                            },
                            "wait_for_port": SCHEMA_PORT,
                            "port_wait_timeout": {"type": "number"},
                            "environment_name": {"type": "string"},
                            "environment_variables": {"type": "object"},
                            "test_list": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "shell_runner": SCHEMA_PATH,
                                        "pytest_ruuner": SCHEMA_PATH,
                                        "timeout": SCHEMA_TIMEOUT
                                    }
                                }
                            }
                        }
                    },
                },
                "required": ["filename"]
            }
        }
    }

    def _apply_overrides(self, filename=None):
        if filename:
            for img_key in self.config:
                self.config[img_key].update(filename=filename)


# This class is not used by itself
class EnvConfig(Config):

    DEFAULT_CONFIG_NAME = "test-environments.yaml"

    def _apply_overrides(
        self,
        os_auth_url=None,
        os_tenant_name=None,
        os_username=None,
        os_password=None
    ):
        env_override = {}
        self.append(env_override, "os_password", os_password)
        self.append(env_override, "os_tenant_name", os_tenant_name)
        self.append(env_override, "os_username", os_username)
        self.append(env_override, "os_auth_url", os_auth_url)
        for env_key in self.config:
            self.config[env_key].update(env_override)


class TestEnvConfig(EnvConfig):
    DEFAULT_CONFIG_NAME = "test.yaml"
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
                            "nics": {
                                "type": "array",
                                'minItem': 1,
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'net-id': {'type': 'string'},
                                        'fixed-ip': {'type': 'string'}
                                    },
                                    'required': ['net-id']
                                }
                            },
                            'main_nic_regexp': {'type': 'string'}
                        }
                    },
                    'glance': SCHEMA_GLANCE,
                    'neutron': {'type': 'object'},

                },
                "required": ['keystone', 'nova']
            }
        }
    }


class UploadEnvConfig(EnvConfig):
    DEFAULT_CONFIG_NAME = "upload.yaml"
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
                    'ss_ca_path': SCHEMA_PATH
                },
                'required': ['keystone']
            }
        }
    }

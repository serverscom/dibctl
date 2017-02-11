#!/usr/bin/python
import os
import yaml
from jsonschema import validate

'''Config support for dibctl'''


class ConfigError(ValueError):
    pass


class ConfigNotFound(ConfigError):
    pass


class NotFoundInConfigError(ConfigError):
    pass


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
        validate(content, self.SCHEMA)
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
        "minItem": 1,
        "patternProperties": {
            ".+": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string"}
                }
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


class UploadEnvConfig(EnvConfig):
    DEFAULT_CONFIG_NAME = "upload.yaml"

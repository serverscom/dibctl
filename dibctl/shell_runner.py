import subprocess
import os
import sys
import itertools

ENV_PREFIX = 'DIBCTL'


class BadRunnerError(EnvironmentError):
    pass


def unwrap_config(prefix, config):
    'returns linear key-value list from a tree'
    return_value = {}
    if type(config) is dict:
        for key, value in config.iteritems():
            new_prefix = prefix + '_' + str(key).upper()
            return_value.update(unwrap_config(new_prefix, value))
    elif type(config) is list:
        for element in config:
            return_value.update(unwrap_config(prefix, element))
    elif config is None:
        pass  # do not add anything, return empty dict
    else:
        return_value = {prefix: str(config)}
    return return_value


def gather_tests(path):
    if os.path.isdir(path):
        filelist = [os.path.join(path, f) for f in os.listdir(path)]
        filelist.sort()
        all_files = map(gather_tests, filelist)
        return list(itertools.chain.from_iterable(filter(None, all_files)))
    elif os.path.isfile(path) and os.access(path, os.X_OK):
        return [path]
    else:
        return None


def run_shell_test(path, env):
    print("Running %s" % path)
    try:
        sys.stdout.flush()
        subprocess.check_call(path, stdout=sys.stdout, stderr=sys.stderr, env=env)
        return True
    except subprocess.CalledProcessError:
        return False


def runner(path, ssh, tos, vars, timeout_val, continue_on_fail):
    result = True
    tests = gather_tests(path)
    if tests is None:
        raise BadRunnerError('Path %s is not a test file or a dir' % path)
    config = dict(os.environ)
    config.update(unwrap_config(ENV_PREFIX, tos.get_env_config()))
    if ssh:
        config.update(ssh.env_vars('DIBCTL_'))
    config.update(unwrap_config(ENV_PREFIX, vars))
    for test in tests:
        test_successfull = run_shell_test(test, config)
        if test_successfull:
            print("Test %s succeeded" % test)
            continue
        elif continue_on_fail:
                print("Test %s failed, continue other tests" % test)
                result = False
                continue
        else:
            print("Test %s failed, skipping all other tests" % test)
            result = False
            break
    return result

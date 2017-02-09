import tempfile


class SSH(object):
    def __init__(self, ip, username, private_key, port=22):
        self.ip = ip
        self.username = username
        self.private_key = private_key
        self.port = port
        self.private_key_file = None

    def save_private_key(self):
        pass

    def wipe_private_key(self):
        pass

    def user_host_and_port(self):
        if self.port == 22:
            return self.username + '@' + self.ip
        else:
            return "{user}@{host}:{port}".format(
                user=self.username,
                host=self.ip,
                port=str(self.port)
            )

    def key_file(self):
        if not self.private_key_file:
            self.private_key_file = tempfile.NamedTemporaryFile(
                prefix='dibctl_key_',
            )
            self.private_key_file.write(self.private_key)
            self.private_key_file.flush()
        return self.private_key_file.name

    def command_line(self):
        command_line = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "UpdateHostKeys=no",
            "-o", "PasswordAuthentication=no",
            "-i", self.key_file(),
            self.user_host_and_port()
        ]

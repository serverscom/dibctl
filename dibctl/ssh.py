'''all stuff for ssh manipulation'''


class SSH(object):
    def __init__(self, ip, username, path_to_private_key, port=22):
        self.ip = ip
        self.username = username
        self.path_to_private_key = path_to_private_key
        self.port = port

    def user_host_and_port(self):
        if self.port == 22:
            return self.username + '@' + self.ip
        else:
            return "{user}@{host}:{port}".format(
                user=self.username,
                host=self.ip,
                port=str(self.port)
            )

    def command_line(self):
        command_line = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "UpdateHostKeys=no",
            "-o", "PasswordAuthentication=no",
            "-i", self.path_to_private_key,
            self.user_host_and_port()
        ]

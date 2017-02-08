'''all stuff for ssh manipulation'''


class SSH(object):
    def __init__(self, ip, username, path_to_private_key, port=22):
        self.ip = ip
        self.username = username
        self.path_to_private_key = path_to_private_key
        self.port = port

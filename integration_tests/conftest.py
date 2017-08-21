import logging
import vcr
import json
import pytest
import sys
import copy


class HappyVCR(object):

    def __init__(self):
        self.VCR = vcr.VCR(
            cassette_library_dir='cassettes/',
            record_mode='once',
            match_on=['uri', 'method', 'headers', 'body'],
            filter_headers=(
                'Content-Length', 'User-Agent',
                'Accept-Encoding', 'Connection', 'Accept'
            ),
            before_record_request=self.filter_request,
            before_record_response=self.filter_response
        )
        self.VCR.decode_compressed_response = True
        logging.basicConfig()
        vcr_log = logging.getLogger('vcr')
        vcr_log.setLevel(logging.INFO)
        ch = logging.FileHandler('/tmp/requests.log', mode='w')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        ch.setFormatter(formatter)
        ch.setLevel(logging.INFO)
        vcr_log.addHandler(ch)
        vcr_log.debug('Set up logging')
        self.log = vcr_log
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        ch.setFormatter(formatter)
        root.addHandler(ch)
        self.count = 0

    def filter_request(self, request):
        # if 'pytest-filtered' in request.headers:
        #     self.log.debug("repeated request to %s %s, ignoring" % (
        #         request.method,
        #         request.uri
        #     ))
        #     return request
        request = copy.deepcopy(request)
        request.add_header('pytest-filtered', 'true')
        self.log.debug("filter request: %s: %s, %s, %s" % (
            id(request), self.count, request.method, request.uri
        ))
        if 'X-Auth-Token' in request.headers:
            self.log.debug("old token %s" % request.headers['X-Auth-Token'])
            request.headers.pop('X-Auth-Token')
            self.log.debug('Consealing X-Auth-Token header in %s (%s)' % (
                request.uri, id(request)
            ))
        request.headers.pop('x-distribution', None)
        if 'tokens' in request.uri and request.method == 'POST':
            self.log.debug("%s: Token request detected", id(request))
            unsafe = json.loads(request.body)
            replacement = '{"tenantName": "pyvcr", ' + \
                '"passwordCredentials": ' + \
                '{"username": "username", "password": "password"}}'
            if 'auth' in unsafe:
                self.log.debug("old creds %s" % str(unsafe['auth']))
                unsafe['auth'] = replacement
                safe = unsafe
            request.body = json.dumps(safe)
            self.log.debug('Consealing request credentials in %s (%s)' % (
                request.uri, id(request)
            ))
        if 'images' in request.uri and request.method == 'POST':
            if len(request.body) > 256:
                self.log.debug("Body is too large (%s bytes), truncating" % (
                    len(request.body)))
                request.body = "'1f\r\nBody was too large, " + \
                    "truncated.\n\r\n0\r\n\r\n'"
        return request

    def filter_response(self, response):
        body = response['body']
        if 'string' in body:
            try:
                decoded_string = json.loads(body['string'])
            except:
                self.log.debug("non-json body, ignoring")
                return response
            if 'access' in decoded_string:
                access = copy.deepcopy(decoded_string['access'])
                if 'token' in access:
                    access['token']['expires'] = '2038-01-15T16:17:18Z'
                    self.log.debug("Patching token expiration date")
                    access['token']['id'] = 'consealed id'
                    self.log.debug("Consealing token id")
                    access['token']['tenant']['description'] = ''
                    self.log.debug("Consealing tenant description")
                    access['token']['tenant']['name'] = 'consealed name'
                    self.log.debug("Consealing tenant name")
                if 'user' in access:
                    access['user']['username'] = 'consealed username'
                    self.log.debug("Consealing username")
                    access['user']['username'] = 'consealed username'
                    self.log.debug("Consealing username")
                    access['user']['name'] = 'consealed name'
                    self.log.debug("Consealing user name")
                response['body']['string'] = json.dumps({'access': access})
            else:
                self.log.debug("no access section in the body, ignoring")
        return response


@pytest.fixture(scope="function")
def happy_vcr(request):
    vcr = HappyVCR()
    return vcr.VCR.use_cassette

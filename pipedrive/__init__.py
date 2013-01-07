from urllib import urlencode
import json

import requests

PIPEDRIVE_API_URL = "https://api.pipedrive.com/v1/"

class PipedriveError(Exception):
    def __init__(self, response):
        self.response = response
    def __str__(self):
        return self.response.get('error', 'No error provided')

class IncorrectLoginError(PipedriveError):
    pass

class Pipedrive(object):
    def _request(self, endpoint, data=None, method="get"):
        if not method in ('get', 'post', 'put', 'delete', 'options', 'headers'):
            raise

        request_action = getattr(requests, method)

        if not data: data = dict()

        if self.api_token:
            data.update({'api_token' : self.api_token})

        kwargs = dict()

        if data:
            if method in ('post', 'put',):
                kwargs.update({'data' : data})
            else:
                kwargs.update({'params' : data})

        response = request_action(PIPEDRIVE_API_URL + endpoint, **kwargs)

        return json.loads(response.text)

    def __init__(self, login, password = None):
        if password:
            response = self._request("/auth/login", {"login": login, "password": password})

            if 'error' in response:
                raise IncorrectLoginError(response)
            
            self.api_token = response['authorization'][0]['api_token']
        else:
            # Assume that login is actually the api token
            self.api_token = login

    def __getattr__(self, name):
        def wrapper(id=None, attribute=None, data=None):
            names = name.split('_')
            method = 'get'

            if names[0] in ('get', 'post', 'put', 'delete'):
                method = names[0]
                names = names[1:]

            if id:
                names.append(str(id))

            if attribute:
                names.append(str(attribute))

            response = self._request('/'.join(names), data, method)

            if 'error' in response:
                raise PipedriveError(response)

            return response
        return wrapper

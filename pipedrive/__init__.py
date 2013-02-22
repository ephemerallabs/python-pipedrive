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
    def _request(self, endpoint, params, data=None, method="get"):
        if not method in ('get', 'post', 'put', 'delete', 'options', 'headers'):
            raise

        request_action = getattr(requests, method)

        if not params: params = dict()

        if self.api_token:
            params.update({'api_token' : self.api_token})

        kwargs = dict()

        if data and method in ('post', 'put',):
            kwargs.update({'data' : data})

        response = request_action(PIPEDRIVE_API_URL + endpoint, params=params, **kwargs)

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
        def wrapper(id=None, attribute=None, data=None, params=None):
            names = name.split('_')
            method = 'get'

            if names[0] in ('get', 'post', 'put', 'delete'):
                method = names[0]
                names = names[1:]

            if id:
                names.append(str(id))

            if attribute:
                names.append(str(attribute))

            response = self._request('/'.join(names), params, data, method)

            if 'error' in response:
                raise PipedriveError(response)

            return response
        return wrapper

    def get_organization_data(self, organization_name):
        organization = self.organizations_find(params={'term' : organization_name})
        if not 'data' in organization:
            return None
        
        return organization['data'][0]

    def get_person_data(self, person_name):
        person = self.persons_find(params={'term' : person_name})
        if not 'data' in person:
            return None
        return person['data'][0]

    def get_pipeline_data(self, pipeline_name=None):
        pipeline = None
        pipelines = self.get_pipelines()

        if 'data' in pipelines:
            pipeline = pipelines['data'][0]

            if pipeline_name is not None:
                for pipe in pipelines['data']:
                    if pipe['name'] == pipeline_name:
                        pipeline = pipe
                        break

        return pipeline

    def get_stage_data(self, stage_name=None, pipeline_id=None):
        stage = None
        params = dict()
        if pipeline_id is not None:
            params['pipeline_id'] = pipeline_id
        stages = self.get_stages(params=params)
        if 'data' in stages:

            stage = stages['data'][0]
            if stage_name is not None:
                for st in stages['data']:
                    if st['name'] == stage_name:
                        stage = st
                        break
        return stage

    def add_deal(self, deal_name, prepared_data, pipeline_name, person_name, organization_name, stage_name=None):

        organization = self.get_organization_data(organization_name)
        person = self.get_person_data(person_name)
        pipeline = self.get_pipeline_data(pipeline_name)
        stage = self.get_stage_data(stage_name, pipeline_id=(pipeline['id'] if pipeline else None))

        if not organization or not person or not pipeline or not stage:
            return False

        pd_fields = self.get_dealFields()
        if not 'data' in pd_fields:
            return False

        pd_fields = pd_fields['data']

        field_pairs = dict()
        field_options = dict()
        field_names = prepared_data.keys()
        for field in pd_fields:
            if field['name'] in field_names:
                field_pairs[field['name']] = field['key']

                if 'options' in field and field['options']:
                    field_options[field['name']] = field['options']

        deal_data = {
            'title' : deal_name,
            'person_id' : person['id'],
            'org_id' : organization['id'],
            'stage_id' : stage['id'],
        }

        def get_option_id(options, value):
            for opt in options:
                if opt['label'] == value:
                    return opt['id']
            
            return None

        for key, field_key in field_pairs.items():
            if key in prepared_data:
                raw_val = prepared_data[key]
                if key in field_options:
                    if isinstance(raw_val, list):
                        value = [get_option_id(field_options[key], val_item) for val_item in raw_val]
                    else:
                        value = get_option_id(field_options[key], raw_val)
                else:
                    value = unicode(raw_val).encode("utf-8")

                deal_data[field_key] = value
            else:
                print key

        deal = self.post_deals(data=deal_data)

        if not 'error' in deal:
            return deal
        else:
            return False

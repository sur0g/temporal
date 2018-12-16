import argparse
import datetime
import re
import sys

import requests
from jira import JIRA
from urllib3.util import Url
from configparser import ConfigParser


def lazy_property(fn):
    attr_name = '_lazy_' + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)
    return _lazy_property


class Config:

    def __init__(self):
        self.parser = ConfigParser()
        self.parser.read('config.ini')

        self.url = self.parser.get('main', 'url')
        self.login = self.parser.get('main', 'login')
        self.password = self.parser.get('main', 'pass')

    def save(self):
        config = self.parser
        config.read('config.ini')
        if 'main' not in config:
            config.add_section('main')
        config.set('main', 'url', self.url)
        config.set('main', 'login', self.login)
        config.set('main', 'pass', self.password)
        with open('config.ini', 'w') as f:
            config.write(f)


class Jira(JIRA):
    def __init__(self):
        config = Config()
        self.url = config.url
        self.login = config.login
        self.password = config.password
        super().__init__(server=self.url, basic_auth=(self.login, self.password))

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value: str):
        if not re.match('https?.*', value):
            value = f'http://{value}'
        self._url = value


class Issue():
    def __init__(self, key=None):
        self._title = None
        self._account = None
        self.remote_data = None
        self._project = None
        self.title = ''
        self.connection = Jira()
        self._description = ''
        self.key = key

    @property
    def project(self):
        return self._project

    @project.setter
    def project(self, value: str):
        self._project = self.connection.project(value.upper())
        response = requests.get(
            f'{self.connection.url}/rest/tempo-accounts/1/account/search?tqlQuery=(project={self._project.id}+OR+project=GLOBAL)',
            auth=(self.connection.login, self.connection.password))
        self._account = response.json()['accounts'][0]

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value: str):
        if value:
            self.project = value.split('-')[0]
            self._key = value

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value: str):
        self._title = value if value else ''

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value: str):
        if value:
            self._description = value

    def __str__(self):
        return f'{self.key}: {self.title}'

    def retrieve(self):
        self.remote_data = self.connection.issue(self.key)
        self.project = self.remote_data.fields.project.key
        self.key = self.remote_data.key
        self.title = self.remote_data.fields.summary
        self.worklogs = self.remote_data.fields.worklog.worklogs
        self.description = self.remote_data.fields.description

    def create(self):
        account = requests.get(f'{self.connection.url}/rest/tempo-accounts/1/account/project/{self.project.id}',
                               auth=(self.connection.login, self.connection.password)).json()[0]
        data = {
            'project': self.project.key,
            'summary': self.title,
            'description': self.description,
            'issuetype': {'name': 'Задача'},
            # 'customfield_10009': {'set': {'id': str(account.get('id'))}},
            # 'customfield_10009': {'id': str(account.get('id'))},
            # 'customfield_10009': account,
            'reporter': {'name': self.connection.login},
            'customfield_10009': str(account.get('id')),
        }
        result = self.connection.create_issue(data)
        self._result = result.json()
        print(self._result)

    def delete(self):
        ...

    def log_work(self, seconds, description):
        ...


class Transition:
    def __init__(self, url, login, passw):
        self.url = url

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value: str):
        if not re.match('https?.*', value):
            value = f'http://{value}'
        self._url = Url(value)


def main(self, *arguments):
    import getopt
    options, arguments = getopt.getopt(arguments, '')
    for option, valeur in options:
        pass


if __name__ == '__main__':
    # transition(transition(*sys.argv[1:]))
    i = Issue('ban')
    i.title = 'Test title'
    i.description = 'Test description'
    # i.retrieve()
    # print(i)
    i.create()
# def main(self, *arguments):
#     import getopt
#     options, arguments = getopt.getopt(arguments, '')
#     for option, valeur in options:
#         pass
#
# run = Main()
# main = run.main
#
# if __name__ == '__main__':
#     import sys
#     main(*sys.argv[1:])

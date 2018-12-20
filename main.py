import datetime
import math
import re
from configparser import ConfigParser

import requests
from jira import JIRA
from urllib3.util import Url

from utils import Singleton


@Singleton
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


class Project:
    def __init__(self, key: str):
        self.key = key

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value):
        self._key = value


class Issue():
    def __init__(self, key=None):
        self._title = None
        self._account = None
        self.remote_data = None
        self._project = None
        self.title = ''
        self._description = ''
        self.key = key

    @property
    def connection(self):
        return Jira()

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
        self.reporter = self.remote_data.fields.reporter

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

    def log_work(self, seconds: int, description: str) -> dict:
        # Convert params to jira format
        days, seconds = divmod(seconds, 3600 * 8)
        hours, seconds = divmod(seconds, 3600)
        minutes = math.floor(seconds / 60)
        time_spent = f'{days}d {hours}h {minutes}m'
        time_start = datetime.datetime.now(datetime.timezone.utc).astimezone().strftime('%Y-%m-%dT%H:%M:%S.000%z')

        data = {
            "timeSpent": time_spent,
            "started": time_start,  # "2018-12-17T21:00:01.089+0000",
            "comment": description
        }
        response = requests.post(f'{self.connection.url}/rest/api/2/issue/{self.key}/worklog',
                                 auth=(self.connection.login, self.connection.password), json=data)
        print(response.json())
        return response.json()


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


class Worklog():
    dt_start: datetime.datetime
    comment: str
    issue: Issue
    latest_start: datetime.datetime

    # latest_start: datetime.datetime
    def __init__(self):
        self.worked = datetime.timedelta(0)
        self.dt_start = datetime.datetime.now(datetime.timezone.utc).astimezone()
        self.latest_start = None
        self.issue = None

    def start_pause(self):
        now = datetime.datetime.now(datetime.timezone.utc).astimezone()
        if self.latest_start:
            self.worked += now - self.latest_start
            self.latest_start = None
        else:
            self.latest_start = now

    @property
    def started(self):
        return bool(self.latest_start)

    @property
    def worked(self):
        if self.started:
            curr_timer = datetime.datetime.now(datetime.timezone.utc).astimezone() - self.latest_start
        else:
            curr_timer = datetime.timedelta(0)
        return self._worked + curr_timer

    @worked.setter
    def worked(self, value: (int, str, datetime.timedelta)):
        """Accepts integer (seconds), str (jira format 2h 57m) and timedelta"""
        if type(value) is int:
            self._worked = datetime.timedelta(seconds=value)
        elif type(value) is str:
            if not re.fullmatch(r'(\d+d)? ?(\d+h)? ?(\d+m)? ?(\d+s)?', value):
                raise ValueError('Incorrect format for the jira timedelta')
            days = re.findall(r'\d+(?=d)', value)[0]
            hours = re.findall(r'\d+(?=h)', value)[0]
            minutes = re.findall(r'\d+(?=m)', value)[0]
            seconds = re.findall(r'\d+(?=s)', value)[0]
            seconds += minutes * 60 + hours * 3600 + days * 8 * 3600
            self._worked = datetime.timedelta(seconds=seconds)
        elif type(value) is datetime.timedelta:
            self._worked = value

    @worked.deleter
    def worked(self):
        self.worked = datetime.timedelta(0)

    def upload(self):
        if self.worked:
            self.issue.log_work(self.worked.seconds, self.comment)


def main(self, *arguments):
    import getopt
    options, arguments = getopt.getopt(arguments, '')
    for option, value in options:
        pass


if __name__ == '__main__':
    # transition(transition(*sys.argv[1:]))
    i = Issue('dan-1300')
    # i.log_work(35415, 'Тесто ворклог')
    i.title = 'Test title'
    i.description = 'Test description'
    i.retrieve()
    print(i)

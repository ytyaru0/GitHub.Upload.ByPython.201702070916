#!python3
#encoding:utf-8
import subprocess
import shlex
import Data
import time
import pytz
import requests
import json
import datetime

class Command:
    def __init__(self, data):
        self.data = data

    def CreateRepository(self):
        self.__CreateLocalRepository()
        r = self.__CreateRemoteRepository()
        self.__InsertRemoteRepository(r)
    def AddCommitPush(self, commit_message):
        subprocess.call(shlex.split("git add ."))
        subprocess.call(shlex.split("git commit -m '{0}'".format(commit_message)))
        subprocess.call(shlex.split("git push origin master"))
        time.sleep(3)
        self.__InsertLanguages()

    def __CreateLocalRepository(self):
        subprocess.call(shlex.split("git init"))
        subprocess.call(shlex.split("git config --local user.name '{0}'".format(self.data.get_username())))
        subprocess.call(shlex.split("git config --local user.email '{0}'".format(self.data.get_mail_address())))
        subprocess.call(shlex.split("git remote add origin git@{0}:{1}/{2}.git".format(self.data.get_ssh_host(), self.data.get_username(), self.data.get_repo_name())))

    def __CreateRemoteRepository(self):
        url = 'https://api.github.com/user/repos'
        post_data = json.dumps({"name": self.data.get_repo_name(), "description": self.data.get_repo_description(), "homepage": self.data.get_repo_homepage()})
        headers={
            "Time-Zone": "Asia/Tokyo",
            "Authorization": "token {0}".format(self.data.get_access_token())
        }
        r = requests.post(url, data=post_data, headers=headers)
        print(r.text)
        time.sleep(3)
        return json.loads(r.text)

    def __InsertRemoteRepository(self, r):
        self.data.db_repo.begin()
        repo = self.data.db_repo['Repositories'].find_one(Name=r['name'])
        # Repositoriesテーブルに挿入する
        if None is repo:
            self.data.db_repo['Repositories'].insert(dict(
                IdOnGitHub=r['id'],
                Name=r['name'],
                Description=r['description'],
                Homepage=r['homepage'],
                CreatedAt=r['created_at'],
                PushedAt=r['pushed_at'],
                UpdatedAt=r['updated_at'],
                CheckedAt="{0:%Y-%m-%dT%H:%M:%SZ}".format(datetime.datetime.now(pytz.utc))
            ))
            repo = self.data.db_repo['Repositories'].find_one(Name=r['name'])
        # 何らかの原因でローカルDBに既存の場合はそのレコードを更新する
        else:
            self.data.db_repo['Repositories'].update(dict(
                IdOnGitHub=r['id'],
                Name=r['name'],
                Description=r['description'],
                Homepage=r['homepage'],
                CreatedAt=r['created_at'],
                PushedAt=r['pushed_at'],
                UpdatedAt=r['updated_at'],
                CheckedAt="{0:%Y-%m-%dT%H:%M:%SZ}".format(datetime.datetime.now(pytz.utc))
            ), ['Name'])

        # Countsテーブルに挿入する
        cnt = self.data.db_repo['Counts'].count(RepositoryId=repo['Id'])
        if 0 == cnt:
            self.data.db_repo['Counts'].insert(dict(
                RepositoryId=self.data.db_repo['Repositories'].find_one(Name=r['name'])['Id'],
                Forks=r['forks_count'],
                Stargazers=r['stargazers_count'],
                Watchers=r['watchers_count'],
                Issues=r['open_issues_count']
            ))
        # 何らかの原因でローカルDBに既存の場合はそのレコードを更新する
        else:
            self.data.db_repo['Counts'].update(dict(
                RepositoryId=repo['Id'],
                Forks=r['forks_count'],
                Stargazers=r['stargazers_count'],
                Watchers=r['watchers_count'],
                Issues=r['open_issues_count']
            ), ['RepositoryId'])
        self.data.db_repo.commit()

    def __InsertLanguages(self):
        url = 'https://api.github.com/repos/{0}/{1}/languages'.format(self.data.get_username(), self.data.get_repo_name())
        r = requests.get(url)
        if 300 <= r.status_code:
            print(r.status_code)
            print(r.text)
            raise Exception("HTTP Error {0}".format(r.status_code))
            return None
        else:
            print(r.text)

        self.data.db_repo.begin()
        repo_id = self.data.db_repo['Repositories'].find_one(Name=self.data.get_repo_name())['Id']
        self.data.db_repo['Languages'].delete(RepositoryId=repo_id)
        res = json.loads(r.text)
        for key in res.keys():
            self.data.db_repo['Languages'].insert(dict(
                RepositoryId=repo_id,
                Language=key,
                Size=res[key]
            ))
        self.data.db_repo.commit()


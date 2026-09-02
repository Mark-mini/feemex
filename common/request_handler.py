# _*_ coding:utf-8 _*_
__author__ = 'dino.j'

import requests
from config.userinfo import Info

class RequestHandler:
    def __init__(self, base_url=Info.ContractSpot.Url):
        self.base_url = base_url

    def post(self, path, headers=None, **kwargs):
        return requests.post(self.base_url + path, headers=headers, **kwargs)

    def get(self, path, headers=None, **kwargs):
        return requests.get(self.base_url + path, headers=headers, **kwargs)
# _*_ coding:utf-8 _*_
__author__ = 'dino.j'

import requests
import logging
import time
from config.userinfo import Info

# 初始化日志配置
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class UserAuth:


    @classmethod
    def login(cls, email=Info.ContractSpot.Email, password=Info.ContractSpot.Password):
        global resp_data
        url = Info.ContractSpot.Url
        path = "/fe-ex-api/v6/user/login_in"

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "DinoTestAgent"
        }
        body = {
            "geetest_challenge": "",
            "geetest_seccode": "",
            "geetest_validate": "",
            "verificationType": "2",
            "token": True,
            "nc": None,
            "mobileNumber": email,
            "loginPword": password
        }

        resp = requests.post(url + path, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if data.get("succ"):
            token = data["data"]["token"]
            confirm = "/fe-ex-api/user/confirm_login"
            confirm_body = {
                "token": token,
                "type": "google",
                "authCode": ""
            }

            for attempt in range(3):
                response = requests.post(url + confirm, json=confirm_body, headers=headers)
                resp_data = response.json()
                if resp_data.get("succ"):
                    return token
                else:
                    logging.warning(f"第 {attempt + 1} 次进入系统失败：{resp_data.get('message')}")
                    time.sleep(1)

            raise Exception(f"进入系统失败（重试3次后仍失败）：{resp_data.get('message')}")
        else:
            raise Exception(f"登录失败：{data.get('message')}")
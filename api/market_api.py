# _*_ coding:utf-8 _*_
__author__ = 'dino.j'

import allure
import requests
from common.utils import attach_request_response


def get_price_spot(symbol: str = "BTCUSDT") -> float:
    """
    获取市场-最新现货成交价格
    :param symbol: 现货交易对，如 BTCUSDT
    :return: 最新成交价格，保留两位小数
    """
    # path = "https://openapi.fameex.com/sapi/v1/ticker"  # OL
    path = "https://openapi.azmgb.com/sapi/v1/ticker"  # PRE
    params = {"symbol": symbol}
    headers = {}

    with allure.step(f"{path} 获取现货最新成交价格"):
        resp = requests.get(url=path, params=params)
        attach_request_response(headers=headers, body=params, response=resp)

    with allure.step("解析现货成交价响应"):
        assert resp.status_code == 200
        data = resp.json()
        price = round(float(data["last"]), 2)
        min_price = round(float(price * 0.8), 2)
        max_price = round(float(price * 1.2), 2)
        allure.attach(str(price), name=f"{symbol} 最新成交价", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(min_price), name=f"{symbol} 小于20%", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(max_price), name=f"{symbol} 大于20%", attachment_type=allure.attachment_type.TEXT)
        return price

def get_price_contract(contract_name: str = "E-BTC-USDT") -> float:
    """
    获取市场-最新合约成交价格
    :param contract_name: 合约名称，如 E-BTC-USDT
    :return: 最新成交价格，保留两位小数
        """
    # path = "https://futuresopenapi.fameex.com/fapi/v1/ticker"
    path = "https://futuresopenapi.azmgb.com/fapi/v1/ticker"
    params = {"contractName": contract_name}
    headers = {}

    with allure.step(f"{path} 获取合约最新成交价格"):
        resp = requests.get(url=path, params=params, headers=headers)
        attach_request_response(headers=headers, body=params, response=resp)

    with allure.step("解析合约成交价响应"):
        assert resp.status_code == 200
        data = resp.json()
        price = round(float(data["last"]), 2)
        allure.attach(str(price), name=f"{contract_name} contract_price", attachment_type=allure.attachment_type.TEXT)
        return price
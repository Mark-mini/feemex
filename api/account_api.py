# _*_ coding:utf-8 _*_
__author__ = 'dino.j'

import time
import allure
from common.utils import build_headers, attach_request_response

class AccountApi:
    def __init__(self, req, token):
        self.req = req
        self.token = token

    def get_spot_balance(self, coin: str = "USDT") -> float:
        """
        获取现货余额
        :param coin: 币种，默认是USDT
        :return: 返回 normal_balance 值
        """
        path = "/fe-ex-api/finance/v6/account_balance"
        headers = build_headers(self.token)
        body = {}

        with allure.step(f"{path} 发送 POST 请求，获取现货余额"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        with allure.step("解析现货余额响应"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["succ"] is True
            balance = data["data"]["allCoinMap"][coin]["normal_balance"]
            allure.attach(str(balance), name=f"{coin} normal_balance", attachment_type=allure.attachment_type.TEXT)
            return float(balance)

    def fetch_assets_list(self) -> dict:
        """
        通用方法：发送接口请求，获取合约资产信息，失败时最多重试3次
        :return: 返回 data 字段（包含 positionList、accountList）
        """
        path = "/fe-co-api/position/get_assets_list"
        headers = build_headers(self.token)
        body = {}

        with allure.step(f"{path} 发送 POST 请求，获取合约资产信息"):
            for attempt in range(1, 4):
                resp = self.req.post(path, json=body, headers=headers)
                attach_request_response(headers, body, resp)

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("succ") is True:
                        return data
                    else:
                        allure.attach(
                            str(data),
                            name=f"获取合约资产信息，第 {attempt} 次失败响应",
                            attachment_type=allure.attachment_type.TEXT
                        )
                else:
                    allure.attach(
                        f"HTTP {resp.status_code}",
                        name=f"获取合约资产信息，第 {attempt} 次异常状态码",
                        attachment_type=allure.attachment_type.TEXT
                    )

                if attempt < 3:
                    time.sleep(3)

            # 最终失败，抛出断言
            assert False, f"获取合约资产信息失败，重试 3 次仍未成功"


    def get_contract_balance(self) -> float:
        """
        获取合约钱包余额
        :return: 返回 totalAmount 值
        """
        data = self.fetch_assets_list()
        with allure.step("解析合约余额响应"):
            account_list = data.get("data", {}).get("accountList", [])
            wallet_balance = [pos["walletBalance"] for pos in account_list]
            assert wallet_balance, "accountList 中 wallet_balance 为空"
            allure.attach(str(wallet_balance[-1]), name="contract_walletBalance", attachment_type=allure.attachment_type.TEXT)
            return float(wallet_balance[-1])

    def get_contract_none(self) -> list:
        """
        获取所有持仓为空[]
        :return:
        """
        with allure.step("解析所有持仓响应，预期 空[]"):
            for i in range(3):
                data = self.fetch_assets_list()
                position_list = data.get("data", {}).get("positionList", [])
                if not position_list:
                    break
                else:
                    time.sleep(3)
            assert position_list == []

    def get_contract_id_with_retry(self) -> list:
        """
        获取合约仓位列表中的 contractId，支持重试
        :return: contractId
        """
        with (allure.step("解析所有持仓响应，预期 有值(contractId)")):
            time.sleep(3)  # 初始等待，确保仓位已创建
            max_retry = 3
            retry_interval = 3

            for i in range(max_retry):
                data = self.fetch_assets_list()
                position_list = data.get("data", {}).get("positionList", [])

                if position_list:
                    contract_ids = [pos["contractId"] for pos in position_list]
                    contract_id = contract_ids[-1]
                    allure.attach(
                        str(contract_id),
                        name="contract_ids",
                        attachment_type=allure.attachment_type.TEXT
                    )
                    return contract_id
                else:
                    time.sleep(retry_interval)

            # 最终未获取到仓位，断言失败
            assert position_list, "positionList 为空，未持有任何仓位"
            return None

    def get_position_with_sl_tp(self, target_income_usdt: float = 1.0, contract_multiplier: float = 0.0001) -> dict:
        """
        提取持仓信息并计算止盈止损价格
        :param target_income_usdt: 目标盈亏金额，默认 1 U
        :param contract_multiplier: 合约乘数，默认 0.0001
        :return: dict，包含 position_id、take_profit、stop_loss、open_avg_price、can_close_volume、contract_ids
        """
        data = self.fetch_assets_list()
        with allure.step("解析仓位信息并计算止盈止损"):
            position_list = data.get("data", {}).get("positionList", [])
            assert position_list, "未持有任何仓位（positionList 为空）"

            # 提取仓位关键字段
            pos = position_list[0]
            open_avg_price = float(pos.get("openAvgPrice", 0))
            can_close_volume = float(pos.get("canCloseVolume", 0))
            position_id = pos.get("id")

            # 止盈止损计算
            take_profit = open_avg_price + (target_income_usdt / contract_multiplier)
            stop_loss = open_avg_price - (target_income_usdt / contract_multiplier)

            allure.attach(
                f"""仓位信息：
                    - 开仓价: {open_avg_price}
                    - 可平仓量: {can_close_volume}
                    - 仓位ID: {position_id}
                    - 止盈价(+{target_income_usdt}U): {take_profit}
                    - 止损价(-{target_income_usdt}U): {stop_loss}
                """,
                name="仓位止盈止损计算结果",
                attachment_type=allure.attachment_type.TEXT
            )

            return {
                "position_id": position_id,
                "take_profit": take_profit,
                "stop_loss": stop_loss
            }

    def co_transfer(self, transfer_type: str, amount: float, coin: str = "USDT", email: str = ""):
        """
        合约划转接口封装：现货 ↔ 合约
        :param transfer_type: 划转类型，wallet_to_contract 或 contract_to_wallet
        :param amount: 划转金额
        :param coin: 币种，默认 USDT
        :param email: 用户邮箱，默认空
        :return: 接口响应 response
        """
        path = "/fe-ex-api/contract/co_transfer"
        headers = build_headers(self.token)
        body = {
            "transferType": transfer_type,
            "amount": amount,
            "coinSymbol": coin,
            "email": email
        }

        with allure.step(f"{path} 发送 POST 请求，划转 {amount} {coin}，方向：{transfer_type}"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)
            assert resp.status_code == 200
            data = resp.json()
            assert data["succ"] is True
            return data


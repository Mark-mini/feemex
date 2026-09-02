# _*_ coding:utf-8 _*_
__author__ = 'dino.j'
__author__ = 'markmo'
'''
2025-07-19 markmo 补充 triggerType 转参，增加第29、61行
'''

import json
import time
import allure
from common.utils import build_headers, attach_request_response

class ContractApi:
    def __init__(self, req, token):
        self.req = req
        self.token = token

    def create_contract_order(
            self,
            side: str = "BUY",
            open_type: str = "OPEN",
            contract_id: int = 1,
            order_unit: int = 0,
            price: str = "0",
            volume: int = 1,
            order_type: int = 1,
            is_condition_order: bool = False,
            trigger_price: str = "",
            triggerType : str = "0"    #markmo : 补充条件单类型传值
    ):
        """
        创建合约订单（只发送请求）
        :return: 响应对象 resp
        """
        path = "/fe-co-api/order/order_create"
        headers = build_headers(self.token)

        # 直接在方法内构造 body
        if open_type == "OPEN":
            body = {
                "side": side,
                "open": open_type,
                "orderUnit": order_unit,
                "expireTime": 14,
                "isOto": False,
                "isCheckLiq": 1,
                "isConditionOrder": is_condition_order,
                "contractId": contract_id,
                "positionType": 1,
                "price": price,
                "volume": volume,
                "leverageLevel": 20,
                "type": order_type,
                "stopLossType": 2,
                "takerProfitType": 2,
                "stopLossPrice": 0,
                "takerProfitPrice": 0,
                "triggerPrice": trigger_price,
                "stopLossTrigger": "",
                "takerProfitTrigger": "",
                "triggerType": triggerType  #markmo : 补充条件单类型传值
            }
        else:
            body = {
                "contractId": contract_id,
                "positionType": 1,
                "side": side,
                "leverageLevel": 20,
                "price": price,
                "volume": volume,
                "open": open_type,
                "type": order_type,
                "isConditionOrder": is_condition_order,
                "orderUnit": order_unit
            }

        with allure.step(
                f"{path} 创建合约{open_type}订单 side={side} type={order_type} orderUnit={order_unit} volume={volume}"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        return resp,body

    def parse_contract_order_response(self, resp, body) -> str:
        """
        解析合约下单响应
        :param resp: 响应对象
        :param body: 请求参数 body，主要用于判断是否是条件单
        :return: 订单ID（字符串）或 None
        """
        data = resp.json()
        assert resp.status_code == 200, f"HTTP状态码错误：{resp.status_code}"
        assert data.get("succ") is True, f"接口返回失败：{data}"

        data_field = data.get("data")
        if not isinstance(data_field, dict):
            raise Exception(f"接口返回 data 非预期内容：{data_field}")

        order_ids = data_field.get("ids")

        # 没有订单 ID 的情况
        if not order_ids:
            if body.get("isConditionOrder"):  # 是条件单，可以接受没有 ids
                allure.attach(json.dumps(data, iendent=2, ensure_ascii=False), name="条件单响应(无订单ID)",
                              attachment_type=allure.attachment_type.JSON)
                return None
            else:
                raise Exception(f"非条件单但未返回订单ID，响应内容：{data}")

        # 有订单 ID，正常返回
        order_id = order_ids[0] if isinstance(order_ids, list) else order_ids
        allure.attach(str(order_id), name="contract_order_id", attachment_type=allure.attachment_type.TEXT)
        return order_id

    def contract_order_response(self, max_retry=3, retry_interval=3, **order_kwargs) -> str:
        """
        合约下单并解析，带重试
        :param max_retry: 最大重试次数
        :param retry_interval: 重试等待时间
        :param order_kwargs: create_contract_order 所需参数
        :return: 订单ID 或 ""（条件单）
        """
        with allure.step("合约下单并解析响应（带重试）"):
            for i in range(max_retry):
                try:
                    resp,body = self.create_contract_order(**order_kwargs)
                    return self.parse_contract_order_response(resp,body)
                except Exception as e:
                    allure.attach(str(e), name=f"第{i + 1}次下单异常", attachment_type=allure.attachment_type.TEXT)
                    time.sleep(retry_interval)

            raise Exception(f"合约下单重试 {max_retry} 次均失败")

    def get_user_order_count(self) -> dict:
        """
        获取当前委托订单数量，包括普通单和条件单
        :return: dict，包含 orderCount 和 triggerOrderCount
        """
        path = "/fe-co-api/order/get_user_order_count"
        headers = build_headers(self.token)
        body = {}

        with allure.step(f"{path} 获取当前委托数量"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        with allure.step("解析响应"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["succ"] is True

            order_count = data["data"].get("orderCount", 0)
            trigger_order_count = data["data"].get("triggerOrderCount", 0)

            allure.attach(f"普通单数: {order_count}, 条件单数: {trigger_order_count}", name="订单统计",
                          attachment_type=allure.attachment_type.TEXT)

            return {
                "orderCount": order_count,
                "triggerOrderCount": trigger_order_count
            }

    def cancel_contract_order(self,order_id: str = None,contract_id: int = 1,is_condition_order: bool = False) -> dict:
        """
        撤销合约订单（支持单个取消与全部取消）

        :param order_id: 订单ID（可为空，若为空则执行“全部取消”）
        :param contract_id: 合约ID（默认1）
        :param is_condition_order: 是否为条件单（默认 False）
        :return: 接口返回的响应数据 dict
        """
        path = "/fe-co-api/order/order_cancel"
        headers = build_headers(self.token)

        # 构造 body，兼容单个取消 与 批量取消
        body = {
            "isConditionOrder": is_condition_order
        }
        if order_id:
            body["orderId"] = order_id
            body["contractId"] = contract_id
            cancel_type = "单个订单"
        else:
            cancel_type = "全部订单"

        with allure.step(f"{path} 撤销合约订单（类型：{cancel_type}）"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        with allure.step("验证撤单响应结果"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["succ"] is True
            return data

    def get_market_prices(self, contract_id: int = 1) -> dict:
        """
        获取合约市场信息（原始指数价 & 标签价）
        :param contract_id: 合约ID
        :return: dict，包含 index_price 和 tag_price
        """
        path = "/fe-co-api/common/public_market_info"
        headers = build_headers(self.token)
        body = {"contractId": contract_id}

        with allure.step(f"{path} 获取合约市场信息（指数价 & 标签价）"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        with allure.step("解析价格数据"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["succ"] is True

            index_price = float(data["data"]["indexPrice"])
            tag_price = float(data["data"]["tagPrice"])

            allure.attach(str(index_price), name="指数价", attachment_type=allure.attachment_type.TEXT)
            allure.attach(str(tag_price), name="标签价", attachment_type=allure.attachment_type.TEXT)

            return {
                "index_price": index_price,
                "tag_price": tag_price
            }

    def create_condition_order(self,position_id: int = None,sl_position_list: list = None,order_list: list = None) -> dict:
        """
        创建条件单（仓位止盈止损 / 普通止盈止损）
        两类：
        1. sl_position_list + position_id → 仓位止盈止损
        2. order_list → 普通止盈止损
        :return: 接口响应数据
        """
        path = "/fe-co-api/order/condition_create"
        headers = build_headers(self.token)

        body = {
            "contractId": 1,
            "positionType": 1,
            "leverageLevel": 20,
            "side": "SELL"
        }

        if sl_position_list and position_id:
            body["positionId"] = position_id
            body["slPositionList"] = sl_position_list
            mode = "仓位止盈止损"
        elif order_list:
            body["orderList"] = order_list
            mode = "普通止盈止损"
        else:
            raise ValueError("必须传入 sl_position_list + position_id 或 order_list")

        with allure.step(f"{path} 创建条件单（模式：{mode}）"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        with allure.step("验证响应"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["succ"] is True
            return data

    def close_all_positions(self, max_retry=3, retry_interval=3) -> dict:
        """
        合约一键平仓接口，支持失败重试
        :param max_retry: 最大重试次数
        :param retry_interval: 每次重试的间隔（秒）
        :return: 返回接口响应数据
        """
        path = "/fe-co-api/order/close_all_position"
        headers = build_headers(self.token)
        body = {}

        with allure.step(f"{path} 执行一键平仓请求"):
            for attempt in range(1, max_retry + 1):
                resp = self.req.post(path, json=body, headers=headers)
                attach_request_response(headers, body, resp)

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("succ") is True:
                        return data
                    else:
                        allure.attach(
                            str(data),
                            name=f"一键平仓第 {attempt} 次失败响应",
                            attachment_type=allure.attachment_type.TEXT
                        )
                else:
                    allure.attach(
                        f"HTTP {resp.status_code}",
                        name=f"一键平仓第 {attempt} 次异常状态码",
                        attachment_type=allure.attachment_type.TEXT
                    )

                if attempt < max_retry:
                    time.sleep(retry_interval)

            # 最终失败，抛出断言
            assert False, f"一键平仓失败，重试 {max_retry} 次仍未成功"



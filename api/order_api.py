# _*_ coding:utf-8 _*_
__author__ = 'dino.j'

import time
import allure
from common.utils import build_headers, attach_request_response


class OrderApi:
    def __init__(self, req, token):
        self.req = req
        self.token = token

    def create_spot_order(
            self, side: str = "BUY",
            volume: str = "50",
            symbol: str = "btcusdt",
            price: str = "",
            order_type: int = 2
    ) -> str:
        """
        创建现货订单（默认市价单买入）
        :param side: BUY or SELL
        :param volume: 数量
        :param symbol: 交易对
        :param price: 价格，限价单时必填
        :param order_type: 1 限价 2 市价
        :return: 返回订单ID
        """
        path = "/fe-ex-api/order/create"
        headers = build_headers(self.token)
        body = {
            "side": side,
            "price": price,
            "volume": volume,
            "symbol": symbol,
            "type": order_type,
            "uaTime": time.strftime('%y-%m-%d %H:%M:%S')
        }

        with allure.step(f"{path} 创建现货订单 side={side} symbol={symbol} type={order_type}"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        with allure.step("解析订单创建响应"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["succ"] is True
            order_id = data["data"][0]
            allure.attach(str(order_id), name="spot_order_id", attachment_type=allure.attachment_type.TEXT)
            return order_id

    def get_order_status(self, order_id: str, symbol: str = "") -> str:
        """
        查询现货历史委托，获取某个订单的状态
        :param order_id: 订单ID
        :param symbol: 可选，交易对
        :return: status_text 字段值（如：已成交、已取消、待成交）
        """
        path = "/fe-ex-api/order/entrust_history/new"
        headers = build_headers(self.token)
        body = {"page": 1, "pageSize": 20, "symbol": symbol}

        with allure.step(f"{path} 查询历史委托，order_id={order_id}"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        with allure.step("解析订单状态"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["succ"] is True

            order_list = data["data"]["orderList"]
            for order in order_list:
                if order["id"] == order_id:
                    status = order["status_text"]
                    allure.attach(status, name=f"订单 {order_id} 状态", attachment_type=allure.attachment_type.TEXT)
                    return status
            return None
            # raise AssertionError(f"未找到订单 ID 为 {order_id} 的记录")

    def cancel_order(self, order_id: str, symbol: str = "btcusdt") -> dict:
        """
        取消指定订单
        :param order_id: 订单 ID
        :param symbol: 交易对
        :return: 返回接口 data 内容
        """
        path = "/fe-ex-api/order/cancel"
        headers = build_headers(self.token)
        body = {
            "symbol": symbol,
            "orderId": order_id
        }

        with allure.step(f"{path} 发送取消订单请求 order_id={order_id}"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        with allure.step("验证取消响应"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["succ"] is True
            return data["data"]

    def cancel_order_all(self) -> dict:
        """
        取消指定订单
        :return: 返回接口 data 内容
        """
        path = "/fe-ex-api/order/cancel/all"
        headers = build_headers(self.token)
        body = {"symbol": None}

        with allure.step(f"{path} 发送取消全部订单请求"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        with allure.step("验证取消响应"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["succ"] is True
            return data["data"]

    def get_open_orders(self, symbol: str = "btcusdt") -> list:
        """
        获取当前挂单
        :param symbol: 交易对
        :return: 当前挂单列表
        """
        time.sleep(1)
        path = "/fe-ex-api/order/open_orders"
        headers = build_headers(self.token)
        body = {"symbol": symbol}

        with allure.step(f"{path} 获取当前挂单"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        with allure.step("解析挂单列表"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["succ"] is True
            return data["data"]

    def get_current_orders(self, page=1, page_size=10):
        """ 获取当前委托订单列表 """
        path = "/fe-ex-api/order/list/new/all"
        headers = build_headers(self.token)
        body = {
            "page": page,
            "pageSize": page_size
        }
        with allure.step(f"{path} 获取当前委托列表"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        with allure.step("解析当前委托列表"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["succ"] is True
            order_list = data.get("data", {}).get("orderList", [])
            ids = [order.get("id") for order in order_list if order.get("id")]
            return ids

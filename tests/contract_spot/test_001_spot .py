# _*_ coding:utf-8 _*_
__author__ = 'dino.j'

import random
import time
import unittest
import allure
from api.account_api import AccountApi
from api.order_api import OrderApi
from api.market_api import get_price_spot
from common.user_auth import UserAuth
from common.request_handler import RequestHandler

@allure.feature("现货交易")
class CaseSpot(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = UserAuth.login()
        cls.req = RequestHandler()

    @allure.story("test_001：市价单 - 买入(当前市场最优价)")
    def test_001_buy_order_create(self):
        account_api = AccountApi(req=self.req, token=self.token)
        order_api = OrderApi(req=self.req, token=self.token)

        with allure.step("step 1：买入前，获取现货USDT&BTC余额"):
            usdt_before = account_api.get_spot_balance(coin="USDT")
            btc_before  = account_api.get_spot_balance(coin="BTC")

        with allure.step("step 2：现货-市价单-买入"):
            order_id = order_api.create_spot_order(side="BUY", volume="50", symbol="btcusdt", order_type=2)

        with allure.step("step 3：历史委托,获取订单状态"):
            time.sleep(3)
            status = order_api.get_order_status(order_id=order_id, symbol="")

        if status is not None:
            with allure.step("step 4：买入后，获取现货USDT&BTC余额"):
                usdt_after = account_api.get_spot_balance(coin="USDT")
                btc_after = account_api.get_spot_balance(coin="BTC")

            if status != "已取消":
                with allure.step("step 5：订单已完成或部分完成，断言USDT&BTC余额变化"):
                    assert usdt_after < usdt_before
                    assert btc_after > btc_before
            else:
                with allure.step("step 5：订单已取消，断言USDT&BTC余额无变化"):
                    assert usdt_after == usdt_before
                    assert btc_after == btc_before

    @allure.story("test_002：市价单 - 卖出(当前市场最优价)")
    def test_002_sell_order_create(self):
        account_api = AccountApi(req=self.req, token=self.token)
        order_api = OrderApi(req=self.req, token=self.token)

        with allure.step("step 1：卖出前，获取现货USDT&BTC余额"):
            usdt_before = account_api.get_spot_balance(coin="USDT")
            btc_before = account_api.get_spot_balance(coin="BTC")

        with allure.step("step 2：现货-市价单-卖出"):
            order_id = order_api.create_spot_order(side="SELL", volume="0.00005", symbol="btcusdt", order_type=2)

        with allure.step("step 3：历史委托,获取订单状态"):
            time.sleep(3)
            status = order_api.get_order_status(order_id=order_id, symbol="")

        if status is not None:
            with allure.step("step 4：卖出后，获取现货USDT&BTC余额"):
                usdt_after = account_api.get_spot_balance(coin="USDT")
                btc_after = account_api.get_spot_balance(coin="BTC")

            if status != "已取消":
                with allure.step("step 5：断言USDT&BTC余额变化"):
                    assert usdt_after > usdt_before
                    assert btc_after < btc_before
            else:
                with allure.step("step 5：订单已取消，断言USDT&BTC余额无变化"):
                    assert usdt_after == usdt_before
                    assert btc_after == btc_before

    @allure.story("test_003：限价单 - 买入(低于最新价) - 单撤")
    def test_003_buy_order_create(self):
        account_api = AccountApi(req=self.req, token=self.token)
        order_api = OrderApi(req=self.req, token=self.token)

        with allure.step("step 1：买入前，获取现货USDT余额"):
            usdt_before = account_api.get_spot_balance(coin="USDT")

        with allure.step("step 2：现货-限价单买入"):
            price = round(float(get_price_spot() * random.uniform(0.97, 0.98)), 2)
            oid = order_api.create_spot_order(
                side="BUY", price=f"{price}",volume="0.00005", symbol="btcusdt", order_type=1
            )

        with allure.step("step 3：买入后，获取现货USDT余额"):
            time.sleep(2)
            usdt_after = account_api.get_spot_balance(coin="USDT")

        with allure.step("step 4：断言买入后余额变化，USDT减少"):
            assert usdt_after < usdt_before

        with allure.step("step 5：当前委托，获取委托订单列表"):
            ids = order_api.get_current_orders()

        with allure.step("step 6：断言买入订单号在委托订单列表"):
            assert oid in ids

        with allure.step("step 7：当前委托，撤单"):
            order_api.cancel_order(order_id=oid, symbol="btcusdt")

        with allure.step("step 8：撤单后，获取现货USDT余额"):
            time.sleep(2)
            usdt_cancel = account_api.get_spot_balance(coin="USDT")

        with allure.step("step 9：断言撤单后余额变化，USDT回到买入前"):
            assert usdt_cancel == usdt_before

    @allure.story("test_004：限价单 - 买入(低于最新价) - 全撤")
    def test_004_buy_order_create(self):
        account_api = AccountApi(req=self.req, token=self.token)
        order_api = OrderApi(req=self.req, token=self.token)

        with allure.step("step 1：买入前，获取现货USDT余额"):
            usdt_before = account_api.get_spot_balance(coin="USDT")

        with allure.step("step 2：现货-限价单-买入"):
            price = round(float(get_price_spot() * random.uniform(0.97, 0.98)), 2)
            oid = order_api.create_spot_order(
                side="BUY", price=f"{price}", volume="0.00005", symbol="btcusdt",order_type=1
            )

        with allure.step("step 3：买入后，获取现货USDT余额"):
            time.sleep(2)
            usdt_after = account_api.get_spot_balance(coin="USDT")

        with allure.step("step 4：断言买入后余额变化，USDT减少"):
            assert usdt_after < usdt_before

        with allure.step("step 5：当前委托，获取委托订单列表"):
            ids = order_api.get_current_orders()

        with allure.step("step 6：断言买入订单号在委托订单列表"):
            assert oid in ids

        with allure.step("step 7：当前委托，全撤"):
            order_api.cancel_order_all()

        with allure.step("step 8：撤单后，获取现货USDT余额"):
            time.sleep(2)
            usdt_cancel = account_api.get_spot_balance(coin="USDT")

        with allure.step("step 9：断言撤单后余额变化，USDT回到买入前"):
            assert usdt_cancel == usdt_before

    @allure.story("test_005：限价单 - 卖出(高于最新价) - 单撤")
    def test_005_sell_order_create(self):
        account_api = AccountApi(req=self.req, token=self.token)
        order_api = OrderApi(req=self.req, token=self.token)

        with allure.step("step 1：卖出前，获取现货BTC余额"):
            btc_before = account_api.get_spot_balance(coin="BTC")

        with allure.step("step 2：现货-限价单-卖出"):
            price = round(float(get_price_spot() * random.uniform(1.02, 1.03)), 2)
            oid = order_api.create_spot_order(
                side="SELL", price=f"{price}", volume="0.00005", symbol="btcusdt",order_type=1
            )

        with allure.step("step 3：卖出后，获取现货BTC余额"):
            time.sleep(2)
            btc_after = account_api.get_spot_balance(coin="BTC")

        with allure.step("step 4：断言卖出后余额变化，BTC"):
            assert btc_after < btc_before

        with allure.step("step 5：当前委托，获取委托订单列表"):
            ids = order_api.get_current_orders()

        with allure.step("step 6：断言卖出订单号在委托订单列表"):
            assert oid in ids

        with allure.step("step 7：当前委托，撤单"):
            order_api.cancel_order(order_id=oid, symbol="btcusdt")

        with allure.step("step 8：撤单后，获取现货BTC余额"):
            time.sleep(3)
            btc_cancel = account_api.get_spot_balance(coin="BTC")

        with allure.step("step 9：断言撤单后余额变化，BTC回到卖出前"):
            assert btc_cancel == btc_before

    @allure.story("test_006：限价单 - 卖出(高于最新价) - 全撤")
    def test_006_sell_order_create(self):
        account_api = AccountApi(req=self.req, token=self.token)
        order_api = OrderApi(req=self.req, token=self.token)

        with allure.step("step 1：卖出前，获取现货BTC余额"):
            btc_before = account_api.get_spot_balance(coin="BTC")

        with allure.step("step 2：现货-限价单-卖出"):
            price = round(float(get_price_spot() * random.uniform(1.02, 1.03)), 2)
            oid = order_api.create_spot_order(
                side="SELL", price=f"{price}", volume="0.00005", symbol="btcusdt", order_type=1
            )

        with allure.step("step 3：卖出后，获取现货BTC余额"):
            time.sleep(2)
            btc_after = account_api.get_spot_balance(coin="BTC")

        with allure.step("step 4：断言卖出后余额变化，BTC"):
            assert btc_after < btc_before

        with allure.step("step 5：当前委托，获取委托订单列表"):
            ids = order_api.get_current_orders()

        with allure.step("step 6：断言卖出订单号在委托订单列表"):
            assert oid in ids

        with allure.step("step 7：当前委托，全撤"):
            order_api.cancel_order_all()

        with allure.step("step 8：撤单后，获取现货BTC余额"):
            time.sleep(3)
            btc_cancel = account_api.get_spot_balance(coin="BTC")

        with allure.step("step 9：断言撤单后余额变化，BTC回到卖出前"):
            assert btc_cancel == btc_before

if __name__ == '__main__':
    unittest.main()

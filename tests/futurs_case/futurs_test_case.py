# _*_ coding:utf-8 _*_
__author__ = 'markmo'

import random
import time
import unittest
import allure
from api.account_api import AccountApi
from api.contract_api import ContractApi
from api.market_api import get_price_contract
from common.user_auth import UserAuth
from common.request_handler import RequestHandler

@allure.feature("合约交易")
class CaseSpot(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = UserAuth.login()
        cls.req = RequestHandler()

    @allure.story("test_001：开仓-条件单（限价）-开空》触发 ")
    def test_001_craete_order(self):
        futurs_api = ContractApi(req=self.req, token=self.token)
        # order_api = ContractApi(req=self.req, token=self.token)
        with allure.step("step 1 : 开空（BTC）触发价格 > 最新价下单"):
            price = get_price_contract()
            trigger_price = round(float(price * random.uniform(1.01, 1.02)), 2)
            futurs_api.contract_order_response(
                order_unit=0, price=trigger_price, volume=1, order_type=1, is_condition_order=True, trigger_price=trigger_price
            ,triggerType=3)

        with allure.step("step 2：合约-当前委托，获取条件单，断言条件单数>0"):
            time.sleep(3)
            order_stats = futurs_api.get_user_order_count()
            try:
                assert int(order_stats["triggerOrderCount"]) > 0
                print("✅ 条件单数量大于 0")
            except AssertionError as e:
                print(f"❌ 断言失败：{e}")
                raise
        # with allure.step("step 3：合约-当前委托-条件单，执行全部取消操作"):
        #     futurs_api.cancel_contract_order(is_condition_order=True)
        #
        # with allure.step("step 2：合约-当前委托，全部取消后，获取条件单，断言条件单数=0"):
        #     time.sleep(3)
        #     order_stats = futurs_api.get_user_order_count()
        #     assert int(order_stats["triggerOrderCount"]) == 0
if __name__ == '__main__':
    unittest.main()



'''
    # ----------------
    def test_021_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(数量BTC)触发价<最新价下单"):
            price = get_price_contract()
            trigger_price = round(float(price * random.uniform(0.97, 0.98)), 2)
            contract_api.contract_order_response(
                order_unit=0,price=trigger_price,volume=1,order_type=1, is_condition_order=True,trigger_price=trigger_price
            )

        with allure.step("step 2：合约-当前委托，获取条件单，断言条件单数>0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) > 0

        with allure.step("step 3：合约-当前委托-条件单，执行全部取消操作"):
            contract_api.cancel_contract_order(is_condition_order=True)

        with allure.step("step 2：合约-当前委托，全部取消后，获取条件单，断言条件单数=0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) == 0
'''
# _*_ coding:utf-8 _*_
__author__ = 'dino.j'
'''
20250721 mark
补充开仓入参-订单类型
'''
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
class CaseContract(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = UserAuth.login()
        cls.req = RequestHandler()
        time.sleep(3)

    def get_balances(self):
        """
        获取现货余额和合约钱包总余额，返回两个浮点数
        """
        api = AccountApi(req=self.req, token=self.token)
        spot = api.get_spot_balance("USDT")
        contract = api.get_contract_balance()
        return spot, contract

    @allure.story("test_001：划账：现货 → 合约")
    def test_001_wallet_to_contract(self):
        amount = random.randint(60, 100)

        with allure.step("step 1：划前 - 获取现货 & 合约余额"):
            spot_balance_01, contract_balance_01 = self.get_balances()

        with allure.step(f"step 2：划账 {amount}USDT，从现货 → 合约"):
            account_api = AccountApi(req=self.req, token=self.token)
            account_api.co_transfer(transfer_type="wallet_to_contract", amount=amount)

        with allure.step("step 3：划后 - 获取现货 & 合约余额"):
            time.sleep(2)
            spot_balance_02, contract_balance_02 = self.get_balances()

        with allure.step("step 4：断言余额变化"):
            assert  spot_balance_02 == spot_balance_01 - amount
            assert  contract_balance_02 == contract_balance_01 + amount

    @allure.story("test_002：划账：合约 → 现货")
    def test_002_contract_to_wallet(self):
        amount = random.randint(50, 80)

        with allure.step("step 1：划前 - 获取现货 & 合约余额"):
            spot_balance_01, contract_balance_01 = self.get_balances()

        with allure.step(f"step 2：划账 {amount}USDT，从合约 → 现货"):
            account_api = AccountApi(req=self.req, token=self.token)
            account_api.co_transfer(transfer_type="contract_to_wallet", amount=amount)

        with allure.step("step 3：划后 - 获取现货 & 合约余额"):
            time.sleep(3)
            spot_balance_02, contract_balance_02 = self.get_balances()

        with allure.step("step 4：断言余额变化"):
            assert  spot_balance_02  == spot_balance_01 + amount
            assert  contract_balance_02 == contract_balance_01 - amount

    @allure.story("test_003：限价单 - (价格<最新价) - 数量(多开下单) - 进入普通委托(单个取消)")
    def test_003_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(数量BTC)<最新价下单"):
            price = round(float(get_price_contract() * random.uniform(0.97, 0.98)), 2)
            oid = contract_api.contract_order_response(order_unit=0,price=price,volume=1,order_type=1)

        with allure.step("step 2：合约-当前委托，获取普通单数，断言验证普通单数＞0"):
            time.sleep(3)
            for attempt in range(1, 4):
                order_stats = contract_api.get_user_order_count()
                order_count = int(order_stats["orderCount"])
                if order_count > 0:
                        break
                else:
                    allure.attach(
                        f"orderCount = {order_count}",
                        name=f"获取普通单，第 {attempt} 次，orderCount值非预期",
                        attachment_type=allure.attachment_type.TEXT
                    )
                if attempt < 4:
                    time.sleep(3)
            assert int(order_stats["orderCount"]) > 0

        with allure.step("step 3：合约-当前委托-普通单，执行单个取消操作"):
            contract_api.cancel_contract_order(order_id=oid,is_condition_order=False)

    @allure.story("test_004：限价单 - (价格>最新价) - 数量(多开下单) - 进入仓位(止盈止损) - 进入条件委托(全部取消) - 回仓位(一键平仓)")
    def test_004_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(数量BTC)>最新价下单"):
            price = round(float(get_price_contract() * random.uniform(1.02, 1.03)), 2)
            contract_api.contract_order_response(order_unit=0, price=price, volume=1, order_type=1)

        with allure.step('step 2：获取当前账户的合约仓位列 contractId，断言仓位列表有值'):
            time.sleep(3)
            account_api.get_contract_id_with_retry()

        with allure.step("step 3：获取合约市场信息（指数价 & 标签价）"):
            price_info  = contract_api.get_market_prices()
            index_price = round(float(price_info["index_price"] * random.uniform(1.02, 1.03)), 2)
            tag_price = round(float(price_info["tag_price"] * random.uniform(0.97, 0.98)), 2)

        with allure.step("step 4：仓位列表-止盈止损"):
            order_list = [
                {"triggerType": 2, "type": 2, "price": 0, "volume": "1", "triggerPrice": index_price},
                {"triggerType": 1, "type": 2, "price": 0, "volume": "1", "triggerPrice": tag_price}
            ]
            contract_api.create_condition_order(order_list=order_list)

        with allure.step("step 5：合约-当前委托，获取条件单，断言条件单数≥2"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) >= 2

        with allure.step("step 6：合约-当前委托-条件单，执行全部取消操作"):
            contract_api.cancel_contract_order(is_condition_order=True)

        with allure.step("step 7：合约-当前委托，获取条件单，断言条件单数=0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) == 0

        with allure.step("step 8：合约-仓位列表，执行一键平仓"):
            contract_api.close_all_positions()

        with (allure.step("step 9：合约-仓位列表，验证一键平仓后positionList=[]")):
            account_api.get_contract_none()


    @allure.story("test_005：限价单 - (价格>最新价) - 数量(多开下单) - 进入仓位(仓位止盈止损) - 进入条件委托(全部取消) - 回仓位(一键平仓)")
    def test_005_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(数量BTC)>最新价下单"):
            price = round(float(get_price_contract() * random.uniform(1.02, 1.03)), 2)
            contract_api.contract_order_response(order_unit=0, price=price, volume=1, order_type=1)

        with allure.step(f"step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            account_api.get_contract_id_with_retry()

        with allure.step("step 3：获取计算仓位止盈止损"):
            data = account_api.get_position_with_sl_tp()
            position_id = data['position_id']
            price_take_profit = data['take_profit']
            price_stop_loss = data['stop_loss']

        with allure.step("step 4：仓位列表-仓位止盈止损"):
            sl_position_list = [
                {"triggerType": 2, "type": 2, "price": f"{price_take_profit}", "profitType":0,"expiredTime":30},
                {"triggerType": 1, "type": 2, "price": f"{price_stop_loss}", "profitType":0,"expiredTime":30}
            ]
            contract_api.create_condition_order(position_id=position_id,sl_position_list=sl_position_list)

        with allure.step("step 5：合约-当前委托，获取条件单，断言条件单数≥2"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) >= 2

        with allure.step("step 6：合约-当前委托-条件单，执行全部取消操作"):
            contract_api.cancel_contract_order(is_condition_order=True)

        with allure.step("step 7：合约-当前委托，获取条件单，断言条件单数=0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) == 0

        with allure.step("step 8：合约-仓位列表，执行一键平仓"):
            contract_api.close_all_positions()

        with (allure.step("step 9：合约-仓位列表，验证一键平仓后positionList=[]")):
            time.sleep(4)
            account_api.get_contract_none()

    @allure.story("test_006：限价单 - (价格>最新价) - 数量(多开下单) - 进入仓位(限价平仓) - 进入普通委托(取消) - 回仓位(一键平仓)")
    def test_006_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(数量BTC)>最新价下单"):
            price = round(float(get_price_contract() * random.uniform(1.02, 1.03)), 2)
            oid = contract_api.contract_order_response(order_unit=0, price=price, volume=1, order_type=1)

        with allure.step("step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            contract_id = account_api.get_contract_id_with_retry()

        with allure.step("step 3：合约-仓位列表-限价-快速平仓"):
            price = round(float(get_price_contract() * random.uniform(1.02, 1.03)), 2)
            contract_api.contract_order_response(
                side="SELL", open_type="CLOSE", contract_id=contract_id, price=price, order_unit=0, volume=1,
                order_type=1
            )

        with allure.step("step 4：合约-当前委托，获取普通单数，断言验证普通单数＞0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["orderCount"]) > 0

        with allure.step("step 5：合约-当前委托-普通单，执行单个取消操作"):
            contract_api.cancel_contract_order(order_id=oid, is_condition_order=False)
            time.sleep(3)

        with allure.step("step 6：合约-仓位列表，执行一键平仓"):
            time.sleep(3)
            contract_api.close_all_positions()

        with (allure.step("step 7：合约-仓位列表，验证一键平仓后positionList=[]")):
            time.sleep(4)
            account_api.get_contract_none()

    @allure.story("test_007：限价单 - (价格>最新价) - 数量(多开下单) - 进入仓位(市价平仓)")
    def test_007_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(数量BTC)>最新价下单"):
            price = round(float(get_price_contract() * random.uniform(1.02, 1.03)), 2)
            contract_api.contract_order_response(order_unit=0, price=price, volume=1, order_type=1)

        with allure.step("step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            contract_id = account_api.get_contract_id_with_retry()

        with allure.step("step 3：合约-仓位列表-市价-快速平仓"):
            contract_api.contract_order_response(
                side="SELL", open_type="CLOSE", contract_id=contract_id,order_unit=0, volume=1, order_type=2
            )

        with (allure.step("step 4：合约-仓位列表，验证市价-快速平仓后positionList=[]")):
            time.sleep(4)
            data = account_api.fetch_assets_list()
            position_list = data.get("positionList", [])
            if not position_list:
                assert position_list == []
            else:
                with allure.step("step 5：合约-仓位列表，执行一键平仓"):
                    contract_api.close_all_positions()

                with (allure.step("step 6：合约-仓位列表，验证一键平仓后positionList=[]")):
                    time.sleep(4)
                    account_api.get_contract_none()


    @allure.story("test_008：限价单 - (价格<最新价) - 价值(多开下单) - 进入普通委托(取消)")
    def test_008_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(价值USDT)<最新价下单"):
            price = round(float(get_price_contract() * random.uniform(0.97, 0.98)), 2)
            oid = contract_api.contract_order_response(order_unit=1, price=price, volume=1, order_type=1)

        with allure.step("step 2：合约-当前委托，获取普通单数，断言验证普通单数＞0"):
            time.sleep(3)
            for attempt in range(1, 4):
                order_stats = contract_api.get_user_order_count()
                order_count = int(order_stats["orderCount"])
                if order_count > 0:
                        break
                else:
                    allure.attach(
                        f"orderCount = {order_count}",
                        name=f"获取普通单，第 {attempt} 次，orderCount值非预期",
                        attachment_type=allure.attachment_type.TEXT
                    )
                if attempt < 4:
                    time.sleep(3)
            assert int(order_stats["orderCount"]) > 0

        with allure.step("step 3：合约-当前委托-普通单，执行单个取消操作"):
            contract_api.cancel_contract_order(order_id=oid, is_condition_order=False)
            time.sleep(3)

    @allure.story("test_009：限价单 - (价格>最新价) - 价值(多开下单) - 进入仓位(止盈止损) - 进入条件委托(全部取消) - 回仓位(一键平仓)")
    def test_009_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(价值BTC)>最新价下单"):
            price = round(float(get_price_contract() * random.uniform(1.05, 1.08)), 2)
            contract_api.contract_order_response(order_unit=1, price=price, volume=1, order_type=1)

        with allure.step(f"step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            account_api.get_contract_id_with_retry()

        with allure.step(f"step 3：获取合约市场信息（指数价 & 标签价）"):
            price_info = contract_api.get_market_prices()
            index_price = round(float(price_info["index_price"] * random.uniform(1.02, 1.03)), 2)
            tag_price = round(float(price_info["tag_price"] * random.uniform(0.97, 0.98)), 2)

        with allure.step("step 4：仓位列表-止盈止损"):
            order_list = [
                {"triggerType": 2, "type": 2, "price": 0, "volume": "1", "triggerPrice": index_price},
                {"triggerType": 1, "type": 2, "price": 0, "volume": "1", "triggerPrice": tag_price}
            ]
            contract_api.create_condition_order(order_list=order_list)

        with allure.step("step 5：合约-当前委托，获取条件单，断言条件单数≥2"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) >= 2

        with allure.step("step 6：合约-当前委托-条件单，执行全部取消操作"):
            contract_api.cancel_contract_order(is_condition_order=True)

        with allure.step("step 7：合约-当前委托，获取条件单，断言条件单数=0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) == 0

        with allure.step("step 8：合约-仓位列表，执行一键平仓"):
            contract_api.close_all_positions()

        with (allure.step("step 9：合约-仓位列表，验证一键平仓后positionList=[]")):
            time.sleep(4)
            account_api.get_contract_none()

    @allure.story("test_010：限价单 - (价格>最新价) - 价值(多开下单) - 进入仓位(仓位止盈止损) - 进入条件委托(全部取消) - 回仓位(一键平仓)")
    def test_010_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(价值BTC)>最新价下单"):
            price = round(float(get_price_contract() * random.uniform(1.02, 1.03)), 2)
            contract_api.contract_order_response(order_unit=1, price=price, volume=1, order_type=1)

        with allure.step(f"step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            account_api.get_contract_id_with_retry()

        with allure.step("step 3：获取计算仓位止盈止损"):
            data = account_api.get_position_with_sl_tp()
            position_id = data['position_id']
            price_take_profit = data['take_profit']
            price_stop_loss = data['stop_loss']

        with allure.step("step 4：仓位列表-仓位止盈止损"):
            sl_position_list = [
                {"triggerType": 2, "type": 2, "price": f"{price_take_profit}", "profitType": 0, "expiredTime": 30},
                {"triggerType": 1, "type": 2, "price": f"{price_stop_loss}", "profitType": 0, "expiredTime": 30}
            ]
            contract_api.create_condition_order(position_id=position_id, sl_position_list=sl_position_list)

        with allure.step("step 5：合约-当前委托，获取条件单，断言条件单数≥2"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) >= 2

        with allure.step("step 6：合约-当前委托-条件单，执行全部取消操作"):
            contract_api.cancel_contract_order(is_condition_order=True)

        with allure.step("step 7：合约-当前委托，获取条件单，断言条件单数=0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) == 0

        with allure.step("step 8：合约-仓位列表，执行一键平仓"):
            contract_api.close_all_positions()

        with (allure.step("step 9：合约-仓位列表，验证一键平仓后positionList=[]")):
            time.sleep(4)
            account_api.get_contract_none()

    @allure.story("test_011：限价单 - (价格>最新价) - 价值(多开下单) - 进入仓位(限价平仓) - 进入普通委托(取消) - 回仓位(一键平仓)")
    def test_011_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(价值BTC)>最新价下单"):
            price = round(float(get_price_contract() * random.uniform(1.02, 1.03)), 2)
            oid = contract_api.contract_order_response(order_unit=1, price=price, volume=1, order_type=1)

        with allure.step("step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            contract_id = account_api.get_contract_id_with_retry()

        with allure.step("step 3：合约-仓位列表-限价-快速平仓"):
            price = round(float(get_price_contract() * random.uniform(1.02, 1.03)), 2)
            contract_api.contract_order_response(
                side="SELL", open_type="CLOSE", contract_id=contract_id, price=price, order_unit=0, volume=1,
                order_type=1
            )

        with allure.step("step 4：合约-当前委托，获取普通单数，断言验证普通单数＞0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["orderCount"]) > 0

        with allure.step("step 5：合约-当前委托-普通单，执行单个取消操作"):
            contract_api.cancel_contract_order(order_id=oid, is_condition_order=False)
            time.sleep(3)

        with allure.step("step 6：合约-仓位列表，执行一键平仓"):
            time.sleep(3)
            contract_api.close_all_positions()

        with (allure.step("step 7：合约-仓位列表，验证一键平仓后positionList=[]")):
            time.sleep(4)
            account_api.get_contract_none()

    @allure.story("test_012：限价单 - (价格>最新价) - 价值(多开下单) - 进入仓位(市价平仓)")
    def test_012_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(价值BTC)>最新价下单"):
            price = round(float(get_price_contract() * random.uniform(1.02, 1.03)), 2)
            contract_api.contract_order_response(order_unit=1, price=price, volume=1, order_type=1)

        with allure.step("step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            contract_id = account_api.get_contract_id_with_retry()

        with allure.step("step 3：合约-仓位列表-市价-快速平仓"):
            contract_api.contract_order_response(
                side="SELL", open_type="CLOSE", contract_id=contract_id, order_unit=0, volume=1, order_type=2
            )

        with (allure.step("step 4：合约-仓位列表，验证市价-快速平仓后positionList=[]")):
            time.sleep(4)
            data = account_api.fetch_assets_list()
            position_list = data.get("positionList", [])
            if not position_list:
                assert position_list == []
            else:
                with allure.step("step 5：合约-仓位列表，执行一键平仓"):
                    contract_api.close_all_positions()

                with (allure.step("step 6：合约-仓位列表，验证一键平仓后positionList=[]")):
                    time.sleep(4)
                    account_api.get_contract_none()


    @allure.story("test_013：市价单 - 价格(当前市场最优价) - 数量(多开下单) - 进入仓位(止盈止损) - 进入条件委托(全部取消) - 回仓位(一键平仓)")
    def test_013_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多以当前市场最优价下单"):
            contract_api.contract_order_response(order_unit=0, volume=0.0001, order_type=2)

        with allure.step(f"step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            account_api.get_contract_id_with_retry()

        with allure.step(f"step 3：获取合约市场信息（指数价 & 标签价）"):
            price_info = contract_api.get_market_prices()
            index_price = round(float(price_info["index_price"] * random.uniform(1.02, 1.03)), 2)
            tag_price = round(float(price_info["tag_price"] * random.uniform(0.97, 0.98)), 2)

        with allure.step("step 4：仓位列表-止盈止损"):
            order_list = [
                {"triggerType": 2, "type": 2, "price": 0, "volume": "1", "triggerPrice": index_price},
                {"triggerType": 1, "type": 2, "price": 0, "volume": "1", "triggerPrice": tag_price}
            ]
            contract_api.create_condition_order(order_list=order_list)

        with allure.step("step 5：合约-当前委托，获取条件单，断言条件单数≥2"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) >= 2

        with allure.step("step 6：合约-当前委托-条件单，执行全部取消操作"):
            contract_api.cancel_contract_order(is_condition_order=True)

        with allure.step("step 7：合约-当前委托，获取条件单，断言条件单数=0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) == 0

        with allure.step("step 8：合约-仓位列表，执行一键平仓"):
            contract_api.close_all_positions()

        with (allure.step("step 9：合约-仓位列表，验证一键平仓后positionList=[]")):
            time.sleep(4)
            account_api.get_contract_none()

    @allure.story("test_014：市价单 - 价格(当前市场最优价) - 数量(多开下单) - 进入仓位(仓位止盈止损) - 进入条件委托(全部取消) - 回仓位(一键平仓)")
    def test_014_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多以当前市场最优价下单"):
            contract_api.contract_order_response(order_unit=0, volume=0.0001, order_type=2)

        with allure.step(f"step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            account_api.get_contract_id_with_retry()

        with allure.step("step 3：获取计算仓位止盈止损"):
            data = account_api.get_position_with_sl_tp()
            position_id = data['position_id']
            price_take_profit = data['take_profit']
            price_stop_loss = data['stop_loss']

        with allure.step("step 4：仓位列表-仓位止盈止损"):
            sl_position_list = [
                {"triggerType": 2, "type": 2, "price": f"{price_take_profit}", "profitType": 0, "expiredTime": 30},
                {"triggerType": 1, "type": 2, "price": f"{price_stop_loss}", "profitType": 0, "expiredTime": 30}
            ]
            contract_api.create_condition_order(position_id=position_id, sl_position_list=sl_position_list)

        with allure.step("step 5：合约-当前委托，获取条件单，断言条件单数≥2"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) >= 2

        with allure.step("step 6：合约-当前委托-条件单，执行全部取消操作"):
            contract_api.cancel_contract_order(is_condition_order=True)

        with allure.step("step 7：合约-当前委托，获取条件单，断言条件单数=0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) == 0

        with allure.step("step 8：合约-仓位列表，执行一键平仓"):
            contract_api.close_all_positions()

        with (allure.step("step 9：合约-仓位列表，验证一键平仓后positionList=[]")):
            time.sleep(4)
            account_api.get_contract_none()

    @allure.story("test_015：市价单 - 价格(当前市场最优价) - 数量(多开下单) - 进入仓位(限价平仓)")
    def test_015_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多以当前市场最优价数量下单"):
            oid = contract_api.contract_order_response(order_unit=0, volume=0.0001, order_type=2)

        with allure.step("step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            contract_id = account_api.get_contract_id_with_retry()

        with allure.step("step 3：合约-仓位列表-限价-快速平仓"):
            price = round(float(get_price_contract() * random.uniform(1.02, 1.03)), 2)
            contract_api.contract_order_response(
                side="SELL", open_type="CLOSE", price=price, contract_id=contract_id, order_unit=0, volume=1,
                order_type=1
            )

        with allure.step("step 4：合约-当前委托，获取普通单数，断言验证普通单数＞0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["orderCount"]) > 0

        with allure.step("step 5：合约-当前委托-普通单，执行单个取消操作"):
            contract_api.cancel_contract_order(order_id=oid)
            time.sleep(3)

        with allure.step("step 6：合约-当前委托，再次获取普通单数，判断普通单数!=0，否则再执行全部取消"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            if int(order_stats["orderCount"]) != 0:
                contract_api.cancel_contract_order()

        with allure.step("step 7：合约-仓位列表，执行一键平仓"):
            time.sleep(3)
            contract_api.close_all_positions()

        with (allure.step("step 8：合约-仓位列表，验证一键平仓后positionList=[]")):
            time.sleep(4)
            account_api.get_contract_none()

    @allure.story("test_016：市价单 - 价格(当前市场最优价) - 数量(多开下单) - 进入仓位(市价平仓)")
    def test_016_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多以当前市场最优价下单"):
            contract_api.contract_order_response(order_unit=0, volume=0.0001, order_type=2)

        with allure.step("step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            contract_id = account_api.get_contract_id_with_retry()

        with allure.step("step 3：合约-仓位列表-市价-快速平仓"):
            contract_api.contract_order_response(
                side="SELL", open_type="CLOSE", contract_id=contract_id, order_unit=0, volume=1, order_type=2
            )

        with (allure.step("step 4：合约-仓位列表，验证市价-快速平仓后positionList=[]")):
            time.sleep(4)
            data = account_api.fetch_assets_list()
            position_list = data.get("positionList", [])
            if not position_list:
                assert position_list == []
            else:
                with allure.step("step 5：合约-仓位列表，执行一键平仓"):
                    contract_api.close_all_positions()

                with (allure.step("step 6：合约-仓位列表，验证一键平仓后positionList=[]")):
                    time.sleep(4)
                    account_api.get_contract_none()

    @allure.story("test_017：市价单 - 价格(当前市场最优价) - 价值(多开下单) - 进入仓位(止盈止损) - 进入条件委托(全部取消) - 回仓位(一键平仓)")
    def test_017_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多以当前市场最优价下单"):
            contract_api.contract_order_response(order_unit=1, volume=12, order_type=2)

        with allure.step(f"step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            account_api.get_contract_id_with_retry()

        with allure.step(f"step 3：获取合约市场信息（指数价 & 标签价）"):
            price_info = contract_api.get_market_prices()
            index_price = round(float(price_info["index_price"] * random.uniform(1.02, 1.03)), 2)
            tag_price = round(float(price_info["tag_price"] * random.uniform(0.97, 0.98)), 2)

        with allure.step("step 4：仓位列表-止盈止损"):
            order_list = [
                {"triggerType": 2, "type": 2, "price": 0, "volume": "1", "triggerPrice": index_price},
                {"triggerType": 1, "type": 2, "price": 0, "volume": "1", "triggerPrice": tag_price}
            ]
            contract_api.create_condition_order(order_list=order_list)

        with allure.step("step 5：合约-当前委托，获取条件单，断言条件单数>0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) > 0

        with allure.step("step 6：合约-当前委托-条件单，执行全部取消操作"):
            contract_api.cancel_contract_order(is_condition_order=True)

        with allure.step("step 7：合约-当前委托，获取条件单，断言条件单数=0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) == 0

        with allure.step("step 8：合约-仓位列表，执行一键平仓"):
            contract_api.close_all_positions()

        with (allure.step("step 9：合约-仓位列表，验证一键平仓后positionList=[]")):
            time.sleep(4)
            account_api.get_contract_none()


    @allure.story("test_018：市价单 - 价格(当前市场最优价) - 价值(多开下单) - 进入仓位(仓位止盈止损) - 进入条件委托(全部取消) - 回仓位(一键平仓)")
    def test_018_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多以当前市场最优价下单"):
            contract_api.contract_order_response(order_unit=1, volume=12, order_type=2)

        with allure.step(f"step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            account_api.get_contract_id_with_retry()

        with allure.step("step 3：获取计算仓位止盈止损"):
            data = account_api.get_position_with_sl_tp()
            position_id = data['position_id']
            price_take_profit = data['take_profit']
            price_stop_loss = data['stop_loss']

        with allure.step("step 4：仓位列表-仓位止盈止损"):
            sl_position_list = [
                {"triggerType": 2, "type": 2, "price": f"{price_take_profit}", "profitType": 0, "expiredTime": 30},
                {"triggerType": 1, "type": 2, "price": f"{price_stop_loss}", "profitType": 0, "expiredTime": 30}
            ]
            contract_api.create_condition_order(position_id=position_id, sl_position_list=sl_position_list)

        with allure.step("step 5：合约-当前委托，获取条件单，断言条件单数≥2"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) >= 2

        with allure.step("step 6：合约-当前委托-条件单，执行全部取消操作"):
            contract_api.cancel_contract_order(is_condition_order=True)
            time.sleep(2)

        with allure.step("step 7：合约-当前委托，获取条件单，断言条件单数=0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["triggerOrderCount"]) == 0

        with allure.step("step 8：合约-仓位列表，执行一键平仓"):
            contract_api.close_all_positions()

        with (allure.step("step 9：合约-仓位列表，验证一键平仓后positionList=[]")):
            time.sleep(4)
            account_api.get_contract_none()

    @allure.story("test_019：市价单 - 价格(当前市场最优价) - 价值(多开下单) - 进入仓位(限价平仓)")
    def test_019_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多以当前市场最优价下单"):
            oid = contract_api.contract_order_response(order_unit=1, volume=12, order_type=2)

        with allure.step("step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            contract_id = account_api.get_contract_id_with_retry()

        with allure.step("step 3：合约-仓位列表-限价-快速平仓"):
            price = round(float(get_price_contract() * random.uniform(1.02, 1.03)), 2)
            contract_api.contract_order_response(
                side="SELL", open_type="CLOSE", contract_id=contract_id, price=price, order_unit=0, volume=1,
                order_type=1
            )

        with allure.step("step 4：合约-当前委托，获取普通单数，断言验证普通单数＞0"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            assert int(order_stats["orderCount"]) > 0

        with allure.step("step 5：合约-当前委托-普通单，执行单个取消操作"):
            contract_api.cancel_contract_order(order_id=oid, is_condition_order=False)
            time.sleep(3)

        with allure.step("step 6：合约-当前委托，再次获取普通单数，判断普通单数!=0，否则再执行全部取消"):
            time.sleep(3)
            order_stats = contract_api.get_user_order_count()
            if int(order_stats["orderCount"]) != 0:
                contract_api.cancel_contract_order()

        with allure.step("step 7：合约-仓位列表，执行一键平仓"):
            contract_api.close_all_positions()

        with (allure.step("step 8：合约-仓位列表，验证一键平仓后positionList=[]")):
            time.sleep(4)
            account_api.get_contract_none()

    @allure.story("test_020：市价单 - 价格(当前市场最优价) - 价值(多开下单) - 进入仓位(市价平仓)")
    def test_020_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)
        account_api = AccountApi(req=self.req, token=self.token)

        with allure.step("step 1：开多以当前市场最优价下单"):
            contract_api.contract_order_response(order_unit=1, volume=12, order_type=2)

        with allure.step("step 2：获取当前账户的合约仓位列表contractId，断言仓位列表有值"):
            time.sleep(3)
            contract_id = account_api.get_contract_id_with_retry()

        with allure.step("step 3：合约-仓位列表-市价-快速平仓"):
            contract_api.contract_order_response(
                side="SELL", open_type="CLOSE", contract_id=contract_id, order_unit=0, volume=1, order_type=2
            )

        with (allure.step("step 4：合约-仓位列表，验证市价-快速平仓后positionList=[]")):
            time.sleep(4)
            data = account_api.fetch_assets_list()
            position_list = data.get("positionList", [])
            if not position_list:
                assert position_list == []
            else:
                with allure.step("step 5：合约-仓位列表，执行一键平仓"):
                    contract_api.close_all_positions()

                with (allure.step("step 6：合约-仓位列表，验证一键平仓后positionList=[]")):
                    time.sleep(4)
                    account_api.get_contract_none()

    @allure.story("test_021：条件单 - 触发价格(低于最新价) - 限价(最新价) - 数量(多开下单) - 进入条件委托(全部取消)")
    def test_021_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(数量BTC)触发价<最新价下单"):
            price = get_price_contract()
            trigger_price = round(float(price * random.uniform(0.97, 0.98)), 2)
            contract_api.contract_order_response(
                order_unit=0,price=trigger_price,volume=1,order_type=1, is_condition_order=True,trigger_price=trigger_price,
            triggerType=4)

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

    @allure.story("test_022：条件单 - 触发价格(低于最新价) - 限价(最新价) - 价值(多开下单) - 进入条件委托(全部取消)")
    def test_022_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(价值BTC)触发价<最新价下单"):
            price = get_price_contract()
            trigger_price = round(float(price * random.uniform(0.97, 0.98)), 2)
            contract_api.contract_order_response(
                order_unit=1, price=trigger_price, volume=1, order_type=1, is_condition_order=True, trigger_price=trigger_price,
            triggerType=3)

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

    @allure.story("test_023：条件单 - 触发价格(低于最新价) - 市价(当前市场最优价) - 价值(多开下单) - 进入条件委托(全部取消)")
    def test_023_create_contract_order(self):
        contract_api = ContractApi(req=self.req, token=self.token)

        with allure.step("step 1：开多(价值BTC)触发价<最新价下单"):
            trigger_price = round(float(get_price_contract() * random.uniform(0.97, 0.98)), 2)
            contract_api.contract_order_response(
                order_unit=1, volume=12, order_type=2, is_condition_order=True, trigger_price=trigger_price
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


if __name__ == '__main__':
    unittest.main()
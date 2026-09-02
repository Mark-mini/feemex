# _*_ coding:utf-8 _*_
__author__ = 'dino.j'

import unittest
import allure
from common.utils import Data, build_headers, attach_request_response, query_mysql, decimal_to_native
from common.user_auth import UserAuth
from common.request_handler import RequestHandler
from config.userinfo import Info


@allure.feature("合约经济人：佣金收入")
class CaseExchangeChildInfo(unittest.TestCase):
    """合约经济人：佣金收入 """

    @classmethod
    def setUpClass(cls):
        cls.token = UserAuth.login(email=Info.Broker.ex_Email, password=Info.Broker.ex_Password)
        cls.req = RequestHandler(base_url=Info.Broker.Url)
        # 提取并保存全局 data
        cls.global_data_01 = None
        cls.global_data_02 = None

    @allure.story("step 1：请求佣金收入")
    @allure.title("获取佣金收入数据")
    def test_01_co_agent_bonus_survey(self):

        path_01 = "/fe-ex-api/co/agent/bonus_survey"  # 累计收入明细
        path_02 = "/fe-ex-api/co/agent/bonus_record"  # 佣金记录
        headers = build_headers(self.token)
        body_01 = {}
        body_02 = {"page":1,"pageSize":10,"start_time":Data.before_30day,"end_time":Data.today}

        with allure.step(f"{path_01} 发送 POST 请求"):
            resp_01 = self.req.post(path_01, json=body_01, headers=headers)
            attach_request_response(headers, body_01, resp_01)

        with allure.step(f"{path_02} 发送 POST 请求"):
            resp_02 = self.req.post(path_01, json=body_02, headers=headers)
            attach_request_response(headers, body_02, resp_02)

        with allure.step("验证响应"):
            data_01 = resp_01.json()
            data_02 = resp_02.json()
            # 存储 data 为类变量，供其他用例使用
            CaseExchangeChildInfo.global_data_01 = data_01["data"]
            CaseExchangeChildInfo.global_data_02 = data_02["data"]
            assert resp_01.status_code == 200
            assert resp_02.status_code == 200
            assert data_01["succ"]is True
            assert data_02["succ"] is True

    @allure.story("step 2：校验累计收入明细")
    @allure.title("校验累计收入明细数据")
    def test_02_child_info(self):

        # 1. 查询数据库 co_fee_bonus_daily 表
        sql01 = f"""
            SELECT SUM(volume) AS tradeVolume, SUM(all_b_amount) AS amount_return, coin
            FROM exchange.co_fee_bonus_daily
            WHERE uid = {Info.Broker.ex_Uid};
        """
        result = query_mysql(sql01)
        results = decimal_to_native(result)

        # 2. 提取 web 响应数据
        map_list = self.global_data_01["mapList"]

        # 3. 删除 不校验的字段：amount_sub、amount_total
        for item in map_list:
            item.pop('amount_sub', None)
            item.pop('amount_total', None)

        # 4. 展示和断言
        with allure.step("校验累计收入明细"):
            comparison_text = (
                f"实际值：{map_list}\n"
                f"预期值：{results}"
            )
            allure.attach(comparison_text, name="数据对比详情", attachment_type=allure.attachment_type.TEXT)
            self.assertEqual(map_list, results, "累计收入明细")


if __name__ == '__main__':
    unittest.main()
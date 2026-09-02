# _*_ coding:utf-8 _*_
__author__ = 'dino.j'

import unittest
import allure
from common.utils import Data, build_headers, attach_request_response, query_mysql, get_uids, date_to_timestamp, decimal_to_native
from common.user_auth import UserAuth
from common.request_handler import RequestHandler
from config.userinfo import Info


@allure.feature("合约经济人：数据面板")
class CaseExchangeChildInfo(unittest.TestCase):
    """合约经济人：数据面板 """

    @classmethod
    def setUpClass(cls):
        cls.token = UserAuth.login(email=Info.Broker.ex_Email, password=Info.Broker.ex_Password)
        cls.req = RequestHandler(base_url=Info.Broker.Url)
        # 提取并保存全局 data
        cls.global_data = None

    @allure.story("step 1：请求数据面板")
    @allure.title("获取数据面板数据")
    def test_01_get_sub_agent_by_role_list(self):

        path = "/fe-ex-api/co/agent/getSubAgentByRoleList"  # 数据面板
        headers = build_headers(self.token)
        body = {
            "page":1,
            "pageSize":10,
            "startDate":date_to_timestamp(Data.first_day),
            "endDate":date_to_timestamp(Data.last_day),
            "queryUids":None,
            "queryRoleIds":"-1",
            "directType":"0"
        }
        print(f"请求参数：{body}")

        with allure.step(f"{path} 发送 POST 请求"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        with allure.step("验证响应"):
            data = resp.json()
            print(f"响应值{data["data"]}")
            # 存储 data 为类变量，供其他用例使用
            CaseExchangeChildInfo.global_data = data["data"]
            assert resp.status_code == 200
            assert data["succ"]is True


    @allure.story("step 2：校验累计收入明细")
    @allure.title("校验累计收入明细数据")
    def test_02_child_info(self):

        # 获取团队UID
        uid = get_uids(Info.Broker.ex_Uid, 9, Data.today)
        print(f"UID {uid}")

        # 1. 查询数据库
        sql01 = f"""
            SELECT 
                (SUM(a.self_deposit_chain_amount)+SUM(a.sub_deposit_chain_amount)) AS depositChainAmount,
	            (SUM(a.self_deposit_chain_amount)+SUM(a.sub_deposit_chain_amount)-SUM(a.self_withdraw_chain_amount)-SUM(a.sub_withdraw_chain_amount)) AS onChainNetFlow,
                SUM(a.self_trading_amount) AS selfTradingVolume, 
                b.role_name AS role_name, 
                a.uid AS uid,
                (SUM(a.open_position_fee_amount) + SUM(a.sub_open_position_fee_amount) + SUM(close_position_fee_amount) + SUM(sub_close_position_fee_amount)) AS feeAmount,
                (SUM(a.trade_amount) + SUM(a.sub_trade_amount)) AS tradeAmount,
                (SUM(a.self_withdraw_chain_amount)+SUM(a.sub_withdraw_chain_amount)) AS withdrawChainAmount, 
                SUM(a.self_deposit_chain_amount) AS selfDepositChainAmount,
                SUM(a.register_num) AS registerNum,
                SUM(a.self_withdraw_chain_amount) AS selfWithdrawChainAmount
            FROM exchange.co_agent_user_team_daily_report AS a
            JOIN exchange.co_agent_user AS b
            ON a.uid = b.uid
            WHERE b.uid in ({uid}) AND stats_date BETWEEN "{Data.first_day}" AND "{Data.last_day}"
            GROUP BY uid;
        """
        result = query_mysql(sql01)
        results = decimal_to_native(result)

        # 2. 提取 web 响应数据
        lists = self.global_data["list"]

        # 3. 删除 不校验的字段
        for item in lists:
            item.pop('depositNum', None)
            item.pop('withdrawNum', None)
            item.pop('subRealizedProfit', None)
            item.pop('selfRealizedProfit', None)
            item.pop('roleColumn', None)
            item.pop('roleName', None)
            item.pop('totalTradeAmount', None)
            item.pop('role_id', None)

        # 4. 展示和断言
        with allure.step("校验数据面板"):

            for i in range(len(results)):
                list_item = lists[i]
                result_item = results[i]

                comparison_text = (
                    f"实际值: {list_item}\n"
                    f"预期值: {result_item}\n"
                )
                allure.attach(comparison_text, name=f"数据对比详情 第{i+1}行", attachment_type=allure.attachment_type.TEXT)
                self.assertEqual(list_item, result_item, )

if __name__ == '__main__':
    unittest.main()
# _*_ coding:utf-8 _*_
__author__ = 'dino.j'

import unittest
import allure
from datetime import datetime
from common.utils import Data,build_headers, attach_request_response, query_mysql, mask_emails_in_result, decimal_to_native
from common.user_auth import UserAuth
from common.request_handler import RequestHandler
from config.userinfo import Info


@allure.feature("合约经济人：业绩状况")
class CaseExchangeChildInfo(unittest.TestCase):
    """合约经济人：业绩状况 """

    @classmethod
    def setUpClass(cls):
        cls.token = UserAuth.login(email=Info.Broker.ex_Email,password=Info.Broker.ex_Password)
        cls.req = RequestHandler(base_url=Info.Broker.Url)
        # 提取并保存全局 data
        cls.global_data = None

    @allure.story("step 1：请求合约经济人信息")
    @allure.title("请求 /co/agent/index 获取 data 值并存入 global_data")
    def test_01_get_agent_data(self):
        path = "/fe-ex-api/co/agent/index"
        headers = build_headers(self.token)
        body = {}

        with allure.step(f"{path} 发送 POST 请求"):
            resp = self.req.post(path, json=body, headers=headers)
            attach_request_response(headers, body, resp)

        with allure.step("验证响应"):
            data = resp.json()
            # 存储 data 为类变量，供其他用例使用
            CaseExchangeChildInfo.global_data = data["data"]
            assert resp.status_code == 200
            assert data["succ"]is True

    @allure.story("step 2：校验团队概况")
    @allure.title("校验团队概况数据")
    def test_02_child_info(self):
        # 1. 提取 Web 响应数据
        data = self.global_data["child_info"]
        withdraw_sum = float(data["withdraw_sum"])
        deposit_sum = float(data["deposit_sum"])
        range_count_two = float(data["range_count_two"])
        count_bonus = float(data["count_bonus"])

        # 2. 查询数据库 exchange.co_agent_user_team 表
        sql01 = f"""
            SELECT * 
            FROM co_agent_user_team 
            WHERE uid = {Info.Broker.ex_Uid};
        """
        result = query_mysql(sql01)
        results = decimal_to_native(result)
        db_data = result[0] if results else {}

        # 3. 查询数据库 exchange.co_fee_bonus 表
        sql02 = f"""
            SELECT COUNT(*) AS group_count FROM (SELECT uid 
            FROM exchange.co_fee_bonus 
            WHERE stats_date = '{Data.yesterday}' AND (uid = {Info.Broker.ex_Uid} OR pid = {Info.Broker.ex_Uid}) 
            GROUP BY uid) AS bonus;
        """
        count = query_mysql(sql02)
        counts = decimal_to_native(count)
        db_count = counts[0] if counts else {}

        # 4. 展示和断言
        with allure.step(f"验证用户相关数据（提现、充值、用户量、分成用户）"):
            # 构造展示用字符串
            comparison_text = (
                f"【提现总额】实际值: {withdraw_sum} | 预期值: {db_data['withdraw_chain']}\n"
                f"【充值总额】实际值: {deposit_sum} | 预期值: {db_data['deposit_chain']}\n"
                f"【用户总量】实际值: {range_count_two} | 预期值: {db_data['team_num']}\n"
                f"【昨日分成用户】实际值: {count_bonus} | 预期值: {db_count['group_count']}"
            )
            allure.attach(comparison_text, name="数据对比详情", attachment_type=allure.attachment_type.TEXT)
            self.assertEqual(withdraw_sum, db_data['withdraw_chain'], "提现总额")
            self.assertEqual(deposit_sum, db_data['deposit_chain'], "充值总额")
            self.assertEqual(range_count_two, db_data['team_num'], "用户总量")
            self.assertEqual(count_bonus, db_count['group_count'], "昨日分成用户")

    @allure.story("step 3：校验业绩概况")
    @allure.title("校验业绩概况数据")
    def test_03_bonus_info(self):
        # 1. 提取 Web 响应数据
        data = self.global_data["bonus_info"]
        amount_total = float(data["amount_total"])
        amount_yesterday = float(data["amount_yesterday"])
        amount_b_yesterday = float(data["amount_b_yesterday"])
        volume_yesterday = float(data["volume_yesterday"])
        volume_month = float(data["volume_month"])
        yesterday_n_volume = float(data["yesterday_N_Volume"])
        n_volume = float(data["n_Volume"])

        # 2. 查询数据库 累计佣金
        sql01 = f"""
            SELECT (SUM(self_fee_to_bonus) + SUM(sub_fee_to_bonus)) AS bonus 
            FROM exchange.co_agent_user_team_daily_report 
            WHERE uid = {Info.Broker.ex_Uid};
        """
        result_1 = query_mysql(sql01)
        result_01 = decimal_to_native(result_1)
        db_data_01 = result_01[0] if result_01 else {}
        # 3. 查询数据库 昨日佣金
        sql02 = f"""
            SELECT (SUM(self_fee_to_bonus) + SUM(sub_fee_to_bonus)) AS bonus 
            FROM exchange.co_agent_user_team_daily_report 
            WHERE uid = {Info.Broker.ex_Uid} AND stats_date = '{Data.yesterday}';
        """
        result_2 = query_mysql(sql02)
        result_02 = decimal_to_native(result_2)
        db_data_02 = result_02[0] if result_02 else {}
        # 4. 查询数据库 前日佣金
        sql03 = f"""
            SELECT (SUM(self_fee_to_bonus) + SUM(sub_fee_to_bonus)) AS bonus 
            FROM exchange.co_agent_user_team_daily_report 
            WHERE uid = {Info.Broker.ex_Uid} AND stats_date = '{Data.before_yesterday}';
        """
        result_3 = query_mysql(sql03)
        result_03 = decimal_to_native(result_3)
        db_data_03 = result_03[0] if result_03 else {}
        # 5. 查询数据库 个人昨日交易量
        sql04 = f"""
            SELECT SUM(self_trading_amount) AS amount
            FROM exchange.co_agent_user_team_daily_report 
            WHERE uid = {Info.Broker.ex_Uid} AND stats_date = '{Data.yesterday}';
        """
        result_4 = query_mysql(sql04)
        result_04 = decimal_to_native(result_4)
        db_data_04 = result_04[0] if result_04 else {}
        # 6. 查询数据库 个人自然月交易量
        sql05 = f"""
            SELECT SUM(self_trading_amount) AS amount
            FROM exchange.co_agent_user_team_daily_report 
            WHERE uid = {Info.Broker.ex_Uid} AND stats_date BETWEEN '{Data.first_day}' AND '{Data.last_day}';
        """
        result_5 = query_mysql(sql05)
        result_05 = decimal_to_native(result_5)
        db_data_05 = result_05[0] if result_05 else {}
        # 7. 查询数据库 团队昨日交易量
        sql06 = f"""
            SELECT (SUM(self_trading_amount) + SUM(sub_trade_amount)) AS amount
            FROM exchange.co_agent_user_team_daily_report 
            WHERE uid = {Info.Broker.ex_Uid} AND stats_date = '{Data.yesterday}';
        """
        result_6 = query_mysql(sql06)
        result_06 = decimal_to_native(result_6)
        db_data_06 = result_06[0] if result_06 else {}
        # 8. 查询数据库 团队自然月交易量
        sql07 = f"""
            SELECT (SUM(self_trading_amount) + SUM(sub_trade_amount)) AS amount
            FROM exchange.co_agent_user_team_daily_report 
            WHERE uid = {Info.Broker.ex_Uid} AND stats_date BETWEEN '{Data.first_day}' AND '{Data.last_day}';
        """
        result_7 = query_mysql(sql07)
        result_07 = decimal_to_native(result_7)
        db_data_07 = result_07[0] if result_07 else {}

        # 9. 展示和断言
        with allure.step(f"校验业绩概况相关数据（累计佣金、昨日佣金、前日佣金、交易量）"):
            # 构造展示用字符串
            comparison_text = (
                f"【累计佣金折合】实际值： {amount_total} | 预期值： {db_data_01['bonus']}\n"
                f"【昨日佣金折合】实际值： {amount_yesterday} | 预期值: {db_data_02['bonus']}\n"
                f"【前日佣金折合】实际值: {amount_b_yesterday} | 预期值: {db_data_03['bonus']}\n"
                f"【个人昨日交易量】实际值: {volume_yesterday} | 预期值: {db_data_04['amount']}\n"
                f"【个人自然月交易量】实际值: {volume_month} | 预期值: {db_data_05['amount']}\n"
                f"【团队昨日交易量】实际值: {yesterday_n_volume} | 预期值: {db_data_04['amount']}\n"
                f"【团队自然月交易量】实际值: {n_volume} | 预期值: {db_data_05['amount']}\n"
            )
            allure.attach(comparison_text, name="数据对比详情", attachment_type=allure.attachment_type.TEXT)
            self.assertEqual(amount_total, db_data_01['bonus'], "累计佣金")
            self.assertEqual(amount_yesterday, db_data_02['bonus'],  "昨日佣金")
            self.assertEqual(amount_b_yesterday, db_data_03['bonus'], "前日佣金")
            self.assertEqual(volume_yesterday, db_data_04['amount'], "个人昨日交易量")
            self.assertEqual(volume_month, db_data_05['amount'], "个人自然月交易量")
            self.assertEqual(yesterday_n_volume, db_data_06['amount'], "团队昨日交易量")
            self.assertEqual(n_volume, db_data_07['amount'], "团队自然月交易量")

    @allure.story("step 4：校验最近一周佣金")
    @allure.title("校验最近一周佣金数据")
    def test_04_bonus_week(self):
        # 1. 提取 Web 响应数据
        web_data = []
        web_display = []
        for i in range(7):
            item = self.global_data['bonus_week'][i]
            timestamp = item['time']
            amount = float(item['amount'])
            # 转换时间戳为日期字符串
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
            web_data.append(amount)
            web_display.append(f"{date_str},{amount}")

        # 2. 查询数据库最近一周佣金
        sql = f"""
            SELECT stats_date, SUM(self_fee_to_bonus + sub_fee_to_bonus) AS amount 
            FROM exchange.co_agent_user_team_daily_report 
            WHERE uid = {Info.Broker.ex_Uid} 
            AND stats_date BETWEEN '{Data.start_date}' AND '{Data.end_date}' 
            GROUP BY stats_date 
            ORDER BY stats_date;
        """
        result = query_mysql(sql)
        results = decimal_to_native(result)

        # 3. 提取数据库结果
        db_data = []
        db_display = []
        if results:
            for row in results:
                date_str = row['stats_date'].strftime("%Y-%m-%d")
                amount = float(row['amount'])
                db_data.append(amount)
                db_display.append(f"{date_str},{amount}")

        # 4. 展示和断言
        with allure.step("校验最近一周佣金"):
            comparison_text = (
                f"实际值：{web_display}\n"
                f"预期值：{db_display}"
            )
            allure.attach(comparison_text, name="数据对比详情", attachment_type=allure.attachment_type.TEXT)
            # self.assertEqual(web_data, db_data, "最近一周佣金")
            self.assertEqual(web_display, db_display, "最近一周佣金（含日期）")

    @allure.story("step 5：返佣排行")
    @allure.title("校验返佣排行数据")
    def test_05_user_return(self):
        # 1. 提取 Web 响应数据
        ranking = self.global_data['user_return']

        # 2. 查询数据库返佣排行
        sql = f"""
            SELECT a.uid, SUM(a.bonus_amount*a.base_rate) AS amount, b.email AS username
            FROM exchange.co_fee_bonus AS a 
            JOIN exchange.user AS b 
            ON a.uid = b.id
            WHERE a.type = 0 AND a.pid = {Info.Broker.ex_Uid}
            GROUP BY a.uid 
            ORDER BY amount DESC 
            LIMIT 5;
        """
        result = query_mysql(sql)
        results = decimal_to_native(result)
        results = mask_emails_in_result(results)

        # 3. 展示和断言
        with allure.step("校验返佣排行"):
            comparison_text = (
                f"实际值：{ranking}\n"
                f"预期值：{results}"
            )
            allure.attach(comparison_text, name="数据对比详情", attachment_type=allure.attachment_type.TEXT)
            self.assertEqual(ranking, results, "返佣排行")

if __name__ == '__main__':
    unittest.main()
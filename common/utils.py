# _*_ coding:utf-8 _*_
__author__ = 'dino.j'

import time
import json
import calendar
from datetime import date, timedelta
import allure
import logging
import requests
import pymysql
from pymysql.cursors import DictCursor
from decimal import Decimal
from time import mktime

def get_current():
    """返回当前自然月的第一天和最后一天，格式为 date 类型"""
    today = date.today()
    year = today.year
    month = today.month
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    return first_day, last_day

def get_week_today():
    """
    返回不包含今天的最近一周起止日期（昨天往前推共 7 天），格式为 date 类型。
    例如今天是 2025-06-08，则返回 (2025-06-01, 2025-06-07)
    """
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)
    return start_date, end_date

class Data:
    # 当天
    today = date.today().isoformat()
    # 昨天
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    # 前日
    before_yesterday = (date.today() - timedelta(days=2)).isoformat()
    # 前30天
    before_30day = (date.today() - timedelta(days=30)).isoformat()
    # 自然月第一天 和 最后一天
    first_day, last_day = get_current()
    # 最近一周起止日期（不含今天）
    start_date, end_date = get_week_today()

def build_headers(token: str) -> dict:
    """ 构建接口请求头 """
    return {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Exchange-Client": "pc",
        "Content-Type": "application/json",
        "User-Agent": "DinoTestAgent",
        "Exchange-token": token
    }

def attach_request_response(headers: dict, body: dict, response):
    """ 封装 allure.attach 逻辑为通用函数 """
    allure.attach(json.dumps(headers, indent=2, ensure_ascii=False), name="请求头", attachment_type=allure.attachment_type.JSON)
    allure.attach(json.dumps(body, indent=2, ensure_ascii=False), name="请求体", attachment_type=allure.attachment_type.JSON)
    try:
        json_resp = response.json()
        allure.attach(json.dumps(json_resp, indent=2, ensure_ascii=False), name="响应内容", attachment_type=allure.attachment_type.JSON)
        logging.info(f"接口响应内容: {json.dumps(json_resp, indent=2, ensure_ascii=False)}")
    except Exception:
        allure.attach(response.text, name="响应内容", attachment_type=allure.attachment_type.TEXT)
        logging.warning(f"接口响应内容（非JSON）: {response.text}")

def get_price_spot(data="BTCUSDT"):
    """ 获取现货最新成交价格 """
    path_openapi = "https://openapi.fameex.com/sapi/v1/ticker"
    params = {"symbol": data}

    with allure.step(f"{path_openapi} 获取最新价格"):
        resp = requests.get(url=path_openapi, params=params)
        attach_request_response(headers={}, body=params, response=resp)
        data = resp.json()
        price = round(float(data["last"]), 2)
        return price

def get_price_contract(data="E-BTC-USDT"):
    """ 获取合约最新成交价格 """
    path_openapi = "https://futuresopenapi.fameex.com/fapi/v1/ticker"
    params = {"contractName": data}

    with allure.step(f"{path_openapi} 获取最新价格"):
        resp = requests.get(url=path_openapi, params=params)
        attach_request_response(headers={}, body=params, response=resp)
        data = resp.json()
        price = round(float(data["last"]), 2)
        return price

def query_mysql(sql):
    """
    连接 MySQL 数据库并执行查询语句，返回结果。
    :param sql: 要执行的 SQL 查询语句
    :return: 查询结果列表（每行是一个 dict）
    """
    global connection
    config = {
        "host": "35.197.158.214",
        "port": 3306,
        "user": "chainup_user",
        "password": "huPhe2I4ucRa",
        "database": "exchange",
        "charset": "utf8mb4",
        "cursorclass": DictCursor
    }

    try:
        connection = pymysql.connect(**config)
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
    except Exception as e:
        print("数据库查询失败：", e)
        return []
    finally:
        if 'connection' in locals():
            connection.close()

def get_uids(uid: int, level: int, end_date: str) -> str:
    """
    获取某代理用户在截止时间前的所有下级 UID，并拼接为 SQL IN (...) 用的字符串

    :param uid: 顶级用户 UID
    :param level: 递归层级深度（不含本人）
    :param end_date: 截止时间（格式 'YYYY-MM-DD HH:MM:SS'）
    :return: 拼接后的 uid 字符串，例如 '123,456,789'
    """
    sql = f"""
        WITH RECURSIVE subordinates AS (
            SELECT uid, 1 AS lvl
            FROM exchange.co_agent_user
            WHERE uid = {uid} AND ctime < '{end_date}'
            UNION ALL
            SELECT c.uid, s.lvl + 1
            FROM exchange.co_agent_user c
            INNER JOIN subordinates s ON c.pid = s.uid
            WHERE s.lvl <= {level} AND c.ctime < '{end_date}'
        )
        SELECT au.uid, au.pid, s.lvl
        FROM exchange.agent_user au
        INNER JOIN subordinates s ON au.pid = s.uid
        WHERE au.ctime < '{end_date}';
    """
    result = query_mysql(sql)
    uid_str = ",".join(str(int(row["uid"])) for row in result)
    return uid_str


def mask_email(email: str) -> str:
    """
    将邮箱打星处理，保留首字符和域名，例如 abc@xxx.com => a****@xxx.com
    """
    if '@' not in email:
        return email
    name, domain = email.split('@', 1)
    if len(name) <= 1:
        masked = name + '****'
    else:
        masked = name[0] + '****'
    return masked + '@' + domain

def mask_emails_in_result(result: list) -> list:
    """
    对查询结果中的 'username' 字段进行邮箱打星处理
    """
    for row in result:
        if 'username' in row and isinstance(row['username'], str):
            row['username'] = mask_email(row['username'])
    return result


def date_to_timestamp(dt):
    """
    将 datetime 对象转换为毫秒级时间戳（int 类型）。

    参数:
        dt (datetime.datetime): 要转换的 datetime 对象。

    返回:
        int: 毫秒时间戳（1970 年以来的毫秒数）。
    """
    return int(mktime(dt.timetuple()) * 1000)


def decimal_to_native(data):
    """
    将嵌套结构中的 Decimal 对象转换为原生 float 或 int 类型：
    - Decimal('0E-16') -> 0.0
    - Decimal('0') -> 0
    - Decimal('123.456') -> float(123.456)

    参数:
        data (Any): 输入数据（可能是 dict、list、Decimal、int、str 等）

    返回:
        转换后的数据，Decimal 将被替换为 float 或 int。
    """
    if isinstance(data, dict):
        return {k: decimal_to_native(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [decimal_to_native(i) for i in data]
    elif isinstance(data, Decimal):
        if data == data.to_integral_value():
            # 是整数（比如 Decimal('0') 或 Decimal('123')）
            return int(data)
        else:
            # 是小数（比如 Decimal('0E-16') 或 Decimal('123.456')）
            return float(data)
    else:
        return data
"""运行合约经纪人测试，并生成 Allure HTML 报告。"""

from run_test import PROJECT_DIR, run_case


def get_test_dir():
    """返回合约经纪人测试目录的绝对路径。"""
    return PROJECT_DIR / "tests" / "exchange_broker"


if __name__ == "__main__":
    report = run_case(test_path=get_test_dir())
    print(f"最新报告：{report}")

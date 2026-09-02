"""运行合约与现货流程测试，并生成 Allure HTML 报告。"""

import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent


def get_test_dir():
    """返回合约与现货测试目录的绝对路径。"""
    return PROJECT_DIR / "tests" / "contract_spot"


def get_test_report():
    """返回 Allure 报告输出目录的绝对路径。"""
    return PROJECT_DIR / "report"


def new_report(test_report):
    """返回报告目录中最近生成的报告路径。"""
    reports = [path for path in test_report.iterdir() if path.is_dir()]
    if not reports:
        raise FileNotFoundError(f"报告目录为空：{test_report}")
    return max(reports, key=lambda path: path.stat().st_mtime)


def run_case(test_path=None, result_path=None):
    """执行指定测试目录并生成独立的 Allure HTML 报告。

    Args:
        test_path: 测试目录；未传入时使用 tests/contract_spot。
        result_path: 报告目录；未传入时使用 report。

    Returns:
        最新生成的 Allure HTML 报告目录。
    """
    test_path = Path(test_path) if test_path else get_test_dir()
    result_path = Path(result_path) if result_path else get_test_report()
    result_path.mkdir(parents=True, exist_ok=True)

    now = time.strftime("%Y%m%d_%H%M%S")
    allure_result = result_path / f"{now}_result"
    allure_report = result_path / f"{now}_report"
    allure_result.mkdir(parents=True, exist_ok=True)

    pytest_command = [
        sys.executable,
        "-m",
        "pytest",
        str(test_path),
        f"--alluredir={allure_result}",
    ]
    print("运行命令:", " ".join(pytest_command))
    pytest_exit = subprocess.run(pytest_command, cwd=PROJECT_DIR).returncode

    allure_executable = shutil.which("allure")
    if platform.system().lower() == "windows":
        allure_executable = allure_executable or r"C:\allure\bin\allure.bat"
    if not allure_executable:
        raise FileNotFoundError("未找到 allure 命令，请先安装并配置 Allure Commandline")

    allure_command = [
        allure_executable,
        "generate",
        str(allure_result),
        "-o",
        str(allure_report),
        "--clean",
    ]
    print("生成报告命令:", " ".join(allure_command))
    allure_exit = subprocess.run(allure_command, cwd=PROJECT_DIR).returncode

    if allure_exit != 0:
        raise RuntimeError(f"Allure 报告生成失败，退出码：{allure_exit}")

    shutil.rmtree(allure_result)
    print(f"Allure 报告生成完成：{allure_report}")

    # 测试失败时保留报告，但把失败状态返回给调用方。
    if pytest_exit != 0:
        print(f"测试存在失败，Pytest 退出码：{pytest_exit}")

    return allure_report


if __name__ == "__main__":
    report = run_case()
    print(f"最新报告：{report}")

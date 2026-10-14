"""AI影视助手第一版入口：建立本地工作流骨架，不调用网络或 AI API。"""

import json
from pathlib import Path

from config import INPUT_DIR, PROJECTS_DIR
from codex_provider import CodexProvider
from environment_checker import inspect_environment
from file_utils import ensure_directory
from file_utils import safe_project_name
from project_manager import create_project
from stage01_manager import run_stage01
from stage02_manager import run_stage02
from stage03_manager import run_stage03
from stage04_manager import run_stage04
from stage05_manager import run_stage05
from stage06_manager import run_stage06
from stage07_manager import run_stage07
from stage08_manager import run_stage08
from stage09_manager import run_stage09
from stage10_manager import run_stage10
from stage11_manager import run_stage11
from stage12_manager import run_stage12


def list_script_files(input_dir: Path) -> list[Path]:
    ensure_directory(input_dir)
    return sorted(
        [path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in {".txt", ".md"}],
        key=lambda path: path.name.lower(),
    )


def choose_script(files: list[Path], input_func=input, print_func=print) -> Path | None:
    if not files:
        print_func("输入剧本文件夹中没有 .txt 或 .md 文件。")
        print_func("请先把剧本放入：输入剧本/")
        return None
    print_func("请选择剧本：")
    for index, path in enumerate(files, 1):
        print_func(f"{index}. {path.name}")
    answer = input_func("请输入数字：").strip()
    try:
        number = int(answer)
    except ValueError:
        print_func("输入无效，请输入列表中的数字。")
        return None
    if not 1 <= number <= len(files):
        print_func("没有这个选项，程序已取消。")
        return None
    return files[number - 1]


def main() -> int:
    print("AI影视助手第一版：本地工作流初始化")
    print("本版本不会调用网络、AI API，也不会修改规则库和模板库。\n")
    try:
        selected = choose_script(list_script_files(INPUT_DIR))
        if selected is None:
            return 0
        existing = PROJECTS_DIR / safe_project_name(selected.stem)
        if existing.is_dir() and (existing / "workflow_state.json").is_file():
            state = json.loads((existing / "workflow_state.json").read_text(encoding="utf-8"))
            if state.get("stages", {}).get("1", {}).get("status") == "failed":
                print("发现这个项目的 Stage 01 上次处理失败。")
                print("1. 重试 Stage 01")
                print("2. 查看错误原因")
                print("3. 返回")
                action = input("请输入数字：").strip()
                if action == "1":
                    environment = inspect_environment()
                    if environment.restricted_network:
                        print("当前是受限开发环境，已跳过真实联网调用；项目文件未损坏。")
                        return 0
                    try:
                        run_stage01(existing, CodexProvider())
                        print("Stage 01 重试成功，状态已更新为 completed。")
                    except Exception as error:
                        print(f"AI 服务暂时不可用，项目文件未损坏，可稍后重试 Stage 01。\n原因：{error}")
                    return 0
                if action == "2":
                    log = existing / "logs" / "stage01_error.log"
                    print(log.read_text(encoding="utf-8") if log.is_file() else "没有找到错误日志。")
                    return 0
                return 0
            if state.get("stages", {}).get("2", {}).get("status") == "failed":
                print("发现这个项目的 Stage 02 上次处理失败。")
                print("1. 重试 Stage 02")
                print("2. 查看错误原因")
                print("3. 返回")
                action = input("请输入数字：").strip()
                if action == "1":
                    environment = inspect_environment()
                    if environment.restricted_network:
                        print("当前是受限开发环境，已跳过真实联网调用；项目文件未损坏。")
                        return 0
                    try:
                        run_stage02(existing, CodexProvider())
                        print("Stage 02 重试成功，状态已更新为 completed。")
                    except Exception as error:
                        print(f"AI 服务暂时不可用，项目文件未损坏，可稍后重试 Stage 02。\n原因：{error}")
                    return 0
                if action == "2":
                    log = existing / "logs" / "stage02_error.log"
                    print(log.read_text(encoding="utf-8") if log.is_file() else "没有找到错误日志。")
                    return 0
                return 0
            if state.get("stages", {}).get("3", {}).get("status") == "failed":
                print("发现这个项目的 Stage 03 上次处理失败。")
                print("1. 重试 Stage 03")
                print("2. 查看错误原因")
                print("3. 返回")
                action = input("请输入数字：").strip()
                if action == "1":
                    environment = inspect_environment()
                    if environment.restricted_network:
                        print("当前是受限开发环境，已跳过真实联网调用；项目文件未损坏。")
                        return 0
                    try:
                        run_stage03(existing, CodexProvider())
                        print("Stage 03 重试成功，资产 ID 已保持稳定。")
                    except Exception as error:
                        print(f"AI 服务暂时不可用，项目文件未损坏，可稍后重试 Stage 03。\n原因：{error}")
                    return 0
                if action == "2":
                    log = existing / "logs" / "stage03_error.log"
                    print(log.read_text(encoding="utf-8") if log.is_file() else "没有找到错误日志。")
                    return 0
                return 0
            if state.get("stages", {}).get("4", {}).get("status") == "failed":
                print("发现这个项目的 Stage 04 上次处理失败。")
                print("1. 重试 Stage 04")
                print("2. 查看错误原因")
                print("3. 返回")
                action = input("请输入数字：").strip()
                if action == "1":
                    environment = inspect_environment()
                    if environment.restricted_network:
                        print("当前是受限开发环境，已跳过真实联网调用；项目文件未损坏。")
                        return 0
                    try:
                        run_stage04(existing, CodexProvider())
                        print("Stage 04 重试成功，资产提示词已生成。")
                    except Exception as error:
                        print(f"AI 服务暂时不可用，项目文件未损坏，可稍后重试 Stage 04。\n原因：{error}")
                    return 0
                if action == "2":
                    log = existing / "logs" / "stage04_error.log"
                    print(log.read_text(encoding="utf-8") if log.is_file() else "没有找到错误日志。")
                    return 0
                return 0
            if state.get("stages", {}).get("5", {}).get("status") == "failed":
                print("发现这个项目的 Stage 05 上次处理失败。")
                print("1. 重试 Stage 05")
                print("2. 查看错误原因")
                print("3. 返回")
                action = input("请输入数字：").strip()
                if action == "1":
                    environment = inspect_environment()
                    if environment.restricted_network:
                        print("当前是受限开发环境，已跳过真实联网调用；项目文件未损坏。")
                        return 0
                    try:
                        run_stage05(existing, CodexProvider())
                        print("Stage 05 重试成功，标准分镜已生成。")
                    except Exception as error:
                        print(f"AI 服务暂时不可用，项目文件未损坏，可稍后重试 Stage 05。\n原因：{error}")
                    return 0
                if action == "2":
                    log = existing / "logs" / "stage05_error.log"
                    print(log.read_text(encoding="utf-8") if log.is_file() else "没有找到错误日志。")
                    return 0
                return 0
            if state.get("stages", {}).get("6", {}).get("status") == "failed":
                print("发现这个项目的 Stage 06 上次处理失败。")
                print("1. 重试 Stage 06")
                print("2. 查看错误原因")
                print("3. 返回")
                action = input("请输入数字：").strip()
                if action == "1":
                    environment = inspect_environment()
                    if environment.restricted_network:
                        print("当前是受限开发环境，已跳过真实联网调用；项目文件未损坏。")
                        return 0
                    try:
                        run_stage06(existing, CodexProvider())
                        print("Stage 06 重试成功，Seedance 2.0 提示词已生成。")
                    except Exception as error:
                        print(f"AI 服务暂时不可用，项目文件未损坏，可稍后重试 Stage 06。\n原因：{error}")
                    return 0
                if action == "2":
                    log = existing / "logs" / "stage06_error.log"
                    print(log.read_text(encoding="utf-8") if log.is_file() else "没有找到错误日志。")
                    return 0
                return 0
            if state.get("stages", {}).get("7", {}).get("status") == "failed":
                print("发现这个项目的 Stage 07 上次处理失败。")
                print("1. 重试 Stage 07")
                print("2. 查看错误原因")
                print("3. 返回")
                action = input("请输入数字：").strip()
                if action == "1":
                    environment = inspect_environment()
                    if environment.restricted_network:
                        print("当前是受限开发环境，已跳过真实联网调用；项目文件未损坏。")
                        return 0
                    try:
                        run_stage07(existing, CodexProvider())
                        print("Stage 07 重试成功，Seedance 2.5 提示词已生成。")
                    except Exception as error:
                        print(f"AI 服务暂时不可用，项目文件未损坏，可稍后重试 Stage 07。\n原因：{error}")
                    return 0
                if action == "2":
                    log = existing / "logs" / "stage07_error.log"
                    print(log.read_text(encoding="utf-8") if log.is_file() else "没有找到错误日志。")
                    return 0
                return 0
            if state.get("stages", {}).get("8", {}).get("status") == "failed":
                print("发现这个项目的 Stage 08 上次处理失败。")
                print("1. 重试 Stage 08")
                print("2. 查看错误原因")
                print("3. 返回")
                action = input("请输入数字：").strip()
                if action == "1":
                    environment = inspect_environment()
                    if environment.restricted_network:
                        print("当前是受限开发环境，已跳过真实联网调用；项目文件未损坏。")
                        return 0
                    try:
                        run_stage08(existing, CodexProvider())
                        print("Stage 08 重试成功，即梦 2.0 提示词已生成。")
                    except Exception as error:
                        print(f"AI 服务暂时不可用，项目文件未损坏，可稍后重试 Stage 08。\n原因：{error}")
                    return 0
                if action == "2":
                    log = existing / "logs" / "stage08_error.log"
                    print(log.read_text(encoding="utf-8") if log.is_file() else "没有找到错误日志。")
                    return 0
                return 0
            if state.get("stages", {}).get("9", {}).get("status") == "failed":
                print("发现这个项目的 Stage 09 上次处理失败。")
                print("1. 重试 Stage 09")
                print("2. 查看错误原因")
                print("3. 返回")
                action = input("请输入数字：").strip()
                if action == "1":
                    environment = inspect_environment()
                    if environment.restricted_network:
                        print("当前是受限开发环境，已跳过真实联网调用；项目文件未损坏。")
                        return 0
                    try:
                        run_stage09(existing, CodexProvider())
                        print("Stage 09 重试成功，即梦 2.5 提示词已生成。")
                    except Exception as error:
                        print(f"AI 服务暂时不可用，项目文件未损坏，可稍后重试 Stage 09。\n原因：{error}")
                    return 0
                if action == "2":
                    log = existing / "logs" / "stage09_error.log"
                    print(log.read_text(encoding="utf-8") if log.is_file() else "没有找到错误日志。")
                    return 0
                return 0
            if state.get("stages", {}).get("10", {}).get("status") == "failed":
                print("发现这个项目的 Stage 10 上次处理失败。")
                print("1. 重试 Stage 10")
                print("2. 查看错误原因")
                print("3. 返回")
                action = input("请输入数字：").strip()
                if action == "1":
                    try:
                        run_stage10(existing)
                        print("Stage 10 重试成功，连续性审核报告已生成。")
                    except Exception as error:
                        print(f"连续性审核失败，上游项目文件未修改。\n原因：{error}")
                    return 0
                if action == "2":
                    log = existing / "logs" / "stage10_error.log"
                    print(log.read_text(encoding="utf-8") if log.is_file() else "没有找到错误日志。")
                    return 0
                return 0
            if state.get("stages", {}).get("11", {}).get("status") == "failed":
                print("发现这个项目的 Stage 11 上次处理失败。")
                print("1. 重试 Stage 11")
                print("2. 查看错误原因")
                print("3. 返回")
                action = input("请输入数字：").strip()
                if action == "1":
                    try:
                        run_stage11(existing)
                        print("Stage 11 重试成功，历史真实性审核报告已生成。")
                    except Exception as error:
                        print(f"历史真实性审核失败，上游项目文件未修改。\n原因：{error}")
                    return 0
                if action == "2":
                    log = existing / "logs" / "stage11_error.log"
                    print(log.read_text(encoding="utf-8") if log.is_file() else "没有找到错误日志。")
                    return 0
                return 0
            if state.get("stages", {}).get("12", {}).get("status") == "failed":
                print("发现这个项目的 Stage 12 上次处理失败。")
                print("1. 重试 Stage 12")
                print("2. 查看错误原因")
                print("3. 返回")
                action = input("请输入数字：").strip()
                if action == "1":
                    try:
                        run_stage12(existing)
                        print("Stage 12 重试成功，AI生成风险终审报告已生成。")
                    except Exception as error:
                        print(f"AI生成风险审核失败，上游项目文件未修改。\n原因：{error}")
                    return 0
                if action == "2":
                    log = existing / "logs" / "stage12_error.log"
                    print(log.read_text(encoding="utf-8") if log.is_file() else "没有找到错误日志。")
                    return 0
                return 0
        project_dir = create_project(selected, mode="confirm", projects_dir=PROJECTS_DIR)
        if project_dir is None:
            print("已取消，没有覆盖已有项目。")
            return 0
        try:
            environment = inspect_environment()
            if environment.restricted_network:
                print("检测到受限开发环境，暂不调用真实 AI；Stage 01 保持等待 AI 处理。")
            else:
                run_stage01(project_dir, CodexProvider())
                print("Stage 01 剧本解析报告已生成。")
                run_stage02(project_dir, CodexProvider())
                print("Stage 02 项目专属规则已生成。")
                run_stage03(project_dir, CodexProvider())
                print("Stage 03 资产库已生成并锁定。")
                run_stage04(project_dir, CodexProvider())
                print("Stage 04 资产生成提示词已完成。")
                run_stage05(project_dir, CodexProvider())
                print("Stage 05 标准分镜已完成。")
                run_stage06(project_dir, CodexProvider())
                print("Stage 06 Seedance 2.0 提示词已完成。")
                run_stage07(project_dir, CodexProvider())
                print("Stage 07 Seedance 2.5 提示词已完成。")
                run_stage08(project_dir, CodexProvider())
                print("Stage 08 即梦 2.0 提示词已完成。")
                run_stage09(project_dir, CodexProvider())
                print("Stage 09 即梦 2.5 提示词已完成。")
                run_stage10(project_dir)
                print("Stage 10 连续性审核已完成。")
                run_stage11(project_dir)
                print("Stage 11 历史真实性审核已完成。")
                run_stage12(project_dir)
                print("Stage 12 AI生成风险终审已完成。")
        except Exception as error:
            print(f"AI 服务暂时不可用，项目文件未损坏，可稍后重试 Stage 01。\n原因：{error}")
        print(f"\n项目创建完成：{project_dir}")
        print("已建立原始剧本、项目配置、资产登记表、阶段状态和 01—12 工作流文件。")
        print("如果 Stage 01—05 均已完成，项目中还会包含标准分镜和 storyboard.json。")
        return 0
    except UnicodeDecodeError:
        print("读取剧本失败：文件不是 UTF-8 编码。请将剧本另存为 UTF-8 后再试。")
        return 1
    except OSError as error:
        print(f"文件操作失败：{error}")
        return 1
    except ValueError as error:
        print(f"输入错误：{error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

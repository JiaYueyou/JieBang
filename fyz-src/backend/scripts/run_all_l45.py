"""一键运行：测试 → L4-L5 补全

用法：
    python scripts/run_all_l45.py          # 测试 + 补全
    python scripts/run_all_l45.py --test   # 仅测试
    python scripts/run_all_l45.py --skip-test  # 仅补全（跳过测试）
"""

import subprocess
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent

ALL_STEPS = [
    ("test", "测试", "python tests/run_l45_tests.py"),
    ("enrich", "L4-L5补全", "python 05_enrich_l45.py"),
]


def run_step(name, label, command, cwd):
    print(f"\n{'='*55}")
    print(f"  [{name}] {label}")
    print(f"  {command}")
    print(f"{'='*55}")
    start = time.time()
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=False)
    elapsed = time.time() - start
    if result.returncode == 0:
        print(f"\n  [{name}] 完成 ({elapsed:.1f}s)")
    else:
        print(f"\n  [{name}] 失败! (exit code {result.returncode})")
    return result.returncode


def main():
    # 解析参数
    skip_test = "--skip-test" in sys.argv
    only_test = "--test" in sys.argv

    steps = []
    if not skip_test:
        steps.append(ALL_STEPS[0])
    if not only_test:
        steps.append(ALL_STEPS[1])

    if not steps:
        print("没有要运行的步骤")
        return

    print("L4-L5 智能体自动化流水线")
    print(f"  步骤: {', '.join(s for _, s, _ in steps)}")
    print()

    all_passed = True
    for name, label, command in steps:
        rc = run_step(name, label, command, BACKEND_DIR)
        if rc != 0:
            all_passed = False
            if name == "enrich":
                print("\n  [ERROR] 补全失败，请检查 DeepSeek API Key 和网络连接")
            break

    print(f"\n{'='*55}")
    if all_passed:
        print("  全部完成!")
    else:
        print("  流程中断，请修复错误后重试")
        sys.exit(1)


if __name__ == "__main__":
    main()

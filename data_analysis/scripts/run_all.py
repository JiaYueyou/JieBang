"""
一键运行清洗流水线的全部 4 步。
用法: python run_all.py
"""

import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
STEPS = [
    ("01_merge_clean.py",   "Step 1: 数据合并与清洗"),
    ("02_normalize_titles.py", "Step 2: 岗位名称标准化"),
    ("03_extract_skills.py",   "Step 3: 技能提取"),
    ("04_build_reference.py",  "Step 4: 构建参考数据集"),
]


def main() -> None:
    total_start = time.time()
    print("=" * 60)
    print("  清洗流水线 — 全链路一键运行")
    print("=" * 60)

    for script, title in STEPS:
        print(f"\n{'─' * 50}")
        print(f"  {title}")
        print(f"{'─' * 50}")
        sys.stdout.flush()

        start = time.time()
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / script)],
            capture_output=False,
            cwd=SCRIPTS_DIR,
        )
        elapsed = time.time() - start

        if result.returncode != 0:
            print(f"\n[FAIL] {script} 失败 (exit code {result.returncode})")
            sys.exit(1)

        print(f"  [OK] {script} 完成 ({elapsed:.1f}s)")

    total = time.time() - total_start
    print(f"\n{'=' * 60}")
    print(f"  全链路完成! 总耗时 {total:.1f} 秒")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

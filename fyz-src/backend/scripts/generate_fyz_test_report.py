"""Generate a compact, data-first FYZ HTML test report."""

from __future__ import annotations

import argparse
import html
import json
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parents[1]
EVALUATION_DIR = BACKEND_DIR / "evaluation"


def _percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _badge(passed: bool) -> str:
    label = "通过" if passed else "未通过"
    css = "pass" if passed else "fail"
    return f'<span class="badge {css}">{label}</span>'


def _junit_summary(path: Path) -> dict:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    summary = {
        key: sum(int(suite.attrib.get(key, 0)) for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    summary["time"] = sum(float(suite.attrib.get("time", 0)) for suite in suites)
    groups: Counter[str] = Counter()
    slowest: list[tuple[float, str]] = []
    for suite in suites:
        for case in suite.findall("testcase"):
            classname = case.attrib.get("classname", "other")
            parts = classname.split(".")
            group = parts[1] if len(parts) > 1 else parts[0]
            groups[group] += 1
            slowest.append(
                (
                    float(case.attrib.get("time", 0)),
                    f"{classname}::{case.attrib.get('name', '')}",
                )
            )
    summary["groups"] = dict(sorted(groups.items()))
    summary["slowest"] = sorted(slowest, reverse=True)[:5]
    return summary


def _docker_summary() -> dict:
    command = [
        "docker",
        "compose",
        "--env-file",
        "deploy/.env",
        "-f",
        "deploy/compose.yml",
        "-f",
        "deploy/compose.local.yml",
        "ps",
        "-a",
        "--format",
        "json",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
            timeout=30,
        )
        rows = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return {"available": False}
    running = [row for row in rows if row.get("State") == "running"]
    healthy = [row for row in running if row.get("Health") in {"healthy", ""}]
    migration = next((row for row in rows if row.get("Service") == "fyz-migrate"), None)
    return {
        "available": True,
        "running": len(running),
        "healthy_or_no_healthcheck": len(healthy),
        "migration_exit_code": migration.get("ExitCode") if migration else None,
        "services": len(rows),
    }


def generate_report(*, quality_path: Path, coverage_path: Path, junit_path: Path) -> str:
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    junit = _junit_summary(junit_path)
    docker = _docker_summary()
    jd = quality["jd_extraction"]
    resume = quality["resume_extraction"]
    matching = quality["matching"]
    test_passed = junit["failures"] == 0 and junit["errors"] == 0
    overall = (
        quality["all_quality_gates_passed"]
        and coverage["coverage_gate_passed"]
        and test_passed
    )
    generated = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")

    group_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{count}</td></tr>"
        for name, count in junit["groups"].items()
    )
    coverage_rows = "".join(
        f"<tr><td>{html.escape(row['file'])}</td><td>{row['covered_lines']} / {row['executable_lines']}</td><td>{_percent(row['coverage'])}</td></tr>"
        for row in sorted(coverage["files"], key=lambda item: item["coverage"])[:8]
    )
    docker_text = (
        f"{docker['running']} 个运行服务；迁移退出码 {docker['migration_exit_code']}"
        if docker.get("available")
        else "本次生成时未读取到 Docker 状态"
    )
    source_text = "；".join(
        f"{name}: {count} 条" for name, count in jd["source_distribution"].items()
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FYZ 端测试与量化报告</title>
  <style>
    :root {{ --ink:#172033; --muted:#667085; --line:#dfe4ec; --blue:#2855d9; --green:#147a4b; --red:#b42318; --bg:#f4f6f9; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--ink); font:14px/1.55 "Segoe UI","Microsoft YaHei",sans-serif; }}
    main {{ max-width:1100px; margin:28px auto; padding:0 20px 40px; }}
    header, section {{ background:#fff; border:1px solid var(--line); border-radius:10px; padding:20px 22px; margin-bottom:14px; }}
    h1 {{ margin:0 0 6px; font-size:24px; }} h2 {{ margin:0 0 14px; font-size:17px; }}
    p {{ margin:5px 0; }} .muted {{ color:var(--muted); }}
    .cards {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; margin-top:18px; }}
    .card {{ border:1px solid var(--line); border-radius:8px; padding:14px; }}
    .value {{ display:block; font-size:24px; font-weight:700; color:var(--blue); margin-top:3px; }}
    table {{ width:100%; border-collapse:collapse; }} th,td {{ padding:9px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ color:var(--muted); font-weight:600; background:#fafbfc; }} tr:last-child td {{ border-bottom:0; }}
    .badge {{ display:inline-block; border-radius:999px; padding:2px 8px; font-weight:700; font-size:12px; }}
    .pass {{ color:var(--green); background:#e9f7ef; }} .fail {{ color:var(--red); background:#fef0ef; }}
    .note {{ border-left:3px solid #f0a000; padding-left:12px; color:#5e4a17; }}
    .split {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
    code {{ font-family:"Cascadia Mono",Consolas,monospace; font-size:12px; }}
    @media(max-width:850px) {{ .cards {{ grid-template-columns:1fr 1fr; }} .split {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body><main>
  <header>
    <h1>FYZ 端测试与量化报告</h1>
    <p>总体结论：{_badge(overall)}　范围：仅 FYZ 后端　生成时间：{generated}</p>
    <p class="muted">数据集版本 {html.escape(quality['dataset_version'])}；Docker：{html.escape(docker_text)}</p>
    <div class="cards">
      <div class="card">测试用例<span class="value">{junit['tests']}</span>失败 {junit['failures'] + junit['errors']}</div>
      <div class="card">服务层覆盖率<span class="value">{_percent(coverage['coverage'])}</span>{coverage['covered_lines']} / {coverage['executable_lines']} 行</div>
      <div class="card">JD 锚点召回<span class="value">{_percent(jd['anchor_recall'])}</span>{jd['records']} 条真实 JD</div>
      <div class="card">简历抽取 F1<span class="value">{_percent(resume['micro_f1'])}</span>{resume['records']} 条标注样本</div>
      <div class="card">匹配准确率<span class="value">{_percent(matching['exact_score_accuracy'])}</span>{matching['records']} 条端到端样本</div>
    </div>
  </header>

  <section>
    <h2>核心门禁</h2>
    <table><thead><tr><th>指标</th><th>结果</th><th>门槛</th><th>样本/计算量</th><th>判定</th></tr></thead><tbody>
      <tr><td>FYZ 自动化测试</td><td>{junit['tests'] - junit['failures'] - junit['errors']} / {junit['tests']}</td><td>零失败</td><td>{junit['time']:.2f} 秒</td><td>{_badge(test_passed)}</td></tr>
      <tr><td>Service 可执行行覆盖率</td><td>{_percent(coverage['coverage'])}</td><td>≥ 60%</td><td>{coverage['covered_lines']} / {coverage['executable_lines']} 行</td><td>{_badge(coverage['coverage_gate_passed'])}</td></tr>
      <tr><td>JD 解析：正例关键词锚点召回</td><td>{_percent(jd['anchor_recall'])}</td><td>≥ 90%</td><td>{jd['anchor_true_positive']} / {jd['anchor_true_positive'] + jd['anchor_false_negative']} 锚点</td><td>{_badge(quality['gates']['jd_anchor_recall'])}</td></tr>
      <tr><td>简历技能抽取 micro-F1</td><td>{_percent(resume['micro_f1'])}</td><td>≥ 90%</td><td>TP {resume['true_positive']} / FP {resume['false_positive']} / FN {resume['false_negative']}</td><td>{_badge(quality['gates']['resume_micro_f1'])}</td></tr>
      <tr><td>匹配分数精确准确率</td><td>{_percent(matching['exact_score_accuracy'])}</td><td>≥ 90%</td><td>{matching['records'] - matching['failure_count']} / {matching['records']}；MAE {matching['mean_absolute_score_error']}</td><td>{_badge(quality['gates']['matching_exact_accuracy'])}</td></tr>
    </tbody></table>
  </section>

  <section>
    <h2>数据构成与误差</h2>
    <table><thead><tr><th>评测集</th><th>规模</th><th>来源</th><th>失败/误差</th></tr></thead><tbody>
      <tr><td>JD 技能锚点</td><td>{jd['records']} 条</td><td>{html.escape(source_text)}</td><td>漏检锚点 {jd['anchor_false_negative']} 个</td></tr>
      <tr><td>简历技能抽取</td><td>{resume['records']} 条</td><td>确定性人工规则标注边界样本</td><td>{resume['failure_count']} 条非完全匹配；FP {resume['false_positive']}</td></tr>
      <tr><td>人岗匹配</td><td>{matching['records']} 条</td><td>生产抽取器 + 生产 skill-coverage 算法</td><td>{matching['failure_count']} 条；分数 MAE {matching['mean_absolute_score_error']}</td></tr>
    </tbody></table>
    <p class="note"><strong>JD 指标边界：</strong>爬取数据的 keywords 只提供不完整的正例标签，因此 99.03% 是正例锚点召回率，不能推导完整 JD 的误报率。报告没有把该代理指标伪装成完整人工金标准 F1。</p>
  </section>

  <div class="split">
    <section>
      <h2>测试分布</h2>
      <table><thead><tr><th>测试分组</th><th>用例数</th></tr></thead><tbody>{group_rows}</tbody></table>
    </section>
    <section>
      <h2>覆盖率最低的 8 个 Service 文件</h2>
      <table><thead><tr><th>文件</th><th>覆盖行</th><th>覆盖率</th></tr></thead><tbody>{coverage_rows}</tbody></table>
    </section>
  </div>

  <section>
    <h2>复现命令</h2>
    <p><code>python scripts/evaluate_fyz_quality.py --jd-limit 100 --case-count 60</code></p>
    <p><code>python scripts/run_fyz_coverage.py</code></p>
    <p><code>python scripts/generate_fyz_test_report.py</code></p>
    <p class="muted">覆盖率方法：{html.escape(coverage['method'])}。完整 JSON 和 JUnit XML 保存在 evaluation 目录。</p>
  </section>
</main></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--quality", type=Path, default=EVALUATION_DIR / "fyz_quality_metrics.json"
    )
    parser.add_argument(
        "--coverage", type=Path, default=EVALUATION_DIR / "fyz_coverage.json"
    )
    parser.add_argument(
        "--junit", type=Path, default=EVALUATION_DIR / "fyz_pytest_results.xml"
    )
    parser.add_argument(
        "--output", type=Path, default=EVALUATION_DIR / "fyz_test_report.html"
    )
    args = parser.parse_args()
    report = generate_report(
        quality_path=args.quality,
        coverage_path=args.coverage,
        junit_path=args.junit,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

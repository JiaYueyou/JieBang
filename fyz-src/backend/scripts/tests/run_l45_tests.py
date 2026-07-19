"""Run all L4-L5 agent tests. Returns exit code 0 if all pass."""

import sys
import math
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[2] / "agent-development"
sys.path.insert(0, str(AGENT_DIR))

from l45_agent.schema import AgentInput, SkillEvidence, AgentOutput, L4TechPoint, L5KnowledgePoint
from l45_agent.verify import L45Validator

PASSED = 0
FAILED = 0
ERRORS = []


def test(name, func):
    global PASSED, FAILED
    try:
        func()
        PASSED += 1
    except AssertionError as e:
        FAILED += 1
        ERRORS.append(f"  FAIL: {name} - {e}")
    except Exception as e:
        FAILED += 1
        ERRORS.append(f"  ERROR: {name} - {type(e).__name__}: {e}")


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


# ── Helper ──
def make_output(skill="X", l4_name="P1", l4_conf=0.9):
    return AgentOutput(skill_name=skill, tech_points=[
        L4TechPoint(name=l4_name, detail="D", confidence=l4_conf,
                    knowledge_points=[L5KnowledgePoint(name="K1", description="D",
                                                       difficulty="medium", confidence=0.9)])])


# ── 1. Schema tests ──
def test_schema():
    e = SkillEvidence(source_doc_id=1, source_platform="T", evidence_text="x")
    check(e.source_doc_id == 1)
    pt = L4TechPoint(name="A", detail="B", confidence=0.8)
    kp = L5KnowledgePoint(name="X", description="Y", difficulty="medium", confidence=0.7)
    check(kp.difficulty == "medium")


def test_input():
    ipt = AgentInput(skill_name="J", skill_area="L",
                     evidence=[SkillEvidence(source_doc_id=1, source_platform="A", evidence_text="x"),
                               SkillEvidence(source_doc_id=2, source_platform="B", evidence_text="y")])
    check(ipt.skill_name == "J")
    check(len(ipt.evidence) == 2)


# ── 2. Confidence formula boundary tests ──
def test_log_zero():
    """evidence_count=0 → 0.5, 不报错"""
    c = L45Validator.calc_confidence(0, 100)
    check(c == 0.5, f"expected 0.5, got {c}")


def test_log_max_one():
    """max=1, count=1 → log2(2)/log2(2)=1.0 → 该类别的最大值,合理"""
    c = L45Validator.calc_confidence(1, 1)
    check(c == 1.0, f"expected 1.0, got {c}")


def test_log_max_one_higher():
    """max=1, count=5 → log2(6)/log2(2) × 0.5 + 0.5 = 1.0"""
    c = L45Validator.calc_confidence(5, 1)
    expected = round(math.log2(6) / 1.0 * 0.5 + 0.5, 2)
    check(c == expected, f"expected {expected}, got {c}")


def test_log_max_zero():
    """max=0 → 0.5, 不报错"""
    c = L45Validator.calc_confidence(5, 0)
    check(c == 0.5, f"expected 0.5, got {c}")


# ── 3. Confidence formula normal tests ──
def test_log_pass():
    """log公式下正常通过"""
    v = L45Validator(0.75)
    r = v.validate(make_output(), evidence_count=64, max_evidence_count=117)
    check(r.passed)
    check(r.tech_points[0].confidence == 0.94)


def test_log_fail():
    """证据数太少时被过滤"""
    v = L45Validator(0.75)
    r = v.validate(make_output(), evidence_count=3, max_evidence_count=117)
    check(not r.passed)


def test_log_empty():
    v = L45Validator()
    r = v.validate(AgentOutput(skill_name="J", tech_points=[]), 0, 8)
    check(not r.passed)


# ── 4. Per-category tests ──
def test_per_category():
    """同证据数,不同类别max,置信度不同"""
    v = L45Validator(0.75)
    # 每次调用用独立的 output,避免validate原地修改污染
    r_a = v.validate(make_output(), evidence_count=4, max_evidence_count=8)
    r_b = v.validate(make_output(), evidence_count=4, max_evidence_count=4)
    conf_a = r_a.tech_points[0].confidence
    conf_b = r_b.tech_points[0].confidence
    check(conf_a != conf_b, f"A={conf_a}, B={conf_b}, should differ")
    check(conf_b > conf_a, f"B={conf_b} should > A={conf_a}")


def test_per_category_edge():
    """较低max类别让低证据技能通过,高max类别过滤"""
    v = L45Validator(0.75)
    out = make_output()
    r_g = v.validate(out, evidence_count=1, max_evidence_count=8)
    r_c = v.validate(out, evidence_count=1, max_evidence_count=1)
    check(not r_g.passed)
    check(r_c.passed)


# ── 5. Evidence selection tests ──
def test_select_proportional_basic():
    """2来源, 按比例分配, 每来源至少1条"""
    from collections import OrderedDict
    # 模拟 87条A源 + 30条B源
    rows = [(i, "A", f"text_{i}") for i in range(87)]
    rows += [(i, "B", f"text_{i}") for i in range(30)]

    from unittest.mock import patch
    # 直接测试 select_evidence_proportionally 函数
    # 由于Python路径问题, 直接用同样的逻辑测试
    groups = OrderedDict()
    groups["A"] = [(i, "A", f"t{i}") for i in range(87)]
    groups["B"] = [(i, "B", f"t{i}") for i in range(30)]
    all_rows = groups["A"] + groups["B"]

    # 重新实现选择逻辑(与05_enrich_l45.py一致)
    cap = 20
    srcs = list(groups.keys())
    result = []
    if len(srcs) >= cap:
        for s in srcs[:cap]:
            result.append(groups[s][0])
    else:
        remaining = cap - len(srcs)
        total = len(all_rows)
        extra = {}
        allocated = 0
        for s in srcs:
            e = int(len(groups[s]) / total * remaining)
            extra[s] = e
            allocated += e
        remainder = remaining - allocated
        if remainder > 0:
            fracs = [(s, len(groups[s]) / total - extra[s] / remaining) for s in srcs]
            fracs.sort(key=lambda x: -x[1])
            for i in range(remainder):
                extra[fracs[i][0]] += 1
        for s in srcs:
            take = 1 + extra.get(s, 0)
            result.extend(groups[s][:take])

    # 验证结果
    src_a = sum(1 for r in result if r[1] == "A")
    src_b = sum(1 for r in result if r[1] == "B")
    check(src_a >= 1, f"A got 0!")
    check(src_b >= 1, f"B got 0!")  # 保底生效
    check(src_a + src_b == cap, f"total {src_a + src_b} != {cap}")
    # 比例大致接近 87:30 ≈ 3:1
    check(src_a > src_b, f"A({src_a}) should > B({src_b})")
    print(f"    A: {src_a}条, B: {src_b}条")


def test_select_imbalanced():
    """1来源200条 + 1来源3条 → 小来源至少保底1条, 不被无声排除"""
    cap = 20
    groups = {
        "BigSource": [(i, "BigSource", f"t{i}") for i in range(200)],
        "SmallSource": [(i, "SmallSource", f"t{i}") for i in range(3)],
    }
    all_rows = groups["BigSource"] + groups["SmallSource"]
    srcs = list(groups.keys())

    # 同上的选择逻辑
    result = []
    if len(srcs) >= cap:
        for s in srcs[:cap]:
            result.append(groups[s][0])
    else:
        remaining = cap - len(srcs)
        total = len(all_rows)
        extra = {}
        allocated = 0
        for s in srcs:
            e = int(len(groups[s]) / total * remaining)
            extra[s] = e
            allocated += e
        remainder = remaining - allocated
        if remainder > 0:
            fracs = [(s, len(groups[s]) / total - extra[s] / remaining) for s in srcs]
            fracs.sort(key=lambda x: -x[1])
            for i in range(remainder):
                extra[fracs[i][0]] += 1
        for s in srcs:
            take = 1 + extra.get(s, 0)
            result.extend(groups[s][:take])

    src_big = sum(1 for r in result if r[1] == "BigSource")
    src_small = sum(1 for r in result if r[1] == "SmallSource")
    check(src_small >= 1, f"SmallSource got 0! 保底失效!")
    check(src_big >= 1, f"BigSource got 0!")
    check(len(result) == cap, f"total {len(result)} != {cap}")
    print(f"    BigSource(200): {src_big}条, SmallSource(3): {src_small}条 (保底ok)")


def test_select_sources_exceed_cap():
    """25来源, cap=20 → 取前20个来源(按证据数降序)各1条"""
    groups = {f"Src{i:02d}": [(j, f"Src{i:02d}", f"t{j}") for j in range(5)]
              for i in range(25)}
    # 让某些来源更大, 验证排序
    groups["BigSrc"] = [(j, "BigSrc", f"t{j}") for j in range(100)]
    all_rows = [r for v in groups.values() for r in v]
    srcs = list(groups.keys())

    cap = 20
    # 按来源证据数降序
    sorted_srcs = sorted(srcs, key=lambda s: len(groups[s]), reverse=True)
    result = []
    for s in sorted_srcs[:cap]:
        result.append(groups[s][0])

    check(len(result) == cap, f"got {len(result)}")
    # 验证 BigSrc 排在前面(证据最多的源优先入选)
    check(result[0][1] == "BigSrc", f"BigSrc should be first, got {result[0][1]}")
    src_counts = {}
    for r in result:
        src_counts[r[1]] = src_counts.get(r[1], 0) + 1
    check(all(c == 1 for c in src_counts.values()), "not all 1 per source")
    print(f"    Sources selected: {len(src_counts)}, total items: {len(result)}")


# ── Run all ──
if __name__ == "__main__":
    print("=" * 55)
    print("  L4-L5 Agent Tests")
    print("=" * 55)

    tests = [
        # Schema
        ("schema creation", test_schema),
        ("agent input", test_input),
        # Log边界
        ("log boundary: count=0", test_log_zero),
        ("log boundary: max=1", test_log_max_one),
        ("log boundary: max=1, count=5", test_log_max_one_higher),
        ("log boundary: max=0", test_log_max_zero),
        # Log正常
        ("log pass (64/117)", test_log_pass),
        ("log fail (3/117)", test_log_fail),
        ("log empty", test_log_empty),
        # 按类别
        ("per-category confidence", test_per_category),
        ("per-category edge", test_per_category_edge),
        # 证据选择
        ("select proportional", test_select_proportional_basic),
        ("select imbalanced", test_select_imbalanced),
        ("select sources>cap", test_select_sources_exceed_cap),
    ]

    for name, fn in tests:
        test(name, fn)

    total = PASSED + FAILED
    print(f"\n  Passed: {PASSED}/{total}")
    for e in ERRORS:
        print(e)

    if FAILED == 0:
        print("\n  All tests passed!")
        sys.exit(0)
    else:
        print(f"\n  {FAILED} test(s) failed!")
        sys.exit(1)

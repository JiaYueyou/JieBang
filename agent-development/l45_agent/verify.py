"""
L4-L5 置信度计算与验证过滤。

置信度 = log2(evidence_count + 1) / log2(max_evidence_count + 1) * 0.5 + 0.5

log 压缩防止单技能拉高整个类别的分母,同时保证:
  - evidence_count = 0    → 0.5（下限,实际不会出现,因为<2已被过滤）
  - evidence_count = 1    → 0.5（同上）
  - max_evidence_count = 1 → 对所有技能打 0.5（分母为 1 时退化为线性公式）
"""

import math

from .schema import AgentOutput, VerifiedResult, L4TechPoint


class L45Validator:
    """验证 Agent 输出，使用来源数计算置信度"""

    def __init__(self, min_confidence: float = 0.75):
        self.min_confidence = min_confidence

    @staticmethod
    def calc_confidence(evidence_count: int, max_evidence_count: int) -> float:
        """log 压缩版置信度公式，含边界保护"""
        # 边界保护
        if evidence_count <= 0 or max_evidence_count <= 0:
            return 0.5
        if max_evidence_count == 1:
            # 分母 log2(2)=1,分子 log2(count+1) ≤ 1
            return round(math.log2(evidence_count + 1) / 1.0 * 0.5 + 0.5, 2)

        denom = math.log2(max_evidence_count + 1)
        if denom == 0:  # max=0 不会发生,防御
            return 0.5

        return round(math.log2(evidence_count + 1) / denom * 0.5 + 0.5, 2)

    def validate(self, output: AgentOutput,
                 evidence_count: int = 0,
                 max_evidence_count: int = 8) -> VerifiedResult:
        """验证并重算置信度

        Args:
            output: Agent 原始输出
            evidence_count: 该技能的实际证据来源数
            max_evidence_count: 该技能所在类别的最大证据来源数
        """
        if not output or not output.tech_points:
            return VerifiedResult(
                skill_name=output.skill_name if output else "",
                tech_points=[],
                passed=False,
                reason="无技术点",
            )

        source_confidence = self.calc_confidence(evidence_count, max_evidence_count)

        valid_points: list[L4TechPoint] = []
        total_points = len(output.tech_points)
        filtered_count = 0

        for pt in output.tech_points:
            # 用来源置信度覆盖 LLM 自评
            pt.confidence = source_confidence

            if pt.confidence < self.min_confidence:
                filtered_count += 1
                continue

            # L5 知识点统一使用来源置信度
            valid_kps = []
            for kp in pt.knowledge_points:
                kp.confidence = source_confidence
                if kp.confidence >= self.min_confidence:
                    valid_kps.append(kp)

            if not valid_kps:
                filtered_count += 1
                continue

            pt.knowledge_points = valid_kps
            valid_points.append(pt)

        passed = len(valid_points) > 0
        reason = ""
        if not passed:
            reason = f"所有技术点被过滤(置信度{source_confidence}<{self.min_confidence})"
        elif filtered_count > 0:
            reason = f"过滤了{filtered_count}/{total_points}个低质量技术点"

        return VerifiedResult(
            skill_name=output.skill_name,
            tech_points=valid_points,
            passed=passed,
            reason=reason,
        )

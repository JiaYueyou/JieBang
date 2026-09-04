<template>
  <div v-if="evidence" class="evidence-popover-content">
    <div class="evidence-popover-title">
      <span>{{ evidence.evidence_type === 'resume_skill' ? '简历原文' : '岗位 JD' }}</span>
      <strong>{{ evidence.skill_name }}</strong>
    </div>
    <p>{{ evidence.evidence_text }}</p>
    <small>{{ location }}</small>
    <div class="evidence-popover-hint">点击索引定位到该来源</div>
  </div>
  <div v-else class="evidence-popover-content"><p>该证据未随本次解释返回。</p></div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { MatchEvidence } from "@/domain/types";

const props = defineProps<{ evidence: MatchEvidence | null }>();
const location = computed(() => {
  const source = props.evidence?.source_ref || {};
  const line = source.line_start ? `第 ${source.line_start}${source.line_end && source.line_end !== source.line_start ? `–${source.line_end}` : ""} 行` : "位置未标注";
  if (props.evidence?.evidence_type === "resume_skill") return `${source.filename || "简历原件"} · ${line}`;
  return `${source.job_title || "岗位说明"} · ${source.department || "部门待补充"} · ${source.level || "职级待补充"}`;
});
</script>

<style scoped>
.evidence-popover-content { color: var(--text-secondary); line-height: 1.65; }
.evidence-popover-title { display: flex; align-items: center; gap: 8px; }
.evidence-popover-title span { padding: 2px 7px; border-radius: 999px; background: var(--color-brand-light); color: var(--color-brand); font-size: 12px; }
.evidence-popover-title strong { color: var(--text-primary); }
.evidence-popover-content p { margin: 9px 0 6px; }
.evidence-popover-content small { color: var(--text-muted); }
.evidence-popover-hint { margin-top: 8px; padding-top: 7px; border-top: 1px solid var(--color-border-light); color: var(--color-brand); font-size: 12px; }
</style>

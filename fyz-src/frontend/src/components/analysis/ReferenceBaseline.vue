<template>
  <section v-if="baseline" class="baseline-panel dash-card">
    <header class="baseline-head">
      <div>
        <div class="baseline-kicker">REFERENCE BASELINE · {{ baseline.version }}</div>
        <h3>基线技术栈与岗位参考标准</h3>
        <p>{{ baseline.source_note }}</p>
      </div>
      <div class="baseline-metrics" aria-label="基线摘要">
        <span><strong>{{ baseline.technology_stack_count }}</strong> 技术栈</span>
        <span><strong>{{ baseline.standard_job_count }}</strong> 标准岗位</span>
        <span><strong>{{ baseline.verified_skill_count }}</strong> 已确认技能</span>
        <span><strong>{{ baseline.verified_fact_count }}</strong> 事实证据</span>
      </div>
    </header>

    <div class="baseline-stacks">
      <article
        v-for="stack in baseline.technology_stacks"
        :key="stack.key"
        class="baseline-stack"
      >
        <div class="stack-top">
          <span class="stack-mark">{{ stack.label.slice(0, 1) }}</span>
          <div>
            <strong>{{ stack.label }}</strong>
            <small>{{ stack.standard_job_count }} 个标准岗位 · {{ stack.source_count }} 条来源</small>
          </div>
        </div>
        <div class="stack-skills">
          <span v-for="skill in stack.top_skills.slice(0, 6)" :key="skill">{{ skill }}</span>
          <span v-if="stack.top_skills.length === 0" class="empty-skill">暂无已确认技能</span>
        </div>
      </article>
    </div>

    <div class="baseline-reference-head">
      <div>
        <strong>岗位参考标准</strong>
        <span>至少 {{ baseline.minimum_source_count }} 条独立来源后进入基线</span>
      </div>
      <div class="baseline-filters">
        <el-input
          v-model="keyword"
          clearable
          size="small"
          placeholder="筛选标准岗位或技能"
          :prefix-icon="Search"
        />
        <el-select v-model="stackFilter" size="small" style="width: 140px">
          <el-option label="全部技术栈" value="" />
          <el-option
            v-for="stack in baseline.technology_stacks"
            :key="stack.key"
            :label="stack.label"
            :value="stack.key"
          />
        </el-select>
      </div>
    </div>

    <el-table :data="filteredStandards" stripe size="small" max-height="360">
      <el-table-column prop="name" label="标准岗位" min-width="190" />
      <el-table-column prop="stack_label" label="技术栈" width="120" />
      <el-table-column label="级别" width="90" align="center">
        <template #default="{ row }">{{ levelLabel(row.level) }}</template>
      </el-table-column>
      <el-table-column prop="source_count" label="独立来源" width="90" align="center" />
      <el-table-column label="核心技能" min-width="260">
        <template #default="{ row }">
          <div class="standard-skills">
            <el-tag
              v-for="skill in row.core_skills.slice(0, 5)"
              :key="skill"
              size="small"
              effect="plain"
            >
              {{ skill }}
            </el-tag>
            <span v-if="row.core_skills.length === 0">暂无已确认技能</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="观测区间" width="190">
        <template #default="{ row }">
          <span class="baseline-date">{{ dateText(row.first_seen_at) }} → {{ dateText(row.last_seen_at) }}</span>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { Search } from "@element-plus/icons-vue";
import type { AnalysisBaseline } from "@/domain/types";

const props = defineProps<{ baseline: AnalysisBaseline | null }>();
const keyword = ref("");
const stackFilter = ref("");

const filteredStandards = computed(() => {
  const needle = keyword.value.trim().toLocaleLowerCase();
  return (props.baseline?.job_standards ?? []).filter((standard) => {
    if (stackFilter.value && standard.stack !== stackFilter.value) return false;
    if (!needle) return true;
    return [
      standard.name,
      standard.stack_label,
      ...standard.aliases,
      ...standard.core_skills,
    ].join(" ").toLocaleLowerCase().includes(needle);
  });
});

function levelLabel(level: string) {
  return ({ junior: "初级", middle: "中级", senior: "高级", expert: "专家" } as Record<string, string>)[level] ?? level;
}

function dateText(value: string) {
  return value ? value.slice(0, 10) : "—";
}
</script>

<style scoped>
.baseline-panel {
  margin-bottom: 16px;
  overflow: hidden;
}
.baseline-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 22px 24px 18px;
  border-bottom: 1px solid var(--color-border);
  background:
    linear-gradient(120deg, color-mix(in srgb, var(--color-brand) 9%, transparent), transparent 52%),
    var(--color-bg-elevated);
}
.baseline-kicker {
  margin-bottom: 5px;
  color: var(--color-brand);
  font: 700 11px/1.4 var(--font-mono);
  letter-spacing: .11em;
}
.baseline-head h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
}
.baseline-head p {
  max-width: 720px;
  margin: 7px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.65;
}
.baseline-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(108px, 1fr));
  gap: 8px;
  min-width: 250px;
}
.baseline-metrics span {
  padding: 9px 11px;
  border: 1px solid color-mix(in srgb, var(--color-brand) 18%, var(--color-border));
  border-radius: 10px;
  background: color-mix(in srgb, var(--color-bg-elevated) 90%, var(--color-brand));
  color: var(--text-secondary);
  font-size: 11px;
}
.baseline-metrics strong {
  margin-right: 4px;
  color: var(--color-brand);
  font: 700 15px/1 var(--font-mono);
}
.baseline-stacks {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 10px;
  padding: 16px 24px;
}
.baseline-stack {
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg-elevated);
}
.stack-top {
  display: flex;
  align-items: center;
  gap: 10px;
}
.stack-mark {
  display: grid;
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  place-items: center;
  border-radius: 9px;
  background: color-mix(in srgb, var(--color-brand) 13%, transparent);
  color: var(--color-brand);
  font-weight: 800;
}
.stack-top strong,
.stack-top small {
  display: block;
}
.stack-top strong {
  color: var(--text-primary);
  font-size: 13px;
}
.stack-top small {
  margin-top: 3px;
  color: var(--text-tertiary);
  font-size: 10px;
}
.stack-skills,
.standard-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.stack-skills {
  margin-top: 12px;
}
.stack-skills span {
  padding: 3px 7px;
  border-radius: 6px;
  background: var(--color-bg);
  color: var(--text-secondary);
  font-size: 10px;
}
.stack-skills .empty-skill,
.standard-skills > span {
  color: var(--text-tertiary);
}
.baseline-reference-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 15px 24px 11px;
  border-top: 1px solid var(--color-border);
}
.baseline-reference-head strong,
.baseline-reference-head span {
  display: block;
}
.baseline-reference-head strong {
  color: var(--text-primary);
  font-size: 14px;
}
.baseline-reference-head span {
  margin-top: 3px;
  color: var(--text-tertiary);
  font-size: 11px;
}
.baseline-filters {
  display: flex;
  gap: 8px;
  width: min(410px, 50%);
}
.baseline-date {
  color: var(--text-secondary);
  font: 11px/1.4 var(--font-mono);
}
@media (max-width: 900px) {
  .baseline-head,
  .baseline-reference-head {
    flex-direction: column;
  }
  .baseline-metrics,
  .baseline-filters {
    width: 100%;
  }
}
</style>

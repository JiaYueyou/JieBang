<template>
  <section v-if="baseline" class="baseline-panel dash-card">
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
        <span>岗位成熟度按独立岗位簇与持续月份判定，来源多样性单独展示</span>
      </div>
      <div class="baseline-filters">
        <el-input
          v-model="keyword"
          clearable
          size="small"
          placeholder="筛选标准岗位或技能"
          :prefix-icon="Search"
          @keyup.enter="loadStandards(1)"
          @clear="loadStandards(1)"
        />
        <el-select v-model="stackFilter" size="small" style="width: 140px" @change="loadStandards(1)">
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

    <el-table v-loading="standardsLoading" :data="standards" stripe size="small" max-height="360">
      <el-table-column prop="name" label="标准岗位" min-width="190" />
      <el-table-column prop="stack_label" label="技术栈" width="120" />
      <el-table-column label="级别" width="90" align="center">
        <template #default="{ row }">{{ levelLabel(row.level) }}</template>
      </el-table-column>
      <el-table-column label="生命周期" width="100" align="center">
        <template #default="{ row }">
          <el-tag
            :type="row.maturity_stage === 'mature' ? 'success' : row.maturity_stage === 'established' ? 'info' : 'warning'"
            size="small"
            effect="plain"
          >{{ maturityLabel(row.maturity_stage) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="source_count" label="岗位证据" width="90" align="center" />
      <el-table-column prop="active_period_count" label="持续月份" width="90" align="center" />
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
    <div class="baseline-pagination">
      <el-pagination
        v-if="standardsTotal > 0"
        background
        layout="total, sizes, prev, pager, next"
        :current-page="standardsPage"
        :page-size="standardsPageSize"
        :page-sizes="[10, 20, 50]"
        :total="standardsTotal"
        @current-change="loadStandards"
        @size-change="changePageSize"
      />
      <span v-else-if="!standardsLoading">暂无符合条件的岗位参考标准</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { Search } from "@element-plus/icons-vue";
import { dataProvider } from "@/data";
import type { AnalysisBaseline, JobReferenceStandard } from "@/domain/types";

const props = defineProps<{ baseline: AnalysisBaseline | null }>();
const keyword = ref("");
const stackFilter = ref("");
const standards = ref<JobReferenceStandard[]>([]);
const standardsLoading = ref(false);
const standardsPage = ref(1);
const standardsPageSize = ref(20);
const standardsTotal = ref(0);
let loadSequence = 0;

async function loadStandards(page = standardsPage.value) {
  if (!props.baseline) return;
  const sequence = ++loadSequence;
  standardsLoading.value = true;
  try {
    const result = await dataProvider.trends.listReferenceStandards({
      page,
      pageSize: standardsPageSize.value,
      keyword: keyword.value.trim() || undefined,
      stack: stackFilter.value || undefined,
    });
    if (sequence !== loadSequence) return;
    standards.value = result.items;
    standardsPage.value = result.page;
    standardsTotal.value = result.total;
  } catch (error) {
    if (sequence === loadSequence) {
      standards.value = [];
      standardsTotal.value = 0;
      ElMessage.error(error instanceof Error ? error.message : "岗位参考标准加载失败");
    }
  } finally {
    if (sequence === loadSequence) standardsLoading.value = false;
  }
}

function changePageSize(size: number) {
  standardsPageSize.value = size;
  void loadStandards(1);
}

watch(() => props.baseline, (baseline) => {
  if (baseline) void loadStandards(1);
  else {
    standards.value = [];
    standardsTotal.value = 0;
  }
}, { immediate: true });

function levelLabel(level: string) {
  return ({ junior: "初级", middle: "中级", senior: "高级", expert: "专家" } as Record<string, string>)[level] ?? level;
}

function maturityLabel(stage: string) {
  return ({ mature: "已成熟", established: "已稳定", observed: "观察中" } as Record<string, string>)[stage] ?? "观察中";
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
.baseline-pagination {
  display: flex;
  min-height: 54px;
  align-items: center;
  justify-content: flex-end;
  padding: 10px 24px 14px;
  border-top: 1px solid var(--color-border);
  color: var(--text-tertiary);
  font-size: 12px;
}
@media (max-width: 900px) {
  .baseline-reference-head {
    flex-direction: column;
  }
  .baseline-filters {
    width: 100%;
  }
}
</style>

<template>
  <div>
    <DataState :loading="loading" :error="error" @retry="store.refresh()" />
    <!-- Stats -->
    <div class="tr-stats anim-fade-up">
      <div class="tr-stat"><span class="tr-num">{{ stats.totalJobs }}</span><span class="tr-label">累计岗位数</span></div>
      <div class="tr-stat"><span class="tr-num brand">{{ stats.newSkills }}</span><span class="tr-label">已确认新技能（当前窗口）</span></div>
      <div class="tr-stat"><span class="tr-num green">{{ stats.avgSalary }}</span><span class="tr-label">平均薪资</span></div>
      <div class="tr-stat"><span class="tr-num amber">{{ stats.activeCities }}</span><span class="tr-label">活跃城市</span></div>
    </div>

    <!-- Filter -->
    <div class="dash-card anim-fade-up anim-delay-1" style="margin-bottom:16px;">
      <div class="dash-card-body" style="padding:12px 20px;">
        <div class="tr-filter-row">
          <el-select v-model="timeRange" size="default" style="width:130px;">
            <el-option label="近 15 天" value="15d" />
            <el-option label="近 1 个月" value="1m" />
            <el-option label="近 3 个月" value="3m" />
            <el-option label="近 6 个月" value="6m" />
          </el-select>
          <el-input v-model="jobFilter" placeholder="筛选岗位" clearable size="default" style="width:180px;" />
          <el-select v-model="cityFilter" size="default" style="width:130px;" clearable placeholder="城市">
            <el-option label="全国" value="" /><el-option label="北京" value="北京" />
            <el-option label="上海" value="上海" /><el-option label="深圳" value="深圳" />
            <el-option label="杭州" value="杭州" /><el-option label="成都" value="成都" />
          </el-select>
          <span class="tr-hint">{{ coverageText }}</span>
        </div>
      </div>
    </div>

    <ReferenceBaseline :baseline="data?.baseline ?? null" class="anim-fade-up anim-delay-1" />

    <el-alert
      v-if="dataQuality?.insufficient_data"
      class="tr-quality-alert anim-fade-up anim-delay-1"
      type="warning"
      :closable="false"
      show-icon
      :title="dataQuality.notes.join(' ') || '当前统计窗口数据不足。'"
    />
    <div v-if="dataQuality" class="tr-evidence-strip anim-fade-up anim-delay-1">
      <span><strong>{{ dataQuality.total_records }}</strong> 原始观测</span>
      <span><strong>{{ dataQuality.deduplicated_records }}</strong> 去重岗位</span>
      <span><strong>{{ dataQuality.independent_job_clusters }}</strong> 独立岗位簇</span>
      <span><strong>{{ dataQuality.independent_companies }}</strong> 独立企业</span>
      <span><strong>{{ dataQuality.reviewable_skill_facts ?? dataQuality.verified_skill_facts }}</strong> 可复核技能事实</span>
      <span v-if="dataQuality.duplicate_records"><strong>{{ dataQuality.duplicate_records }}</strong> 条转载/重复已合并</span>
    </div>

    <!-- Chart grid -->
    <div class="tr-chart-grid anim-fade-up anim-delay-2">
      <div class="dash-card">
        <div class="dash-card-header"><span class="dash-card-title">岗位需求趋势</span><span class="dash-card-badge">{{ windowLabel }}</span></div>
        <div class="dash-card-body"><v-chart :option="jobDemandOption" autoresize style="height:300px;" /></div>
      </div>
      <div class="dash-card">
        <div class="dash-card-header"><span class="dash-card-title">薪资趋势</span><span class="dash-card-badge">月薪·K</span></div>
        <div class="dash-card-body"><v-chart :option="salaryOption" autoresize style="height:300px;" /></div>
      </div>
      <div class="dash-card">
        <div class="dash-card-header"><span class="dash-card-title">技能热度热力图</span><span class="dash-card-badge">频次</span></div>
        <div class="dash-card-body"><v-chart :option="skillHeatOption" autoresize style="height:300px;" /></div>
      </div>
      <div class="dash-card">
        <div class="dash-card-header"><span class="dash-card-title">地域需求分布</span><span class="dash-card-badge">岗位数</span></div>
        <div class="dash-card-body"><v-chart :option="locationOption" autoresize style="height:300px;" /></div>
      </div>
    </div>

    <!-- Emerging skills -->
    <div class="dash-card anim-fade-up anim-delay-3" style="margin-top:16px;">
      <div class="dash-card-header">
        <div>
          <span class="dash-card-title">技术变化候选</span>
          <span class="tr-header-note">结合冻结历史基线与成熟技术目录，按跨企业、跨来源和持续性分级</span>
        </div>
        <span class="dash-card-badge">{{ emergingTotal }} 项技术判定</span>
      </div>
      <div
        v-loading="isPageLoading"
        class="dash-card-body"
        style="padding-top:12px;"
        :element-loading-text="pageLoadingText"
        element-loading-background="rgba(255, 255, 255, 0.72)"
      >
        <el-table :data="emergingSkills" style="width:100%" size="default" stripe>
          <el-table-column prop="skill" label="技能名称" min-width="160" />
          <el-table-column label="分类" width="120" align="center">
            <template #default="{ row }">{{ skillCategoryLabel(row.category) }}</template>
          </el-table-column>
          <el-table-column label="热度趋势" width="200" align="center">
            <template #default="{ row }">
              <v-chart :option="sparkOption(row)" autoresize style="height:36px;width:170px;" />
            </template>
          </el-table-column>
          <el-table-column label="趋势评分" width="100" align="center">
            <template #default="{ row }">
              <span :style="{ color: row.trend_score >= 75 ? 'var(--color-success)' : row.trend_score >= 55 ? 'var(--color-warning)' : 'var(--text-secondary)', fontWeight: 700, fontFamily: 'var(--font-mono)' }">
                {{ row.trend_score }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="本期 / 历史" width="120" align="center">
            <template #default="{ row }">
              <span class="trend-evidence-count">{{ row.current_count }} / {{ row.previous_count }}</span>
            </template>
          </el-table-column>
          <el-table-column label="市场证据" width="150" align="center">
            <template #default="{ row }">{{ row.current_companies }}家 · {{ row.current_sources }}源 · {{ row.current_periods }}期</template>
          </el-table-column>
          <el-table-column prop="evidence_note" label="变化证据" min-width="260" show-overflow-tooltip />
          <el-table-column prop="stage" label="生命周期" width="150" align="center">
            <template #default="{ row }">
              <el-tag :type="row.stage === '新出现' ? 'success' : row.stage.includes('待确认') ? 'warning' : 'info'" size="small">{{ row.stage }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div class="tr-pagination-row">
          <el-pagination
            v-model:current-page="emergingPage"
            :page-size="emergingPageSize"
            :total="emergingTotal"
            layout="total, prev, pager, next"
            @current-change="loadEmergingPage"
          />
        </div>
      </div>
    </div>

    <!-- New jobs -->
    <div class="dash-card anim-fade-up anim-delay-3" style="margin-top:16px;">
      <div class="dash-card-header">
        <span class="dash-card-title">新增岗位一览（含待确认）</span>
        <span class="dash-card-badge">{{ newJobsTotal }} 项</span>
      </div>
      <div
        v-loading="isPageLoading"
        class="dash-card-body"
        style="padding-top:12px;"
        :element-loading-text="pageLoadingText"
        element-loading-background="rgba(255, 255, 255, 0.72)"
      >
        <div class="tr-section-tools">
          <el-input
            v-model="newJobFilter"
            clearable
            placeholder="搜索岗位、技能或说明"
            style="width:300px;"
            @clear="searchNewJobs"
            @keyup.enter="searchNewJobs"
          />
          <el-button type="primary" @click="searchNewJobs">搜索</el-button>
          <span v-if="newJobObservationTotal > newJobsTotal" class="tr-hint">
            另有 {{ newJobObservationTotal - newJobsTotal }} 个岗位观察信号未展示
          </span>
        </div>
        <el-table :data="newJobs" style="width:100%" size="default" stripe>
          <el-table-column prop="name" label="岗位名称" min-width="180" />
          <el-table-column label="核心技能" min-width="220">
            <template #default="{ row }">
              <span v-for="skill in (row.core_skills || [])" :key="skill" class="tr-skill-chip">{{ skill }}</span>
              <span v-if="!(row.core_skills || []).length" class="tr-hint">暂无已确认技能</span>
            </template>
          </el-table-column>
          <el-table-column prop="source_count" label="独立来源" width="100" align="center" />
          <el-table-column prop="description" label="说明" min-width="240" show-overflow-tooltip />
        </el-table>
        <div v-if="!newJobsTotal" class="tr-hint" style="padding:8px 2px;">当前窗口内没有相对历史对照期首次出现的岗位</div>
        <div v-else class="tr-pagination-row">
          <el-pagination
            v-model:current-page="newJobPage"
            :page-size="newJobPageSize"
            :total="newJobsTotal"
            layout="total, prev, pager, next"
            @current-change="loadNewJobPage"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { LineChart, BarChart, HeatmapChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent, VisualMapComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { useTrendStore } from "@/stores/trends";
import DataState from "@/components/common/DataState.vue";
import ReferenceBaseline from "@/components/analysis/ReferenceBaseline.vue";
import type { TrendQuery } from "@/domain/types";
import { skillCategoryLabel } from "@/utils/displayLabels";

use([LineChart, BarChart, HeatmapChart, GridComponent, TooltipComponent, LegendComponent, VisualMapComponent, CanvasRenderer]);

const PALETTE = ["#4f6ef6","#34b37e","#f59e4b","#7c6ff7","#5b9df5","#e85d5d"];
const timeRange = ref<TrendQuery["window"]>("3m");
const jobFilter = ref("");
const cityFilter = ref("");
const newJobFilter = ref("");
const route = useRoute();

const store = useTrendStore();
const { data, loading, error } = storeToRefs(store);
const months = computed(() => data.value?.months ?? []);
const stats = computed(() => data.value?.stats ?? { totalJobs:"0",newSkills:0,avgSalary:"0",activeCities:0 });
const emergingSkills = computed(() => data.value?.emergingSkills ?? []);
const emergingTotal = computed(() => data.value?.emergingTotal ?? 0);
const newJobs = computed(() => data.value?.newJobs ?? []);
const newJobsTotal = computed(() => data.value?.newJobsTotal ?? 0);
const newJobObservationTotal = computed(() => data.value?.newJobObservationTotal ?? 0);
const dataQuality = computed(() => data.value?.dataQuality ?? null);
const windowLabel = computed(() => data.value?.windowLabel ?? "近 3 个月");
const coverageText = computed(() => {
  const quality = dataQuality.value;
  if (!quality?.coverage_start || !quality?.coverage_end) return "暂无可统计的岗位时间范围";
  return `覆盖 ${quality.coverage_start.slice(0, 10)} 至 ${quality.coverage_end.slice(0, 10)} · ${quality.total_records} 条岗位`;
});

const emergingPage = ref(1);
const emergingPageSize = ref(10);
const newJobPage = ref(1);
const newJobPageSize = ref(10);
const isPageLoading = ref(false);
const pageLoadingText = ref("正在加载趋势数据…");
let loadSequence = 0;

async function loadTrends() {
  const sequence = ++loadSequence;
  isPageLoading.value = true;
  try {
    await store.load({
      window: timeRange.value,
      keyword: jobFilter.value.trim() || undefined,
      city: cityFilter.value || undefined,
      emergingPage: emergingPage.value,
      emergingPageSize: emergingPageSize.value,
      newJobPage: newJobPage.value,
      newJobPageSize: newJobPageSize.value,
      newJobKeyword: newJobFilter.value.trim() || undefined,
    });
  } finally {
    if (sequence === loadSequence) isPageLoading.value = false;
  }
}

function searchNewJobs() {
  newJobPage.value = 1;
  pageLoadingText.value = "正在搜索新增岗位…";
  void loadTrends();
}

function loadEmergingPage(page: number) {
  emergingPage.value = page;
  pageLoadingText.value = `正在加载新兴技能第 ${page} 页…`;
  void loadTrends();
}

function loadNewJobPage(page: number) {
  newJobPage.value = page;
  pageLoadingText.value = `正在加载新增岗位第 ${page} 页…`;
  void loadTrends();
}

let filterTimer: number | undefined;
watch([timeRange, jobFilter, cityFilter], () => {
  // 筛选条件变化时回到第一页，避免停留在越界页
  emergingPage.value = 1;
  newJobPage.value = 1;
  pageLoadingText.value = "正在更新筛选结果…";
  window.clearTimeout(filterTimer);
  filterTimer = window.setTimeout(() => void loadTrends(), 350);
});

onMounted(() => {
  if (typeof route.query.keyword === "string") jobFilter.value = route.query.keyword;
  void loadTrends();
});

// ── Job demand option ──
const jobDemandOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { bottom: 15, textStyle: { fontSize: 12 } },
  grid: { left: 12, right: 20, top: 8, bottom: 60 },
  xAxis: { type: "category", data: months.value, axisLabel: { fontSize: 10, hideOverlap: true } },
  yAxis: { type: "value", axisLabel: { fontSize: 10 } },
  series: (data.value?.jobDemand ?? []).map((series,index)=>({name:series.name,type:"line",data:series.values,smooth:true,lineStyle:{width:2},itemStyle:{color:PALETTE[index]}})),
}));

// ── Salary option ──
const salaryOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { bottom: 15, textStyle: { fontSize: 12 } },
  grid: { left: 12, right: 20, top: 8, bottom: 60 },
  xAxis: { type: "category", data: months.value, axisLabel: { fontSize: 10, hideOverlap: true } },
  yAxis: { type: "value", name: "K", axisLabel: { fontSize: 10 } },
  series: (data.value?.salary ?? []).map((series,index)=>({name:series.name,type:"line",data:series.values,smooth:true,lineStyle:{width:2},itemStyle:{color:PALETTE[index]}})),
}));

// ── Skill heat map ──
const skillHeatOption = computed(() => ({
  tooltip: { formatter: (p: any) => `${p.value[1]} · ${p.value[0]} : ${p.value[2]} 次` },
  grid: { left: 80, right: 40, top: 8, bottom: 24 },
  xAxis: { type: "category", data: months.value, axisLabel: { fontSize: 10, hideOverlap: true }, position: "top" },
  yAxis: { type: "category", data: data.value?.heatmapSkills ?? [], axisLabel: { fontSize: 11 }, inverse: true },
  visualMap: { min: 0, max: 200, calculable: true, orient: "vertical", right: 0, top: 6, bottom: 6, textStyle: { fontSize: 10 }, inRange: { color: ["#f0f4ff","#c8d6fb","#8fa8f4","#4f6ef6","#1a3a8a"] } },
  series: [{
    type: "heatmap",
    data: (data.value?.heatmap ?? []).map((point)=>[point.x,point.y,point.value]),
    label: { show: true, fontSize: 10 },
  }],
}));

// ── Location ──
const locationOption = computed(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 12, right: 20, top: 4, bottom: 4 },
  xAxis: { type: "value", axisLabel: { fontSize: 10 } },
  yAxis: { type: "category", data: (data.value?.locations ?? []).map((item)=>item.city), inverse: true, axisLabel: { fontSize: 11 } },
  series: [{
    type: "bar", data: (data.value?.locations ?? []).map((item)=>item.value),
    itemStyle: { borderRadius: [0, 4, 4, 0], color: { type: "linear", x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: "#c8d6fb" },{ offset: 1, color: PALETTE[0] }] } },
    barWidth: 18,
  }],
}));

// ── Sparkline ──
function sparkOption(row: any) {
  return {
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { type: "category", show: false, data: ["","","","","",""] },
    yAxis: { type: "value", show: false, min: 0 },
    series: [{ type: "line", data: row.sparkline, smooth: true, lineStyle: { width: 1.5, color: row.growth === null ? "var(--color-warning)" : row.growth > 0 ? "var(--color-success)" : "var(--color-danger)" }, showSymbol: false, areaStyle: { color: row.growth === null ? "rgba(245,158,75,.15)" : row.growth > 0 ? "rgba(52,179,126,.15)" : "rgba(232,93,93,.15)" } }],
  };
}

</script>

<style scoped>
.tr-quality-alert {
  margin: -4px 0 16px;
  border-radius: 12px;
}
.tr-evidence-strip {
  display:flex;
  flex-wrap:wrap;
  gap:10px;
  margin:-4px 0 16px;
}
.tr-evidence-strip span {
  padding:8px 12px;
  border:1px solid var(--color-border);
  border-radius:10px;
  background:var(--color-bg-elevated);
  color:var(--text-secondary);
  font-size:12px;
}
.tr-evidence-strip strong {
  margin-right:4px;
  color:var(--color-brand);
  font-family:var(--font-mono);
}
.trend-evidence-count {
  color:var(--text-primary);
  font-family:var(--font-mono);
  font-weight:700;
}
.tr-skill-chip {
  display:inline-block;
  margin:2px 6px 2px 0;
  padding:2px 10px;
  border-radius:999px;
  background:var(--color-bg-elevated);
  border:1px solid var(--color-border);
  color:var(--color-brand);
  font-size:12px;
}
.tr-header-note {
  margin-left:10px;
  color:var(--text-secondary);
  font-size:12px;
  font-weight:400;
}
.tr-section-tools {
  display:flex;
  align-items:center;
  gap:10px;
  margin:0 0 12px;
}
.tr-pagination-row {
  display:flex;
  justify-content:flex-end;
  margin-top:12px;
}
</style>

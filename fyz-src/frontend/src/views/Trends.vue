<template>
  <div>
    <DataState :loading="loading" :error="error" @retry="store.refresh()" />
    <!-- Stats -->
    <div class="tr-stats anim-fade-up">
      <div class="tr-stat"><span class="tr-num">{{ stats.totalJobs }}</span><span class="tr-label">累计岗位数</span></div>
      <div class="tr-stat"><span class="tr-num brand">{{ stats.newSkills }}</span><span class="tr-label">新兴技能 (月)</span></div>
      <div class="tr-stat"><span class="tr-num green">{{ stats.avgSalary }}</span><span class="tr-label">平均薪资</span></div>
      <div class="tr-stat"><span class="tr-num amber">{{ stats.activeCities }}</span><span class="tr-label">活跃城市</span></div>
    </div>

    <!-- Filter -->
    <div class="dash-card anim-fade-up anim-delay-1" style="margin-bottom:16px;">
      <div class="dash-card-body" style="padding:12px 20px;">
        <div class="tr-filter-row">
          <el-select v-model="timeRange" size="default" style="width:130px;">
            <el-option label="近 6 个月" value="6" /><el-option label="近 12 个月" value="12" />
            <el-option label="近 24 个月" value="24" />
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

    <el-alert
      v-if="dataQuality?.insufficient_data"
      class="tr-quality-alert anim-fade-up anim-delay-1"
      type="warning"
      :closable="false"
      show-icon
      :title="dataQuality.notes.join(' ') || '当前统计窗口数据不足。'"
    />

    <!-- Chart grid -->
    <div class="tr-chart-grid anim-fade-up anim-delay-2">
      <div class="dash-card">
        <div class="dash-card-header"><span class="dash-card-title">岗位需求趋势</span><span class="dash-card-badge">{{ timeRange }} 个月</span></div>
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
      <div class="dash-card-header"><span class="dash-card-title">新兴技能一览</span><span class="dash-card-badge">{{ emergingSkills.length }} 项</span></div>
      <div class="dash-card-body" style="padding-top:12px;">
        <el-table :data="emergingSkills" style="width:100%" size="default" stripe>
          <el-table-column prop="skill" label="技能名称" min-width="160" />
          <el-table-column prop="category" label="分类" width="120" align="center" />
          <el-table-column label="热度趋势" width="200" align="center">
            <template #default="{ row }">
              <v-chart :option="sparkOption(row)" autoresize style="height:36px;width:170px;" />
            </template>
          </el-table-column>
          <el-table-column prop="growth" label="增长率" width="100" align="center">
            <template #default="{ row }">
              <span :style="{ color: row.growth > 0 ? 'var(--color-success)' : 'var(--color-danger)', fontWeight: 700, fontFamily: 'var(--font-mono)' }">
                {{ row.growth > 0 ? '+' : '' }}{{ row.growth }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="stage" label="生命周期" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="row.stage === '成长期' ? 'success' : row.stage === '成熟期' ? '' : 'warning'" size="small">{{ row.stage }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
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

use([LineChart, BarChart, HeatmapChart, GridComponent, TooltipComponent, LegendComponent, VisualMapComponent, CanvasRenderer]);

const PALETTE = ["#4f6ef6","#34b37e","#f59e4b","#7c6ff7","#5b9df5","#e85d5d"];
const timeRange = ref("12");
const jobFilter = ref("");
const cityFilter = ref("");
const route = useRoute();

const store = useTrendStore();
const { data, loading, error } = storeToRefs(store);
const months = computed(() => data.value?.months ?? []);
const stats = computed(() => data.value?.stats ?? { totalJobs:"0",newSkills:0,avgSalary:"0",activeCities:0 });
const emergingSkills = computed(() => data.value?.emergingSkills ?? []);
const dataQuality = computed(() => data.value?.dataQuality ?? null);
const coverageText = computed(() => {
  const quality = dataQuality.value;
  if (!quality?.coverage_start || !quality?.coverage_end) return "暂无可统计的岗位时间范围";
  return `覆盖 ${quality.coverage_start.slice(0, 10)} 至 ${quality.coverage_end.slice(0, 10)} · ${quality.total_records} 条岗位`;
});

function loadTrends() {
  return store.load({
    months: Number(timeRange.value),
    keyword: jobFilter.value.trim() || undefined,
    city: cityFilter.value || undefined,
  });
}

let filterTimer: number | undefined;
watch([timeRange, jobFilter, cityFilter], () => {
  window.clearTimeout(filterTimer);
  filterTimer = window.setTimeout(loadTrends, 350);
});

onMounted(() => {
  if (typeof route.query.keyword === "string") jobFilter.value = route.query.keyword;
  loadTrends();
});

// ── Job demand option ──
const jobDemandOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { bottom: 0, textStyle: { fontSize: 12 } },
  grid: { left: 12, right: 20, top: 8, bottom: 32 },
  xAxis: { type: "category", data: months.value.slice(0, Number(timeRange.value)), axisLabel: { fontSize: 10 } },
  yAxis: { type: "value", axisLabel: { fontSize: 10 } },
  series: (data.value?.jobDemand ?? []).map((series,index)=>({name:series.name,type:"line",data:series.values.slice(0,Number(timeRange.value)),smooth:true,lineStyle:{width:2},itemStyle:{color:PALETTE[index]}})),
}));

// ── Salary option ──
const salaryOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { bottom: 0, textStyle: { fontSize: 12 } },
  grid: { left: 12, right: 20, top: 8, bottom: 32 },
  xAxis: { type: "category", data: months.value.slice(0, Number(timeRange.value)), axisLabel: { fontSize: 10 } },
  yAxis: { type: "value", name: "K", axisLabel: { fontSize: 10 } },
  series: (data.value?.salary ?? []).map((series,index)=>({name:series.name,type:"line",data:series.values.slice(0,Number(timeRange.value)),smooth:true,lineStyle:{width:2},itemStyle:{color:PALETTE[index]}})),
}));

// ── Skill heat map ──
const skillHeatOption = computed(() => ({
  tooltip: { formatter: (p: any) => `${p.value[1]} · ${p.value[0]} : ${p.value[2]} 次` },
  grid: { left: 80, right: 40, top: 8, bottom: 24 },
  xAxis: { type: "category", data: months.value.slice(0, Number(timeRange.value)), axisLabel: { fontSize: 10 }, position: "top" },
  yAxis: { type: "category", data: data.value?.heatmapSkills ?? [], axisLabel: { fontSize: 11 }, inverse: true },
  visualMap: { min: 0, max: 200, calculable: true, orient: "vertical", right: 0, top: 6, bottom: 6, textStyle: { fontSize: 10 }, inRange: { color: ["#f0f4ff","#c8d6fb","#8fa8f4","#4f6ef6","#1a3a8a"] } },
  series: [{
    type: "heatmap",
    data: (data.value?.heatmap ?? []).filter((point)=>point.x<Number(timeRange.value)).map((point)=>[point.x,point.y,point.value]),
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
    series: [{ type: "line", data: row.sparkline, smooth: true, lineStyle: { width: 1.5, color: row.growth > 0 ? "var(--color-success)" : "var(--color-danger)" }, showSymbol: false, areaStyle: { color: row.growth > 0 ? "rgba(52,179,126,.15)" : "rgba(232,93,93,.15)" } }],
  };
}

</script>

<style scoped>
.tr-quality-alert {
  margin: -4px 0 16px;
  border-radius: 12px;
}
</style>

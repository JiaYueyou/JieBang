<template>
  <div>
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
          <span class="tr-hint">* 数据为模拟演示，后续接入 Neo4j 实时数据</span>
        </div>
      </div>
    </div>

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
import { ref, computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { LineChart, BarChart, HeatmapChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent, VisualMapComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

use([LineChart, BarChart, HeatmapChart, GridComponent, TooltipComponent, LegendComponent, VisualMapComponent, CanvasRenderer]);

const PALETTE = ["#4f6ef6","#34b37e","#f59e4b","#7c6ff7","#5b9df5","#e85d5d"];
const months = ["01月","02月","03月","04月","05月","06月","07月","08月","09月","10月","11月","12月"];
const timeRange = ref("12");
const jobFilter = ref("");
const cityFilter = ref("");

const stats = { totalJobs: "12,847", newSkills: 23, avgSalary: "18.5K", activeCities: 36 };

// ── Job demand option ──
const jobDemandOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { bottom: 0, textStyle: { fontSize: 12 } },
  grid: { left: 12, right: 20, top: 8, bottom: 32 },
  xAxis: { type: "category", data: months.slice(0, Number(timeRange.value)), axisLabel: { fontSize: 10 } },
  yAxis: { type: "value", axisLabel: { fontSize: 10 } },
  series: [
    { name: "Java", type: "line", data: [120,132,101,134,90,145,160,155,140,162,150,170].slice(0, Number(timeRange.value)), smooth: true, lineStyle: { width: 2 }, itemStyle: { color: PALETTE[0] }, areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(79,110,246,.25)" },{ offset: 1, color: "rgba(79,110,246,.02)" }] } } },
    { name: "Python", type: "line", data: [80,90,95,100,110,125,130,135,128,145,140,155].slice(0, Number(timeRange.value)), smooth: true, lineStyle: { width: 2 }, itemStyle: { color: PALETTE[1] }, areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(52,179,126,.20)" },{ offset: 1, color: "rgba(52,179,126,.02)" }] } } },
    { name: "AI", type: "line", data: [30,35,42,55,62,78,85,90,95,110,120,140].slice(0, Number(timeRange.value)), smooth: true, lineStyle: { width: 2 }, itemStyle: { color: PALETTE[2] }, areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(245,158,75,.25)" },{ offset: 1, color: "rgba(245,158,75,.02)" }] } } },
  ],
}));

// ── Salary option ──
const salaryOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { bottom: 0, textStyle: { fontSize: 12 } },
  grid: { left: 12, right: 20, top: 8, bottom: 32 },
  xAxis: { type: "category", data: months.slice(0, Number(timeRange.value)), axisLabel: { fontSize: 10 } },
  yAxis: { type: "value", name: "K", axisLabel: { fontSize: 10 } },
  series: [
    { name: "北京", type: "line", data: [22,23,22.5,24,24.5,25,26,25.5,26.5,27,28,29].slice(0, Number(timeRange.value)), smooth: true, lineStyle: { width: 2 }, itemStyle: { color: PALETTE[0] } },
    { name: "上海", type: "line", data: [20,21,21.5,22,23,23.5,24,24.5,25,26,26.5,27].slice(0, Number(timeRange.value)), smooth: true, lineStyle: { width: 2 }, itemStyle: { color: PALETTE[1] } },
    { name: "深圳", type: "line", data: [19,20,20.5,21,22,22.5,23,23.5,24,25,25.5,26].slice(0, Number(timeRange.value)), smooth: true, lineStyle: { width: 2 }, itemStyle: { color: PALETTE[2] } },
  ],
}));

// ── Skill heat map ──
const skillHeatOption = computed(() => ({
  tooltip: { formatter: (p: any) => `${p.value[1]} · ${p.value[0]} : ${p.value[2]} 次` },
  grid: { left: 80, right: 40, top: 8, bottom: 24 },
  xAxis: { type: "category", data: months.slice(0, Number(timeRange.value)), axisLabel: { fontSize: 10 }, position: "top" },
  yAxis: { type: "category", data: ["大模型应用","RAG","LangChain","K8s","FastAPI","Rust","WebAssembly","向量数据库"], axisLabel: { fontSize: 11 }, inverse: true },
  visualMap: { min: 0, max: 200, calculable: true, orient: "vertical", right: 0, top: 6, bottom: 6, textStyle: { fontSize: 10 }, inRange: { color: ["#f0f4ff","#c8d6fb","#8fa8f4","#4f6ef6","#1a3a8a"] } },
  series: [{
    type: "heatmap",
    data: [
      [0,"大模型应用",180],[1,"大模型应用",168],[2,"大模型应用",172],[3,"大模型应用",190],[4,"大模型应用",185],[5,"大模型应用",195],
      [0,"RAG",120],[1,"RAG",130],[2,"RAG",145],[3,"RAG",150],[4,"RAG",160],[5,"RAG",175],
      [0,"LangChain",80],[1,"LangChain",90],[2,"LangChain",105],[3,"LangChain",115],[4,"LangChain",125],[5,"LangChain",140],
      [0,"K8s",150],[1,"K8s",155],[2,"K8s",148],[3,"K8s",160],[4,"K8s",158],[5,"K8s",165],
      [0,"FastAPI",60],[1,"FastAPI",70],[2,"FastAPI",85],[3,"FastAPI",95],[4,"FastAPI",110],[5,"FastAPI",130],
      [0,"Rust",40],[1,"Rust",50],[2,"Rust",60],[3,"Rust",72],[4,"Rust",80],[5,"Rust",95],
      [0,"WebAssembly",20],[1,"WebAssembly",30],[2,"WebAssembly",42],[3,"WebAssembly",55],[4,"WebAssembly",65],[5,"WebAssembly",78],
      [0,"向量数据库",35],[1,"向量数据库",48],[2,"向量数据库",60],[3,"向量数据库",75],[4,"向量数据库",88],[5,"向量数据库",105],
    ].filter((d: any) => Number(d[0]) < Number(timeRange.value)),
    label: { show: true, fontSize: 10 },
  }],
}));

// ── Location ──
const locationOption = computed(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 12, right: 20, top: 4, bottom: 4 },
  xAxis: { type: "value", axisLabel: { fontSize: 10 } },
  yAxis: { type: "category", data: ["北京","上海","深圳","杭州","成都","广州","武汉","南京","西安","苏州"], inverse: true, axisLabel: { fontSize: 11 } },
  series: [{
    type: "bar", data: [3240,2850,2410,1980,1620,1480,1250,1120,980,860],
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

// ── Table data ──
const emergingSkills = ref([
  { skill: "大模型应用开发", category: "AI/ML", growth: 45, stage: "成长期", sparkline: [20,35,50,65,85,110] },
  { skill: "RAG 检索增强", category: "AI/ML", growth: 38, stage: "成长期", sparkline: [30,45,60,78,95,120] },
  { skill: "Kubernetes 编排", category: "云原生", growth: 22, stage: "成熟期", sparkline: [110,115,122,130,138,145] },
  { skill: "Rust 系统编程", category: "编程语言", growth: 18, stage: "成长期", sparkline: [25,32,40,48,56,68] },
  { skill: "WebAssembly", category: "前端", growth: 15, stage: "引入期", sparkline: [8,12,18,24,32,42] },
  { skill: "向量数据库", category: "数据库", growth: 28, stage: "成长期", sparkline: [15,25,38,52,65,82] },
]);
</script>

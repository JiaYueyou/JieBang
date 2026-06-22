<template>
  <div>
    <DataState :loading="loading" :error="error" @retry="store.refresh()" />
    <!-- ═══ Top: Hero Metrics ═══ -->
    <div class="db-hero anim-fade-up">
      <div class="db-hero-card" v-for="card in heroCards" :key="card.label">
        <div class="db-hero-top">
          <span class="db-hero-num" :class="card.color">{{ card.value }}</span>
          <span class="db-hero-change" :class="card.up ? 'up' : 'down'">{{ card.up ? '↑' : '↓' }}{{ card.change }}</span>
        </div>
        <div class="db-hero-label">{{ card.label }}</div>
        <button class="db-hero-action" :title="card.action" @click="$router.push(card.link)">
          <el-icon><Plus /></el-icon>
        </button>
      </div>
    </div>

    <!-- ═══ Middle: Execution Center ═══ -->
    <div class="db-exec-row anim-fade-up anim-delay-1">
      <!-- Left 70%: Kanban -->
      <div class="db-kanban">
        <div class="dash-card" style="height:100%;display:flex;flex-direction:column;">
          <div class="dash-card-header">
            <span class="dash-card-title">团队招聘看板</span>
            <span class="dash-card-badge">{{ kanban.length }} 个岗位</span>
          </div>
          <div class="dash-card-body" style="flex:1;overflow-y:auto;padding-top:8px;">
            <div class="db-kanban-item" v-for="job in kanban" :key="job.title">
              <div class="db-kanban-head">
                <span class="db-kanban-title">{{ job.title }}</span>
                <div class="db-kanban-actions">
                  <FavoriteButton type="job" :target-id="job.job_id" :title="job.title" compact />
                  <el-button text size="small" circle @click="$router.push('/jobs')"><el-icon><Edit /></el-icon></el-button>
                </div>
              </div>
              <div class="db-kanban-stages">
                <div class="db-stage" v-for="s in job.stages" :key="s.name" :style="{ flex: s.count ? 1 : 0 }">
                  <span class="db-stage-count">{{ s.count }}</span>
                  <span class="db-stage-name">{{ s.name }}</span>
                </div>
              </div>
              <div class="db-kanban-bar">
                <div
                  v-for="(s, i) in job.stages"
                  :key="i"
                  class="db-kanban-seg"
                  :style="{ width: (s.count / job.total * 100) + '%', background: ['var(--color-brand)', 'var(--color-success)', 'var(--color-warning)', '#7c6ff7'][i] }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right 30%: Match Radar -->
      <div class="db-match-col">
        <div class="dash-card" style="height:100%;display:flex;flex-direction:column;">
          <div class="dash-card-header">
            <span class="dash-card-title">智能匹配雷达</span>
            <router-link to="/matching" class="dash-card-badge" style="cursor:pointer;">查看全部</router-link>
          </div>
          <div class="dash-card-body" style="flex:1;overflow-y:auto;padding-top:8px;">
            <div
              class="db-match-item"
              v-for="item in alerts.slice(0, 6)"
              :key="item.id"
              @click="openTalent(item)"
            >
              <div class="db-match-avatar">{{ item.name.charAt(0) }}</div>
              <div class="db-match-body">
                <div class="db-match-name">
                  {{ item.name }}
                  <el-tag v-if="item.urgent" size="small" type="warning" effect="dark">急</el-tag>
                </div>
                <div class="db-match-pos">{{ item.position }}</div>
                <div class="db-match-gap" v-if="item.missing.length">
                  缺：<span v-for="s in item.missing.slice(0,2)" :key="s">{{ s }} </span>
                </div>
              </div>
              <div class="db-match-score">
                <div class="score-ring" :style="{ '--pct': item.score }"><span>{{ item.score }}%</span></div>
              </div>
              <FavoriteButton type="resume" :target-id="item.id" :title="item.name" compact />
              <el-popover placement="left" :width="240" trigger="hover" :show-after="400">
                <template #reference>
                  <button class="db-match-pop-btn"><el-icon><MoreFilled /></el-icon></button>
                </template>
                <div class="db-pop-content">
                  <div class="db-pop-row"><span>匹配度</span><strong>{{ item.score }}%</strong></div>
                  <div class="db-pop-row"><span>经验</span><strong>{{ item.experience }}</strong></div>
                  <div class="db-pop-row"><span>学历</span><strong>{{ item.education }}</strong></div>
                  <el-divider style="margin:8px 0;" />
                  <div class="db-pop-tags">
                    <el-tag v-for="s in item.missing" :key="s" size="small" type="danger" effect="plain">{{ s }}</el-tag>
                  </div>
                </div>
              </el-popover>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ Bottom: Market Insights ═══ -->
    <div class="db-insight-row anim-fade-up anim-delay-2">
      <!-- Left: Hot jobs with sparkline -->
      <div class="dash-card">
        <div class="dash-card-header">
          <span class="dash-card-title">IT 热门岗位风向标</span>
          <span class="dash-card-badge">近 6 个月</span>
        </div>
        <div class="dash-card-body" style="padding-top:8px;">
          <div class="db-hot-row db-hot-header">
            <span class="db-hot-col rank">#</span>
            <span class="db-hot-col name">岗位</span>
            <span class="db-hot-col chart">趋势</span>
            <span class="db-hot-col num">在招</span>
            <span class="db-hot-col trend">变化</span>
          </div>
          <div class="db-hot-row" v-for="(job, i) in hotJobs.slice(0, 6)" :key="i">
            <span class="db-hot-col rank" :class="{ top: i < 3 }">{{ i + 1 }}</span>
            <span class="db-hot-col name">{{ job.title }}</span>
            <span class="db-hot-col chart">
              <v-chart :option="sparkOption(job.spark)" autoresize style="height:28px;width:100px;" />
            </span>
            <span class="db-hot-col num" style="font-family:var(--font-mono);font-weight:600;">{{ job.demand }}</span>
            <span class="db-hot-col trend" :class="job.trend > 0 ? 'up' : 'down'" style="font-family:var(--font-mono);font-weight:700;">{{ job.trend > 0 ? '+' : '' }}{{ job.trend }}%</span>
            <FavoriteButton type="job" :target-id="job.job_id" :title="job.title" compact />
          </div>
        </div>
      </div>

      <!-- Right: Emerging skills -->
      <div class="dash-card">
        <div class="dash-card-header">
          <span class="dash-card-title">技能涌现捕捉器</span>
          <span class="dash-card-badge">AI 发现</span>
        </div>
        <div class="dash-card-body" style="padding-top:8px;">
          <div class="db-skill-list">
            <div class="db-skill-item" v-for="(sk, i) in emergingSkills" :key="i">
              <div class="db-skill-rank" :class="{ hot: i < 2 }">{{ i + 1 }}</div>
              <div class="db-skill-body">
                <div class="db-skill-name">{{ sk.name }}</div>
                <div class="db-skill-combo">{{ sk.combo }}</div>
              </div>
              <div class="db-skill-right">
                <span class="db-skill-growth" :class="sk.growth > 20 ? 'hot' : ''">↑{{ sk.growth }}%</span>
                <el-tag size="small" type="warning" effect="plain">{{ sk.confidence }}%</el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ Talent Drawer ═══ -->
    <el-drawer v-model="drawerVisible" :title="selectedTalent?.name" size="640px" destroy-on-close>
      <div v-if="selectedTalent" class="db-drawer">
        <div class="db-drawer-header">
          <div class="db-drawer-avatar">{{ selectedTalent.name.charAt(0) }}</div>
          <div>
            <h2>{{ selectedTalent.name }}</h2>
            <p>{{ selectedTalent.position }} · 匹配 {{ selectedTalent.score }}%</p>
          </div>
          <div class="score-ring" :style="{ '--pct': selectedTalent.score }">
            <span>{{ selectedTalent.score }}%</span>
          </div>
        </div>
        <el-divider />
        <div class="db-drawer-section">
          <h4>技能对比</h4>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div class="dash-card" style="padding:14px;">
              <h5 style="font-size:14px;color:var(--color-success);margin-bottom:8px;">✓ 已匹配</h5>
              <div style="display:flex;gap:5px;flex-wrap:wrap;">
                <el-tag v-for="s in selectedTalent.matched" :key="s" size="small" type="success" effect="plain">{{ s }}</el-tag>
              </div>
            </div>
            <div class="dash-card" style="padding:14px;">
              <h5 style="font-size:14px;color:var(--color-danger);margin-bottom:8px;">✗ 待补充</h5>
              <div style="display:flex;gap:5px;flex-wrap:wrap;">
                <el-tag v-for="s in selectedTalent.missing" :key="s" size="small" type="danger" effect="plain">{{ s }}</el-tag>
              </div>
            </div>
          </div>
        </div>
        <div class="db-drawer-section">
          <h4>基本信息</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="经验">{{ selectedTalent.experience }}</el-descriptions-item>
            <el-descriptions-item label="学历">{{ selectedTalent.education }}</el-descriptions-item>
            <el-descriptions-item label="部门">{{ selectedTalent.department }}</el-descriptions-item>
            <el-descriptions-item label="急缺">{{ selectedTalent.urgent ? '是' : '否' }}</el-descriptions-item>
          </el-descriptions>
        </div>
        <div class="db-drawer-section">
          <h4>匹配岗位</h4>
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
            <el-tag v-for="j in selectedTalent.targetJobs" :key="j" type="primary" effect="plain">{{ j }}</el-tag>
          </div>
        </div>
        <div class="db-drawer-footer">
          <el-button type="primary" size="large" style="width:100%;" @click="$router.push(`/matching/${selectedTalent.id}`);drawerVisible=false">
            查看完整匹配报告
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { storeToRefs } from "pinia";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { ArrowDown, Plus, Edit, MoreFilled } from "@element-plus/icons-vue";
import FavoriteButton from "@/components/common/FavoriteButton.vue";
import DataState from "@/components/common/DataState.vue";
import { useDashboardStore } from "@/stores/dashboard";
import type { TalentSummary } from "@/domain/types";

use([LineChart, GridComponent, CanvasRenderer]);

const drawerVisible = ref(false);
const selectedTalent = ref<TalentSummary | null>(null);
const store = useDashboardStore();
const { data, loading, error } = storeToRefs(store);
const heroCards = computed(() => data.value?.heroCards ?? []);
const kanban = computed(() => data.value?.kanban ?? []);
const alerts = computed(() => data.value?.highMatches ?? []);
const hotJobs = computed(() => data.value?.hotJobs ?? []);
const emergingSkills = computed(() => data.value?.emergingSkills ?? []);
onMounted(() => store.refresh());

function openTalent(item: TalentSummary) {
  selectedTalent.value = item;
  drawerVisible.value = true;
}

function sparkOption(data: number[]) {
  return {
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { type: "category", show: false, data: data.map(() => "") },
    yAxis: { type: "value", show: false },
    series: [{
      type: "line", data, smooth: true, showSymbol: false,
      lineStyle: { width: 1.5, color: data[data.length-1] > data[0] ? "var(--color-success)" : "var(--color-danger)" },
      areaStyle: { color: data[data.length-1] > data[0] ? "rgba(52,179,126,.15)" : "rgba(232,93,93,.10)" },
    }],
  };
}

</script>

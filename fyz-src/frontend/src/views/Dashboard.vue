<template>
  <div>
    <DataState :loading="loading" :error="error" @retry="store.refresh()" />
    <!-- ═══ Top: Hero Metrics ═══ -->
    <div class="db-hero anim-fade-up">
      <div class="db-hero-card" v-for="card in heroCards" :key="card.label">
        <div class="db-hero-top">
          <span class="db-hero-num" :class="card.color">{{ card.value }}</span>
          <span class="db-hero-change" :class="card.up ? 'up' : 'down'">{{ card.change }}</span>
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
        <div class="dash-card db-kanban-card">
          <div class="db-kanban-header">
            <div>
              <div class="db-kanban-heading">
                <span class="dash-card-title">团队招聘看板</span>
                <span class="dash-card-badge">{{ kanban.length }} 个在招岗位</span>
              </div>
              <p>当前账号人才池与在招岗位的有效匹配覆盖</p>
            </div>
            <router-link to="/matching" class="db-board-link">
              进入人才匹配
              <el-icon><ArrowRight /></el-icon>
            </router-link>
          </div>

          <div class="db-board-summary">
            <div
              v-for="metric in kanbanMetrics"
              :key="metric.label"
              class="db-board-metric"
              :class="`is-${metric.tone}`"
            >
              <span class="db-board-metric-label">{{ metric.label }}</span>
              <strong>{{ metric.value }}</strong>
              <span class="db-board-metric-unit">{{ metric.unit }}</span>
            </div>
          </div>

          <div class="db-kanban-body">
            <div v-if="!kanban.length" class="db-board-empty">
              <div class="db-board-empty-mark">00</div>
              <div>
                <strong>暂无在招岗位</strong>
                <p>发布岗位后，这里会展示人才池覆盖与匹配分层。</p>
              </div>
              <router-link to="/jobs">管理岗位</router-link>
            </div>

            <article
              v-for="(job, index) in kanban"
              v-else
              :key="job.job_id"
              class="db-kanban-item"
            >
              <div class="db-kanban-head">
                <div class="db-kanban-identity">
                  <span class="db-kanban-index">{{ String(index + 1).padStart(2, "0") }}</span>
                  <div>
                    <div class="db-kanban-title-row">
                      <span class="db-kanban-title">{{ job.title }}</span>
                      <span v-if="job.urgent" class="db-urgent-tag">急招</span>
                    </div>
                    <div class="db-kanban-meta">
                      <span>{{ job.department }}</span>
                      <i></i>
                      <span>{{ job.location }}</span>
                      <i></i>
                      <span>需求 {{ job.headcount }} 人</span>
                    </div>
                  </div>
                </div>
                <div class="db-kanban-actions">
                  <FavoriteButton type="job" :target-id="job.job_id" :title="job.title" compact />
                  <el-button text size="small" circle title="管理岗位" @click="$router.push('/jobs')">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </div>
              </div>

              <div class="db-kanban-overview">
                <div class="db-coverage-block">
                  <div class="db-coverage-value">{{ job.coverage }}<span>%</span></div>
                  <span>评估覆盖率</span>
                  <small>{{ job.evaluated }} / {{ job.total }} 份人才档案</small>
                </div>
                <div class="db-kanban-stages">
                  <div
                    class="db-stage"
                    :class="`is-${stage.kind}`"
                    v-for="stage in job.stages"
                    :key="stage.kind"
                  >
                    <span class="db-stage-dot"></span>
                    <span class="db-stage-count">{{ stage.count }}</span>
                    <span class="db-stage-name">{{ stage.name }}</span>
                  </div>
                </div>
              </div>

              <div class="db-kanban-bar">
                <div
                  v-for="stage in job.stages"
                  :key="stage.kind"
                  class="db-kanban-seg"
                  :class="`is-${stage.kind}`"
                  :style="{ width: stageRate(job.total, stage.count) + '%' }"
                ></div>
              </div>

              <div v-if="job.total === 0" class="db-kanban-notice is-neutral">
                <span>人才池暂无可评估档案，岗位需求信息仍保留展示。</span>
                <router-link to="/matching">上传简历</router-link>
              </div>
              <div v-else-if="job.pending > 0" class="db-kanban-notice">
                <span>
                  <strong>{{ job.pending }} 份</strong>
                  人才尚未针对该岗位生成有效匹配快照
                </span>
                <button
                  type="button"
                  :disabled="recalculating"
                  @click="recalculateDashboardMatches"
                >
                  {{ recalculating ? "评估中…" : "开始评估" }}
                </button>
              </div>

              <div class="db-kanban-skills">
                <span class="db-kanban-skills-label">关键技能</span>
                <span v-if="!job.skills.length" class="db-kanban-no-skill">尚未配置</span>
                <span v-for="skill in job.skills" :key="skill" class="db-kanban-skill">{{ skill }}</span>
              </div>
            </article>
          </div>
        </div>
      </div>

      <!-- Right 30%: Match Radar -->
      <div class="db-match-col">
        <div class="dash-card db-match-card">
          <div class="dash-card-header">
            <span class="dash-card-title">智能匹配雷达</span>
            <router-link to="/matching" class="dash-card-badge" style="cursor:pointer;">查看全部</router-link>
          </div>
          <div class="dash-card-body" style="flex:1;overflow-y:auto;padding-top:8px;">
            <div
              class="db-match-item"
              v-for="item in alerts"
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
                  <span class="db-match-gap-label">缺：</span>
                  <span
                    v-for="s in item.missing.slice(0, 2)"
                    :key="s"
                    class="db-match-gap-skill"
                  >
                    {{ s }}
                  </span>
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
            <div v-if="!alerts.length" class="db-match-empty">
              <span class="db-match-empty-code">NO ACTIVE MATCH</span>
              <strong>暂无有效岗位匹配</strong>
              <p>现有人才档案尚未针对当前在招岗位生成有效匹配快照。</p>
              <button
                type="button"
                :disabled="recalculating"
                @click="recalculateDashboardMatches"
              >
                {{ recalculating ? "正在重新评估…" : "重新评估人才池" }}
              </button>
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
          <span class="dash-card-badge">近 6 个月 · {{ hotJobsTotal }} 个岗位</span>
        </div>
        <div class="dash-card-body db-module-scroll" style="padding-top:8px;">
          <div class="db-hot-row db-hot-header">
            <span class="db-hot-col rank">#</span>
            <span class="db-hot-col name">岗位</span>
            <span class="db-hot-col chart">趋势</span>
            <span class="db-hot-col num">岗位数</span>
            <span class="db-hot-col trend">本月</span>
            <span class="db-hot-col action"></span>
          </div>
          <div class="db-hot-row" v-for="(job, i) in hotJobs" :key="job.standard_job_id">
            <span class="db-hot-col rank" :class="{ top: (hotJobsPage - 1) * hotJobsPageSize + i < 3 }">{{ (hotJobsPage - 1) * hotJobsPageSize + i + 1 }}</span>
            <span class="db-hot-col name">
              {{ job.title }}
              <el-tag
                v-if="job.lifecycle_stage !== 'observed'"
                :type="job.lifecycle_stage === 'mature' ? 'success' : 'info'"
                size="small"
                effect="plain"
                style="margin-left:6px;vertical-align:middle;"
              >{{ job.lifecycle_stage === 'mature' ? '已成熟' : '已稳定' }}</el-tag>
              <span v-if="job.core_skills?.length" class="db-hot-skills">{{ job.core_skills.slice(0, 3).join(" · ") }}</span>
            </span>
            <span class="db-hot-col chart">
              <v-chart :option="sparkOption(job.spark)" autoresize style="height:28px;width:100px;" />
            </span>
            <span class="db-hot-col num" style="font-family:var(--font-mono);font-weight:600;">{{ job.demand }}</span>
            <span class="db-hot-col trend" :class="job.trend > 0 ? 'up' : job.trend < 0 ? 'down' : ''" style="font-family:var(--font-mono);font-weight:700;">{{ job.trend > 0 ? '+' : '' }}{{ job.trend }}</span>
            <el-tooltip content="风向标是市场标准岗位聚合，请进入岗位管理后收藏具体的在招岗位" placement="top">
              <el-button text type="primary" size="small" @click="$router.push('/jobs')">查看在招</el-button>
            </el-tooltip>
          </div>
          <div class="db-pagination-row">
            <el-pagination
              v-model:current-page="hotJobsPage"
              :page-size="hotJobsPageSize"
              :total="hotJobsTotal"
              layout="total, prev, pager, next"
              @current-change="loadDashboard"
            />
          </div>
        </div>
      </div>

      <!-- Right: Emerging skills -->
      <div class="dash-card">
        <div class="dash-card-header">
          <span class="dash-card-title">技能涌现捕捉器</span>
          <span class="dash-card-badge">AI 发现 · {{ emergingSkillsTotal }} 项</span>
        </div>
        <div class="dash-card-body db-module-scroll" style="padding-top:8px;">
          <div class="db-skill-list">
            <div class="db-skill-item" v-for="(sk, i) in emergingSkills" :key="i">
              <div class="db-skill-rank" :class="{ hot: (emergingPage - 1) * emergingPageSize + i < 2 }">{{ (emergingPage - 1) * emergingPageSize + i + 1 }}</div>
              <div class="db-skill-body">
                <div class="db-skill-name">{{ sk.name }}</div>
                <div class="db-skill-combo">{{ skillSummaryLabel(sk.combo) }}</div>
              </div>
              <div class="db-skill-right">
                <span class="db-skill-growth" :class="{ hot: sk.growth > 0 }">近30天 +{{ sk.growth }} 条</span>
                <el-tag size="small" type="warning" effect="plain">{{ sk.confidence }}%</el-tag>
              </div>
            </div>
          </div>
          <div class="db-pagination-row">
            <el-pagination
              v-model:current-page="emergingPage"
              :page-size="emergingPageSize"
              :total="emergingSkillsTotal"
              layout="total, prev, pager, next"
              @current-change="loadDashboard"
            />
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
import { ElMessage } from "element-plus";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { ArrowRight, Plus, Edit, MoreFilled } from "@element-plus/icons-vue";
import FavoriteButton from "@/components/common/FavoriteButton.vue";
import DataState from "@/components/common/DataState.vue";
import { dataProvider } from "@/data";
import { useDashboardStore } from "@/stores/dashboard";
import type { DashboardOverview, TalentSummary } from "@/domain/types";
import { skillSummaryLabel } from "@/utils/displayLabels";

use([LineChart, GridComponent, CanvasRenderer]);

const drawerVisible = ref(false);
const recalculating = ref(false);
const selectedTalent = ref<TalentSummary | null>(null);
const store = useDashboardStore();
const { data, loading, error } = storeToRefs(store);
const heroCards = computed(() => data.value?.heroCards ?? []);
const kanban = computed(() => data.value?.kanban ?? []);
const alerts = computed(() => data.value?.highMatches ?? []);
const hotJobs = computed(() => data.value?.hotJobs ?? []);
const hotJobsTotal = computed(() => data.value?.hotJobsTotal ?? 0);
const emergingSkills = computed(() => data.value?.emergingSkills ?? []);
const emergingSkillsTotal = computed(() => data.value?.emergingSkillsTotal ?? 0);

const hotJobsPage = ref(1);
const hotJobsPageSize = ref(10);
const emergingPage = ref(1);
const emergingPageSize = ref(10);

function loadDashboard() {
  void store.load({
    hotJobsPage: hotJobsPage.value,
    hotJobsPageSize: hotJobsPageSize.value,
    emergingPage: emergingPage.value,
    emergingPageSize: emergingPageSize.value,
  }, true);
}
const kanbanSummary = computed(() => {
  const jobs = kanban.value;
  const headcount = jobs.reduce((sum, job) => sum + job.headcount, 0);
  const talentPool = jobs.reduce((max, job) => Math.max(max, job.total), 0);
  const evaluated = jobs.reduce((sum, job) => sum + job.evaluated, 0);
  const pending = jobs.reduce((sum, job) => sum + job.pending, 0);
  return { headcount, talentPool, evaluated, pending };
});
const kanbanMetrics = computed(() => [
  { label: "需求席位", value: kanbanSummary.value.headcount, unit: "人", tone: "brand" },
  { label: "当前人才池", value: kanbanSummary.value.talentPool, unit: "份", tone: "ink" },
  { label: "已完成评估", value: kanbanSummary.value.evaluated, unit: "项", tone: "success" },
  { label: "等待评估", value: kanbanSummary.value.pending, unit: "项", tone: "warning" },
]);
onMounted(() => loadDashboard());

function openTalent(item: TalentSummary) {
  selectedTalent.value = item;
  drawerVisible.value = true;
}

function stageRate(total: DashboardOverview["kanban"][number]["total"], count: number) {
  return total ? count / total * 100 : 0;
}

async function recalculateDashboardMatches() {
  if (recalculating.value) return;
  recalculating.value = true;
  try {
    const result = await dataProvider.talents.recalculate();
    await store.refresh();
    if (result.matches_upserted > 0) {
      ElMessage.success(
        `已重新评估 ${result.resumes_processed} 份人才档案，更新 ${result.matches_upserted} 项匹配`,
      );
    } else {
      ElMessage.warning("当前没有可评估的人才档案或在招岗位");
    }
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : "人才池评估失败");
  } finally {
    recalculating.value = false;
  }
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

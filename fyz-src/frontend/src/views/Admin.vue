<template>
  <div class="admin-page">
    <DataState :loading="loading" :error="error" @retry="store.refresh()" />
    <nav class="admin-nav anim-fade-up">
      <div class="admin-nav-items">
        <button
          v-for="item in navItems"
          :key="item.value"
          type="button"
          :class="{ active: activeSection === item.value }"
          @click="selectSection(item.value)"
        >
          <span class="nav-icon"><el-icon><component :is="item.icon" /></el-icon></span>
          <span><strong>{{ item.label }}</strong><small>{{ item.desc }}</small></span>
          <i v-if="item.badge">{{ item.badge }}</i>
        </button>
      </div>
      <div class="admin-status">
        <span class="status-pulse"></span>
        <div><strong>系统运行正常</strong><small>最后巡检：刚刚</small></div>
        <button type="button" @click="refreshSystem"><el-icon><Refresh /></el-icon>刷新</button>
      </div>
    </nav>

    <!-- Overview -->
    <section v-if="activeSection === 'overview'" class="admin-section anim-fade-up">
      <div class="admin-metrics">
        <article v-for="metric in metrics" :key="metric.label" class="metric-card">
          <div class="metric-icon" :class="metric.tone"><el-icon><component :is="metric.icon" /></el-icon></div>
          <div class="metric-copy"><span>{{ metric.label }}</span><strong>{{ metric.value }}</strong><small :class="metric.trendTone">{{ metric.trend }}</small></div>
          <div class="metric-bars">
            <i v-for="(bar, index) in metric.bars" :key="index" :style="{ height: `${bar}%` }"></i>
          </div>
        </article>
      </div>

      <div class="overview-grid">
        <article class="admin-card service-health">
          <div class="card-heading">
            <div><span>服务状态</span><h2>核心依赖健康度</h2></div>
            <span class="healthy-chip">5 / 5 正常</span>
          </div>
          <div class="service-list">
            <div v-for="service in services" :key="service.name" class="service-row">
              <span class="service-logo" :class="service.tone"><el-icon><component :is="service.icon" /></el-icon></span>
              <div class="service-name"><strong>{{ service.name }}</strong><small>{{ service.desc }}</small></div>
              <div class="latency"><strong>{{ service.latency }}</strong><small>响应时间</small></div>
              <span class="service-state"><i></i>正常</span>
            </div>
          </div>
        </article>

        <article class="admin-card resource-card">
          <div class="card-heading">
            <div><span>服务器资源</span><h2>实时负载</h2></div>
            <span class="live-label"><i></i>LIVE</span>
          </div>
          <div class="resource-rings">
            <div v-for="resource in resources" :key="resource.label" class="resource-item">
              <div class="resource-ring" :style="{ '--value': resource.value, '--ring-color': resource.color }">
                <span>{{ resource.value }}<small>%</small></span>
              </div>
              <strong>{{ resource.label }}</strong>
              <small>{{ resource.detail }}</small>
            </div>
          </div>
          <div class="traffic-strip">
            <div><el-icon><Top /></el-icon><span>入站</span><strong>18.4 MB/s</strong></div>
            <div><el-icon><Bottom /></el-icon><span>出站</span><strong>7.2 MB/s</strong></div>
          </div>
        </article>

        <article class="admin-card task-card">
          <div class="card-heading">
            <div><span>任务动态</span><h2>最近采集任务</h2></div>
            <button type="button" @click="activeSection = 'crawler'">全部任务 <el-icon><ArrowRight /></el-icon></button>
          </div>
          <div class="task-list">
            <div v-for="task in recentTasks" :key="task.name" class="task-row">
              <span class="task-state" :class="task.status"><el-icon><component :is="task.icon" /></el-icon></span>
              <div><strong>{{ task.name }}</strong><small>{{ task.source }} · {{ task.time }}</small></div>
              <span class="task-count">{{ task.count }}</span>
              <span class="task-status" :class="task.status">{{ task.statusLabel }}</span>
            </div>
          </div>
        </article>

        <article class="admin-card event-card">
          <div class="card-heading">
            <div><span>系统事件</span><h2>需要关注</h2></div>
            <span class="event-count">3 项</span>
          </div>
          <div class="event-list">
            <button v-for="event in systemEvents" :key="event.title" type="button" @click="handleEvent(event)">
              <span class="event-level" :class="event.level"><el-icon><component :is="event.icon" /></el-icon></span>
              <span><strong>{{ event.title }}</strong><small>{{ event.desc }}</small></span>
              <time>{{ event.time }}</time>
            </button>
          </div>
        </article>
      </div>
    </section>

    <!-- Crawler -->
    <section v-else-if="activeSection === 'crawler'" class="admin-section anim-fade-up">
      <div class="section-heading">
        <div><span>DATA PIPELINE</span><h2>爬虫数据采集中心</h2><p>配置多源数据采集、调度周期、失败重试和数据质量规则。</p></div>
        <div class="section-actions">
          <el-button @click="showCrawlerSettings = true"><el-icon><Setting /></el-icon>全局策略</el-button>
          <el-button type="primary" @click="createSource"><el-icon><Plus /></el-icon>添加数据源</el-button>
        </div>
      </div>

      <div class="crawler-summary">
        <div><span>今日入库</span><strong>{{ pipelineSummary.todayImported }}</strong><small>数据库新增岗位</small></div>
        <div><span>有效数据率</span><strong class="green">{{ pipelineSummary.validRate.toFixed(1) }}%</strong><small>{{ pipelineSummary.validRecords }} / {{ pipelineSummary.totalJobs }} 条正文有效</small></div>
        <div><span>运行中任务</span><strong class="brand">{{ runningCrawlerCount }}</strong><small>共 {{ crawlers.length }} 个数据源</small></div>
        <div><span>失败任务</span><strong class="amber">{{ pipelineSummary.failedTasks }}</strong><small>今日导入任务</small></div>
      </div>

      <div v-if="lastImportResult" class="import-result" role="status">
        <div class="import-result-head">
          <div><span>最近一次数据闭环</span><strong>{{ lastImportResult.files.join("、") }}</strong></div>
          <span class="healthy-chip">job-v1 校验通过</span>
        </div>
        <div class="import-result-grid">
          <div><span>校验通过</span><strong>{{ validationPassed }}</strong></div>
          <div><span>质量警告</span><strong>{{ validationWarnings }}</strong></div>
          <div><span>成功入库</span><strong>{{ lastImportResult.imported }}</strong></div>
          <div><span>重复跳过</span><strong>{{ lastImportResult.duplicates }}</strong></div>
          <div><span>技能事实</span><strong>{{ lastImportResult.skill_facts }}</strong></div>
          <div><span>已验证事实</span><strong>{{ lastImportResult.verified_skill_facts }}</strong></div>
          <div><span>待验证事实</span><strong>{{ lastImportResult.unverified_skill_facts }}</strong></div>
        </div>
      </div>

      <div class="crawler-grid">
        <article v-for="crawler in crawlers" :key="crawler.id" class="crawler-card" :class="{ paused: !crawler.enabled }">
          <div class="crawler-head">
            <span class="source-logo" :class="crawler.tone">{{ crawler.short }}</span>
            <div><h3>{{ crawler.name }}</h3><p>{{ crawler.endpoint }}</p></div>
            <el-switch v-model="crawler.enabled" @change="toggleCrawler(crawler)" />
          </div>
          <div class="crawler-stats">
            <div><span>今日采集</span><strong>{{ crawler.today }}</strong></div>
            <div><span>成功率</span><strong>{{ crawler.success }}%</strong></div>
            <div><span>平均耗时</span><strong>{{ crawler.duration }}</strong></div>
          </div>
          <div class="crawler-progress">
            <div><span>{{ crawler.progress_info || (crawler.running ? "正在采集" : crawler.enabled ? "等待调度" : "任务已暂停") }}</span><strong>{{ crawler.progress }}%</strong></div>
            <el-progress :percentage="crawler.progress" :show-text="false" :status="crawler.enabled ? undefined : 'warning'" />
          </div>
          <div class="crawler-meta">
            <span><el-icon><Calendar /></el-icon>{{ crawler.schedule }}</span>
            <span><el-icon><Clock /></el-icon>下次 {{ crawler.nextRun }}</span>
          </div>
          <footer>
            <button type="button" :disabled="crawler.running || !crawler.enabled" @click="runCrawler(crawler)">
              <el-icon><VideoPlay /></el-icon>{{ crawler.running ? "运行中" : "采集并入库" }}
            </button>
            <button type="button" @click="editCrawler(crawler)"><el-icon><Edit /></el-icon>配置</button>
            <button type="button" @click="viewCrawlerLog(crawler)"><el-icon><Document /></el-icon>日志</button>
          </footer>
        </article>
      </div>

      <article class="admin-card quality-panel">
        <div class="card-heading">
          <div><span>数据质量</span><h2>最近 7 天清洗结果</h2></div>
          <span class="healthy-chip">总体质量 {{ pipelineSummary.overallQuality.toFixed(1) }}%</span>
        </div>
        <div class="quality-grid">
          <div v-for="quality in qualities" :key="quality.label">
            <span>{{ quality.label }}</span>
            <strong>{{ quality.value }}</strong>
            <el-progress :percentage="quality.percent" :show-text="false" :color="quality.color" />
            <small>{{ quality.note }}</small>
          </div>
        </div>
      </article>
    </section>

    <!-- Skill fact review -->
    <section v-else-if="activeSection === 'review'" class="admin-section anim-fade-up">
      <div class="review-summary">
        <button
          v-for="option in reviewStatusOptions"
          :key="option.value"
          type="button"
          :class="{ active: reviewStatus === option.value }"
          @click="changeReviewStatus(option.value)"
        >
          <span>{{ option.label }}</span><strong>{{ reviewSummary[option.countKey] }}</strong>
        </button>
      </div>

      <div class="review-toolbar">
        <el-input
          v-model="reviewKeyword"
          clearable
          placeholder="搜索技能、岗位或证据文本"
          @keyup.enter="reviewStore.load(true)"
          @clear="reviewStore.load(true)"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="reviewStore.load(true)">检索证据</el-button>
        <span>当前结果 {{ reviewTotal }} 条</span>
      </div>

      <DataState :loading="reviewLoading" :error="reviewError" @retry="reviewStore.load()" />

      <div v-if="!reviewLoading && !reviewError && reviewItems.length" class="review-grid">
        <article
          v-for="item in reviewItems"
          :key="item.id"
          class="review-card"
          :class="`review-${item.verification_status}`"
        >
          <header>
            <div><small>FACT / {{ String(item.id).padStart(4, "0") }}</small><h3>{{ item.skill_name }}</h3></div>
            <span :class="item.verification_status">{{ reviewStatusLabel(item.verification_status) }}</span>
          </header>
          <div class="review-job">
            <div><small>关联岗位</small><strong>{{ item.job_title }}</strong><span>{{ item.company || "企业信息未提供" }}</span></div>
            <a v-if="item.source_url" :href="item.source_url" target="_blank" rel="noreferrer">{{ item.source }} ↗</a>
            <span v-else>{{ item.source }}</span>
          </div>
          <blockquote><small>证据原文</small><p>“{{ item.evidence_text }}”</p></blockquote>
          <div class="review-signals">
            <span>置信度 <strong>{{ Math.round(item.confidence * 100) }}%</strong></span>
            <span>来源 <strong>{{ item.source_count }} 个</strong></span>
            <span>类型 <strong>{{ item.kind === "required" ? "必备" : "加分" }}</strong></span>
            <span>方式 <strong>{{ item.extraction_method === "llm" ? "Agent" : "规则" }}</strong></span>
          </div>
          <div v-if="item.verification_status !== 'unverified'" class="review-audit">
            <small>{{ item.reviewer_name || "管理员" }} · {{ formatReviewDate(item.reviewed_at) }}</small>
            <p>{{ item.review_note || "已完成审核" }}</p>
          </div>
          <footer v-else>
            <el-button type="danger" plain @click="openFactReject(item)">驳回事实</el-button>
            <el-button type="success" @click="approveFact(item)">确认证据</el-button>
          </footer>
        </article>
      </div>
      <el-empty
        v-else-if="!reviewLoading && !reviewError"
        :description="reviewStatus === 'unverified' ? '待审核事实已处理完毕' : '没有符合条件的事实'"
      />
      <el-pagination
        v-if="reviewTotalPages > 1"
        class="review-pagination"
        background
        layout="prev, pager, next"
        :current-page="reviewPage"
        :page-size="reviewPageSize"
        :total="reviewTotal"
        @current-change="changeReviewPage"
      />
    </section>

    <!-- Logs & Performance -->
    <section v-else-if="activeSection === 'monitor'" class="admin-section anim-fade-up">
      <div class="section-heading">
        <div><h2>运行日志与性能监控</h2><p>指标和事件均来自 MySQL 技能事实与异步任务审计记录。</p></div>
        <div class="section-actions">
          <el-button @click="store.refresh()"><el-icon><Refresh /></el-icon>刷新数据</el-button>
          <el-button @click="exportLogs"><el-icon><Download /></el-icon>导出日志</el-button>
        </div>
      </div>

      <div class="performance-grid">
        <article v-for="perf in performanceCards" :key="perf.label" class="performance-card">
          <span>{{ perf.label }}</span><strong>{{ perf.value }}</strong><small :class="perf.tone">{{ perf.note }}</small>
          <div class="spark-bars"><i v-for="(height, i) in perf.bars" :key="i" :style="{ height: `${height}%` }"></i></div>
        </article>
      </div>

      <div class="monitor-grid">
        <article class="admin-card endpoint-panel">
          <div class="card-heading"><div><span>真实接口</span><h2>数据覆盖情况</h2></div><span class="live-label"><i></i>数据库</span></div>
          <div class="endpoint-list">
            <div v-for="api in endpoints" :key="api.path">
              <span class="method" :class="api.method.toLowerCase()">{{ api.method }}</span>
              <code>{{ api.path }}</code>
              <div class="endpoint-bar"><i :style="{ width: `${api.percent}%` }"></i></div>
              <strong>{{ api.value }}</strong>
            </div>
          </div>
        </article>
      </div>

      <article class="admin-card log-panel">
        <div class="log-toolbar">
          <div><span>实时日志</span><h2>应用事件流</h2></div>
          <div>
            <el-select v-model="logLevel" clearable placeholder="全部级别" style="width:120px"><el-option label="INFO" value="INFO" /><el-option label="WARN" value="WARN" /><el-option label="ERROR" value="ERROR" /></el-select>
            <el-input v-model="logKeyword" clearable placeholder="搜索日志内容" style="width:220px"><template #prefix><el-icon><Search /></el-icon></template></el-input>
            <el-switch v-model="autoScroll" active-text="自动滚动" />
          </div>
        </div>
        <div class="log-console">
          <div v-for="log in filteredLogs" :key="log.id" class="log-line">
            <time>{{ log.time }}</time><span class="log-level" :class="log.level.toLowerCase()">{{ log.level }}</span><span class="log-service">{{ log.service }}</span><code>{{ log.message }}</code>
          </div>
          <el-empty v-if="!filteredLogs.length" description="暂无真实任务或审核事件" />
        </div>
      </article>
    </section>

    <el-dialog v-model="showCrawlerSettings" title="全局采集策略" width="520px">
      <el-form label-position="top">
        <el-form-item label="最大并发任务"><el-slider v-model="crawlerPolicy.concurrency" :min="1" :max="10" show-input /></el-form-item>
        <el-form-item label="失败重试次数"><el-input-number v-model="crawlerPolicy.retries" :min="0" :max="10" /></el-form-item>
        <el-form-item label="请求间隔（秒）"><el-input-number v-model="crawlerPolicy.interval" :min="1" :max="60" /></el-form-item>
        <el-form-item label="数据去重"><el-switch v-model="crawlerPolicy.deduplicate" active-text="写入前自动去重" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCrawlerSettings = false">取消</el-button><el-button type="primary" @click="saveCrawlerPolicy">保存策略</el-button></template>
    </el-dialog>

    <el-dialog v-model="showFactRejectDialog" title="驳回技能事实" width="520px">
      <div v-if="rejectFactTarget" class="reject-fact-context">
        <span>{{ rejectFactTarget.skill_name }}</span>
        <strong>{{ rejectFactTarget.job_title }}</strong>
        <p>驳回后该事实不会进入正式图谱，请填写可复核的原因。</p>
      </div>
      <el-input
        v-model="rejectFactNote"
        type="textarea"
        :rows="4"
        maxlength="500"
        show-word-limit
        placeholder="例如：原文仅描述业务场景，不能证明岗位要求该技能"
      />
      <template #footer>
        <el-button @click="showFactRejectDialog = false">取消</el-button>
        <el-button type="danger" :loading="factReviewing" @click="confirmFactReject">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { storeToRefs } from "pinia";
import { ElMessage, ElMessageBox } from "element-plus";
import { useAdminStore } from "@/stores/admin";
import { useSkillReviewsStore } from "@/stores/skillReviews";
import DataState from "@/components/common/DataState.vue";
import type {
  JobImportResult,
  SkillFactReviewItem,
  SkillFactReviewSummary,
  SkillFactVerificationStatus,
} from "@/domain/types";
import { classifyImportFailure, errorMessage } from "@/utils/crawlerFlowError";

type Section = "overview" | "crawler" | "review" | "monitor";

const activeSection = ref<Section>("overview");
const showCrawlerSettings = ref(false);
const logLevel = ref("");
const logKeyword = ref("");
const autoScroll = ref(true);
const lastImportResult = ref<JobImportResult | null>(null);
const store = useAdminStore();
const { data: admin, loading, error } = storeToRefs(store);
const reviewStore = useSkillReviewsStore();
const {
  items: reviewItems,
  summary: reviewSummary,
  status: reviewStatus,
  keyword: reviewKeyword,
  page: reviewPage,
  pageSize: reviewPageSize,
  total: reviewTotal,
  totalPages: reviewTotalPages,
  loading: reviewLoading,
  error: reviewError,
} = storeToRefs(reviewStore);
const showFactRejectDialog = ref(false);
const rejectFactTarget = ref<SkillFactReviewItem | null>(null);
const rejectFactNote = ref("");
const factReviewing = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;

onMounted(() => store.load());
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer); });

const navItems: { value: Section; label: string; desc: string; icon: string; badge?: string }[] = [
  { value: "overview", label: "运行总览", desc: "系统健康与关键指标", icon: "Odometer" },
  { value: "crawler", label: "采集中心", desc: "爬虫任务与数据质量", icon: "Download", badge: "4" },
  { value: "review", label: "事实审核", desc: "证据确认与驳回", icon: "DocumentChecked" },
  { value: "monitor", label: "日志与性能", desc: "真实事实与任务审计", icon: "DataLine" },
];
const reviewStatusOptions: Array<{
  value: SkillFactVerificationStatus | "all";
  label: string;
  countKey: keyof SkillFactReviewSummary;
}> = [
  { value: "unverified", label: "待审核", countKey: "unverified" },
  { value: "verified", label: "已确认", countKey: "verified" },
  { value: "rejected", label: "已驳回", countKey: "rejected" },
  { value: "all", label: "全部事实", countKey: "all" },
];

const metrics = computed(() => admin.value?.metrics ?? []);
const services = computed(() => admin.value?.services ?? []);
const resources = computed(() => admin.value?.resources ?? []);
const recentTasks = computed(() => admin.value?.recentTasks ?? []);
const systemEvents = computed(() => admin.value?.systemEvents ?? []);
const crawlers = computed(() => admin.value?.crawlers ?? []);
const qualities = computed(() => admin.value?.qualities ?? []);
const pipelineSummary = computed(() => admin.value?.pipelineSummary ?? {
  totalJobs: 0,
  todayImported: 0,
  sourceCount: 0,
  validRecords: 0,
  validRate: 0,
  failedTasks: 0,
  processedToday: 0,
  duplicatesToday: 0,
  verifiedFacts: 0,
  unverifiedFacts: 0,
  overallQuality: 0,
});
const crawlerPolicy = computed(() => admin.value?.crawlerPolicy ?? { concurrency:4,retries:3,interval:5,deduplicate:true });
const performanceCards = computed(() => admin.value?.performanceCards ?? []);
const endpoints = computed(() => admin.value?.endpoints ?? []);
const logs = computed(() => admin.value?.logs ?? []);
const runningCrawlerCount = computed(() => crawlers.value.filter((item) => item.running).length);
const validationPassed = computed(() => lastImportResult.value?.validation.reduce((sum, item) => sum + item.passed, 0) ?? 0);
const validationWarnings = computed(() => lastImportResult.value?.validation.reduce((sum, item) => sum + item.warning_count, 0) ?? 0);
const filteredLogs = computed(() => logs.value.filter((log) => (!logLevel.value || log.level === logLevel.value) && (!logKeyword.value || `${log.service} ${log.message}`.toLowerCase().includes(logKeyword.value.toLowerCase()))));

async function refreshSystem() { await store.refresh(); ElMessage.success("系统状态已刷新"); }
async function selectSection(section: Section) {
  activeSection.value = section;
  if (section === "review") await reviewStore.load(true);
  if (section === "monitor") await store.load(true);
}
function handleEvent(event: any) { ElMessage.info(`正在查看：${event.title}`); }
async function toggleCrawler(crawler: any) { await store.toggleCrawler(crawler.id); ElMessage.success(`${crawler.name}状态已更新`); }
async function runCrawler(crawler: any) {
  try {
    await store.runCrawler(crawler.id);
  } catch (error) {
    ElMessage.error(`${crawler.name}采集启动失败：${errorMessage(error)}`);
    return;
  }
  ElMessage.success(`${crawler.name}采集任务已启动`);
  // 自动轮询进度（每 2 秒刷新）
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const res: any = await store.pollCrawler(crawler.id);
      if (res?.done) {
        // 爬虫已结束（成功或失败）
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
        const result = res.result;
        if (result?.returncode !== 0) {
          // 失败：展示 stderr 里的错误
          const errMsg = result?.stderr || result?.stdout || "未知错误";
          ElMessage.error(`${crawler.name}采集失败：${errMsg.slice(0, 200)}`);
        } else {
          if (!result?.filename) {
            ElMessage.warning(`${crawler.name}采集完成，但没有生成新的数据文件`);
          } else {
            ElMessage.info(`${crawler.name}采集完成，正在执行 job-v1 校验和入库`);
            try {
              lastImportResult.value = await store.importCrawlerOutput(result.filename);
              ElMessage.success(
                `${crawler.name}闭环完成：入库 ${lastImportResult.value.imported} 条，重复 ${lastImportResult.value.duplicates} 条`,
              );
            } catch (error) {
              const stage = classifyImportFailure(error);
              ElMessage.error(`${crawler.name}${stage}：${errorMessage(error)}`);
            }
          }
        }
        await store.load(true);
      } else {
        // 仍在运行，刷新进度
        await store.load(true);
      }
    } catch (error) {
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
      ElMessage.error(`${crawler.name}状态轮询失败：${errorMessage(error)}`);
    }
  }, 2000);
}
function editCrawler(crawler: any) { ElMessage.info(`正在配置：${crawler.name}`); }
function viewCrawlerLog(crawler: any) { activeSection.value = "monitor"; logKeyword.value = crawler.name; }
function createSource() { ElMessage.info("添加数据源表单待后端数据源协议确定后接入"); }
function saveCrawlerPolicy() { showCrawlerSettings.value = false; ElMessage.success("全局采集策略已保存"); }
function exportLogs() {
  const content = filteredLogs.value
    .map((log) => [log.time, log.level, log.service, log.message].join("\t"))
    .join("\n");
  const url = URL.createObjectURL(new Blob([content], { type: "text/plain;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `事实任务审计-${new Date().toISOString().slice(0, 10)}.log`;
  anchor.click();
  URL.revokeObjectURL(url);
  ElMessage.success(`已导出 ${filteredLogs.value.length} 条真实审计记录`);
}
async function changeReviewStatus(value: SkillFactVerificationStatus | "all") {
  reviewStatus.value = value;
  await reviewStore.load(true);
}
async function changeReviewPage(value: number) {
  reviewPage.value = value;
  await reviewStore.load();
}
async function approveFact(item: SkillFactReviewItem) {
  try {
    await ElMessageBox.confirm(
      `确认“${item.skill_name}”与岗位原文证据一致，并允许进入正式图谱？`,
      "确认技能事实",
      { confirmButtonText: "确认通过", cancelButtonText: "再核对一下", type: "success" },
    );
    factReviewing.value = true;
    await reviewStore.review(item, "verified", "证据充分，人工确认");
    ElMessage.success("技能事实已确认");
  } catch (value) {
    if (value !== "cancel" && value !== "close") {
      ElMessage.error(errorMessage(value, "审核操作失败"));
    }
  } finally {
    factReviewing.value = false;
  }
}
function openFactReject(item: SkillFactReviewItem) {
  rejectFactTarget.value = item;
  rejectFactNote.value = "";
  showFactRejectDialog.value = true;
}
async function confirmFactReject() {
  if (!rejectFactTarget.value) return;
  if (!rejectFactNote.value.trim()) {
    ElMessage.warning("请填写驳回原因");
    return;
  }
  factReviewing.value = true;
  try {
    await reviewStore.review(
      rejectFactTarget.value,
      "rejected",
      rejectFactNote.value.trim(),
    );
    showFactRejectDialog.value = false;
    ElMessage.success("技能事实已驳回并记录原因");
  } catch (value) {
    ElMessage.error(errorMessage(value, "审核操作失败"));
  } finally {
    factReviewing.value = false;
  }
}
function reviewStatusLabel(value: SkillFactVerificationStatus) {
  return { unverified: "待审核", verified: "已确认", rejected: "已驳回" }[value];
}
function formatReviewDate(value: string | null) {
  if (!value) return "时间未记录";
  return new Date(value).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
</script>

<style scoped>
.admin-page{max-width:1480px;margin:0 auto;--admin-dark:#202437}.admin-status{display:flex;align-items:center;gap:10px;flex:0 0 auto;padding:9px 10px 9px 17px;border-left:1px solid var(--color-border);border-radius:0 9px 9px 0;background:var(--color-success-light)}.status-pulse{width:9px;height:9px;border-radius:50%;background:var(--color-success);box-shadow:0 0 0 5px rgba(52,179,126,.12)}.admin-status div{display:flex;flex-direction:column;margin-right:4px}.admin-status strong{font-size:14px;color:var(--text-primary)}.admin-status small{font-size:14px;color:var(--text-muted)}.admin-status button,.card-heading button{display:flex;align-items:center;gap:5px;border:0;background:#fff;border-radius:8px;padding:7px 9px;color:var(--text-secondary);font:600 14px var(--font-sans);cursor:pointer}
.admin-nav{display:flex;align-items:stretch;gap:7px;padding:7px;margin-bottom:17px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.admin-nav-items{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;min-width:0;flex:1}.admin-nav-items button{position:relative;display:flex;align-items:center;gap:10px;padding:10px;border:0;border-radius:10px;background:transparent;text-align:left;cursor:pointer;color:var(--text-secondary);transition:.2s}.admin-nav-items button:hover{background:var(--color-bg-muted)}.admin-nav-items button.active{background:var(--color-brand-light);color:var(--color-brand)}.nav-icon{display:grid;width:34px;height:34px;place-items:center;border-radius:9px;background:var(--color-bg-muted);font-size:16px}.admin-nav-items button.active .nav-icon{background:#fff}.admin-nav-items button>span:nth-child(2){display:flex;min-width:0;flex-direction:column}.admin-nav strong{font-size:14px}.admin-nav small{font-size:14px;color:var(--text-muted);margin-top:1px}.admin-nav-items button>i{position:absolute;right:8px;top:8px;min-width:17px;padding:1px 5px;border-radius:999px;background:var(--color-danger);color:#fff;font:700 14px var(--font-mono);text-align:center}
.admin-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:11px;margin-bottom:13px}.metric-card{display:flex;align-items:center;gap:11px;min-width:0;padding:16px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.metric-icon{display:grid;width:38px;height:38px;flex:0 0 38px;place-items:center;border-radius:11px;font-size:17px}.brand{background:var(--color-brand-light);color:var(--color-brand)}.green{background:var(--color-success-light);color:var(--color-success)}.amber{background:var(--color-warning-light);color:var(--color-warning)}.rose{background:var(--color-danger-light);color:var(--color-danger)}.violet{background:#f0edff;color:#7c6ff7}.blue{background:var(--color-info-light);color:var(--color-info)}.metric-copy{display:flex;min-width:0;flex:1;flex-direction:column}.metric-copy span{font-size:14px;color:var(--text-muted)}.metric-copy strong{font:700 22px var(--font-mono);letter-spacing:-.04em}.metric-copy small{font-size:14px}.positive,.green{color:var(--color-success)}.warning,.amber{color:var(--color-warning)}.metric-bars,.spark-bars{display:flex;align-items:flex-end;gap:2px;height:38px}.metric-bars i,.spark-bars i{width:3px;min-height:4px;border-radius:2px;background:var(--color-brand);opacity:.55}.overview-grid{display:grid;grid-template-columns:1.3fr .7fr;gap:13px}.admin-card{border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.card-heading{display:flex;align-items:center;justify-content:space-between;padding:16px 18px 11px}.card-heading>div{display:flex;flex-direction:column}.card-heading span,.section-heading>div>span{font:700 14px var(--font-mono);letter-spacing:.09em;color:var(--text-muted);text-transform:uppercase}.card-heading h2{font-size:14px;margin-top:2px}.healthy-chip,.event-count{padding:4px 8px;border-radius:999px;background:var(--color-success-light);color:var(--color-success)!important;font:700 14px var(--font-sans)!important;letter-spacing:0!important}.service-list,.task-list,.event-list{padding:0 18px 12px}.service-row,.task-row{display:flex;align-items:center;gap:10px;padding:10px 0}.service-row+.service-row,.task-row+.task-row{border-top:1px solid var(--color-border-light)}.service-logo,.task-state{display:grid;width:31px;height:31px;flex:0 0 31px;place-items:center;border-radius:9px}.service-name,.task-row>div{display:flex;min-width:0;flex:1;flex-direction:column}.service-name strong,.task-row strong{font-size:14px}.service-name small,.task-row small{font-size:14px;color:var(--text-muted)}.latency{display:flex;flex-direction:column;align-items:flex-end}.latency strong{font:600 14px var(--font-mono)}.latency small{font-size:14px;color:var(--text-muted)}.service-state{display:flex;align-items:center;gap:4px;color:var(--color-success);font-size:14px;font-weight:600}.service-state i,.live-label i{width:6px;height:6px;border-radius:50%;background:currentColor}.resource-card{padding-bottom:14px}.live-label{display:flex;align-items:center;gap:5px;color:var(--color-success)!important;font:700 14px var(--font-mono)!important}.resource-rings{display:flex;justify-content:space-around;padding:12px 15px 16px}.resource-item{display:flex;align-items:center;flex-direction:column}.resource-ring{display:grid;width:76px;height:76px;place-items:center;border-radius:50%;background:conic-gradient(var(--ring-color) calc(var(--value)*1%),var(--color-bg-muted) 0);position:relative}.resource-ring:before{content:"";position:absolute;inset:6px;border-radius:50%;background:#fff}.resource-ring span{z-index:1;font:700 17px var(--font-mono)}.resource-ring small{font-size:14px}.resource-item>strong{font-size:14px;margin-top:7px}.resource-item>small{font-size:14px;color:var(--text-muted)}.traffic-strip{display:grid;grid-template-columns:1fr 1fr;gap:7px;padding:0 15px}.traffic-strip div{display:flex;align-items:center;gap:6px;padding:9px;border-radius:8px;background:var(--color-bg-muted);font-size:14px}.traffic-strip strong{margin-left:auto;font:600 14px var(--font-mono)}.task-state.success{background:var(--color-success-light);color:var(--color-success)}.task-state.running{background:var(--color-brand-light);color:var(--color-brand)}.task-state.warning{background:var(--color-warning-light);color:var(--color-warning)}.task-count{font:600 14px var(--font-mono);color:var(--text-secondary)}.task-status{min-width:48px;text-align:right;font-size:14px;font-weight:700}.task-status.success{color:var(--color-success)}.task-status.running{color:var(--color-brand)}.task-status.warning{color:var(--color-warning)}.event-card .event-count{background:var(--color-danger-light);color:var(--color-danger)!important}.event-list button{display:flex;align-items:center;gap:9px;width:100%;padding:10px 0;border:0;border-top:1px solid var(--color-border-light);background:transparent;text-align:left;cursor:pointer}.event-level{display:grid;width:29px;height:29px;place-items:center;border-radius:8px}.event-level.warning{background:var(--color-warning-light)}.event-level.danger{background:var(--color-danger-light);color:var(--color-danger)}.event-level.info{background:var(--color-info-light);color:var(--color-info)}.event-list button>span:nth-child(2){display:flex;min-width:0;flex:1;flex-direction:column}.event-list strong{font-size:14px}.event-list small{font-size:14px;color:var(--text-muted)}.event-list time{font:500 14px var(--font-mono);color:var(--text-muted)}
.section-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin:8px 2px 16px}.section-heading h2{font-size:20px;letter-spacing:-.03em}.section-heading p{font-size:14px;color:var(--text-muted);margin-top:3px}.section-actions{display:flex;gap:8px}.crawler-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:13px}.crawler-summary>div{display:flex;flex-direction:column;padding:14px 16px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.crawler-summary span{font-size:14px;color:var(--text-muted)}.crawler-summary strong{font:700 20px var(--font-mono)}.crawler-summary small{font-size:14px;color:var(--text-muted)}.crawler-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:13px}.crawler-card{padding:16px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff;transition:.2s}.crawler-card.paused{opacity:.72;background:var(--color-bg-muted)}.crawler-head{display:flex;align-items:center;gap:10px}.source-logo{display:grid;width:39px;height:39px;place-items:center;border-radius:11px;background:var(--color-brand-light);color:var(--color-brand);font-weight:700}.crawler-head>div{min-width:0;flex:1}.crawler-head h3{font-size:14px}.crawler-head p{font-size:14px;color:var(--text-muted)}.crawler-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:14px 0}.crawler-stats div{display:flex;flex-direction:column;padding:8px;border-radius:8px;background:var(--color-bg-muted)}.crawler-stats span,.crawler-progress span,.crawler-meta{font-size:14px;color:var(--text-muted)}.crawler-stats strong{font:600 14px var(--font-mono)}.crawler-progress>div{display:flex;justify-content:space-between;margin-bottom:5px}.crawler-progress strong{font:600 14px var(--font-mono)}.crawler-meta{display:flex;justify-content:space-between;margin-top:9px}.crawler-meta span{display:flex;align-items:center;gap:4px}.crawler-card footer{display:flex;gap:5px;padding-top:11px;margin-top:11px;border-top:1px solid var(--color-border-light)}.crawler-card footer button{display:flex;align-items:center;justify-content:center;gap:4px;flex:1;height:29px;border:1px solid var(--color-border);border-radius:7px;background:#fff;color:var(--text-secondary);font:600 14px var(--font-sans);cursor:pointer}.crawler-card footer button:first-child{border-color:var(--color-brand);color:var(--color-brand)}.crawler-card footer button:disabled{opacity:.5;cursor:not-allowed}.quality-panel{padding-bottom:16px}.quality-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:2px 18px}.quality-grid>div{padding:12px;border-radius:9px;background:var(--color-bg-muted)}.quality-grid span{font-size:14px;color:var(--text-muted)}.quality-grid strong{display:block;font:700 17px var(--font-mono);margin:2px 0 7px}.quality-grid small{font-size:14px;color:var(--text-muted)}
.import-result{padding:16px;margin-bottom:13px;border:1px solid color-mix(in srgb,var(--color-success) 35%,var(--color-border));border-radius:var(--radius-lg);background:color-mix(in srgb,var(--color-success) 5%,#fff)}.import-result-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}.import-result-head>div{display:flex;flex-direction:column}.import-result-head span{font-size:13px;color:var(--text-muted)}.import-result-head strong{font-size:14px}.import-result-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}.import-result-grid>div{padding:9px 10px;border-radius:8px;background:#fff}.import-result-grid span{display:block;font-size:12px;color:var(--text-muted)}.import-result-grid strong{font:700 16px var(--font-mono)}
.review-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:11px;padding:6px;border:1px solid var(--color-border);border-radius:12px;background:#fff}.review-summary button{display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border:0;border-radius:8px;background:transparent;color:var(--text-secondary);font:600 13px var(--font-sans);cursor:pointer}.review-summary button.active{background:var(--color-brand-light);color:var(--color-brand)}.review-summary strong{padding:2px 7px;border-radius:999px;background:#fff;font:700 12px var(--font-mono)}.review-toolbar{display:flex;align-items:center;gap:8px;margin-bottom:12px}.review-toolbar .el-input{max-width:480px}.review-toolbar>span{margin-left:auto;font:600 12px var(--font-mono);color:var(--text-muted)}.review-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px}.review-card{position:relative;overflow:hidden;padding:17px 17px 14px 21px;border:1px solid var(--color-border);border-radius:13px;background:#fff;box-shadow:0 4px 14px rgba(32,36,55,.04)}.review-card:before{content:"";position:absolute;inset:0 auto 0 0;width:4px;background:var(--color-warning)}.review-card.review-verified:before{background:var(--color-success)}.review-card.review-rejected:before{background:var(--color-danger)}.review-card header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.review-card header small{font:600 11px var(--font-mono);letter-spacing:.08em;color:var(--text-muted)}.review-card h3{margin-top:2px;font-size:20px}.review-card header>span{padding:4px 8px;border-radius:999px;background:var(--color-warning-light);color:var(--color-warning);font-size:12px;font-weight:700}.review-card header>span.verified{background:var(--color-success-light);color:var(--color-success)}.review-card header>span.rejected{background:var(--color-danger-light);color:var(--color-danger)}.review-job{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:12px 0 10px;padding:9px 11px;border-radius:8px;background:var(--color-bg-muted)}.review-job>div{display:flex;min-width:0;flex-direction:column}.review-job small,.review-job>div>span{font-size:12px;color:var(--text-muted)}.review-job strong{overflow:hidden;font-size:14px;text-overflow:ellipsis;white-space:nowrap}.review-job>a,.review-job>span{flex:0 0 auto;color:var(--color-brand);font-size:12px;font-weight:700;text-decoration:none}.review-card blockquote{margin:0;padding:11px 12px;border:1px solid #e7eaf4;border-radius:9px;background:#fbfbfd}.review-card blockquote small{font:700 11px var(--font-mono);letter-spacing:.07em;color:var(--text-muted)}.review-card blockquote p{margin-top:5px;color:#34394a;font-size:13px;line-height:1.65}.review-signals{display:grid;grid-template-columns:repeat(4,1fr);gap:5px;margin-top:10px}.review-signals span{padding:7px;border-radius:7px;background:var(--color-bg-muted);font-size:11px;color:var(--text-muted)}.review-signals strong{display:block;margin-top:2px;font:700 12px var(--font-mono);color:var(--text-secondary)}.review-audit{margin-top:10px;padding:9px 11px;border-left:3px solid var(--color-border);background:var(--color-bg-muted)}.review-audit small{font:600 11px var(--font-mono);color:var(--text-muted)}.review-audit p{margin-top:3px;font-size:13px;color:var(--text-secondary)}.review-card footer{display:flex;justify-content:flex-end;gap:6px;margin-top:11px;padding-top:11px;border-top:1px solid var(--color-border-light)}.review-pagination{justify-content:center;margin-top:16px}.reject-fact-context{margin-bottom:12px;padding:11px;border-radius:9px;background:var(--color-bg-muted)}.reject-fact-context span{display:block;font:700 12px var(--font-mono);color:var(--color-danger)}.reject-fact-context strong{display:block;margin:3px 0;font-size:14px}.reject-fact-context p{font-size:13px;color:var(--text-muted)}
.performance-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:13px}.performance-card{position:relative;overflow:hidden;padding:15px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.performance-card>span{font-size:14px;color:var(--text-muted)}.performance-card>strong{display:block;font:700 20px var(--font-mono)}.performance-card>small{font-size:14px}.spark-bars{position:absolute;right:13px;bottom:13px;height:33px}.monitor-grid{margin-bottom:13px}.endpoint-list{padding:0 18px 14px}.endpoint-list>div{display:grid;grid-template-columns:54px 1.2fr 1fr 90px;gap:8px;align-items:center;padding:10px 0;border-top:1px solid var(--color-border-light)}.method{padding:2px 4px;border-radius:4px;font:700 12px var(--font-mono);text-align:center}.method.get{background:var(--color-success-light);color:var(--color-success)}.method.post{background:var(--color-brand-light);color:var(--color-brand)}.method.patch{background:var(--color-warning-light);color:var(--color-warning)}.endpoint-list code{overflow:hidden;font-size:14px;text-overflow:ellipsis}.endpoint-bar{height:4px;border-radius:999px;background:var(--color-bg-muted)}.endpoint-bar i{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,var(--color-brand),var(--color-success))}.endpoint-list strong{font:600 14px var(--font-mono);text-align:right}.log-panel{overflow:hidden}.log-toolbar{display:flex;align-items:center;justify-content:space-between;padding:14px 17px}.log-toolbar>div:first-child{display:flex;flex-direction:column}.log-toolbar span{font:700 14px var(--font-mono);color:var(--text-muted)}.log-toolbar h2{font-size:14px}.log-toolbar>div:last-child{display:flex;align-items:center;gap:7px}.log-console{max-height:340px;overflow:auto;padding:8px 12px 12px;background:#1d2130;color:#cfd5e6;font:14px/1.8 var(--font-mono)}.log-line{display:grid;grid-template-columns:118px 48px 150px 1fr;gap:8px;padding:3px 5px;border-radius:4px}.log-line:hover{background:rgba(255,255,255,.04)}.log-line time{color:#747d94}.log-level{font-weight:700}.log-level.info{color:#68b4ff}.log-level.warn{color:#f6b85d}.log-level.error{color:#ff7474}.log-service{overflow:hidden;color:#8e9abb;text-overflow:ellipsis;white-space:nowrap}.log-line code{color:#d8deec;white-space:normal}
@media(max-width:1200px){.admin-nav{flex-wrap:wrap}.admin-nav-items{grid-template-columns:repeat(2,1fr);flex-basis:100%}.admin-status{width:100%;justify-content:flex-end;border-top:1px solid var(--color-border-light);border-left:0;border-radius:0 0 9px 9px}.admin-metrics,.crawler-summary,.performance-grid{grid-template-columns:repeat(2,1fr)}.import-result-grid{grid-template-columns:repeat(3,1fr)}.overview-grid{grid-template-columns:1fr}}@media(max-width:900px){.review-grid{grid-template-columns:1fr}}@media(max-width:768px){.section-heading{align-items:stretch;flex-direction:column}.admin-nav-items{grid-template-columns:1fr 1fr}.crawler-grid{grid-template-columns:1fr}.quality-grid{grid-template-columns:1fr 1fr}.review-summary{grid-template-columns:1fr 1fr}.review-toolbar{align-items:stretch;flex-wrap:wrap}.review-toolbar .el-input{max-width:none;flex-basis:100%}.review-toolbar>span{display:none}.log-toolbar{align-items:stretch;flex-direction:column;gap:10px}.log-toolbar>div:last-child{flex-wrap:wrap}.resource-rings{gap:8px}.resource-ring{width:65px;height:65px}.endpoint-list>div{grid-template-columns:54px 1fr 90px}.endpoint-bar{display:none}.log-line{grid-template-columns:105px 44px 1fr}.log-line code{grid-column:1/-1}}@media(max-width:540px){.admin-metrics,.crawler-summary,.performance-grid,.quality-grid,.import-result-grid{grid-template-columns:1fr}.admin-nav small{display:none}.admin-status{justify-content:flex-start}.metric-card{min-height:80px}.review-signals{grid-template-columns:1fr 1fr}.review-job{align-items:flex-start;flex-direction:column}}
</style>

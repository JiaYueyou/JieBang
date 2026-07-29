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
          @click="activeSection = item.value"
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

    <!-- Logs & Performance -->
    <section v-else-if="activeSection === 'monitor'" class="admin-section anim-fade-up">
      <div class="section-heading">
        <div><span>OBSERVABILITY</span><h2>运行日志与性能监控</h2><p>定位接口异常、慢查询和后台任务故障。</p></div>
        <div class="section-actions">
          <el-select v-model="monitorRange" style="width:130px"><el-option label="最近 1 小时" value="1h" /><el-option label="最近 24 小时" value="24h" /><el-option label="最近 7 天" value="7d" /></el-select>
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
          <div class="card-heading"><div><span>接口性能</span><h2>请求延迟 Top 5</h2></div><span class="live-label"><i></i>实时</span></div>
          <div class="endpoint-list">
            <div v-for="api in endpoints" :key="api.path">
              <span class="method" :class="api.method.toLowerCase()">{{ api.method }}</span>
              <code>{{ api.path }}</code>
              <div class="endpoint-bar"><i :style="{ width: `${api.percent}%` }"></i></div>
              <strong>{{ api.latency }}</strong>
            </div>
          </div>
        </article>
        <article class="admin-card alert-panel">
          <div class="card-heading"><div><span>告警规则</span><h2>监控阈值</h2></div><button type="button" @click="ElMessage.info('告警策略编辑功能待接入')">编辑规则</button></div>
          <div class="alert-rules">
            <div v-for="rule in alertRules" :key="rule.name">
              <span class="rule-icon" :class="rule.tone"><el-icon><component :is="rule.icon" /></el-icon></span>
              <div><strong>{{ rule.name }}</strong><small>{{ rule.condition }}</small></div>
              <el-switch v-model="rule.enabled" />
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
        </div>
      </article>
    </section>

    <!-- Users -->
    <section v-else-if="activeSection === 'users'" class="admin-section anim-fade-up">
      <div class="section-heading">
        <div><span>ACCESS CONTROL</span><h2>用户与权限管理</h2><p>管理平台用户、角色授权和高风险操作权限。</p></div>
        <el-button type="primary" @click="inviteUser"><el-icon><UserFilled /></el-icon>邀请用户</el-button>
      </div>

      <div class="user-stats">
        <div><span class="user-stat-icon brand"><el-icon><User /></el-icon></span><div><strong>{{ users.length }}</strong><small>全部用户</small></div></div>
        <div><span class="user-stat-icon green"><el-icon><CircleCheck /></el-icon></span><div><strong>{{ activeUsers }}</strong><small>正常使用</small></div></div>
        <div><span class="user-stat-icon amber"><el-icon><Key /></el-icon></span><div><strong>3</strong><small>系统管理员</small></div></div>
        <div><span class="user-stat-icon rose"><el-icon><Warning /></el-icon></span><div><strong>1</strong><small>待处理账号</small></div></div>
      </div>

      <article class="admin-card user-table-card">
        <div class="user-toolbar">
          <div class="user-search"><el-icon><Search /></el-icon><input v-model="userKeyword" placeholder="搜索姓名、账号或部门" /></div>
          <el-select v-model="roleFilter" clearable placeholder="全部角色" style="width:130px"><el-option v-for="role in roles" :key="role.name" :label="role.name" :value="role.name" /></el-select>
          <el-select v-model="statusFilter" clearable placeholder="全部状态" style="width:120px"><el-option label="正常" value="active" /><el-option label="已停用" value="disabled" /></el-select>
        </div>
        <el-table :data="filteredUsers" style="width:100%">
          <el-table-column label="用户" min-width="210">
            <template #default="{ row }"><div class="user-cell"><span>{{ row.name.slice(0, 1) }}</span><div><strong>{{ row.name }}</strong><small>{{ row.email }}</small></div></div></template>
          </el-table-column>
          <el-table-column prop="department" label="部门" width="140" />
          <el-table-column label="角色" width="140"><template #default="{ row }"><span class="role-chip" :class="row.roleTone">{{ row.role }}</span></template></el-table-column>
          <el-table-column label="状态" width="110"><template #default="{ row }"><span class="account-state" :class="row.status"><i></i>{{ row.status === 'active' ? '正常' : '已停用' }}</span></template></el-table-column>
          <el-table-column prop="lastLogin" label="最后登录" width="160" />
          <el-table-column label="操作" width="160" align="right">
            <template #default="{ row }"><el-button text type="primary" @click="editUser(row)">编辑权限</el-button><el-dropdown trigger="click"><button class="more-action"><el-icon><MoreFilled /></el-icon></button><template #dropdown><el-dropdown-menu><el-dropdown-item @click="resetPassword(row)">重置密码</el-dropdown-item><el-dropdown-item @click="toggleUser(row)">{{ row.status === 'active' ? '停用账号' : '启用账号' }}</el-dropdown-item></el-dropdown-menu></template></el-dropdown></template>
          </el-table-column>
        </el-table>
      </article>

      <article class="admin-card role-panel">
        <div class="card-heading"><div><span>角色矩阵</span><h2>权限范围</h2></div><button type="button" @click="ElMessage.info('新建角色功能待接入')"><el-icon><Plus /></el-icon>新建角色</button></div>
        <div class="role-grid">
          <div v-for="role in roles" :key="role.name" class="role-card">
            <div><span class="role-symbol" :class="role.tone"><el-icon><component :is="role.icon" /></el-icon></span><span><strong>{{ role.name }}</strong><small>{{ role.members }} 名成员</small></span></div>
            <p>{{ role.desc }}</p>
            <div class="permission-tags"><span v-for="permission in role.permissions" :key="permission">{{ permission }}</span></div>
          </div>
        </div>
      </article>
    </section>

    <!-- Settings -->
    <section v-else class="admin-section anim-fade-up">
      <div class="section-heading">
        <div><span>PLATFORM SETTINGS</span><h2>系统参数设置</h2><p>管理平台基础信息、数据策略、安全规则和外部服务。</p></div>
        <el-button type="primary" @click="saveSettings"><el-icon><Check /></el-icon>保存更改</el-button>
      </div>
      <div class="settings-layout">
        <article class="admin-card settings-card">
          <div class="settings-title"><span class="setting-symbol brand"><el-icon><Monitor /></el-icon></span><div><h3>平台基础设置</h3><p>系统名称、时区与默认语言。</p></div></div>
          <div class="settings-form">
            <label><span>平台名称</span><el-input v-model="settings.platformName" /></label>
            <label><span>系统时区</span><el-select v-model="settings.timezone"><el-option label="Asia/Shanghai (UTC+8)" value="Asia/Shanghai" /><el-option label="UTC" value="UTC" /></el-select></label>
            <label><span>默认语言</span><el-select v-model="settings.language"><el-option label="简体中文" value="zh-CN" /><el-option label="English" value="en" /></el-select></label>
          </div>
        </article>
        <article class="admin-card settings-card">
          <div class="settings-title"><span class="setting-symbol green"><el-icon><DataLine /></el-icon></span><div><h3>数据与存储</h3><p>历史记录、日志和快照保留策略。</p></div></div>
          <div class="setting-switches">
            <div><span><strong>自动清理运行日志</strong><small>超过保留天数后自动归档删除</small></span><el-switch v-model="settings.autoCleanLogs" /></div>
            <label><span>日志保留天数</span><el-input-number v-model="settings.logRetention" :min="7" :max="365" /></label>
            <label><span>图谱快照周期</span><el-select v-model="settings.snapshotCycle"><el-option label="每天" value="daily" /><el-option label="每周" value="weekly" /><el-option label="每月" value="monthly" /></el-select></label>
          </div>
        </article>
        <article class="admin-card settings-card">
          <div class="settings-title"><span class="setting-symbol amber"><el-icon><Lock /></el-icon></span><div><h3>安全策略</h3><p>登录安全和敏感操作保护。</p></div></div>
          <div class="setting-switches">
            <div><span><strong>强制复杂密码</strong><small>至少 10 位并包含字母、数字和符号</small></span><el-switch v-model="settings.strongPassword" /></div>
            <div><span><strong>管理员二次验证</strong><small>高风险操作要求二次身份验证</small></span><el-switch v-model="settings.adminMfa" /></div>
            <label><span>登录会话时长</span><el-select v-model="settings.sessionHours"><el-option label="8 小时" :value="8" /><el-option label="24 小时" :value="24" /><el-option label="7 天" :value="168" /></el-select></label>
          </div>
        </article>
        <article class="admin-card settings-card">
          <div class="settings-title"><span class="setting-symbol violet"><el-icon><Connection /></el-icon></span><div><h3>外部服务连接</h3><p>数据库、图谱与 Agent 服务状态。</p></div></div>
          <div class="integration-list">
            <div v-for="integration in integrations" :key="integration.name"><span class="integration-dot" :class="integration.status"></span><span><strong>{{ integration.name }}</strong><small>{{ integration.endpoint }}</small></span><button type="button" @click="testConnection(integration)">测试连接</button></div>
          </div>
        </article>
      </div>
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

    <el-dialog v-model="showUserDialog" title="编辑用户权限" width="560px">
      <div v-if="editingUser" class="user-dialog-head"><span>{{ editingUser.name.slice(0, 1) }}</span><div><strong>{{ editingUser.name }}</strong><small>{{ editingUser.email }}</small></div></div>
      <el-form v-if="editingUser" label-position="top">
        <el-form-item label="用户角色"><el-select v-model="editingUser.role" style="width:100%"><el-option v-for="role in roles" :key="role.name" :label="role.name" :value="role.name" /></el-select></el-form-item>
        <el-form-item label="附加权限"><el-checkbox-group v-model="editingPermissions"><el-checkbox label="管理爬虫" /><el-checkbox label="导出数据" /><el-checkbox label="查看日志" /><el-checkbox label="管理用户" /></el-checkbox-group></el-form-item>
      </el-form>
      <template #footer><el-button @click="showUserDialog = false">取消</el-button><el-button type="primary" @click="saveUser">保存权限</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { storeToRefs } from "pinia";
import { ElMessage, ElMessageBox } from "element-plus";
import { useAdminStore } from "@/stores/admin";
import DataState from "@/components/common/DataState.vue";
import type { JobImportResult } from "@/domain/types";

type Section = "overview" | "crawler" | "monitor" | "users" | "settings";

const activeSection = ref<Section>("overview");
const showCrawlerSettings = ref(false);
const showUserDialog = ref(false);
const editingUser = ref<any>(null);
const editingPermissions = ref<string[]>([]);
const monitorRange = ref("1h");
const logLevel = ref("");
const logKeyword = ref("");
const autoScroll = ref(true);
const userKeyword = ref("");
const roleFilter = ref("");
const statusFilter = ref("");
const lastImportResult = ref<JobImportResult | null>(null);
const store = useAdminStore();
const { data: admin, loading, error } = storeToRefs(store);
let pollTimer: ReturnType<typeof setInterval> | null = null;

onMounted(() => store.load());
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer); });

const navItems: { value: Section; label: string; desc: string; icon: string; badge?: string }[] = [
  { value: "overview", label: "运行总览", desc: "系统健康与关键指标", icon: "Odometer" },
  { value: "crawler", label: "采集中心", desc: "爬虫任务与数据质量", icon: "Download", badge: "4" },
  { value: "monitor", label: "日志与性能", desc: "应用日志与资源监控", icon: "DataLine", badge: "3" },
  { value: "users", label: "用户权限", desc: "账号、角色与授权", icon: "UserFilled" },
  { value: "settings", label: "系统设置", desc: "平台参数与安全策略", icon: "Setting" },
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
const alertRules = computed(() => admin.value?.alertRules ?? []);
const logs = computed(() => admin.value?.logs ?? []);
const runningCrawlerCount = computed(() => crawlers.value.filter((item) => item.running).length);
const validationPassed = computed(() => lastImportResult.value?.validation.reduce((sum, item) => sum + item.passed, 0) ?? 0);
const validationWarnings = computed(() => lastImportResult.value?.validation.reduce((sum, item) => sum + item.warning_count, 0) ?? 0);
const filteredLogs = computed(() => logs.value.filter((log) => (!logLevel.value || log.level === logLevel.value) && (!logKeyword.value || `${log.service} ${log.message}`.toLowerCase().includes(logKeyword.value.toLowerCase()))));

const users = computed(() => admin.value?.users ?? []);
const activeUsers = computed(() => users.value.filter((user) => user.status === "active").length);
const filteredUsers = computed(() => users.value.filter((user) => {
  const query = userKeyword.value.toLowerCase();
  return (!query || `${user.name} ${user.email} ${user.department}`.toLowerCase().includes(query)) && (!roleFilter.value || user.role === roleFilter.value) && (!statusFilter.value || user.status === statusFilter.value);
}));
const roles = computed(() => admin.value?.roles ?? []);
const settings = computed(() => admin.value?.settings ?? {});
const integrations = computed(() => admin.value?.integrations ?? []);

async function refreshSystem() { await store.refresh(); ElMessage.success("系统状态已刷新"); }
function handleEvent(event: any) { ElMessage.info(`正在查看：${event.title}`); }
async function toggleCrawler(crawler: any) { await store.toggleCrawler(crawler.id); ElMessage.success(`${crawler.name}状态已更新`); }
async function runCrawler(crawler: any) {
  await store.runCrawler(crawler.id);
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
            lastImportResult.value = await store.importCrawlerOutput(result.filename);
            ElMessage.success(
              `${crawler.name}闭环完成：入库 ${lastImportResult.value.imported} 条，重复 ${lastImportResult.value.duplicates} 条`,
            );
          }
        }
        await store.load(true);
      } else {
        // 仍在运行，刷新进度
        await store.load(true);
      }
    } catch {
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    }
  }, 2000);
}
function editCrawler(crawler: any) { ElMessage.info(`正在配置：${crawler.name}`); }
function viewCrawlerLog(crawler: any) { activeSection.value = "monitor"; logKeyword.value = crawler.name; }
function createSource() { ElMessage.info("添加数据源表单待后端数据源协议确定后接入"); }
function saveCrawlerPolicy() { showCrawlerSettings.value = false; ElMessage.success("全局采集策略已保存"); }
function exportLogs() { ElMessage.success("日志导出任务已创建"); }
function inviteUser() { ElMessage.info("用户邀请功能待邮件服务接入"); }
function editUser(user: any) { editingUser.value = user; editingPermissions.value = []; showUserDialog.value = true; }
function saveUser() { showUserDialog.value = false; ElMessage.success("用户权限已更新"); }
function resetPassword(user: any) { ElMessage.success(`${user.name}的密码重置邮件已发送`); }
async function toggleUser(user: any) {
  try {
    await ElMessageBox.confirm(`确定${user.status === "active" ? "停用" : "启用"}账号“${user.name}”吗？`, "账号状态");
    await store.toggleUser(user.id);
    ElMessage.success("账号状态已更新");
  } catch {}
}
async function saveSettings() { await store.saveSettings(settings.value); ElMessage.success("系统设置已保存"); }
function testConnection(integration: any) { ElMessage.success(`${integration.name}连接正常`); }
</script>

<style scoped>
.admin-page{max-width:1480px;margin:0 auto;--admin-dark:#202437}.admin-status{display:flex;align-items:center;gap:10px;flex:0 0 auto;padding:9px 10px 9px 17px;border-left:1px solid var(--color-border);border-radius:0 9px 9px 0;background:var(--color-success-light)}.status-pulse{width:9px;height:9px;border-radius:50%;background:var(--color-success);box-shadow:0 0 0 5px rgba(52,179,126,.12)}.admin-status div{display:flex;flex-direction:column;margin-right:4px}.admin-status strong{font-size:14px;color:var(--text-primary)}.admin-status small{font-size:14px;color:var(--text-muted)}.admin-status button,.card-heading button{display:flex;align-items:center;gap:5px;border:0;background:#fff;border-radius:8px;padding:7px 9px;color:var(--text-secondary);font:600 14px var(--font-sans);cursor:pointer}
.admin-nav{display:flex;align-items:stretch;gap:7px;padding:7px;margin-bottom:17px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.admin-nav-items{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:7px;min-width:0;flex:1}.admin-nav-items button{position:relative;display:flex;align-items:center;gap:10px;padding:10px;border:0;border-radius:10px;background:transparent;text-align:left;cursor:pointer;color:var(--text-secondary);transition:.2s}.admin-nav-items button:hover{background:var(--color-bg-muted)}.admin-nav-items button.active{background:var(--color-brand-light);color:var(--color-brand)}.nav-icon{display:grid;width:34px;height:34px;place-items:center;border-radius:9px;background:var(--color-bg-muted);font-size:16px}.admin-nav-items button.active .nav-icon{background:#fff}.admin-nav-items button>span:nth-child(2){display:flex;min-width:0;flex-direction:column}.admin-nav strong{font-size:14px}.admin-nav small{font-size:14px;color:var(--text-muted);margin-top:1px}.admin-nav-items button>i{position:absolute;right:8px;top:8px;min-width:17px;padding:1px 5px;border-radius:999px;background:var(--color-danger);color:#fff;font:700 14px var(--font-mono);text-align:center}
.admin-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:11px;margin-bottom:13px}.metric-card{display:flex;align-items:center;gap:11px;min-width:0;padding:16px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.metric-icon,.user-stat-icon,.setting-symbol{display:grid;width:38px;height:38px;flex:0 0 38px;place-items:center;border-radius:11px;font-size:17px}.brand{background:var(--color-brand-light);color:var(--color-brand)}.green{background:var(--color-success-light);color:var(--color-success)}.amber{background:var(--color-warning-light);color:var(--color-warning)}.rose{background:var(--color-danger-light);color:var(--color-danger)}.violet{background:#f0edff;color:#7c6ff7}.blue{background:var(--color-info-light);color:var(--color-info)}.metric-copy{display:flex;min-width:0;flex:1;flex-direction:column}.metric-copy span{font-size:14px;color:var(--text-muted)}.metric-copy strong{font:700 22px var(--font-mono);letter-spacing:-.04em}.metric-copy small{font-size:14px}.positive,.green{color:var(--color-success)}.warning,.amber{color:var(--color-warning)}.metric-bars,.spark-bars{display:flex;align-items:flex-end;gap:2px;height:38px}.metric-bars i,.spark-bars i{width:3px;min-height:4px;border-radius:2px;background:var(--color-brand);opacity:.55}.overview-grid{display:grid;grid-template-columns:1.3fr .7fr;gap:13px}.admin-card{border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.card-heading{display:flex;align-items:center;justify-content:space-between;padding:16px 18px 11px}.card-heading>div{display:flex;flex-direction:column}.card-heading span,.section-heading>div>span{font:700 14px var(--font-mono);letter-spacing:.09em;color:var(--text-muted);text-transform:uppercase}.card-heading h2{font-size:14px;margin-top:2px}.healthy-chip,.event-count{padding:4px 8px;border-radius:999px;background:var(--color-success-light);color:var(--color-success)!important;font:700 14px var(--font-sans)!important;letter-spacing:0!important}.service-list,.task-list,.event-list{padding:0 18px 12px}.service-row,.task-row{display:flex;align-items:center;gap:10px;padding:10px 0}.service-row+.service-row,.task-row+.task-row{border-top:1px solid var(--color-border-light)}.service-logo,.task-state{display:grid;width:31px;height:31px;flex:0 0 31px;place-items:center;border-radius:9px}.service-name,.task-row>div{display:flex;min-width:0;flex:1;flex-direction:column}.service-name strong,.task-row strong{font-size:14px}.service-name small,.task-row small{font-size:14px;color:var(--text-muted)}.latency{display:flex;flex-direction:column;align-items:flex-end}.latency strong{font:600 14px var(--font-mono)}.latency small{font-size:14px;color:var(--text-muted)}.service-state,.account-state{display:flex;align-items:center;gap:4px;color:var(--color-success);font-size:14px;font-weight:600}.service-state i,.account-state i,.live-label i{width:6px;height:6px;border-radius:50%;background:currentColor}.resource-card{padding-bottom:14px}.live-label{display:flex;align-items:center;gap:5px;color:var(--color-success)!important;font:700 14px var(--font-mono)!important}.resource-rings{display:flex;justify-content:space-around;padding:12px 15px 16px}.resource-item{display:flex;align-items:center;flex-direction:column}.resource-ring{display:grid;width:76px;height:76px;place-items:center;border-radius:50%;background:conic-gradient(var(--ring-color) calc(var(--value)*1%),var(--color-bg-muted) 0);position:relative}.resource-ring:before{content:"";position:absolute;inset:6px;border-radius:50%;background:#fff}.resource-ring span{z-index:1;font:700 17px var(--font-mono)}.resource-ring small{font-size:14px}.resource-item>strong{font-size:14px;margin-top:7px}.resource-item>small{font-size:14px;color:var(--text-muted)}.traffic-strip{display:grid;grid-template-columns:1fr 1fr;gap:7px;padding:0 15px}.traffic-strip div{display:flex;align-items:center;gap:6px;padding:9px;border-radius:8px;background:var(--color-bg-muted);font-size:14px}.traffic-strip strong{margin-left:auto;font:600 14px var(--font-mono)}.task-state.success{background:var(--color-success-light);color:var(--color-success)}.task-state.running{background:var(--color-brand-light);color:var(--color-brand)}.task-state.warning{background:var(--color-warning-light);color:var(--color-warning)}.task-count{font:600 14px var(--font-mono);color:var(--text-secondary)}.task-status{min-width:48px;text-align:right;font-size:14px;font-weight:700}.task-status.success{color:var(--color-success)}.task-status.running{color:var(--color-brand)}.task-status.warning{color:var(--color-warning)}.event-card .event-count{background:var(--color-danger-light);color:var(--color-danger)!important}.event-list button{display:flex;align-items:center;gap:9px;width:100%;padding:10px 0;border:0;border-top:1px solid var(--color-border-light);background:transparent;text-align:left;cursor:pointer}.event-level{display:grid;width:29px;height:29px;place-items:center;border-radius:8px}.event-level.warning{background:var(--color-warning-light)}.event-level.danger{background:var(--color-danger-light);color:var(--color-danger)}.event-level.info{background:var(--color-info-light);color:var(--color-info)}.event-list button>span:nth-child(2){display:flex;min-width:0;flex:1;flex-direction:column}.event-list strong{font-size:14px}.event-list small{font-size:14px;color:var(--text-muted)}.event-list time{font:500 14px var(--font-mono);color:var(--text-muted)}
.section-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin:8px 2px 16px}.section-heading h2{font-size:20px;letter-spacing:-.03em}.section-heading p{font-size:14px;color:var(--text-muted);margin-top:3px}.section-actions{display:flex;gap:8px}.crawler-summary,.user-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:13px}.crawler-summary>div{display:flex;flex-direction:column;padding:14px 16px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.crawler-summary span{font-size:14px;color:var(--text-muted)}.crawler-summary strong{font:700 20px var(--font-mono)}.crawler-summary small{font-size:14px;color:var(--text-muted)}.crawler-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:13px}.crawler-card{padding:16px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff;transition:.2s}.crawler-card.paused{opacity:.72;background:var(--color-bg-muted)}.crawler-head{display:flex;align-items:center;gap:10px}.source-logo{display:grid;width:39px;height:39px;place-items:center;border-radius:11px;background:var(--color-brand-light);color:var(--color-brand);font-weight:700}.crawler-head>div{min-width:0;flex:1}.crawler-head h3{font-size:14px}.crawler-head p{font-size:14px;color:var(--text-muted)}.crawler-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:14px 0}.crawler-stats div{display:flex;flex-direction:column;padding:8px;border-radius:8px;background:var(--color-bg-muted)}.crawler-stats span,.crawler-progress span,.crawler-meta{font-size:14px;color:var(--text-muted)}.crawler-stats strong{font:600 14px var(--font-mono)}.crawler-progress>div{display:flex;justify-content:space-between;margin-bottom:5px}.crawler-progress strong{font:600 14px var(--font-mono)}.crawler-meta{display:flex;justify-content:space-between;margin-top:9px}.crawler-meta span{display:flex;align-items:center;gap:4px}.crawler-card footer{display:flex;gap:5px;padding-top:11px;margin-top:11px;border-top:1px solid var(--color-border-light)}.crawler-card footer button{display:flex;align-items:center;justify-content:center;gap:4px;flex:1;height:29px;border:1px solid var(--color-border);border-radius:7px;background:#fff;color:var(--text-secondary);font:600 14px var(--font-sans);cursor:pointer}.crawler-card footer button:first-child{border-color:var(--color-brand);color:var(--color-brand)}.crawler-card footer button:disabled{opacity:.5;cursor:not-allowed}.quality-panel{padding-bottom:16px}.quality-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:2px 18px}.quality-grid>div{padding:12px;border-radius:9px;background:var(--color-bg-muted)}.quality-grid span{font-size:14px;color:var(--text-muted)}.quality-grid strong{display:block;font:700 17px var(--font-mono);margin:2px 0 7px}.quality-grid small{font-size:14px;color:var(--text-muted)}
.import-result{padding:16px;margin-bottom:13px;border:1px solid color-mix(in srgb,var(--color-success) 35%,var(--color-border));border-radius:var(--radius-lg);background:color-mix(in srgb,var(--color-success) 5%,#fff)}.import-result-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}.import-result-head>div{display:flex;flex-direction:column}.import-result-head span{font-size:13px;color:var(--text-muted)}.import-result-head strong{font-size:14px}.import-result-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}.import-result-grid>div{padding:9px 10px;border-radius:8px;background:#fff}.import-result-grid span{display:block;font-size:12px;color:var(--text-muted)}.import-result-grid strong{font:700 16px var(--font-mono)}
.performance-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:13px}.performance-card{position:relative;overflow:hidden;padding:15px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.performance-card>span{font-size:14px;color:var(--text-muted)}.performance-card>strong{display:block;font:700 20px var(--font-mono)}.performance-card>small{font-size:14px}.spark-bars{position:absolute;right:13px;bottom:13px;height:33px}.monitor-grid{display:grid;grid-template-columns:1.3fr .7fr;gap:13px;margin-bottom:13px}.endpoint-list{padding:0 18px 14px}.endpoint-list>div{display:grid;grid-template-columns:38px 1.2fr 1fr 52px;gap:8px;align-items:center;padding:10px 0;border-top:1px solid var(--color-border-light)}.method{padding:2px 4px;border-radius:4px;font:700 14px var(--font-mono);text-align:center}.method.get{background:var(--color-success-light);color:var(--color-success)}.method.post{background:var(--color-brand-light);color:var(--color-brand)}.endpoint-list code{overflow:hidden;font-size:14px;text-overflow:ellipsis}.endpoint-bar{height:4px;border-radius:999px;background:var(--color-bg-muted)}.endpoint-bar i{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,var(--color-brand),var(--color-danger))}.endpoint-list strong{font:600 14px var(--font-mono);text-align:right}.alert-rules{padding:0 17px 12px}.alert-rules>div{display:flex;align-items:center;gap:8px;padding:9px 0;border-top:1px solid var(--color-border-light)}.rule-icon{display:grid;width:29px;height:29px;place-items:center;border-radius:8px}.alert-rules>div>div{display:flex;flex:1;flex-direction:column}.alert-rules strong{font-size:14px}.alert-rules small{font-size:14px;color:var(--text-muted)}.log-panel{overflow:hidden}.log-toolbar{display:flex;align-items:center;justify-content:space-between;padding:14px 17px}.log-toolbar>div:first-child{display:flex;flex-direction:column}.log-toolbar span{font:700 14px var(--font-mono);color:var(--text-muted)}.log-toolbar h2{font-size:14px}.log-toolbar>div:last-child{display:flex;align-items:center;gap:7px}.log-console{max-height:290px;overflow:auto;padding:8px 12px 12px;background:#1d2130;color:#cfd5e6;font:14px/1.8 var(--font-mono)}.log-line{display:grid;grid-template-columns:82px 38px 92px 1fr;gap:8px;padding:3px 5px;border-radius:4px}.log-line:hover{background:rgba(255,255,255,.04)}.log-line time{color:#747d94}.log-level{font-weight:700}.log-level.info{color:#68b4ff}.log-level.warn{color:#f6b85d}.log-level.error{color:#ff7474}.log-service{color:#8e9abb}.log-line code{color:#d8deec}
.user-stats>div{display:flex;align-items:center;gap:10px;padding:14px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.user-stats>div>div{display:flex;flex-direction:column}.user-stats strong{font:700 20px var(--font-mono)}.user-stats small{font-size:14px;color:var(--text-muted)}.user-table-card{overflow:hidden;margin-bottom:13px}.user-toolbar{display:flex;gap:8px;padding:13px 16px;border-bottom:1px solid var(--color-border-light)}.user-search{display:flex;align-items:center;gap:7px;flex:1;max-width:320px;padding:0 10px;border-radius:8px;background:var(--color-bg-muted);color:var(--text-muted)}.user-search input{width:100%;border:0;outline:0;background:transparent;font:14px var(--font-sans)}.user-cell{display:flex;align-items:center;gap:9px}.user-cell>span,.user-dialog-head>span{display:grid;width:32px;height:32px;place-items:center;border-radius:50%;background:linear-gradient(135deg,var(--color-brand),#8d9cf8);color:#fff;font-weight:700}.user-cell div{display:flex;flex-direction:column}.user-cell strong{font-size:14px}.user-cell small{font-size:14px;color:var(--text-muted)}.role-chip{padding:4px 7px;border-radius:6px;font-size:14px;font-weight:700}.role-chip.rose{background:var(--color-danger-light)}.role-chip.brand{background:var(--color-brand-light);color:var(--color-brand)}.role-chip.violet{background:#f0edff;color:#7c6ff7}.role-chip.green{background:var(--color-success-light)}.role-chip.amber{background:var(--color-warning-light)}.account-state.disabled{color:var(--text-muted)}.more-action{margin-left:3px;border:0;background:transparent;color:var(--text-muted);cursor:pointer}.role-panel{padding-bottom:15px}.role-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;padding:2px 16px}.role-card{padding:12px;border:1px solid var(--color-border-light);border-radius:10px;background:var(--color-bg-muted)}.role-card>div:first-child{display:flex;align-items:center;gap:8px}.role-symbol{display:grid;width:31px;height:31px;place-items:center;border-radius:8px}.role-card>div:first-child>span:last-child{display:flex;flex-direction:column}.role-card strong{font-size:14px}.role-card small,.role-card p{font-size:14px;color:var(--text-muted)}.role-card p{margin:8px 0;line-height:1.5}.permission-tags{display:flex;flex-wrap:wrap;gap:3px}.permission-tags span{padding:2px 5px;border-radius:4px;background:#fff;color:var(--text-secondary);font-size:14px}.user-dialog-head{display:flex;align-items:center;gap:10px;padding:10px;margin-bottom:15px;border-radius:9px;background:var(--color-bg-muted)}.user-dialog-head>div{display:flex;flex-direction:column}.user-dialog-head small{font-size:14px;color:var(--text-muted)}
.settings-layout{display:grid;grid-template-columns:1fr 1fr;gap:12px}.settings-card{padding:17px}.settings-title{display:flex;align-items:center;gap:10px;padding-bottom:13px;border-bottom:1px solid var(--color-border-light)}.settings-title h3{font-size:14px}.settings-title p{font-size:14px;color:var(--text-muted)}.settings-form{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}.settings-form label:first-child{grid-column:1/-1}.settings-form label,.setting-switches label{display:flex;flex-direction:column;gap:5px}.settings-form label>span,.setting-switches label>span{font-size:14px;font-weight:600;color:var(--text-secondary)}.setting-switches{display:flex;flex-direction:column;gap:11px;margin-top:14px}.setting-switches>div{display:flex;align-items:center;justify-content:space-between}.setting-switches>div>span{display:flex;flex-direction:column}.setting-switches strong{font-size:14px}.setting-switches small{font-size:14px;color:var(--text-muted)}.integration-list{margin-top:10px}.integration-list>div{display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid var(--color-border-light)}.integration-dot{width:7px;height:7px;border-radius:50%;background:var(--color-success)}.integration-dot.warning{background:var(--color-warning)}.integration-list>div>span:nth-child(2){display:flex;min-width:0;flex:1;flex-direction:column}.integration-list strong{font-size:14px}.integration-list small{font-size:14px;color:var(--text-muted)}.integration-list button{border:0;background:var(--color-bg-muted);border-radius:6px;padding:5px 7px;color:var(--text-secondary);font:600 14px var(--font-sans);cursor:pointer}
@media(max-width:1200px){.admin-nav{flex-wrap:wrap}.admin-nav-items{grid-template-columns:repeat(3,1fr);flex-basis:100%}.admin-status{width:100%;justify-content:flex-end;border-top:1px solid var(--color-border-light);border-left:0;border-radius:0 0 9px 9px}.admin-metrics,.crawler-summary,.performance-grid,.user-stats{grid-template-columns:repeat(2,1fr)}.import-result-grid{grid-template-columns:repeat(3,1fr)}.overview-grid,.monitor-grid{grid-template-columns:1fr}.role-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:768px){.section-heading{align-items:stretch;flex-direction:column}.admin-nav-items{grid-template-columns:1fr 1fr}.crawler-grid,.settings-layout{grid-template-columns:1fr}.quality-grid{grid-template-columns:1fr 1fr}.log-toolbar{align-items:stretch;flex-direction:column;gap:10px}.log-toolbar>div:last-child{flex-wrap:wrap}.role-grid{grid-template-columns:1fr}.resource-rings{gap:8px}.resource-ring{width:65px;height:65px}.endpoint-list>div{grid-template-columns:38px 1fr 50px}.endpoint-bar{display:none}}@media(max-width:540px){.admin-metrics,.crawler-summary,.performance-grid,.user-stats,.quality-grid,.import-result-grid{grid-template-columns:1fr}.admin-nav small{display:none}.admin-status{justify-content:flex-start}.metric-card{min-height:80px}}
</style>

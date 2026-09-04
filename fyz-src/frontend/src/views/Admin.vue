<template>
  <div class="admin-page">
    <DataState :loading="loading && !loaded" :error="error" @retry="store.refresh()" />
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
        </button>
      </div>
      <div class="admin-status" :class="overallStatus">
        <span class="status-pulse"></span>
        <div><strong>{{ overallStatusLabel }}</strong><small>最后巡检：{{ generatedAtLabel }}</small></div>
        <button type="button" :disabled="manualRefreshing" @click="refreshSystem"><el-icon :class="{ 'is-loading': manualRefreshing }"><Refresh /></el-icon>刷新</button>
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
            <span class="healthy-chip">{{ healthyServiceCount }} / {{ services.length }} 正常</span>
          </div>
          <div class="service-list">
            <div v-for="service in services" :key="service.name" class="service-row">
              <span class="service-logo" :class="service.tone"><el-icon><component :is="service.icon" /></el-icon></span>
              <div class="service-name"><strong>{{ service.name }}</strong><small>{{ service.desc }}</small></div>
              <div class="latency"><strong>{{ service.latency }}</strong><small>探测 / 最近耗时</small></div>
              <span class="service-state" :class="service.status"><i></i>{{ service.statusLabel }}</span>
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
            <div><el-icon><Top /></el-icon><span>入站</span><strong>{{ traffic.inbound }}</strong><small>累计 {{ traffic.receivedTotal }}</small></div>
            <div><el-icon><Bottom /></el-icon><span>出站</span><strong>{{ traffic.outbound }}</strong><small>累计 {{ traffic.sentTotal }}</small></div>
          </div>
        </article>

        <article class="admin-card task-card">
          <div class="card-heading">
            <div><span>任务动态</span><h2>最近采集任务</h2></div>
            <button type="button" @click="activeSection = 'crawler'">全部任务 <el-icon><ArrowRight /></el-icon></button>
          </div>
          <div class="task-list">
            <div v-for="task in recentTasks" :key="task.id" class="task-row">
              <span class="task-state" :class="task.status"><el-icon><component :is="task.icon" /></el-icon></span>
              <div><strong>{{ task.name }}</strong><small>{{ task.source }} · {{ task.time }}</small></div>
              <span class="task-count">{{ task.count }}</span>
              <span class="task-status" :class="task.status">{{ task.statusLabel }}</span>
            </div>
            <el-empty v-if="!recentTasks.length" description="暂无真实岗位导入任务" />
          </div>
        </article>

        <article class="admin-card event-card">
          <div class="card-heading">
            <div><span>系统事件</span><h2>需要关注</h2></div>
            <span class="event-count">{{ systemEvents.length }} 项</span>
          </div>
          <div class="event-list">
            <button v-for="event in systemEvents" :key="event.title" type="button" @click="handleEvent(event)">
              <span class="event-level" :class="event.level"><el-icon><component :is="event.icon" /></el-icon></span>
              <span><strong>{{ event.title }}</strong><small>{{ event.desc }}</small></span>
              <time>{{ event.time }}</time>
            </button>
            <el-empty v-if="!systemEvents.length" description="当前没有需要关注的真实事件" />
          </div>
        </article>
      </div>
    </section>

    <!-- Crawler -->
    <section v-else-if="activeSection === 'crawler'" class="admin-section anim-fade-up">
      <div class="section-heading">
        <div><span>DATA PIPELINE</span><h2>爬虫数据采集中心</h2><p>展示后端已注册采集脚本、真实运行状态和数据库质量结果。</p></div>
        <el-button type="primary" class="automation-config-button" @click="openAutomationDialog">
          <el-icon><Setting /></el-icon>自动爬取配置
        </el-button>
      </div>

      <div class="crawler-summary">
        <div><span>今日入库</span><strong>{{ pipelineSummary.todayImported }}</strong><small>数据库新增岗位</small></div>
        <div><span>有效数据率</span><strong class="summary-success">{{ pipelineSummary.validRate.toFixed(1) }}%</strong><small>{{ pipelineSummary.validRecords }} / {{ pipelineSummary.totalJobs }} 条正文有效</small></div>
        <div><span>运行中任务</span><strong class="summary-brand">{{ runningCrawlerCount }}</strong><small>共 {{ crawlers.length }} 个数据源</small></div>
        <div><span>失败任务</span><strong class="summary-warning">{{ pipelineSummary.failedTasks }}</strong><small>今日导入任务</small></div>
      </div>

      <article class="admin-card pipeline-run-card" role="status">
        <div class="card-heading">
          <div><span>AUTOMATIC CLOSED LOOP</span><h2>自动更新流水线</h2></div>
          <span class="healthy-chip">{{ currentPipelineRun ? `${currentPipelineRun.progress}%` : "等待下一周期" }}</span>
        </div>
        <div v-if="currentPipelineRun" class="pipeline-run-body">
          <div class="pipeline-run-title">
            <strong>{{ pipelineStageLabel(currentPipelineRun.stage) }}</strong>
            <small>运行 ID {{ currentPipelineRun.id.slice(0, 8) }} · {{ currentPipelineRun.trigger === "scheduled" ? "定时触发" : "手动触发" }}</small>
          </div>
          <el-progress :percentage="currentPipelineRun.progress" :status="currentPipelineRun.status === 'failed' ? 'exception' : undefined" />
          <div class="pipeline-stages">
            <span v-for="stage in pipelineStages" :key="stage.key" :class="{ active: stage.key === currentPipelineRun.stage }">{{ stage.label }}</span>
          </div>
        </div>
        <div v-else-if="latestPipelineRun" class="pipeline-run-body">
          <div class="pipeline-run-title">
            <strong>最近更新：{{ pipelineStatusLabel(latestPipelineRun.status) }}</strong>
            <small>{{ formatLocalDate(latestPipelineRun.finished_at) }} · 运行 ID {{ latestPipelineRun.id.slice(0, 8) }}</small>
          </div>
          <p v-if="latestPipelineRun.error_message" class="pipeline-error">{{ latestPipelineRun.error_message }}</p>
        </div>
        <el-empty v-else description="尚无自动更新运行记录" :image-size="48" />
      </article>

      <article class="admin-card competition-test-card" aria-labelledby="competition-test-title">
        <div class="card-heading">
          <div>
            <span>COMPETITION ACCEPTANCE</span>
            <h2 id="competition-test-title">赛方测试数据复现</h2>
          </div>
          <span class="test-data-chip">2 个时间窗口 + 1 个新岗位</span>
        </div>
        <p class="competition-test-intro">
          请按编号依次导入两个时间窗口。第二个文件同时包含新岗位数据，导入完成后系统将提交技能图谱同步任务。
        </p>
        <div class="competition-test-steps">
          <section>
            <span class="step-number">1</span>
            <div><strong>导入第一时间窗口</strong><small>AI应用开发工程师 · 2 条记录 · 2 个来源</small></div>
            <el-button type="primary" :loading="competitionImporting === 'baseline'" :disabled="Boolean(competitionImporting)" @click="importCompetitionData('baseline')">导入第一时间窗口</el-button>
          </section>
          <section>
            <span class="step-number">2</span>
            <div><strong>导入第二时间窗口并同步图谱</strong><small>AI应用开发工程师 2 条记录 + 大模型安全工程师 2 条记录</small></div>
            <el-button type="primary" :loading="competitionImporting === 'scenario'" :disabled="Boolean(competitionImporting)" @click="importCompetitionData('scenario')">导入第二时间窗口</el-button>
          </section>
          <section>
            <span class="step-number">3</span>
            <div><strong>查看处理结果</strong><small>岗位洞察展示时间窗口和技能字段，技能图谱展示节点与关系</small></div>
            <div class="competition-result-actions">
              <el-button @click="openCompetitionInsights">查看岗位洞察</el-button>
              <el-button @click="openCompetitionGraph">查看技能图谱</el-button>
            </div>
          </section>
        </div>
        <el-alert v-if="competitionStatus" :title="competitionStatus" type="success" :closable="false" show-icon />
      </article>

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
          <div><span>近重复标记</span><strong>{{ lastImportResult.near_duplicates }}</strong></div>
          <div><span>时间异常</span><strong>{{ lastImportResult.time_anomalies }}</strong></div>
          <div><span>低质量记录</span><strong>{{ lastImportResult.low_quality }}</strong></div>
          <div><span>技能事实</span><strong>{{ lastImportResult.skill_facts }}</strong></div>
          <div><span>已验证事实</span><strong>{{ lastImportResult.verified_skill_facts }}</strong></div>
          <div><span>待验证事实</span><strong>{{ lastImportResult.unverified_skill_facts }}</strong></div>
          <div><span>岗位版本</span><strong>{{ lastImportResult.versions_created ?? 0 }}</strong></div>
          <div><span>影响岗位</span><strong>{{ lastImportResult.affected_standard_job_ids?.length ?? 0 }}</strong></div>
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
            <div><span>成功率</span><strong>{{ crawler.success === null ? "—" : `${crawler.success}%` }}</strong></div>
            <div><span>平均耗时</span><strong>{{ crawler.duration }}</strong></div>
          </div>
          <div class="crawler-progress">
            <div><span>{{ crawler.progress_info || (crawler.running ? "正在采集" : crawler.enabled ? "等待手动触发" : "任务已暂停") }}</span><strong>{{ crawler.progress }}%</strong></div>
            <el-progress :percentage="crawler.progress" :show-text="false" :status="crawler.enabled ? undefined : 'warning'" />
          </div>
          <div class="crawler-meta">
            <span><el-icon><Calendar /></el-icon>{{ crawler.schedule }}</span>
            <span><el-icon><Clock /></el-icon>{{ crawler.nextRun }}</span>
          </div>
          <footer>
            <button type="button" :disabled="crawler.running || !crawler.enabled || Boolean(currentPipelineRun)" @click="runPipeline(crawler)">
              <el-icon><VideoPlay /></el-icon>{{ crawler.running ? "运行中" : "采集并入库" }}
            </button>
            <button type="button" @click="viewCrawlerLog(crawler)"><el-icon><Document /></el-icon>日志</button>
          </footer>
        </article>
      </div>

      <article class="admin-card quality-panel">
        <div class="card-heading">
          <div><span>数据质量</span><h2>当前数据库质量</h2></div>
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

      <article class="admin-card quality-review-panel">
        <div class="card-heading">
          <div><span>QUALITY REVIEW</span><h2>原始岗位质量审核</h2></div>
          <span class="healthy-chip">
            平均质量 {{ ((qualityPage?.summary.average_quality_score ?? 0) * 100).toFixed(1) }}%
          </span>
        </div>
        <div class="quality-review-summary">
          <div><span>通过</span><strong>{{ qualityPage?.summary.accepted ?? 0 }}</strong></div>
          <div><span>警告</span><strong>{{ qualityPage?.summary.warning ?? 0 }}</strong></div>
          <div><span>拒绝</span><strong>{{ qualityPage?.summary.rejected ?? 0 }}</strong></div>
          <div><span>近重复</span><strong>{{ qualityPage?.summary.near_duplicates ?? 0 }}</strong></div>
          <div><span>已排除</span><strong>{{ qualityPage?.summary.excluded ?? 0 }}</strong></div>
        </div>
        <div class="quality-review-toolbar">
          <el-select v-model="qualityStatus" clearable placeholder="全部质量状态" @change="refreshQuality(1)">
            <el-option label="通过" value="accepted" />
            <el-option label="警告" value="warning" />
            <el-option label="拒绝" value="rejected" />
            <el-option label="待评估" value="pending" />
          </el-select>
          <el-input
            v-model="qualitySource"
            clearable
            placeholder="按数据源精确筛选"
            @keyup.enter="refreshQuality(1)"
            @clear="refreshQuality(1)"
          />
          <el-select v-model="qualityExcluded" clearable placeholder="全部处置状态" @change="refreshQuality(1)">
            <el-option label="正常保留" :value="false" />
            <el-option label="已排除" :value="true" />
          </el-select>
          <el-button :loading="qualityLoading" @click="refreshQuality(1)">刷新</el-button>
        </div>
        <el-alert v-if="qualityError" :title="qualityError" type="error" :closable="false" show-icon />
        <el-table
          v-loading="qualityLoading"
          :data="qualityPage?.items ?? []"
          empty-text="没有符合条件的质量记录"
          row-key="id"
        >
          <el-table-column label="岗位与来源" min-width="230">
            <template #default="{ row }">
              <div class="quality-job">
                <strong>{{ row.title }}</strong>
                <span>{{ row.source }} · {{ row.company || "公司未标注" }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="发布时间" min-width="145">
            <template #default="{ row }">
              <span class="mono">{{ formatQualityDate(row.posted_at, row.posted_at_text) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="质量分" width="105">
            <template #default="{ row }">
              <strong class="mono">{{ (row.quality_score * 100).toFixed(1) }}</strong>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="qualityStatusType(row.quality_status)" effect="light">
                {{ qualityStatusLabel(row.quality_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="质量标记" min-width="220">
            <template #default="{ row }">
              <div class="quality-flags">
                <el-tag v-for="flag in row.quality_flags" :key="flag" size="small" type="warning">
                  {{ qualityFlagLabel(flag) }}
                </el-tag>
                <span v-if="!row.quality_flags.length">无异常标记</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="处置" width="116" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="!row.is_excluded"
                link
                type="danger"
                @click="excludeQualityRecord(row)"
              >
                排除
              </el-button>
              <el-button v-else link type="success" @click="restoreQualityRecord(row)">恢复</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          class="quality-pagination"
          background
          layout="prev, pager, next, total"
          :current-page="qualityPage?.meta.page ?? 1"
          :page-size="qualityPage?.meta.page_size ?? 20"
          :total="qualityPage?.meta.total ?? 0"
          @current-change="refreshQuality"
        />
      </article>

      <el-dialog
        v-model="automationDialogVisible"
        title="自动爬取配置"
        width="680px"
        class="automation-dialog"
        modal-class="automation-global-mask"
        append-to-body
        :z-index="3000"
        :close-on-click-modal="false"
        lock-scroll
        destroy-on-close
      >
        <div v-loading="automationLoading" class="automation-form">
          <div class="automation-intro">
            <span class="automation-icon"><el-icon><Timer /></el-icon></span>
            <div><strong>定时采集并自动入库</strong><p>按计划抓取选定官方招聘门户，完成校验、入库和后续图谱流水线。</p></div>
            <el-switch v-model="automationForm.enabled" active-text="已启用" inactive-text="已停用" />
          </div>

          <el-form label-position="top">
            <el-form-item label="数据来源">
              <el-checkbox-group v-model="automationForm.source_ids" class="source-checks">
                <el-checkbox v-for="crawler in crawlers" :key="crawler.id" :value="Number(crawler.id)">
                  <span class="source-option"><i :class="crawler.tone">{{ crawler.short }}</i>{{ crawler.name }}</span>
                </el-checkbox>
              </el-checkbox-group>
            </el-form-item>

            <div class="automation-grid">
              <el-form-item label="执行计划">
                <el-select v-model="automationForm.schedule_type">
                  <el-option label="固定间隔" value="interval" />
                  <el-option label="每天定时" value="daily" />
                  <el-option label="每周定时" value="weekly" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="automationForm.schedule_type === 'interval'" label="间隔时长">
                <el-input-number v-model="automationForm.interval_minutes" :min="15" :max="10080" :step="15" controls-position="right" />
                <small>分钟，最短 15 分钟</small>
              </el-form-item>
              <el-form-item v-else label="执行时间">
                <el-time-select v-model="automationForm.run_time" start="00:00" step="00:15" end="23:45" />
                <small>北京时间（Asia/Shanghai）</small>
              </el-form-item>
            </div>

            <el-form-item v-if="automationForm.schedule_type === 'weekly'" label="执行星期">
              <el-checkbox-group v-model="automationForm.weekdays" class="weekday-checks">
                <el-checkbox-button v-for="day in weekdayOptions" :key="day.value" :value="day.value">{{ day.label }}</el-checkbox-button>
              </el-checkbox-group>
            </el-form-item>

            <div class="automation-section-title"><span>采集规模</span><small>限制单个来源每次请求和入库的数据量</small></div>
            <div class="automation-grid">
              <el-form-item label="单来源最多岗位数">
                <el-input-number v-model="automationForm.max_records" :min="1" :max="2000" :step="10" controls-position="right" />
              </el-form-item>
              <el-form-item label="单来源最多页数">
                <el-input-number v-model="automationForm.max_pages" :min="1" :max="100" controls-position="right" />
              </el-form-item>
            </div>

            <div class="automation-section-title"><span>容错策略</span><small>网络异常时按设置重试，避免任务长期占用</small></div>
            <div class="automation-grid three-columns">
              <el-form-item label="失败重试次数">
                <el-input-number v-model="automationForm.retry_count" :min="0" :max="5" controls-position="right" />
              </el-form-item>
              <el-form-item label="重试间隔（分钟）">
                <el-input-number v-model="automationForm.retry_delay_minutes" :min="1" :max="1440" controls-position="right" />
              </el-form-item>
              <el-form-item label="请求超时（秒）">
                <el-input-number v-model="automationForm.timeout_seconds" :min="30" :max="3600" :step="30" controls-position="right" />
              </el-form-item>
            </div>
          </el-form>
        </div>
        <template #footer>
          <el-button @click="automationDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="automationSaving" @click="saveAutomationConfig">保存配置</el-button>
        </template>
      </el-dialog>
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
        <template v-if="reviewStatus === 'unverified'">
          <el-checkbox
            :model-value="allPageFactsSelected"
            :indeterminate="somePageFactsSelected"
            @change="toggleCurrentPageFacts"
          >选择本页</el-checkbox>
          <el-button
            type="success"
            :disabled="selectedFactIds.length === 0"
            :loading="factReviewing"
            @click="batchApproveFacts"
          >批量同意（{{ selectedFactIds.length }}）</el-button>
          <el-button
            type="danger"
            plain
            :disabled="selectedFactIds.length === 0"
            :loading="factReviewing"
            @click="batchRejectFacts"
          >批量驳回</el-button>
          <el-button
            class="approve-all-button"
            type="success"
            plain
            :disabled="reviewSummary.unverified === 0"
            :loading="factReviewing"
            @click="approveAllFacts"
          >一键同意全部待审核</el-button>
        </template>
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
          <el-checkbox
            v-if="item.verification_status === 'unverified'"
            v-model="selectedFactIds"
            class="review-select"
            :label="item.id"
            :value="item.id"
          ><span class="sr-only">选择 {{ item.skill_name }}</span></el-checkbox>
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

    <!-- Graph enrichment review -->
    <section v-else-if="activeSection === 'graphReview'" class="admin-section anim-fade-up">
      <div class="section-heading">
        <div><span>GRAPH AGENT</span><h2>L4/L5 图谱补充审核</h2><p>机器校验、人工审核和图谱发布相互独立；只有已批准候选会进入正式图谱。</p></div>
        <div class="section-actions">
          <el-button
            class="graph-heading-action"
            type="danger"
            plain
            :disabled="graphMachineFailedPendingCount === 0"
            :loading="graphAutoRejecting"
            @click="rejectAllMachineFailedCandidates"
          >一键驳回机器未通过（{{ graphMachineFailedPendingCount }}）</el-button>
          <el-button class="graph-heading-action" type="primary" :plain="graphGenerating" :loading="graphGenerating" :disabled="graphTasks.anyRunning.value && !graphGenerating" @click="generateGraphCandidates">一键生成候选</el-button>
          <el-button class="graph-heading-action" type="primary" :loading="graphPublishing" :disabled="graphTasks.anyRunning.value && !graphPublishing" @click="publishGraphCandidates">发布已批准项</el-button>
        </div>
      </div>
      <div v-if="graphBackgroundTask" class="graph-agent-progress" role="status" aria-live="polite">
        <div><strong>{{ graphGenerating ? "正在并发生成 L4/L5 候选" : "正在发布已批准候选" }}</strong><span>{{ graphBackgroundTask.result?.detail || "任务已提交，可切换到其他子页面" }}</span></div>
        <el-progress :percentage="graphBackgroundTask.progress" />
      </div>
      <div class="graph-review-toolbar">
        <el-select v-model="graphReviewStatus" style="width: 160px" @change="loadGraphCandidates(1)">
          <el-option label="全部状态" value="" />
          <el-option label="待审核" value="pending" />
          <el-option label="已批准" value="approved" />
          <el-option label="已驳回" value="rejected" />
        </el-select>
        <span>共 {{ graphCandidateTotal }} 条候选</span>
      </div>
      <div v-loading="graphCandidatesLoading" class="graph-candidate-grid">
        <article v-for="candidate in graphCandidates" :key="candidate.id" class="graph-candidate-card">
          <header>
            <div><span>L3 技术栈</span><h3>{{ candidate.skill_name }}</h3></div>
            <div class="candidate-badges">
              <el-tag :type="candidate.machine_validation_status === 'passed' ? 'success' : 'warning'">机器：{{ machineStatusLabel(candidate.machine_validation_status) }}</el-tag>
              <el-tag :type="candidate.review_status === 'approved' ? 'success' : candidate.review_status === 'rejected' ? 'danger' : 'info'">审核：{{ graphReviewStatusLabel(candidate.review_status) }}</el-tag>
              <el-tag v-if="candidate.publication_status === 'published'" type="success">已发布</el-tag>
              <el-tag v-else-if="candidate.publication_status === 'superseded'" type="info">已被新版替代</el-tag>
            </div>
          </header>
          <div class="candidate-summary">
            <span>置信度 <strong>{{ Math.round(candidate.confidence * 100) }}%</strong></span>
            <span>证据 <strong>{{ candidate.evidence_source_ids.length }}</strong></span>
            <span>L4 节点 <strong>{{ candidate.candidate_data.tech_points?.length || 0 }}</strong></span>
          </div>
          <div v-if="candidate.candidate_data.tech_points?.length" class="candidate-points">
            <div v-for="point in candidate.candidate_data.tech_points" :key="point.name">
              <strong>{{ point.name }}</strong><p>{{ point.detail }}</p>
              <small>{{ point.knowledge_points?.length || 0 }} 个 L5 知识点</small>
            </div>
          </div>
          <el-alert v-else type="warning" :closable="false" :title="`未形成可审核节点：${candidateReasonLabel(candidate.candidate_data.reason)}`" />
          <footer v-if="candidate.review_status === 'pending'">
            <el-button type="danger" plain @click="reviewGraphCandidate(candidate, 'reject')">驳回</el-button>
            <el-button type="success" :disabled="candidate.machine_validation_status !== 'passed'" @click="reviewGraphCandidate(candidate, 'approve')">批准候选</el-button>
          </footer>
          <p v-else-if="candidate.review_note" class="candidate-note">审核备注：{{ candidate.review_note }}</p>
        </article>
      </div>
      <el-empty v-if="!graphCandidatesLoading && !graphCandidates.length" description="暂无 L4/L5 补充候选，可点击一键生成" />
      <el-pagination
        v-if="graphCandidateTotal > graphCandidatePageSize"
        class="review-pagination" background layout="prev, pager, next"
        :current-page="graphCandidatePage" :page-size="graphCandidatePageSize" :total="graphCandidateTotal"
        @current-change="loadGraphCandidates"
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
            <div v-for="api in endpoints" :key="api.key">
              <span class="operation-mark"><el-icon><DataLine /></el-icon></span>
              <span class="operation-copy"><strong>{{ api.title }}</strong><small>{{ api.description }}</small></span>
              <div class="endpoint-bar"><i :style="{ width: `${api.percent}%` }"></i></div>
              <strong>{{ api.value }}</strong>
            </div>
          </div>
        </article>
      </div>

      <article class="admin-card agent-run-panel">
        <div class="log-toolbar">
          <div><span>AGENT AUDIT</span><h2>Agent 运行审计</h2></div>
          <div>
            <el-select v-model="agentRunType" clearable placeholder="全部 Agent" style="width:180px" @change="reloadAgentRuns">
              <el-option label="JD 生成" value="jd_generation" />
              <el-option label="JD 输入建议" value="jd_input_suggestion" />
              <el-option label="职业规划" value="career_planning" />
              <el-option label="匹配解释" value="match_explanation" />
              <el-option label="技能抽取" value="skill_extraction" />
              <el-option label="图谱补全" value="graph_enrichment" />
            </el-select>
            <el-select v-model="agentRunStatus" clearable placeholder="全部状态" style="width:130px" @change="reloadAgentRuns">
              <el-option label="排队中" value="queued" />
              <el-option label="运行中" value="running" />
              <el-option label="成功" value="succeeded" />
              <el-option label="降级完成" value="degraded" />
              <el-option label="失败" value="failed" />
              <el-option label="已取消" value="cancelled" />
            </el-select>
          </div>
        </div>
        <el-table
          v-loading="agentRunsLoading"
          :data="agentRuns"
          style="width:100%"
          @row-click="selectedAgentRun = $event"
        >
          <el-table-column prop="agent_type" label="Agent" min-width="150" />
          <el-table-column label="状态" width="105">
            <template #default="{ row }"><el-tag :type="agentStatusTone(row.status)" effect="plain">{{ agentStatusLabel(row.status) }}</el-tag></template>
          </el-table-column>
          <el-table-column label="模型" min-width="150">
            <template #default>{{ DISPLAY_MODEL_NAME }}</template>
          </el-table-column>
          <el-table-column prop="prompt_version" label="Prompt 版本" min-width="125" />
          <el-table-column label="耗时" width="100"><template #default="{ row }">{{ row.duration_ms === null ? "—" : `${row.duration_ms} ms` }}</template></el-table-column>
          <el-table-column label="创建时间" min-width="175"><template #default="{ row }">{{ formatLocalDate(row.created_at) }}</template></el-table-column>
          <el-table-column label="操作" width="90"><template #default="{ row }"><el-button link type="primary" @click.stop="selectedAgentRun = row">详情</el-button></template></el-table-column>
        </el-table>
        <el-empty v-if="!agentRunsLoading && !agentRuns.length" description="暂无 Agent 运行记录" />
        <el-pagination
          v-if="agentRunsTotal > agentRunPageSize"
          v-model:current-page="agentRunPage"
          :page-size="agentRunPageSize"
          :total="agentRunsTotal"
          layout="prev, pager, next, total"
          class="agent-run-pagination"
          @current-change="store.loadAgentRuns()"
        />
      </article>

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

    <el-dialog v-model="showFactRejectDialog" title="驳回技能事实" width="520px" :teleported="false">
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

    <el-drawer v-model="agentRunDrawerVisible" title="Agent 运行详情" size="520px" :teleported="false">
      <template v-if="selectedAgentRun">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="运行 ID">{{ selectedAgentRun.id }}</el-descriptions-item>
          <el-descriptions-item label="Agent">{{ selectedAgentRun.agent_type }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ agentStatusLabel(selectedAgentRun.status) }}</el-descriptions-item>
          <el-descriptions-item label="模型">{{ DISPLAY_MODEL_NAME }}</el-descriptions-item>
          <el-descriptions-item label="Prompt 版本">{{ selectedAgentRun.prompt_version }}</el-descriptions-item>
          <el-descriptions-item label="输入摘要">{{ selectedAgentRun.input_summary }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatLocalDate(selectedAgentRun.started_at) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ formatLocalDate(selectedAgentRun.finished_at) }}</el-descriptions-item>
          <el-descriptions-item label="Token">{{ selectedAgentRun.prompt_tokens ?? "—" }} / {{ selectedAgentRun.completion_tokens ?? "—" }}</el-descriptions-item>
          <el-descriptions-item v-if="selectedAgentRun.error_message" label="错误">{{ selectedAgentRun.error_code }}：{{ selectedAgentRun.error_message }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="selectedAgentRun.structured_output" class="agent-output">
          <strong>结构化输出</strong>
          <pre>{{ JSON.stringify(selectedAgentRun.structured_output, null, 2) }}</pre>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { useAdminStore } from "@/stores/admin";
import { useSkillReviewsStore } from "@/stores/skillReviews";
import { dataProvider } from "@/data";
import { useGraphTasks } from "@/composables/useGraphTasks";
import DataState from "@/components/common/DataState.vue";
import type {
  DataQualityStatus,
  GraphEnrichmentCandidate,
  JobImportResult,
  AgentRunAudit,
  AgentRunStatus,
  RawJobQualityItem,
  SkillFactReviewItem,
  SkillFactReviewSummary,
  SkillFactVerificationStatus,
  CrawlerAutomationConfig,
} from "@/domain/types";
import { classifyImportFailure, errorMessage } from "@/utils/crawlerFlowError";

type Section = "overview" | "crawler" | "review" | "graphReview" | "monitor";

const DISPLAY_MODEL_NAME = "Spark X2";
const activeSection = ref<Section>("overview");
const router = useRouter();
const logLevel = ref("");
const logKeyword = ref("");
const autoScroll = ref(true);
const lastImportResult = ref<JobImportResult | null>(null);
const competitionImporting = ref<"" | "baseline" | "scenario">("");
const competitionStatus = ref("");
const automationDialogVisible = ref(false);
const automationLoading = ref(false);
const automationSaving = ref(false);
const automationForm = ref<CrawlerAutomationConfig>({
  enabled: false,
  source_ids: [],
  schedule_type: "interval",
  interval_minutes: 60,
  run_time: "02:00",
  weekdays: [0, 2, 4],
  max_records: 100,
  max_pages: 5,
  retry_count: 2,
  retry_delay_minutes: 10,
  timeout_seconds: 300,
});
const weekdayOptions = [
  { value: 0, label: "周一" }, { value: 1, label: "周二" },
  { value: 2, label: "周三" }, { value: 3, label: "周四" },
  { value: 4, label: "周五" }, { value: 5, label: "周六" },
  { value: 6, label: "周日" },
];
const store = useAdminStore();
const {
  data: admin,
  loading,
  loaded,
  error,
  agentRuns,
  agentRunsLoading,
  agentRunsTotal,
  agentRunPage,
  agentRunPageSize,
  agentRunStatus,
  agentRunType,
  qualityPage,
  qualityLoading,
  qualityError,
} = storeToRefs(store);
const selectedAgentRun = ref<AgentRunAudit | null>(null);
const agentRunDrawerVisible = computed({
  get: () => selectedAgentRun.value !== null,
  set: (value) => { if (!value) selectedAgentRun.value = null; },
});
const qualityStatus = ref<DataQualityStatus | "">("");
const qualitySource = ref("");
const qualityExcluded = ref<boolean | "">("");
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
const selectedFactIds = ref<number[]>([]);
const currentPageFactIds = computed(() => reviewItems.value
  .filter(item => item.verification_status === "unverified")
  .map(item => item.id));
const allPageFactsSelected = computed(() => currentPageFactIds.value.length > 0
  && currentPageFactIds.value.every(id => selectedFactIds.value.includes(id)));
const somePageFactsSelected = computed(() => !allPageFactsSelected.value
  && currentPageFactIds.value.some(id => selectedFactIds.value.includes(id)));
const graphCandidates = ref<GraphEnrichmentCandidate[]>([]);
const manualRefreshing = ref(false);
const graphCandidatesLoading = ref(false);
const graphCandidateTotal = ref(0);
const graphMachineFailedPendingCount = ref(0);
const graphAutoRejecting = ref(false);
const graphCandidatePage = ref(1);
const graphCandidatePageSize = 12;
const graphReviewStatus = ref("");
const graphTasks = useGraphTasks();
const graphGenerating = computed(() => ["queued", "running"].includes(graphTasks.tasks.enrichment?.status || ""));
const graphPublishing = computed(() => ["queued", "running"].includes(graphTasks.tasks.publication?.status || ""));
const graphBackgroundTask = computed(() => {
  if (graphGenerating.value) return graphTasks.tasks.enrichment;
  if (graphPublishing.value) return graphTasks.tasks.publication;
  return null;
});
let pollTimer: ReturnType<typeof setInterval> | null = null;
let resourceTimer: ReturnType<typeof setInterval> | null = null;
let pipelineTimer: ReturnType<typeof setInterval> | null = null;
let resourceRequestRunning = false;
let pipelineRequestRunning = false;

async function pollResources() {
  if (document.hidden || resourceRequestRunning || activeSection.value !== "overview") return;
  resourceRequestRunning = true;
  try { await store.refreshResources(); } finally { resourceRequestRunning = false; }
}
async function pollPipeline() {
  if (document.hidden || pipelineRequestRunning || activeSection.value !== "crawler") return;
  pipelineRequestRunning = true;
  try { await store.refreshSilently(); } finally { pipelineRequestRunning = false; }
}
onMounted(async () => {
  graphTasks.resume();
  await store.load();
  resourceTimer = setInterval(pollResources, 2000);
  pipelineTimer = setInterval(pollPipeline, 3000);
});

watch(() => graphTasks.tasks.enrichment?.status, async status => {
  if (status === "succeeded") {
    ElMessage.success("候选生成完成，已刷新审核列表");
    graphReviewStatus.value = "pending";
    await loadGraphCandidates(1);
  } else if (status === "failed") {
    ElMessage.error(graphTasks.tasks.enrichment?.error_message || "候选生成失败");
  }
});

watch(() => graphTasks.tasks.publication?.status, async status => {
  if (status === "succeeded") {
    ElMessage.success("已批准候选已写入正式图谱");
    await loadGraphCandidates();
  } else if (status === "failed") {
    ElMessage.error(graphTasks.tasks.publication?.error_message || "图谱发布失败");
  }
});
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
  if (resourceTimer) clearInterval(resourceTimer);
  if (pipelineTimer) clearInterval(pipelineTimer);
});

const navItems: { value: Section; label: string; desc: string; icon: string }[] = [
  { value: "overview", label: "运行总览", desc: "系统健康与关键指标", icon: "Odometer" },
  { value: "crawler", label: "采集中心", desc: "爬虫任务与数据质量", icon: "Download" },
  { value: "review", label: "事实审核", desc: "证据确认与驳回", icon: "DocumentChecked" },
  { value: "graphReview", label: "图谱审核", desc: "L4/L5 生成与发布", icon: "Share" },
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
const traffic = computed(() => admin.value?.traffic ?? {
  inbound: "0.0 B/s",
  outbound: "0.0 B/s",
  receivedTotal: "0.0 B",
  sentTotal: "0.0 B",
});
const recentTasks = computed(() => admin.value?.recentTasks ?? []);
const systemEvents = computed(() => admin.value?.systemEvents ?? []);
const crawlers = computed(() => admin.value?.crawlers ?? []);
const currentPipelineRun = computed(() => admin.value?.currentPipelineRun ?? null);
const latestPipelineRun = computed(() => admin.value?.pipelineRuns?.[0] ?? null);
const pipelineStages = [
  { key: "collect", label: "采集" },
  { key: "validate_import", label: "校验入库" },
  { key: "quality_gate", label: "质量门禁" },
  { key: "graph_publish", label: "入图发布" },
  { key: "baseline_refresh", label: "滚动基线" },
  { key: "trend_verify", label: "趋势验收" },
];
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
const performanceCards = computed(() => admin.value?.performanceCards ?? []);
const endpoints = computed(() => admin.value?.endpoints ?? []);
const logs = computed(() => admin.value?.logs ?? []);
const runningCrawlerCount = computed(() => crawlers.value.filter((item) => item.running).length);
const healthyServiceCount = computed(() => services.value.filter((item) => item.status === "healthy").length);
const overallStatus = computed(() => {
  if (services.value.some((item) => item.status === "unavailable")) return "unavailable";
  if (services.value.some((item) => item.status === "degraded")) return "degraded";
  return "healthy";
});
const overallStatusLabel = computed(() => ({
  healthy: "系统运行正常",
  degraded: "系统降级运行",
  unavailable: "系统存在异常",
})[overallStatus.value]);
const generatedAtLabel = computed(() => {
  const value = admin.value?.generatedAt;
  return value
    ? new Date(value).toLocaleTimeString("zh-CN", { hour12: false })
    : "尚未完成";
});
const validationPassed = computed(() => lastImportResult.value?.validation.reduce((sum, item) => sum + item.passed, 0) ?? 0);
const validationWarnings = computed(() => lastImportResult.value?.validation.reduce((sum, item) => sum + item.warning_count, 0) ?? 0);
const filteredLogs = computed(() => logs.value.filter((log) => (!logLevel.value || log.level === logLevel.value) && (!logKeyword.value || `${log.service} ${log.message}`.toLowerCase().includes(logKeyword.value.toLowerCase()))));

async function refreshSystem() {
  manualRefreshing.value = true;
  try {
    await store.refreshSilently();
    ElMessage.success("系统状态已刷新");
  } finally {
    manualRefreshing.value = false;
  }
}
async function selectSection(section: Section) {
  activeSection.value = section;
  if (section === "crawler") await refreshQuality(1);
  if (section === "review") await reviewStore.load(true);
  if (section === "graphReview") await loadGraphCandidates(1);
  if (section === "monitor") await Promise.all([store.load(true), store.loadAgentRuns()]);
}

async function loadGraphCandidates(page = graphCandidatePage.value) {
  graphCandidatePage.value = page;
  graphCandidatesLoading.value = true;
  try {
    const result = await dataProvider.graph.listEnrichment({
      page, pageSize: graphCandidatePageSize,
      reviewStatus: graphReviewStatus.value || undefined,
    });
    graphCandidates.value = result.items;
    graphCandidateTotal.value = result.total;
    graphMachineFailedPendingCount.value = result.machine_failed_pending_count;
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "图谱候选加载失败");
  } finally {
    graphCandidatesLoading.value = false;
  }
}

async function generateGraphCandidates() {
  try {
    await graphTasks.startEnrichment();
    ElMessage.success("候选生成任务已提交，可继续审核其他内容");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "候选生成失败");
  }
}

async function reviewGraphCandidate(candidate: GraphEnrichmentCandidate, action: "approve" | "reject") {
  let note = action === "approve" ? "证据与节点结构审核通过" : "";
  if (action === "reject" && candidate.machine_validation_status === "passed") {
    try {
      const result = await ElMessageBox.prompt("请填写驳回原因，审核记录将被保留。", "驳回图谱候选", {
        inputValidator: (value) => Boolean(value.trim()) || "请填写驳回原因",
      });
      note = result.value;
    } catch { return; }
  }
  try {
    await dataProvider.graph.reviewEnrichment(candidate.id, {
      action, note, lockVersion: candidate.lock_version,
    });
    ElMessage.success(action === "approve" ? "候选已批准，已自动触发 L4/L5 图谱发布，稍后可在技能图谱页查看" : "候选已驳回");
    await loadGraphCandidates();
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "候选审核失败");
  }
}

async function rejectAllMachineFailedCandidates() {
  if (!graphMachineFailedPendingCount.value) return;
  try {
    await ElMessageBox.confirm(
      `系统将使用各候选的机器审核结果，自动驳回 ${graphMachineFailedPendingCount.value} 条未通过项。审核理由会逐条写入记录，是否继续？`,
      "一键驳回机器未通过项",
      { confirmButtonText: "自动驳回", cancelButtonText: "取消", type: "warning" },
    );
    graphAutoRejecting.value = true;
    const result = await dataProvider.graph.rejectMachineFailedEnrichment();
    ElMessage.success(`已自动驳回 ${result.rejected_count} 条候选，并记录机器审核理由`);
    await loadGraphCandidates(1);
  } catch (value) {
    if (value !== "cancel" && value !== "close") {
      ElMessage.error(errorMessage(value, "自动驳回失败"));
    }
  } finally {
    graphAutoRejecting.value = false;
  }
}

async function publishGraphCandidates() {
  const approved = graphCandidates.value.filter(item => item.review_status === "approved" && item.publication_status !== "published");
  try {
    await graphTasks.startPublication(approved.map(item => item.id));
    ElMessage.success("图谱发布任务已提交，可继续使用当前页面");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "图谱发布失败");
  }
}

function machineStatusLabel(status: string) {
  return ({ passed: "通过", failed: "生成失败", pending: "待执行", skipped: "已跳过", retrieval_failed: "检索失败", insufficient_evidence: "证据不足" } as Record<string, string>)[status] || status;
}

function candidateReasonLabel(reason?: unknown) {
  const key = typeof reason === "string" ? reason : "insufficient_evidence";
  return ({
    llm_timeout: "模型响应超时，已完成自动重试，可稍后重新生成",
    llm_failed: "模型调用失败，请查看运行日志后重试",
    llm_disabled: "模型服务未配置",
    retrieval_unavailable: "证据检索服务不可用",
    insufficient_evidence: "独立来源不足，未达到双来源门槛",
    insufficient_grounding: "生成内容未通过证据引用校验",
  } as Record<string, string>)[key] || key;
}
function graphReviewStatusLabel(status: GraphEnrichmentCandidate["review_status"]) {
  return { pending: "待审核", approved: "已批准", rejected: "已驳回" }[status];
}
async function reloadAgentRuns() {
  agentRunPage.value = 1;
  await store.loadAgentRuns();
}
function agentStatusLabel(status: AgentRunStatus) {
  return { queued:"排队中",running:"运行中",succeeded:"成功",degraded:"降级完成",failed:"失败",cancelled:"已取消" }[status];
}
function agentStatusTone(status: AgentRunStatus) {
  if (status === "succeeded") return "success";
  if (status === "degraded") return "warning";
  if (status === "failed" || status === "cancelled") return "danger";
  return "info";
}
function formatLocalDate(value: string | null) {
  return value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "—";
}
function handleEvent(event: any) {
  if (["overview", "crawler", "review", "graphReview", "monitor"].includes(event.target)) {
    void selectSection(event.target as Section);
  }
}
async function toggleCrawler(crawler: any) { await store.toggleCrawler(crawler.id); ElMessage.success(`${crawler.name}状态已更新`); }
async function openAutomationDialog() {
  automationDialogVisible.value = true;
  automationLoading.value = true;
  try {
    automationForm.value = await store.getCrawlerAutomation();
  } catch (error) {
    ElMessage.error(`配置加载失败：${errorMessage(error)}`);
  } finally {
    automationLoading.value = false;
  }
}
async function saveAutomationConfig() {
  if (automationForm.value.enabled && automationForm.value.source_ids.length === 0) {
    ElMessage.warning("启用自动爬取时请至少选择一个数据来源");
    return;
  }
  if (automationForm.value.schedule_type === "weekly" && automationForm.value.weekdays.length === 0) {
    ElMessage.warning("按周执行时请至少选择一天");
    return;
  }
  automationSaving.value = true;
  try {
    automationForm.value = await store.saveCrawlerAutomation({ ...automationForm.value });
    automationDialogVisible.value = false;
    ElMessage.success(automationForm.value.enabled ? "自动爬取计划已启用" : "自动爬取计划已停用");
  } catch (error) {
    ElMessage.error(`配置保存失败：${errorMessage(error)}`);
  } finally {
    automationSaving.value = false;
  }
}
async function runPipeline(crawler: any) {
  try {
    const run = await store.startPipeline([crawler.id]);
    ElMessage.success(`${crawler.name}端到端更新已启动（${run.id.slice(0, 8)}）`);
  } catch (error) {
    ElMessage.error(`${crawler.name}更新启动失败：${errorMessage(error)}`);
  }
}
function pipelineStageLabel(stage: string) {
  return pipelineStages.find((item) => item.key === stage)?.label ?? "准备执行";
}
function pipelineStatusLabel(status: string) {
  return ({ succeeded: "全部成功", partial: "部分成功", failed: "失败" } as Record<string, string>)[status] ?? status;
}
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
          // 运行失败：优先展示后端结构化可读消息，回退 stderr
          const errMsg = result?.message || result?.stderr || result?.stdout || "未知错误";
          ElMessage.error(`${crawler.name}采集失败：${errMsg.slice(0, 200)}`);
        } else {
          if (!result?.filename || result?.error_category === "no_data") {
            // 静默失败：展示后端细分的具体原因（反爬/超时/内容无变化）
            const noDataMsg = result?.message || "没有生成新的数据文件，请检查站点可访问性";
            ElMessage.warning(`${crawler.name}采集完成但未产生新数据：${noDataMsg}`);
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
        await store.refreshSilently();
      } else {
        // 仍在运行，刷新进度
        await store.refreshSilently();
      }
    } catch (error) {
      if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
      ElMessage.error(`${crawler.name}状态轮询失败：${errorMessage(error)}`);
    }
  }, 2000);
}
async function importCompetitionData(kind: "baseline" | "scenario") {
  const filename = kind === "baseline"
    ? "competition-test/01_existing_job_baseline.json"
    : "competition-test/02_new_job_and_existing_update_v2.json";
  competitionImporting.value = kind;
  competitionStatus.value = "";
  try {
    lastImportResult.value = await store.importCrawlerOutput(filename);
    if (kind === "baseline") {
      competitionStatus.value = `第一时间窗口处理完成：入库 ${lastImportResult.value.imported} 条，技能事实 ${lastImportResult.value.skill_facts} 条。`;
      ElMessage.success("第一时间窗口处理完成，请继续执行步骤 2");
    } else {
      if (!graphTasks.anyRunning.value) await graphTasks.startSync();
      competitionStatus.value = `第二时间窗口处理完成：入库 ${lastImportResult.value.imported} 条，涉及 ${lastImportResult.value.affected_standard_job_ids?.length ?? 0} 个标准岗位；图谱同步任务已提交。`;
      ElMessage.success("步骤 2 完成，可查看岗位洞察与技能图谱");
    }
    await store.refreshSilently();
  } catch (error) {
    ElMessage.error(`测试数据导入失败：${errorMessage(error)}`);
  } finally {
    competitionImporting.value = "";
  }
}
function openCompetitionInsights() {
  void router.push({ path: "/jobs", query: { tab: "insight", skill: "RAG" } });
}
function openCompetitionGraph() {
  void router.push("/graph");
}
function viewCrawlerLog(crawler: any) { activeSection.value = "monitor"; logKeyword.value = crawler.name; }
function createSource() { ElMessage.info("添加数据源表单待后端数据源协议确定后接入"); }
async function refreshQuality(page = qualityPage.value?.meta.page ?? 1) {
  await store.loadQuality({
    page,
    pageSize: qualityPage.value?.meta.page_size ?? 20,
    source: qualitySource.value.trim() || undefined,
    qualityStatus: qualityStatus.value || undefined,
    excluded: qualityExcluded.value === "" ? undefined : qualityExcluded.value,
  });
}
async function excludeQualityRecord(row: RawJobQualityItem) {
  try {
    const { value } = await ElMessageBox.prompt(
      `排除“${row.title}”后，其技能事实将退出正式图谱。请输入审核原因。`,
      "排除低质量记录",
      {
        confirmButtonText: "确认排除",
        cancelButtonText: "取消",
        inputPlaceholder: "例如：发布时间异常且正文不完整",
        inputValidator: (value: string) => value.trim().length > 0 || "必须填写排除原因",
        type: "warning",
      },
    );
    await store.decideQuality(Number(row.id), "exclude", value.trim());
    await refreshQuality();
    ElMessage.success("记录已排除，关联事实已降级为待验证");
  } catch (value) {
    if (value !== "cancel" && value !== "close") {
      ElMessage.error(errorMessage(value, "排除操作失败"));
    }
  }
}
async function restoreQualityRecord(row: RawJobQualityItem) {
  try {
    await ElMessageBox.confirm(
      `恢复“${row.title}”并重新执行跨来源事实认证？`,
      "恢复质量记录",
      { confirmButtonText: "确认恢复", cancelButtonText: "取消", type: "success" },
    );
    await store.decideQuality(Number(row.id), "restore");
    await refreshQuality();
    ElMessage.success("记录已恢复，并已重新计算事实认证状态");
  } catch (value) {
    if (value !== "cancel" && value !== "close") {
      ElMessage.error(errorMessage(value, "恢复操作失败"));
    }
  }
}
function qualityStatusLabel(value: DataQualityStatus) {
  return { accepted: "通过", warning: "警告", rejected: "拒绝", pending: "待评估" }[value];
}
function qualityStatusType(value: DataQualityStatus) {
  return {
    accepted: "success",
    warning: "warning",
    rejected: "danger",
    pending: "info",
  }[value] as "success" | "warning" | "danger" | "info";
}
function qualityFlagLabel(value: string) {
  return {
    near_duplicate: "近重复",
    stale: "数据陈旧",
    missing_posted_at: "缺少发布时间",
    invalid_posted_at: "发布时间无效",
    future_posted_at: "发布时间在未来",
    missing_or_invalid_crawled_at: "采集时间无效",
    thin_content: "正文过短",
  }[value] ?? value;
}
function formatQualityDate(value: string | null, fallback: string | null) {
  if (!value) return fallback || "未记录";
  return new Date(value).toLocaleDateString("zh-CN");
}
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
  selectedFactIds.value = [];
  reviewStatus.value = value;
  await reviewStore.load(true);
}
async function changeReviewPage(value: number) {
  selectedFactIds.value = [];
  reviewPage.value = value;
  await reviewStore.load();
}
function toggleCurrentPageFacts(value: unknown) {
  if (Boolean(value)) {
    selectedFactIds.value = Array.from(new Set([...selectedFactIds.value, ...currentPageFactIds.value]));
    return;
  }
  const currentIds = new Set(currentPageFactIds.value);
  selectedFactIds.value = selectedFactIds.value.filter(id => !currentIds.has(id));
}
async function batchApproveFacts() {
  if (!selectedFactIds.value.length) return;
  try {
    await ElMessageBox.confirm(
      `确认同意已选择的 ${selectedFactIds.value.length} 条技能事实？`,
      "批量同意",
      { confirmButtonText: "批量通过", cancelButtonText: "取消", type: "success" },
    );
    factReviewing.value = true;
    const result = await reviewStore.reviewBatch(selectedFactIds.value, "verified", "证据充分，管理员批量确认");
    selectedFactIds.value = [];
    ElMessage.success(`已同意 ${result.processed_count} 条技能事实，已自动触发图谱增量同步，稍后可在技能图谱页查看`);
  } catch (value) {
    if (value !== "cancel" && value !== "close") ElMessage.error(errorMessage(value, "批量审核失败"));
  } finally {
    factReviewing.value = false;
  }
}
async function batchRejectFacts() {
  if (!selectedFactIds.value.length) return;
  try {
    const { value: note } = await ElMessageBox.prompt(
      `请输入驳回这 ${selectedFactIds.value.length} 条事实的统一原因`,
      "批量驳回",
      {
        confirmButtonText: "确认驳回", cancelButtonText: "取消",
        inputPlaceholder: "例如：证据仅描述业务场景，不能证明岗位要求",
        inputValidator: value => Boolean(value.trim()) || "必须填写驳回原因",
        type: "warning",
      },
    );
    factReviewing.value = true;
    const result = await reviewStore.reviewBatch(selectedFactIds.value, "rejected", note.trim());
    selectedFactIds.value = [];
    ElMessage.success(`已驳回 ${result.processed_count} 条技能事实`);
  } catch (value) {
    if (value !== "cancel" && value !== "close") ElMessage.error(errorMessage(value, "批量审核失败"));
  } finally {
    factReviewing.value = false;
  }
}
async function approveAllFacts() {
  const scopeText = reviewKeyword.value.trim()
    ? `当前检索条件下的 ${reviewTotal.value} 条待审核事实`
    : `${reviewSummary.value.unverified} 条全部待审核事实`;
  try {
    await ElMessageBox.confirm(
      `将一次性同意${scopeText}。该操作会保留审核人和审核时间，是否继续？`,
      "一键同意",
      { confirmButtonText: "同意全部", cancelButtonText: "取消", type: "warning" },
    );
    factReviewing.value = true;
    const result = await reviewStore.approveAll();
    selectedFactIds.value = [];
    ElMessage.success(`已同意 ${result.processed_count} 条技能事实，已自动触发图谱增量同步，稍后可在技能图谱页查看`);
  } catch (value) {
    if (value !== "cancel" && value !== "close") ElMessage.error(errorMessage(value, "一键同意失败"));
  } finally {
    factReviewing.value = false;
  }
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
    ElMessage.success("技能事实已确认，已自动触发图谱增量同步，稍后可在技能图谱页查看");
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

<style>
.pipeline-run-card { margin: 0 0 13px; }
.pipeline-run-body { padding: 0 18px 16px; }
.pipeline-run-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.pipeline-run-title strong { font-size: 14px; }
.pipeline-run-title small { color: var(--text-muted); font: 500 12px var(--font-mono); }
.pipeline-stages { display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; margin-top: 10px; }
.pipeline-stages span { padding: 6px; border-radius: 7px; background: var(--color-bg-muted); color: var(--text-muted); font-size: 12px; text-align: center; }
.pipeline-stages span.active { background: var(--color-brand-light); color: var(--color-brand); font-weight: 700; }
.pipeline-error { margin: 8px 0 0; color: var(--color-danger); font-size: 12px; }
.graph-agent-progress {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(300px, 42%);
  align-items: center;
  gap: 24px;
  margin-bottom: 16px;
  padding: 14px 18px;
  border: 1px solid rgba(79, 110, 246, 0.22);
  border-radius: var(--radius-lg);
  background: linear-gradient(100deg, #f5f7ff, #fff);
}
.graph-agent-progress strong,
.graph-agent-progress span { display: block; }
.graph-agent-progress span { margin-top: 4px; color: var(--text-muted); font-size: 13px; }
@scope (.admin-page) {
:scope{max-width:1480px;margin:0 auto;--admin-dark:#202437}.admin-status{display:flex;align-items:center;gap:10px;flex:0 0 auto;padding:9px 10px 9px 17px;border-left:1px solid var(--color-border);border-radius:0 9px 9px 0;background:var(--color-success-light)}.status-pulse{width:9px;height:9px;border-radius:50%;background:var(--color-success);box-shadow:0 0 0 5px rgba(52,179,126,.12)}.admin-status div{display:flex;flex-direction:column;margin-right:4px}.admin-status strong{font-size:14px;color:var(--text-primary)}.admin-status small{font-size:14px;color:var(--text-muted)}.admin-status button,.card-heading button{display:flex;align-items:center;gap:5px;border:0;background:#fff;border-radius:8px;padding:7px 9px;color:var(--text-secondary);font:600 14px var(--font-sans);cursor:pointer}.admin-status button:disabled{cursor:wait;opacity:.72}
.admin-nav{display:flex;align-items:stretch;gap:6px;padding:6px;margin-bottom:17px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.admin-nav-items{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:5px;min-width:0;flex:1}.admin-nav-items button{position:relative;display:flex;align-items:center;gap:7px;min-width:0;padding:8px 7px;border:0;border-radius:9px;background:transparent;text-align:left;cursor:pointer;color:var(--text-secondary);transition:.2s}.admin-nav-items button:hover{background:var(--color-bg-muted)}.admin-nav-items button.active{background:var(--color-brand-light);color:var(--color-brand)}.nav-icon{display:grid;width:30px;height:30px;flex:0 0 30px;place-items:center;border-radius:8px;background:var(--color-bg-muted);font-size:15px}.admin-nav-items button.active .nav-icon{background:#fff}.admin-nav-items button>span:nth-child(2){display:flex;min-width:0;flex-direction:column}.admin-nav strong{overflow:hidden;font-size:13px;text-overflow:ellipsis;white-space:nowrap}.admin-nav small{overflow:hidden;margin-top:1px;color:var(--text-muted);font-size:11px;text-overflow:ellipsis;white-space:nowrap}.admin-nav-items button>i{position:absolute;right:5px;top:5px;min-width:17px;padding:1px 5px;border-radius:999px;background:var(--color-danger);color:#fff;font:700 11px var(--font-mono);text-align:center}
.admin-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:11px;margin-bottom:13px}.metric-card{display:flex;align-items:center;gap:11px;min-width:0;padding:16px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.metric-icon{display:grid;width:38px;height:38px;flex:0 0 38px;place-items:center;border-radius:11px;font-size:17px}.brand{background:var(--color-brand-light);color:var(--color-brand)}.green{background:var(--color-success-light);color:var(--color-success)}.amber{background:var(--color-warning-light);color:var(--color-warning)}.rose{background:var(--color-danger-light);color:var(--color-danger)}.violet{background:#f0edff;color:#7c6ff7}.blue{background:var(--color-info-light);color:var(--color-info)}.metric-copy{display:flex;min-width:0;flex:1;flex-direction:column}.metric-copy span{font-size:14px;color:var(--text-muted)}.metric-copy strong{font:700 22px var(--font-mono);letter-spacing:-.04em}.metric-copy small{font-size:14px}.positive,.green{color:var(--color-success)}.warning,.amber{color:var(--color-warning)}.metric-bars,.spark-bars{display:flex;align-items:flex-end;gap:2px;height:38px}.metric-bars i,.spark-bars i{width:3px;min-height:4px;border-radius:2px;background:var(--color-brand);opacity:.55}.overview-grid{display:grid;grid-template-columns:1.3fr .7fr;gap:13px}.admin-card{border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.card-heading{display:flex;align-items:center;justify-content:space-between;padding:16px 18px 11px}.card-heading>div{display:flex;flex-direction:column}.card-heading span,.section-heading>div>span{font:700 14px var(--font-mono);letter-spacing:.09em;color:var(--text-muted);text-transform:uppercase}.card-heading h2{font-size:14px;margin-top:2px}.healthy-chip,.event-count{padding:4px 8px;border-radius:999px;background:var(--color-success-light);color:var(--color-success)!important;font:700 14px var(--font-sans)!important;letter-spacing:0!important}.service-list,.task-list,.event-list{padding:0 18px 12px}.service-row,.task-row{display:flex;align-items:center;gap:10px;padding:10px 0}.service-row+.service-row,.task-row+.task-row{border-top:1px solid var(--color-border-light)}.service-logo,.task-state{display:grid;width:31px;height:31px;flex:0 0 31px;place-items:center;border-radius:9px}.service-name,.task-row>div{display:flex;min-width:0;flex:1;flex-direction:column}.service-name strong,.task-row strong{font-size:14px}.service-name small,.task-row small{font-size:14px;color:var(--text-muted)}.latency{display:flex;flex-direction:column;align-items:flex-end}.latency strong{font:600 14px var(--font-mono)}.latency small{font-size:14px;color:var(--text-muted)}.service-state{display:flex;align-items:center;gap:4px;color:var(--color-success);font-size:14px;font-weight:600}.service-state i,.live-label i{width:6px;height:6px;border-radius:50%;background:currentColor}.resource-card{padding-bottom:14px}.live-label{display:flex;align-items:center;gap:5px;color:var(--color-success)!important;font:700 14px var(--font-mono)!important}.resource-rings{display:flex;justify-content:space-around;padding:12px 15px 16px}.resource-item{display:flex;align-items:center;flex-direction:column}.resource-ring{display:grid;width:76px;height:76px;place-items:center;border-radius:50%;background:conic-gradient(var(--ring-color) calc(var(--value)*1%),var(--color-bg-muted) 0);position:relative}.resource-ring:before{content:"";position:absolute;inset:6px;border-radius:50%;background:#fff}.resource-ring span{z-index:1;font:700 17px var(--font-mono)}.resource-ring small{font-size:14px}.resource-item>strong{font-size:14px;margin-top:7px}.resource-item>small{font-size:14px;color:var(--text-muted)}.traffic-strip{display:grid;grid-template-columns:1fr 1fr;gap:7px;padding:0 15px}.traffic-strip div{display:flex;align-items:center;gap:6px;padding:9px;border-radius:8px;background:var(--color-bg-muted);font-size:14px}.traffic-strip strong{margin-left:auto;font:600 14px var(--font-mono)}.task-state.success{background:var(--color-success-light);color:var(--color-success)}.task-state.running{background:var(--color-brand-light);color:var(--color-brand)}.task-state.warning{background:var(--color-warning-light);color:var(--color-warning)}.task-count{font:600 14px var(--font-mono);color:var(--text-secondary)}.task-status{min-width:48px;text-align:right;font-size:14px;font-weight:700}.task-status.success{color:var(--color-success)}.task-status.running{color:var(--color-brand)}.task-status.warning{color:var(--color-warning)}.event-card .event-count{background:var(--color-danger-light);color:var(--color-danger)!important}.event-list button{display:flex;align-items:center;gap:9px;width:100%;padding:10px 0;border:0;border-top:1px solid var(--color-border-light);background:transparent;text-align:left;cursor:pointer}.event-level{display:grid;width:29px;height:29px;place-items:center;border-radius:8px}.event-level.warning{background:var(--color-warning-light)}.event-level.danger{background:var(--color-danger-light);color:var(--color-danger)}.event-level.info{background:var(--color-info-light);color:var(--color-info)}.event-list button>span:nth-child(2){display:flex;min-width:0;flex:1;flex-direction:column}.event-list strong{font-size:14px}.event-list small{font-size:14px;color:var(--text-muted)}.event-list time{font:500 14px var(--font-mono);color:var(--text-muted)}
.section-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin:8px 2px 16px}.section-heading h2{font-size:20px;letter-spacing:-.03em}.section-heading p{font-size:14px;color:var(--text-muted);margin-top:3px}.section-actions{display:flex;gap:8px}.crawler-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:13px}.crawler-summary>div{display:flex;flex-direction:column;padding:14px 16px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.crawler-summary span{font-size:14px;color:var(--text-muted)}.crawler-summary strong{font:700 20px var(--font-mono)}.crawler-summary small{font-size:14px;color:var(--text-muted)}.crawler-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:13px}.crawler-card{padding:16px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff;transition:.2s}.crawler-card.paused{opacity:.72;background:var(--color-bg-muted)}.crawler-head{display:flex;align-items:center;gap:10px}.source-logo{display:grid;width:39px;height:39px;place-items:center;border-radius:11px;background:var(--color-brand-light);color:var(--color-brand);font-weight:700}.crawler-head>div{min-width:0;flex:1}.crawler-head h3{font-size:14px}.crawler-head p{font-size:14px;color:var(--text-muted)}.crawler-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:14px 0}.crawler-stats div{display:flex;flex-direction:column;padding:8px;border-radius:8px;background:var(--color-bg-muted)}.crawler-stats span,.crawler-progress span,.crawler-meta{font-size:14px;color:var(--text-muted)}.crawler-stats strong{font:600 14px var(--font-mono)}.crawler-progress>div{display:flex;justify-content:space-between;margin-bottom:5px}.crawler-progress strong{font:600 14px var(--font-mono)}.crawler-meta{display:flex;justify-content:space-between;margin-top:9px}.crawler-meta span{display:flex;align-items:center;gap:4px}.crawler-card footer{display:flex;gap:5px;padding-top:11px;margin-top:11px;border-top:1px solid var(--color-border-light)}.crawler-card footer button{display:flex;align-items:center;justify-content:center;gap:4px;flex:1;height:29px;border:1px solid var(--color-border);border-radius:7px;background:#fff;color:var(--text-secondary);font:600 14px var(--font-sans);cursor:pointer}.crawler-card footer button:first-child{border-color:var(--color-brand);color:var(--color-brand)}.crawler-card footer button:disabled{opacity:.5;cursor:not-allowed}.quality-panel{padding-bottom:16px}.quality-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:2px 18px}.quality-grid>div{padding:12px;border-radius:9px;background:var(--color-bg-muted)}.quality-grid span{font-size:14px;color:var(--text-muted)}.quality-grid strong{display:block;font:700 17px var(--font-mono);margin:2px 0 7px}.quality-grid small{font-size:14px;color:var(--text-muted)}
.import-result{padding:16px;margin-bottom:13px;border:1px solid color-mix(in srgb,var(--color-success) 35%,var(--color-border));border-radius:var(--radius-lg);background:color-mix(in srgb,var(--color-success) 5%,#fff)}.import-result-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}.import-result-head>div{display:flex;flex-direction:column}.import-result-head span{font-size:13px;color:var(--text-muted)}.import-result-head strong{font-size:14px}.import-result-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}.import-result-grid>div{padding:9px 10px;border-radius:8px;background:#fff}.import-result-grid span{display:block;font-size:12px;color:var(--text-muted)}.import-result-grid strong{font:700 16px var(--font-mono)}
.competition-test-card{margin-bottom:13px;padding-bottom:16px;border-color:rgba(79,110,246,.3);background:linear-gradient(120deg,#f7f9ff 0,#fff 55%)}.test-data-chip{padding:5px 9px;border-radius:999px;background:var(--color-brand-light);color:var(--color-brand)!important;font:700 12px var(--font-sans)!important;letter-spacing:0!important;text-transform:none!important}.competition-test-intro{padding:0 18px 12px;color:var(--text-muted);font-size:13px}.competition-test-steps{display:grid;gap:8px;padding:0 18px 14px}.competition-test-steps section{display:flex;align-items:center;gap:11px;padding:11px 12px;border:1px solid var(--color-border-light);border-radius:10px;background:rgba(255,255,255,.9)}.step-number{display:grid;width:28px;height:28px;flex:0 0 28px;place-items:center;border-radius:50%;background:var(--color-brand);color:#fff;font:700 13px var(--font-mono)}.competition-test-steps section>div:nth-child(2){display:flex;min-width:0;flex:1;flex-direction:column}.competition-test-steps strong{font-size:14px}.competition-test-steps small{margin-top:2px;color:var(--text-muted);font-size:12px}.competition-result-actions{display:flex;gap:7px}.competition-test-card>.el-alert{margin:0 18px;width:auto}
.automation-config-button{height:38px;padding:0 16px!important;border-radius:9px!important}.automation-form{min-height:260px}.automation-intro{display:flex;align-items:center;gap:12px;margin:-4px 0 20px;padding:14px 15px;border:1px solid #dfe5ff;border-radius:12px;background:linear-gradient(110deg,#f3f6ff,#fff)}.automation-intro>div{min-width:0;flex:1}.automation-intro strong{font-size:14px}.automation-intro p{margin-top:2px;color:var(--text-muted);font-size:12px;line-height:1.5}.automation-icon{display:grid;width:38px;height:38px;flex:0 0 38px;place-items:center;border-radius:10px;background:var(--color-brand);color:#fff;font-size:18px}.source-checks{display:grid;width:100%;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.source-checks .el-checkbox{height:auto;margin:0;padding:9px 11px;border:1px solid var(--color-border);border-radius:9px}.source-option{display:flex;align-items:center;gap:8px}.source-option i{display:grid;width:27px;height:27px;place-items:center;border-radius:7px;background:var(--color-brand-light);color:var(--color-brand);font-size:10px;font-style:normal;font-weight:700}.automation-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.automation-grid.three-columns{grid-template-columns:repeat(3,minmax(0,1fr))}.automation-grid .el-input-number,.automation-grid .el-select{width:100%}.automation-grid .el-form-item small{display:block;margin-top:4px;color:var(--text-muted);font-size:11px}.automation-section-title{display:flex;align-items:baseline;gap:8px;margin:3px 0 12px;padding-top:15px;border-top:1px solid var(--color-border-light)}.automation-section-title span{font-size:13px;font-weight:700}.automation-section-title small{color:var(--text-muted);font-size:11px}.weekday-checks{display:flex;flex-wrap:wrap}.automation-dialog .el-dialog__footer{padding-top:4px}
.quality-review-panel{margin-top:13px;overflow:hidden}.quality-review-summary{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;padding:0 18px 12px}.quality-review-summary>div{padding:10px 12px;border-radius:8px;background:var(--color-bg-muted)}.quality-review-summary span{display:block;font-size:12px;color:var(--text-muted)}.quality-review-summary strong{font:700 17px var(--font-mono)}.quality-review-toolbar{display:flex;gap:8px;padding:0 18px 14px}.quality-review-toolbar .el-select{width:150px}.quality-review-toolbar .el-input{max-width:260px}.quality-job{display:flex;min-width:0;flex-direction:column}.quality-job strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.quality-job span,.quality-flags>span{font-size:12px;color:var(--text-muted)}.quality-flags{display:flex;flex-wrap:wrap;gap:4px}.mono{font-family:var(--font-mono)}.quality-pagination{justify-content:center;padding:15px 18px}
.review-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:11px;padding:6px;border:1px solid var(--color-border);border-radius:12px;background:#fff}.review-summary button{display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border:0;border-radius:8px;background:transparent;color:var(--text-secondary);font:600 13px var(--font-sans);cursor:pointer}.review-summary button.active{background:var(--color-brand-light);color:var(--color-brand)}.review-summary strong{padding:2px 7px;border-radius:999px;background:#fff;font:700 12px var(--font-mono)}.review-toolbar{display:flex;align-items:center;gap:8px;margin-bottom:12px}.review-toolbar .el-input{max-width:480px}.review-toolbar>span{margin-left:auto;font:600 12px var(--font-mono);color:var(--text-muted)}.review-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px}.review-card{position:relative;overflow:hidden;padding:17px 17px 14px 21px;border:1px solid var(--color-border);border-radius:13px;background:#fff;box-shadow:0 4px 14px rgba(32,36,55,.04)}.review-card:before{content:"";position:absolute;inset:0 auto 0 0;width:4px;background:var(--color-warning)}.review-card.review-verified:before{background:var(--color-success)}.review-card.review-rejected:before{background:var(--color-danger)}.review-card header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.review-card header small{font:600 11px var(--font-mono);letter-spacing:.08em;color:var(--text-muted)}.review-card h3{margin-top:2px;font-size:20px}.review-card header>span{padding:4px 8px;border-radius:999px;background:var(--color-warning-light);color:var(--color-warning);font-size:12px;font-weight:700}.review-card header>span.verified{background:var(--color-success-light);color:var(--color-success)}.review-card header>span.rejected{background:var(--color-danger-light);color:var(--color-danger)}.review-job{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:12px 0 10px;padding:9px 11px;border-radius:8px;background:var(--color-bg-muted)}.review-job>div{display:flex;min-width:0;flex-direction:column}.review-job small,.review-job>div>span{font-size:12px;color:var(--text-muted)}.review-job strong{overflow:hidden;font-size:14px;text-overflow:ellipsis;white-space:nowrap}.review-job>a,.review-job>span{flex:0 0 auto;color:var(--color-brand);font-size:12px;font-weight:700;text-decoration:none}.review-card blockquote{margin:0;padding:11px 12px;border:1px solid #e7eaf4;border-radius:9px;background:#fbfbfd}.review-card blockquote small{font:700 11px var(--font-mono);letter-spacing:.07em;color:var(--text-muted)}.review-card blockquote p{margin-top:5px;color:#34394a;font-size:13px;line-height:1.65}.review-signals{display:grid;grid-template-columns:repeat(4,1fr);gap:5px;margin-top:10px}.review-signals span{padding:7px;border-radius:7px;background:var(--color-bg-muted);font-size:11px;color:var(--text-muted)}.review-signals strong{display:block;margin-top:2px;font:700 12px var(--font-mono);color:var(--text-secondary)}.review-audit{margin-top:10px;padding:9px 11px;border-left:3px solid var(--color-border);background:var(--color-bg-muted)}.review-audit small{font:600 11px var(--font-mono);color:var(--text-muted)}.review-audit p{margin-top:3px;font-size:13px;color:var(--text-secondary)}.review-card footer{display:flex;justify-content:flex-end;gap:6px;margin-top:11px;padding-top:11px;border-top:1px solid var(--color-border-light)}.review-pagination{justify-content:center;margin-top:16px}.reject-fact-context{margin-bottom:12px;padding:11px;border-radius:9px;background:var(--color-bg-muted)}.reject-fact-context span{display:block;font:700 12px var(--font-mono);color:var(--color-danger)}.reject-fact-context strong{display:block;margin:3px 0;font-size:14px}.reject-fact-context p{font-size:13px;color:var(--text-muted)}
.performance-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:13px}.performance-card{position:relative;overflow:hidden;padding:15px;border:1px solid var(--color-border);border-radius:var(--radius-lg);background:#fff}.performance-card>span{font-size:14px;color:var(--text-muted)}.performance-card>strong{display:block;font:700 20px var(--font-mono)}.performance-card>small{font-size:14px}.spark-bars{position:absolute;right:13px;bottom:13px;height:33px}.monitor-grid{margin-bottom:13px}.endpoint-list{padding:0 18px 14px}.endpoint-list>div{display:grid;grid-template-columns:40px minmax(220px,1.35fr) 1fr 90px;gap:12px;align-items:center;padding:12px 0;border-top:1px solid var(--color-border-light)}.operation-mark{display:grid;width:32px;height:32px;place-items:center;border-radius:9px;background:var(--color-brand-light);color:var(--color-brand)}.operation-copy{display:flex;min-width:0;flex-direction:column}.operation-copy>strong{font-family:var(--font-sans);font-size:14px;text-align:left}.operation-copy>small{margin-top:2px;color:var(--text-muted);font-size:12px}.endpoint-bar{height:4px;border-radius:999px;background:var(--color-bg-muted)}.endpoint-bar i{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,var(--color-brand),var(--color-success))}.endpoint-list>div>strong{font:600 14px var(--font-mono);text-align:right}.log-panel{overflow:hidden}.log-toolbar{display:flex;align-items:center;justify-content:space-between;padding:14px 17px}.log-toolbar>div:first-child{display:flex;flex-direction:column}.log-toolbar span{font:700 14px var(--font-mono);color:var(--text-muted)}.log-toolbar h2{font-size:14px}.log-toolbar>div:last-child{display:flex;align-items:center;gap:7px}.log-console{max-height:340px;overflow:auto;padding:8px 12px 12px;background:#1d2130;color:#cfd5e6;font:14px/1.8 var(--font-mono)}.log-line{display:grid;grid-template-columns:118px 48px 150px 1fr;gap:8px;padding:3px 5px;border-radius:4px}.log-line:hover{background:rgba(255,255,255,.04)}.log-line time{color:#747d94}.log-level{font-weight:700}.log-level.info{color:#68b4ff}.log-level.warn{color:#f6b85d}.log-level.error{color:#ff7474}.log-service{overflow:hidden;color:#8e9abb;text-overflow:ellipsis;white-space:nowrap}.log-line code{color:#d8deec;white-space:normal}
@media(max-width:1200px){.admin-nav{flex-wrap:nowrap}.admin-nav-items{grid-template-columns:repeat(5,minmax(0,1fr));flex-basis:auto}.admin-nav small{display:none}.admin-status{width:auto;padding-left:10px;border-top:0;border-left:1px solid var(--color-border);border-radius:0 9px 9px 0}.admin-status div{display:none}.admin-metrics,.crawler-summary,.performance-grid{grid-template-columns:repeat(2,1fr)}.import-result-grid{grid-template-columns:repeat(3,1fr)}.overview-grid{grid-template-columns:1fr}}@media(max-width:900px){.review-grid{grid-template-columns:1fr}}@media(max-width:768px){.section-heading{align-items:stretch;flex-direction:column}.admin-nav{flex-wrap:wrap}.admin-nav-items{grid-template-columns:1fr 1fr;flex-basis:100%}.admin-status{width:100%;justify-content:flex-end;border-top:1px solid var(--color-border-light);border-left:0}.crawler-grid{grid-template-columns:1fr}.quality-grid{grid-template-columns:1fr 1fr}.review-summary{grid-template-columns:1fr 1fr}.review-toolbar{align-items:stretch;flex-wrap:wrap}.review-toolbar .el-input{max-width:none;flex-basis:100%}.review-toolbar>span{display:none}.log-toolbar{align-items:stretch;flex-direction:column;gap:10px}.log-toolbar>div:last-child{flex-wrap:wrap}.resource-rings{gap:8px}.resource-ring{width:65px;height:65px}.endpoint-list>div{grid-template-columns:40px 1fr 90px}.endpoint-bar{display:none}.log-line{grid-template-columns:105px 44px 1fr}.log-line code{grid-column:1/-1}}@media(max-width:540px){.admin-metrics,.crawler-summary,.performance-grid,.quality-grid,.import-result-grid{grid-template-columns:1fr}.admin-nav small{display:none}.admin-status{justify-content:flex-start}.metric-card{min-height:80px}.review-signals{grid-template-columns:1fr 1fr}.review-job{align-items:flex-start;flex-direction:column}}
.agent-run-panel{overflow:hidden;margin-bottom:13px}.agent-run-pagination{justify-content:flex-end;padding:14px 17px}.agent-output{margin-top:18px}.agent-output>strong{display:block;margin-bottom:8px}.agent-output pre{max-height:360px;overflow:auto;padding:12px;border-radius:9px;background:#1d2130;color:#d8deec;font:12px/1.6 var(--font-mono);white-space:pre-wrap;word-break:break-word}
.admin-status.degraded{background:var(--color-warning-light)}.admin-status.degraded .status-pulse{background:var(--color-warning)}.admin-status.unavailable{background:var(--color-danger-light)}.admin-status.unavailable .status-pulse{background:var(--color-danger)}.service-state.degraded{color:var(--color-warning)}.service-state.unavailable{color:var(--color-danger)}.traffic-strip div{flex-wrap:wrap}.traffic-strip small{flex-basis:100%;padding-left:22px;color:var(--text-muted)}.event-list .el-empty,.task-list .el-empty{padding:18px 0}
@media(max-width:768px){.quality-review-summary{grid-template-columns:repeat(2,1fr)}.quality-review-toolbar{align-items:stretch;flex-wrap:wrap}.quality-review-toolbar .el-input{max-width:none;flex:1 1 100%}.source-checks,.automation-grid,.automation-grid.three-columns{grid-template-columns:1fr}}
@media(max-width:540px){.quality-review-summary{grid-template-columns:1fr}}
}
.graph-review-toolbar { display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; color:var(--text-muted); }
.graph-heading-action { height:40px; padding-inline:18px; border-radius:10px; }
.review-toolbar{flex-wrap:wrap}.review-toolbar .el-input{max-width:360px}.approve-all-button{margin-left:2px}.review-card{position:relative}.review-select{position:absolute;z-index:2;right:17px;top:46px}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.graph-candidate-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; min-height:120px; }
.graph-candidate-card { display:flex; flex-direction:column; gap:14px; padding:20px; border:1px solid var(--color-border); border-radius:var(--radius-lg); background:var(--color-bg-elevated); box-shadow:var(--shadow-sm); }
.graph-candidate-card header { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
.graph-candidate-card header span { color:var(--text-muted); font-size:12px; }
.graph-candidate-card h3 { margin:4px 0 0; color:var(--text-primary); }
.candidate-badges { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:6px; }
.candidate-summary { display:grid; grid-template-columns:repeat(3,1fr); padding:12px; border-radius:var(--radius-md); background:var(--color-bg-muted); }
.candidate-summary span { color:var(--text-muted); font-size:13px; }
.candidate-summary strong { display:block; margin-top:4px; color:var(--text-primary); font-family:var(--font-mono); font-size:18px; }
.candidate-points { display:flex; max-height:260px; flex-direction:column; gap:8px; overflow:auto; }
.candidate-points div { padding:11px 12px; border-left:3px solid var(--color-brand); border-radius:0 var(--radius-sm) var(--radius-sm) 0; background:var(--color-bg-muted); }
.candidate-points p { margin:4px 0; color:var(--text-secondary); line-height:1.5; }
.candidate-points small,.candidate-note { color:var(--text-muted); }
.graph-candidate-card footer { display:flex; justify-content:flex-end; margin-top:auto; }
@media (max-width:1100px) { .graph-candidate-grid { grid-template-columns:1fr; } }

/* App-level crawler configuration modal. It is appended to body so the mask
   covers the sidebar, topbar and content as one interaction surface. */
.automation-global-mask.el-overlay {
  background:rgba(24,28,38,.62)!important;
}
.automation-global-mask .el-overlay-dialog {
  display:flex;
  align-items:center;
  justify-content:center;
  padding:24px;
}
.automation-global-mask .automation-dialog {
  width:min(680px,calc(100vw - 32px))!important;
  max-height:calc(100vh - 48px);
  margin:0!important;
  overflow:hidden;
  border:1px solid rgba(255,255,255,.72);
  border-radius:14px;
  box-shadow:0 28px 80px rgba(12,17,29,.28);
}
.automation-global-mask .automation-dialog .el-dialog__body {
  max-height:calc(100vh - 170px);
  overflow-y:auto;
  overscroll-behavior:contain;
  scrollbar-gutter:stable;
}
.automation-global-mask .automation-form{min-height:260px}
.automation-global-mask .automation-intro{display:flex;align-items:center;gap:12px;margin:-4px 0 20px;padding:14px 15px;border:1px solid #dfe5ff;border-radius:12px;background:linear-gradient(110deg,#f3f6ff,#fff)}
.automation-global-mask .automation-intro>div{min-width:0;flex:1}.automation-global-mask .automation-intro strong{font-size:14px}.automation-global-mask .automation-intro p{margin-top:2px;color:var(--text-muted);font-size:12px;line-height:1.5}
.automation-global-mask .automation-icon{display:grid;width:38px;height:38px;flex:0 0 38px;place-items:center;border-radius:10px;background:var(--color-brand);color:#fff;font-size:18px}
.automation-global-mask .source-checks{display:grid;width:100%;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.automation-global-mask .source-checks .el-checkbox{height:auto;margin:0;padding:9px 11px;border:1px solid var(--color-border);border-radius:9px}
.automation-global-mask .source-option{display:flex;align-items:center;gap:8px}.automation-global-mask .source-option i{display:grid;width:27px;height:27px;place-items:center;border-radius:7px;background:var(--color-brand-light);color:var(--color-brand);font-size:10px;font-style:normal;font-weight:700}
.automation-global-mask .automation-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.automation-global-mask .automation-grid.three-columns{grid-template-columns:repeat(3,minmax(0,1fr))}.automation-global-mask .automation-grid .el-input-number,.automation-global-mask .automation-grid .el-select{width:100%}.automation-global-mask .automation-grid .el-form-item small{display:block;margin-top:4px;color:var(--text-muted);font-size:11px}
.automation-global-mask .automation-section-title{display:flex;align-items:baseline;gap:8px;margin:3px 0 12px;padding-top:15px;border-top:1px solid var(--color-border-light)}.automation-global-mask .automation-section-title span{font-size:13px;font-weight:700}.automation-global-mask .automation-section-title small{color:var(--text-muted);font-size:11px}.automation-global-mask .weekday-checks{display:flex;flex-wrap:wrap}
.crawler-summary strong.summary-success{background:transparent;color:var(--color-success)}
.crawler-summary strong.summary-brand{background:transparent;color:var(--color-brand)}
.crawler-summary strong.summary-warning{background:transparent;color:var(--color-warning)}
.review-grid .review-card{padding-left:17px!important}
.review-grid .review-card::before,.review-grid .review-card.review-unverified::before,.review-grid .review-card.review-verified::before,.review-grid .review-card.review-rejected::before{display:none!important;content:none!important}
@media(max-width:680px){.automation-global-mask .automation-grid,.automation-global-mask .automation-grid.three-columns,.automation-global-mask .source-checks{grid-template-columns:1fr}.automation-global-mask .el-overlay-dialog{padding:12px}}
</style>

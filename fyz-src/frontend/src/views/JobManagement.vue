<template>
  <div>
    <DataState :loading="loading" :error="error" @retry="store.refresh()" />
    <!-- Tab bar -->
    <div class="jm-tabs anim-fade-up">
      <button class="jm-tab" :class="{ active: tab === 'publish' }" @click="tab = 'publish'">
        <el-icon><Plus /></el-icon> 岗位发布
      </button>
      <button class="jm-tab" :class="{ active: tab === 'insight' }" @click="tab = 'insight'">
        <el-icon><TrendCharts /></el-icon> 岗位洞察
      </button>
    </div>

    <!-- ═══ Tab A: 岗位发布 ═══ -->
    <div v-show="tab === 'publish'" class="anim-fade-up anim-delay-2">
      <div class="jm-grid">
        <!-- Left: Input -->
        <div class="dash-card">
          <div class="dash-card-header">
            <span class="dash-card-title">智能岗位发布</span>
            <span class="dash-card-badge">Agent 辅助</span>
          </div>
          <div class="dash-card-body">
            <el-form :model="jdForm" label-position="top" size="default">
              <div class="demand-switch" role="radiogroup" aria-label="岗位需求类型">
                <button type="button" class="demand-option public" :class="{ active: demandTarget === 'public' }" @click="selectDemandTarget('public')">
                  <span class="demand-mark"><el-icon><Promotion /></el-icon></span>
                  <span><strong>公开招聘需求</strong><small>面向外部候选人，生成公开 JD</small></span>
                </button>
                <button type="button" class="demand-option internal" :class="{ active: demandTarget === 'internal' }" @click="selectDemandTarget('internal')">
                  <span class="demand-mark"><el-icon><OfficeBuilding /></el-icon></span>
                  <span><strong>内部私有需求</strong><small>仅用于企业人才流动，不对 C 端公开</small></span>
                </button>
              </div>
              <div class="jm-form-hint">
                <el-radio-group v-model="jdMode" size="small">
                  <el-radio-button value="req">输入需求生成 JD</el-radio-button>
                  <el-radio-button value="profile">参考人才画像生成</el-radio-button>
                </el-radio-group>
              </div>
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="岗位名称">
                    <el-input v-model="jdForm.title" placeholder="如：高级 Java 开发工程师" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="级别">
                    <el-select v-model="jdForm.level" placeholder="选择级别" style="width:100%">
                      <el-option label="初级" value="junior" /><el-option label="中级" value="mid" />
                      <el-option label="高级" value="senior" /><el-option label="专家" value="expert" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="所属部门">
                <el-select v-model="jdForm.department" placeholder="请选择所属部门" style="width:100%">
                  <el-option v-for="department in JD_DEPARTMENT_OPTIONS" :key="department" :label="department" :value="department" />
                </el-select>
              </el-form-item>
              <el-row v-if="demandTarget === 'internal'" :gutter="16">
                <el-col :span="12">
                  <el-form-item label="接收负责人">
                    <el-input v-model="internalForm.receivingManager" placeholder="如：平台研发负责人" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="内部开放名额">
                    <el-input-number v-model="internalForm.headcount" :min="1" :max="100" style="width:100%" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item v-if="demandTarget === 'internal'" label="内部需求原因">
                <el-input v-model="internalForm.openReason" placeholder="如：新项目启动，需要补充平台能力" />
              </el-form-item>
              <div class="suggestion-field">
                <div class="suggestion-heading">
                  <div>
                    <span>{{ jdMode === 'req' ? '核心技能要求' : '目标人才特征' }}</span>
                    <small>输入岗位名称后，Agent 会自动补充常见建议</small>
                  </div>
                  <el-button text type="primary" size="small" :loading="suggestionLoading" :disabled="jdForm.title.trim().length < 2" @click="requestSuggestions(true)">
                    <el-icon><Refresh /></el-icon>重新建议
                  </el-button>
                </div>

                <el-select
                  v-if="jdMode === 'req'"
                  v-model="skillRequirements"
                  multiple
                  filterable
                  allow-create
                  default-first-option
                  placeholder="输入或选择核心技能"
                  style="width:100%"
                  @change="markSuggestionDirty"
                />
                <div v-else class="profile-editor">
                  <div v-for="(_, index) in talentTraits" :key="index" class="profile-row">
                    <el-input v-model="talentTraits[index]" placeholder="输入一条目标人才特征" @input="markSuggestionDirty" />
                    <el-button text type="danger" aria-label="删除人才特征" @click="removeTalentTrait(index)"><el-icon><Delete /></el-icon></el-button>
                  </div>
                  <el-button size="small" @click="addTalentTrait"><el-icon><Plus /></el-icon>添加人才特征</el-button>
                </div>

                <div v-if="suggestionLoading || suggestionNotice || suggestionWarning" class="suggestion-status">
                  <span v-if="suggestionLoading" class="suggestion-pulse"><i></i>Agent 正在分析岗位名称</span>
                  <span v-else-if="suggestionNotice">{{ suggestionNotice }}</span>
                  <small v-if="suggestionWarning">{{ suggestionWarning }}</small>
                </div>

                <div v-if="pendingSuggestions.length" class="suggestion-review">
                  <div><strong>发现 {{ pendingSuggestions.length }} 条新建议</strong><small>检测到你已编辑当前内容，因此没有自动覆盖。</small></div>
                  <div>
                    <el-button size="small" @click="applyPendingSuggestions('append')">追加</el-button>
                    <el-button size="small" type="primary" plain @click="applyPendingSuggestions('replace')">替换</el-button>
                    <el-button size="small" text @click="pendingSuggestions = []">忽略</el-button>
                  </div>
                </div>
              </div>
              <el-form-item>
                <el-button type="primary" :class="{ 'internal-generate': demandTarget === 'internal' }" :loading="generating" style="width:100%;height:42px;" @click="generateJD">
                  <el-icon><MagicStick /></el-icon> {{ demandTarget === 'internal' ? '生成内部岗位说明' : '智能生成公开 JD' }}
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </div>

        <!-- Right: Preview -->
        <div class="dash-card" style="display:flex;flex-direction:column;">
          <div class="dash-card-header">
            <span class="dash-card-title">{{ previewTarget === 'internal' ? '内部岗位说明预览' : '公开 JD 预览' }}</span>
            <span class="dash-card-badge" :class="{ 'badge-internal': previewTarget === 'internal' }" v-if="generated">{{ previewTarget === 'internal' ? '内部私有' : '公开招聘' }}</span>
          </div>
          <div class="dash-card-body" style="flex:1;display:flex;flex-direction:column;">
            <div v-if="!generated" class="jm-empty jm-empty-fill">
              <el-icon style="font-size:40px;color:var(--color-border);"><Document /></el-icon>
              <p style="margin-top:12px;">填写岗位信息后点击"智能生成 JD"</p>
            </div>
            <div v-else class="jd-preview">
              <div class="jd-preview-scroll">
                <h3>{{ generated.title }}</h3>
                <div class="jd-meta-row">
                  <el-tag size="small" type="info">{{ generated.level }}</el-tag>
                  <el-tag size="small">{{ generated.department }}</el-tag>
                  <span v-if="previewTarget === 'public'" class="jd-salary">{{ generated.salary_range }}</span>
                </div>
                <el-alert v-if="generationWarning" :title="generationWarning" type="warning" :closable="false" show-icon />
                <div class="jd-section"><h4>工作职责</h4><ul><li v-for="(r,i) in generated.responsibilities" :key="i">{{ r }}</li></ul></div>
                <div class="jd-section"><h4>任职要求</h4><ul><li v-for="(r,i) in generated.requirements" :key="i">{{ r }}</li></ul></div>
                <div class="jd-section"><h4>加分技能</h4><div style="display:flex;gap:6px;flex-wrap:wrap;"><el-tag v-for="s in generated.bonus_skills" :key="s" size="small" type="success">{{ s }}</el-tag></div></div>
                <template v-if="previewTarget === 'internal' && generatedDraft">
                  <div class="jd-section"><h4>可培养技能</h4><div class="skill-wrap"><el-tag v-for="s in generatedDraft.trainable_skills" :key="s" size="small" type="warning" effect="plain">{{ s }}</el-tag></div></div>
                  <div class="jd-section"><h4>适合转岗人才特征</h4><ul><li v-for="item in generatedDraft.transfer_profile" :key="item">{{ item }}</li></ul></div>
                  <div class="jd-section manager-check"><h4>管理层待确认</h4><ul><li v-for="item in generatedDraft.manager_confirmations" :key="item">{{ item }}</li></ul></div>
                </template>
              </div>
              <div class="jd-preview-actions">
                <el-button @click="copyJD"><el-icon><CopyDocument /></el-icon> 复制</el-button>
                <el-button v-if="previewTarget === 'public'" @click="openDetail(generated, true)"><el-icon><Edit /></el-icon> 编辑草稿</el-button>
                <el-button type="primary" @click="publishFromPreview"><el-icon><Check /></el-icon> {{ previewTarget === 'internal' ? '保存内部岗位' : '发布公开岗位' }}</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Public and internal positions stay visually adjacent but operationally isolated. -->
      <div id="position-ledger" class="position-ledger" style="margin-top:16px;">
        <section class="dash-card ledger-pane public-ledger">
          <div class="ledger-head">
            <div><span class="ledger-kicker">PUBLIC MARKET</span><h3>公开招聘信息</h3><p>仅进入外部招聘与 C 端岗位市场</p></div>
            <span class="ledger-count">{{ filteredPublicJobs.length }}</span>
          </div>
          <div class="ledger-filters">
            <el-input v-model="publicKeyword" clearable placeholder="搜索公开岗位" :prefix-icon="Search" />
            <el-select v-model="publicStatus" clearable placeholder="招聘状态"><el-option label="招聘中" value="open"/><el-option label="草稿" value="draft"/><el-option label="已暂停" value="paused"/><el-option label="已关闭" value="closed"/></el-select>
          </div>
          <el-table :data="filteredPublicJobs" style="width:100%" size="default">
            <el-table-column prop="title" label="岗位名称" min-width="180" />
            <el-table-column prop="department" label="部门" min-width="110" />
            <el-table-column prop="headcount" label="人数" width="66" align="center" />
            <el-table-column prop="status" label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'open' ? 'success' : 'info'" size="small">
                  {{ row.status === 'open' ? '招聘中' : '草稿' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" align="right">
              <template #default="{ row }">
                <div class="table-actions">
                  <el-button text type="primary" size="small" @click="openDetail(row)">
                    <el-icon><Edit /></el-icon> 编辑
                  </el-button>
                  <el-popconfirm title="确定关闭该岗位？" @confirm="closeJob(row)">
                    <template #reference>
                      <el-button text type="danger" size="small">
                        <el-icon><Delete /></el-icon> 关闭
                      </el-button>
                    </template>
                  </el-popconfirm>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <section class="dash-card ledger-pane internal-ledger">
          <div class="ledger-head">
            <div><span class="ledger-kicker">PRIVATE MOBILITY</span><h3>内部需求岗位</h3><p>仅用于企业人才流动与管理决策</p></div>
            <span class="ledger-count">{{ filteredInternalPositions.length }}</span>
          </div>
          <div class="ledger-filters">
            <el-input v-model="internalKeyword" clearable placeholder="搜索内部岗位" :prefix-icon="Search" />
            <el-select v-model="internalStatus" clearable placeholder="内部状态"><el-option label="内部开放" value="open"/><el-option label="待审批" value="pending_approval"/><el-option label="草稿" value="draft"/><el-option label="已暂停" value="paused"/><el-option label="名额已满" value="filled"/><el-option label="已关闭" value="closed"/></el-select>
          </div>
          <el-table :data="filteredInternalPositions" style="width:100%" size="default">
            <el-table-column prop="title" label="内部岗位" min-width="160" />
            <el-table-column prop="department" label="接收部门" min-width="110" />
            <el-table-column prop="headcount" label="名额" width="66" align="center" />
            <el-table-column prop="status" label="状态" width="96" align="center">
              <template #default="{ row }"><el-tag size="small" :type="row.status === 'open' ? 'warning' : 'info'">{{ internalStatusLabel(row.status) }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" width="160" align="right">
              <template #default="{ row }">
                <el-button v-if="row.status === 'draft'" text type="primary" size="small" @click="setInternalStatus(row.id, 'pending_approval')">提交审批</el-button>
                <el-button v-else-if="row.status === 'pending_approval'" text type="warning" size="small" @click="setInternalStatus(row.id, 'open')">开放</el-button>
                <el-button v-else-if="row.status === 'open'" text type="warning" size="small" @click="setInternalStatus(row.id, 'paused')">暂停</el-button>
                <el-button v-else-if="row.status === 'paused'" text type="primary" size="small" @click="setInternalStatus(row.id, 'open')">恢复</el-button>
                <el-button v-if="row.status === 'open'" text size="small" @click="router.push({ path: '/career', query: { positionId: row.id } })">适配人才</el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </div>
    </div>

    <!-- ═══ Tab B: 岗位洞察 ═══ -->
    <div v-show="tab === 'insight'" class="anim-fade-up anim-delay-2">
      <div class="dash-card jm-insight-search">
        <div class="dash-card-body" style="padding:14px 20px;">
          <div class="insight-search-row">
            <el-icon style="font-size:18px;color:var(--color-brand);"><Search /></el-icon>
            <input v-model="skillPreference" class="insight-search-input"
              placeholder="输入关注的技能点，系统据此定向搜索新岗位和能力变化..." @keyup.enter="searchInsight" />
            <el-button type="primary" size="default" @click="searchInsight">搜索</el-button>
          </div>
        </div>
      </div>

      <DataState :loading="insightLoading" :error="insightError" @retry="store.loadInsights(skillPreference)" />
      <el-alert
        v-if="insightQuality?.insufficient_data"
        class="insight-quality-alert"
        type="warning"
        :closable="false"
        show-icon
        :title="insightQuality.notes.join(' ') || '当前数据量不足，洞察结果仅供参考。'"
      />

      <div class="jm-grid" style="margin-top:16px;">
        <div class="dash-card">
          <div class="dash-card-header"><span class="dash-card-title">新兴岗位发现</span><span class="dash-card-badge">AI 驱动</span></div>
          <div class="dash-card-body">
            <div class="insight-list">
              <div class="insight-card" v-for="(job,i) in emergingJobs" :key="i" :class="{ collapsed: !emergingExpanded && i >= 3 }">
                <div class="insight-card-top">
                  <div class="insight-dot"></div>
                  <span class="insight-name">{{ job.name }}</span>
                  <el-tag size="small" :type="job.confidence > 90 ? 'success' : 'warning'">{{ job.confidence }}%</el-tag>
                  <el-tag v-if="job.decision" size="small" type="success">
                    {{ job.decision === 'confirmed' ? '已确认' : job.decision === 'planned' ? '已纳入计划' : '已忽略' }}
                  </el-tag>
                </div>
                <div class="insight-skills"><el-tag v-for="s in job.core_skills" :key="s" size="small" effect="plain">{{ s }}</el-tag></div>
                <div class="insight-desc">{{ job.description }}</div>
                <div class="insight-actions">
                  <el-button text size="small" type="primary" :disabled="job.decision === 'confirmed'" @click="confirmEmergingJob(job)">确认为新岗位</el-button>
                  <el-button text size="small" @click="prepareHiringPlan(job)">加入招聘计划</el-button>
                </div>
              </div>
              <el-empty v-if="!insightLoading && emergingJobs.length === 0" description="暂无满足来源阈值的新兴岗位" />
            </div>
            <button v-if="emergingJobs.length > 3" class="expand-btn" @click="emergingExpanded = !emergingExpanded">
              {{ emergingExpanded ? '收起' : `展开全部 (${emergingJobs.length} 个)` }}
              <el-icon :class="{ rotated: emergingExpanded }"><ArrowDown /></el-icon>
            </button>
          </div>
        </div>

        <div class="dash-card">
          <div class="dash-card-header"><span class="dash-card-title">能力动态更新</span><span class="dash-card-badge">近期变化</span></div>
          <div class="dash-card-body">
            <div class="insight-list">
              <div class="insight-card" v-for="(ch,i) in capabilityChanges" :key="i">
                <div class="insight-card-top">
                  <span class="insight-name">{{ ch.job }}</span><span class="insight-period">{{ ch.period }}</span>
                </div>
                <div class="change-tags">
                  <template v-for="s in ch.added" :key="'add_'+s"><el-tag size="small" type="success" effect="dark">+ {{ s }}</el-tag></template>
                  <template v-for="s in ch.modified" :key="'mod_'+s"><el-tag size="small" type="warning" effect="dark">~ {{ s }}</el-tag></template>
                  <template v-for="s in ch.removed" :key="'rem_'+s"><el-tag size="small" type="danger" effect="plain">- {{ s }}</el-tag></template>
                </div>
                <div class="change-stats">新增 {{ ch.added.length }} 项 · 修改 {{ ch.modified.length }} 项 · 淘汰 {{ ch.removed.length }} 项</div>
                <div class="insight-actions">
                  <el-button text size="small" type="primary" @click="viewChangeTrend(ch)">查看趋势图</el-button>
                  <el-button text size="small" @click="prepareJDUpdate(ch)">更新岗位 JD</el-button>
                </div>
              </div>
              <el-empty v-if="!insightLoading && capabilityChanges.length === 0" description="当前时间窗口暂无可确认的能力变化" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ Detail / Edit Dialog (shared) ═══ -->
    <el-dialog v-model="detailVisible" :title="isEditing ? '编辑岗位详情' : '岗位详情'" width="680px" destroy-on-close top="5vh">
      <div v-if="detailJob" class="jd-detail-editor">
        <el-row :gutter="16">
          <el-col :span="14">
            <label class="jd-edit-label">岗位名称</label>
            <el-input v-model="detailJob.title" :disabled="!isEditing" size="default" />
          </el-col>
          <el-col :span="10">
            <label class="jd-edit-label">级别</label>
            <el-select v-model="detailJob.level" :disabled="!isEditing" style="width:100%" size="default">
              <el-option label="初级" value="初级" /><el-option label="中级" value="中级" />
              <el-option label="高级" value="高级" /><el-option label="专家" value="专家" />
            </el-select>
          </el-col>
        </el-row>
        <el-row :gutter="16" style="margin-top:16px;">
          <el-col :span="14">
            <label class="jd-edit-label">部门</label>
            <el-input v-model="detailJob.department" :disabled="!isEditing" size="default" />
          </el-col>
          <el-col :span="10">
            <label class="jd-edit-label">薪资范围</label>
            <el-input v-model="detailJob.salary_range" :disabled="!isEditing" size="default" placeholder="如：20K-35K·14薪" />
          </el-col>
        </el-row>
        <div style="margin-top:16px;">
          <label class="jd-edit-label">工作职责</label>
          <div v-if="isEditing" class="jd-edit-lines">
            <div v-for="(r,i) in detailJob.responsibilities" :key="i" class="jd-edit-line">
              <el-input v-model="detailJob.responsibilities[i]" size="small" />
              <el-button text type="danger" size="small" @click="detailJob.responsibilities.splice(i,1)"><el-icon><Delete /></el-icon></el-button>
            </div>
            <el-button size="small" @click="detailJob.responsibilities.push('')">+ 添加职责</el-button>
          </div>
          <ul v-else class="jd-edit-ul"><li v-for="(r,i) in detailJob.responsibilities" :key="i">{{ r }}</li></ul>
        </div>
        <div style="margin-top:16px;">
          <label class="jd-edit-label">任职要求</label>
          <div v-if="isEditing" class="jd-edit-lines">
            <div v-for="(r,i) in detailJob.requirements" :key="i" class="jd-edit-line">
              <el-input v-model="detailJob.requirements[i]" size="small" />
              <el-button text type="danger" size="small" @click="detailJob.requirements.splice(i,1)"><el-icon><Delete /></el-icon></el-button>
            </div>
            <el-button size="small" @click="detailJob.requirements.push('')">+ 添加要求</el-button>
          </div>
          <ul v-else class="jd-edit-ul"><li v-for="(r,i) in detailJob.requirements" :key="i">{{ r }}</li></ul>
        </div>
        <div style="margin-top:16px;">
          <label class="jd-edit-label">加分技能</label>
          <el-input v-if="isEditing" v-model="bonusSkillsStr" size="default" placeholder="用逗号分隔" />
          <div v-else style="display:flex;gap:6px;flex-wrap:wrap;margin-top:4px;">
            <el-tag v-for="s in detailJob.bonus_skills" :key="s" size="small" type="success">{{ s }}</el-tag>
          </div>
        </div>
        <el-divider />
        <el-row :gutter="16">
          <el-col :span="8">
            <label class="jd-edit-label">招聘人数</label>
            <el-input-number v-model="detailJob.headcount" :min="1" :disabled="!isEditing" size="default" style="width:100%" />
          </el-col>
          <el-col :span="8">
            <label class="jd-edit-label">状态</label>
            <el-select v-model="detailJob.status" :disabled="!isEditing" style="width:100%" size="default">
              <el-option label="招聘中" value="open" /><el-option label="草稿" value="draft" />
            </el-select>
          </el-col>
          <el-col :span="8">
            <label class="jd-edit-label">发布日期</label>
            <el-input :model-value="detailJob.created_at" disabled size="default" />
          </el-col>
        </el-row>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">{{ isEditing ? '取消' : '关闭' }}</el-button>
        <el-button v-if="!isEditing" type="primary" @click="isEditing = true"><el-icon><Edit /></el-icon> 编辑</el-button>
        <el-button v-if="isEditing" type="success" @click="saveDetail"><el-icon><Check /></el-icon> 保存</el-button>
        <el-popconfirm v-if="isEditing" title="确定删除该岗位？" @confirm="deleteDetail">
          <template #reference>
            <el-button type="danger"><el-icon><Delete /></el-icon> 删除</el-button>
          </template>
        </el-popconfirm>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, onBeforeUnmount, onMounted, watch } from "vue";
import { storeToRefs } from "pinia";
import { Plus, TrendCharts, MagicStick, Document, Search, CopyDocument, Check, ArrowDown, View, Edit, Delete, Refresh, Promotion, OfficeBuilding } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { useRoute, useRouter } from "vue-router";
import { useJobStore } from "@/stores/jobs";
import DataState from "@/components/common/DataState.vue";
import { JD_DEPARTMENT_OPTIONS } from "@/config/jdOptions";
import type { CapabilityChange, EmergingJob, GeneratedJDDraft, InternalPositionStatus, JobSummary } from "@/domain/types";

const tab = ref<"publish" | "insight">("publish");

// ── Tab A ──
const jdMode = ref<"req" | "profile">("req");
const demandTarget = ref<"public" | "internal">("public");
const generating = ref(false);
const generated = ref<JobSummary | null>(null);
const generatedDraft = ref<GeneratedJDDraft | null>(null);
const generationWarning = ref("");
const jdForm = reactive({ title: "", level: "", department: "" });
const internalForm = reactive({
  receivingManager: "",
  headcount: 1,
  openReason: "组织人才配置",
});
const skillRequirements = ref<string[]>([]);
const talentTraits = ref<string[]>([]);
const inputDirty = reactive({ requirements: false, profile: false });
const suggestionLoading = ref(false);
const suggestionNotice = ref("");
const suggestionWarning = ref("");
const pendingSuggestions = ref<string[]>([]);
let suggestionTimer: ReturnType<typeof setTimeout> | undefined;
let suggestionRequestId = 0;
let lastSuggestionKey = "";
const store = useJobStore();
const router = useRouter();
const route = useRoute();
const {
  jobs: publishedJobs,
  internalPositions,
  emergingJobs,
  capabilityChanges,
  insightQuality,
  insightLoading,
  insightError,
  loading,
  error,
} = storeToRefs(store);
const publicKeyword = ref("");
const publicStatus = ref("");
const internalKeyword = ref("");
const internalStatus = ref("");
const filteredPublicJobs = computed(() => {
  const keyword = publicKeyword.value.trim().toLowerCase();
  return publishedJobs.value.filter((job) => {
    const matchesKeyword = !keyword || `${job.title} ${job.department}`.toLowerCase().includes(keyword);
    return matchesKeyword && (!publicStatus.value || job.status === publicStatus.value);
  });
});
const filteredInternalPositions = computed(() => {
  const keyword = internalKeyword.value.trim().toLowerCase();
  return internalPositions.value.filter((position) => {
    const matchesKeyword = !keyword || `${position.title} ${position.department} ${position.receiving_manager || ""}`.toLowerCase().includes(keyword);
    return matchesKeyword && (!internalStatus.value || position.status === internalStatus.value);
  });
});
const previewTarget = computed(() => generatedDraft.value?.target || demandTarget.value);
onMounted(async () => {
  await Promise.all([store.load(), store.loadInsights()]);
  if (route.query.scope === "internal") {
    await nextTick();
    document.getElementById("position-ledger")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
});
onBeforeUnmount(() => {
  if (suggestionTimer) clearTimeout(suggestionTimer);
  suggestionRequestId += 1;
});

watch(
  () => [jdForm.title, jdMode.value, jdForm.level, jdForm.department, demandTarget.value],
  () => {
    pendingSuggestions.value = [];
    suggestionNotice.value = "";
    if (suggestionTimer) clearTimeout(suggestionTimer);
    if (jdForm.title.trim().length < 2) {
      suggestionLoading.value = false;
      return;
    }
    suggestionTimer = setTimeout(() => requestSuggestions(), 700);
  },
);

function currentMode() {
  return jdMode.value === "req" ? "requirements" as const : "profile" as const;
}

function currentItems(): string[] {
  return jdMode.value === "req" ? skillRequirements.value : talentTraits.value;
}

function setCurrentItems(items: string[]) {
  const cleaned = [...new Set(items.map((item) => item.trim()).filter(Boolean))];
  if (jdMode.value === "req") skillRequirements.value = cleaned;
  else talentTraits.value = cleaned;
}

function currentDirty() {
  return jdMode.value === "req" ? inputDirty.requirements : inputDirty.profile;
}

function markSuggestionDirty() {
  if (jdMode.value === "req") inputDirty.requirements = true;
  else inputDirty.profile = true;
}

function selectDemandTarget(target: "public" | "internal") {
  if (target === demandTarget.value) return;
  demandTarget.value = target;
  if (generated.value) {
    generated.value = null;
    generatedDraft.value = null;
    generationWarning.value = "";
    ElMessage.info("需求类型已切换，请按新的发布目标重新生成岗位内容");
  }
}

async function requestSuggestions(force = false) {
  const title = jdForm.title.trim();
  if (title.length < 2) return;
  const mode = currentMode();
  const key = JSON.stringify([title, mode, jdForm.level, jdForm.department, demandTarget.value]);
  if (!force && key === lastSuggestionKey) return;
  lastSuggestionKey = key;
  const requestId = ++suggestionRequestId;
  suggestionLoading.value = true;
  suggestionWarning.value = "";
  try {
    const result = await store.suggestJDInput({
      title,
      mode,
      target: demandTarget.value,
      level: jdForm.level || undefined,
      department: jdForm.department || undefined,
    });
    if (requestId !== suggestionRequestId || key !== JSON.stringify([jdForm.title.trim(), currentMode(), jdForm.level, jdForm.department, demandTarget.value])) return;
    suggestionWarning.value = result.warnings.join(" ");
    suggestionNotice.value = result.generation_mode === "template" ? "已使用岗位规则模板补充" : "Agent 建议已就绪";
    if (!currentDirty()) {
      setCurrentItems(result.suggestions);
      pendingSuggestions.value = [];
    } else {
      const existing = new Set(currentItems());
      pendingSuggestions.value = result.suggestions.filter((item) => !existing.has(item));
    }
  } catch (error) {
    if (requestId === suggestionRequestId) {
      suggestionWarning.value = error instanceof Error ? error.message : "岗位建议生成失败";
    }
  } finally {
    if (requestId === suggestionRequestId) suggestionLoading.value = false;
  }
}

function applyPendingSuggestions(action: "append" | "replace") {
  setCurrentItems(action === "append" ? [...currentItems(), ...pendingSuggestions.value] : pendingSuggestions.value);
  markSuggestionDirty();
  pendingSuggestions.value = [];
  suggestionNotice.value = action === "append" ? "新建议已追加" : "已替换为新建议";
}

function addTalentTrait() {
  talentTraits.value.push("");
  inputDirty.profile = true;
}

function removeTalentTrait(index: number) {
  talentTraits.value.splice(index, 1);
  inputDirty.profile = true;
}

async function generateJD() {
  if (!jdForm.title) { ElMessage.warning("请先输入岗位名称"); return; }
  if (!jdForm.department) { ElMessage.warning("请选择所属部门"); return; }
  generating.value = true;
  try {
    const draft = await store.generateJD({
      mode: jdMode.value === "req" ? "requirements" : "profile",
      target: demandTarget.value,
      title: jdForm.title,
      level: jdForm.level || undefined,
      department: jdForm.department || undefined,
      skills_input: currentItems().filter(Boolean).join(jdMode.value === "req" ? ", " : "\n"),
      headcount: demandTarget.value === "internal" ? internalForm.headcount : undefined,
      internal_reason: demandTarget.value === "internal" ? internalForm.openReason : undefined,
      receiving_manager: demandTarget.value === "internal" ? internalForm.receivingManager || undefined : undefined,
    });
    generatedDraft.value = draft;
    generated.value = toPreviewJob(draft);
    generationWarning.value = draft.warnings.join(" ");
    ElMessage.success("JD 生成完成");
  } catch {
    ElMessage.error("JD 生成失败，请稍后重试");
  } finally {
    generating.value = false;
  }
}

function copyJD() {
  const jd = generated.value;
  if (!jd) return;
  const internalSections = generatedDraft.value?.target === "internal"
    ? `\n\n可培养技能：${generatedDraft.value.trainable_skills.join("、")}\n\n适合转岗人才特征：\n${generatedDraft.value.transfer_profile.map((item, index) => `${index + 1}. ${item}`).join("\n")}\n\n管理层待确认：\n${generatedDraft.value.manager_confirmations.map((item, index) => `${index + 1}. ${item}`).join("\n")}`
    : "";
  navigator.clipboard.writeText(`【${jd.title}】\n${jd.department} · ${jd.level}${previewTarget.value === "public" ? ` · ${jd.salary_range}` : " · 内部私有需求"}\n\n工作职责：\n${jd.responsibilities.map((r:string,i:number)=>`${i+1}. ${r}`).join("\n")}\n\n任职要求：\n${jd.requirements.map((r:string,i:number)=>`${i+1}. ${r}`).join("\n")}\n\n加分技能：${jd.bonus_skills.join("、")}${internalSections}`);
  ElMessage.success("已复制到剪贴板");
}

async function publishFromPreview() {
  if (!generated.value || !generatedDraft.value) return;
  if (generatedDraft.value.target === "internal") {
    const draft = generatedDraft.value;
    await store.createInternalPosition({
      title: draft.title,
      standardized_title: draft.standardized_title,
      department: draft.department,
      receiving_manager: internalForm.receivingManager || null,
      level: draft.level,
      headcount: internalForm.headcount,
      open_reason: internalForm.openReason,
      responsibilities: draft.responsibilities,
      requirements: draft.requirements,
      required_skills: draft.skills,
      trainable_skills: draft.trainable_skills,
      transfer_profile: draft.transfer_profile,
      manager_confirmations: draft.manager_confirmations,
      min_tenure_months: 6,
      min_position_tenure_months: 6,
      allowed_departments: [],
      restrictions: [],
      target_start_date: null,
      open_from: null,
      open_until: null,
      internal_description: draft.jd_text,
      status: "draft",
    });
    ElMessage.success("内部岗位已保存为草稿，可提交审批后开放");
  } else {
    await store.create(toPublishPayload(generated.value));
    ElMessage.success("公开岗位发布成功");
  }
  generated.value = null;
  generatedDraft.value = null;
  generationWarning.value = "";
  jdForm.title = "";
  internalForm.receivingManager = "";
  internalForm.headcount = 1;
  internalForm.openReason = "组织人才配置";
  skillRequirements.value = [];
  talentTraits.value = [];
  inputDirty.requirements = false;
  inputDirty.profile = false;
}

function internalStatusLabel(status: InternalPositionStatus) {
  return {
    draft: "草稿",
    pending_approval: "待审批",
    open: "内部开放",
    paused: "已暂停",
    filled: "名额已满",
    closed: "已关闭",
  }[status];
}

async function setInternalStatus(id: number, status: InternalPositionStatus) {
  await store.updateInternalPositionStatus(id, status);
  ElMessage.success(`内部岗位状态已更新为“${internalStatusLabel(status)}”`);
}

async function closeJob(row: JobSummary) {
  await store.updateStatus(row.id, "closed");
  ElMessage.success(`已关闭"${row.title}"`);
}

// ── Detail dialog (shared) ──
const detailVisible = ref(false);
const isEditing = ref(false);
const detailJob = ref<JobSummary | null>(null);

const bonusSkillsStr = computed({
  get: () => detailJob.value?.bonus_skills?.join(", ") || "",
  set: (val: string) => { if (detailJob.value) detailJob.value.bonus_skills = val.split(",").map((s:string) => s.trim()).filter(Boolean); },
});

function openDetail(job: JobSummary, editing = false) {
  detailJob.value = JSON.parse(JSON.stringify(job));
  isEditing.value = editing;
  detailVisible.value = true;
}

async function saveDetail() {
  if (!detailJob.value) return;
  if (detailJob.value.id === 0) {
    generated.value = JSON.parse(JSON.stringify(detailJob.value));
    detailVisible.value = false;
    ElMessage.success("JD 草稿已更新，确认后即可发布");
    return;
  }
  await store.update(detailJob.value);
  ElMessage.success("岗位信息已更新");
  detailVisible.value = false;
}

function toPreviewJob(draft: GeneratedJDDraft): JobSummary {
  return {
    id: 0,
    title: draft.title,
    department: draft.department,
    headcount: 1,
    status: "draft",
    created_at: "未发布",
    level: draft.level,
    salary_range: "待管理员补充",
    responsibilities: draft.responsibilities,
    requirements: draft.requirements,
    skills: draft.skills,
    bonus_skills: draft.bonus_skills,
    jd_text: draft.jd_text,
  };
}

function toPublishPayload(job: JobSummary) {
  const jdText = [
    `岗位名称：${job.title}`,
    `所属部门：${job.department}`,
    `岗位职责：${job.responsibilities.join("；")}`,
    `任职要求：${job.requirements.join("；")}`,
  ].join("\n");
  return {
    title: job.title,
    level: job.level,
    department: job.department,
    headcount: job.headcount || 1,
    responsibilities: job.responsibilities.filter(Boolean),
    requirements: job.requirements.filter(Boolean),
    skills: job.skills || [],
    bonus_skills: job.bonus_skills,
    jd_text: jdText,
    status: "open" as const,
  };
}

async function deleteDetail() {
  if (!detailJob.value) return;
  await store.remove(detailJob.value.id);
  ElMessage.success("岗位已删除");
  detailVisible.value = false;
}

// ── Tab B ──
const skillPreference = ref("");
const emergingExpanded = ref(false);
async function searchInsight() {
  await store.loadInsights(skillPreference.value.trim());
}

async function confirmEmergingJob(job: EmergingJob) {
  await store.decideInsight(job.id, "confirmed", "由岗位洞察页面确认");
  ElMessage.success(`已确认“${job.name}”为新兴岗位`);
}

async function prepareHiringPlan(job: EmergingJob) {
  await store.decideInsight(job.id, "planned", "已转入智能 JD 招聘计划");
  tab.value = "publish";
  demandTarget.value = "public";
  jdMode.value = "req";
  jdForm.title = job.name;
  jdForm.level = "mid";
  skillRequirements.value = [...job.core_skills];
  inputDirty.requirements = true;
  ElMessage.success("已填入岗位发布表单，请补充部门后生成 JD");
}

function prepareJDUpdate(change: CapabilityChange) {
  tab.value = "publish";
  demandTarget.value = "public";
  jdMode.value = "req";
  jdForm.title = change.job;
  skillRequirements.value = [
    ...change.added.map((skill) => `新增：${skill}`),
    ...change.modified.map((skill) => `强化：${skill}`),
    ...change.removed.map((skill) => `待移除：${skill}`),
  ];
  inputDirty.requirements = true;
  ElMessage.success("能力变化已填入 JD Agent，请审核后生成更新草稿");
}

function viewChangeTrend(change: CapabilityChange) {
  router.push({ path: "/trends", query: { keyword: change.job } });
}

</script>

<style scoped>
.insight-quality-alert {
  margin-top: 12px;
  border-radius: 12px;
}
.suggestion-field { margin-bottom: 18px; }
.suggestion-heading { display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px; }
.suggestion-heading>div { display:flex;flex-direction:column; }
.suggestion-heading span { color:var(--text-primary);font-size:14px;font-weight:600; }
.suggestion-heading small { margin-top:2px;color:var(--text-muted);font-size:12px; }
.profile-editor { display:flex;flex-direction:column;gap:8px; }
.profile-row { display:flex;align-items:center;gap:6px; }
.suggestion-status { display:flex;align-items:flex-start;flex-direction:column;gap:3px;margin-top:8px;color:var(--color-brand);font-size:12px; }
.suggestion-status small { color:var(--color-warning);line-height:1.5; }
.suggestion-pulse { display:flex;align-items:center;gap:6px; }
.suggestion-pulse i { width:7px;height:7px;border-radius:50%;background:var(--color-brand);box-shadow:0 0 0 4px var(--color-brand-light);animation:suggestion-breathe 1.2s ease-in-out infinite; }
.suggestion-review { display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:10px;padding:11px 12px;border:1px solid var(--color-brand);border-radius:10px;background:var(--color-brand-light); }
.suggestion-review>div:first-child { display:flex;flex-direction:column; }
.suggestion-review strong { color:var(--text-primary);font-size:13px; }
.suggestion-review small { margin-top:2px;color:var(--text-secondary);font-size:12px; }
.suggestion-review>div:last-child { display:flex;align-items:center;white-space:nowrap; }
.demand-switch { display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:18px; }
.demand-option { display:flex;align-items:center;gap:11px;padding:12px;border:1px solid var(--border-color);border-radius:12px;background:var(--bg-card);color:var(--text-primary);text-align:left;cursor:pointer;transition:.2s ease; }
.demand-option:hover { border-color:var(--color-brand);transform:translateY(-1px); }
.demand-option.active.public { border-color:var(--color-brand);background:var(--color-brand-light);box-shadow:0 0 0 2px rgba(79,110,246,.08); }
.demand-option.active.internal { border-color:#c98228;background:#fff8eb;box-shadow:0 0 0 2px rgba(201,130,40,.08); }
.demand-mark { display:grid;place-items:center;width:34px;height:34px;border-radius:10px;background:#edf1ff;color:var(--color-brand);font-size:17px;flex:0 0 auto; }
.demand-option.internal .demand-mark { background:#fff0d5;color:#b46b12; }
.demand-option span:last-child { display:flex;flex-direction:column;min-width:0; }
.demand-option strong { font-size:13px; }
.demand-option small { margin-top:2px;color:var(--text-muted);font-size:11px;line-height:1.35; }
.internal-generate { --el-button-bg-color:#b87420;--el-button-border-color:#b87420;--el-button-hover-bg-color:#c98228;--el-button-hover-border-color:#c98228; }
.badge-internal { color:#9a5a0b!important;background:#fff1d8!important; }
.skill-wrap { display:flex;gap:6px;flex-wrap:wrap; }
.manager-check { padding:12px 14px;border:1px solid #f2d29e;border-radius:10px;background:#fffaf1; }
.position-ledger { display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px;align-items:start; }
.ledger-pane { min-width:0;overflow:hidden; }
.ledger-head { display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:18px 20px 12px;border-bottom:1px solid var(--border-color); }
.ledger-head h3 { margin:3px 0 2px;color:var(--text-primary);font-size:17px; }
.ledger-head p { margin:0;color:var(--text-muted);font-size:12px; }
.ledger-kicker { color:var(--color-brand);font-family:"JetBrains Mono",monospace;font-size:10px;font-weight:700;letter-spacing:.1em; }
.internal-ledger .ledger-kicker { color:#ad680f; }
.ledger-count { display:grid;place-items:center;min-width:34px;height:34px;padding:0 8px;border-radius:10px;background:var(--color-brand-light);color:var(--color-brand);font-family:"JetBrains Mono",monospace;font-weight:700; }
.internal-ledger .ledger-count { background:#fff1d8;color:#a35e0c; }
.ledger-filters { display:grid;grid-template-columns:minmax(0,1fr) 124px;gap:8px;padding:12px 14px; }
.public-ledger { border-top:3px solid var(--color-brand); }
.internal-ledger { border-top:3px solid #c98228; }
.table-actions { display:flex;align-items:center;justify-content:flex-end; }
@keyframes suggestion-breathe { 50% { opacity:.45;transform:scale(.8); } }
@media(max-width:1180px){.position-ledger{grid-template-columns:1fr}}
@media(max-width:768px){.suggestion-review{align-items:flex-start;flex-direction:column}.suggestion-heading{align-items:flex-start}.demand-switch{grid-template-columns:1fr}.ledger-filters{grid-template-columns:1fr}}
</style>

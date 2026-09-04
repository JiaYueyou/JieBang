<template>
  <DataState :loading="loading" :error="error" @retry="store.refresh()" />
  <div v-if="!loading && talent" class="anim-fade-up">
    <!-- Back button -->
    <div class="md-back">
      <el-button text @click="$router.push('/matching')">
        <el-icon><ArrowLeft /></el-icon> 返回人才列表
      </el-button>
    </div>

    <!-- Header -->
    <div class="md-header">
      <div class="md-avatar">{{ talent.name.charAt(0) }}</div>
      <div class="md-info">
        <h1>{{ talent.name }}</h1>
        <p>{{ talent.position }} · {{ displayJobTitle }} 匹配度 {{ displayScore }}%</p>
        <div class="md-contact" aria-label="候选人联系方式">
          <span><el-icon><Phone /></el-icon>{{ displayPhone }}</span>
          <span><el-icon><Message /></el-icon>{{ displayEmail }}</span>
        </div>
        <div class="md-meta">
          <el-tag size="small">{{ talent.experience }}</el-tag>
          <el-tag size="small" type="info">{{ talent.education }}</el-tag>
          <el-tag v-if="talent.isNew" size="small" type="danger">NEW</el-tag>
        </div>
      </div>
      <div class="md-header-actions">
        <el-button class="admit-main-action" type="primary" size="large" @click="openAdmissionDialog">录用至企业人才池</el-button>
        <FavoriteButton type="resume" :target-id="talent.id" :title="talent.name" show-label />
      </div>
      <div class="md-score-lg">
        <div class="score-ring-lg" :style="{ '--pct': `${displayScore}%` }"><span>{{ displayScore }}%</span></div>
        <div class="md-score-label">{{ displayJobTitle }} 匹配度</div>
      </div>
    </div>

    <!-- Content grid -->
    <div class="md-grid">
      <!-- Left: Skills & gap -->
      <div class="dash-card">
        <div class="dash-card-header match-skill-header">
          <span class="dash-card-title">技能分析</span>
          <div class="match-job-picker">
            <span>匹配岗位</span>
            <el-select v-model="selectedJobId" :loading="jobsLoading" popper-class="hierarchy-job-popper" @change="matchSelectedJob">
              <el-option-group v-for="group in groupedJobOptions" :key="group.level" :label="levelLabel(group.level)">
                <el-option v-for="job in group.jobs" :key="job.id" :label="job.title" :value="job.id">
                  <div class="job-option-title">{{ job.title }}</div>
                  <div class="job-option-meta"><span>{{ job.department || '部门待补充' }}</span><span>{{ levelLabel(job.level) }}</span></div>
                </el-option>
              </el-option-group>
            </el-select>
          </div>
        </div>
        <div class="dash-card-body">
          <div v-if="activeMatch" class="match-snapshot">
            <strong>{{ activeMatch.job_title }}</strong>
            <span>技能覆盖 {{ activeMatch.score }}%</span>
          </div>
          <div class="md-section">
            <h4><el-icon style="color:var(--color-success);"><CircleCheck /></el-icon> 已匹配技能</h4>
            <div class="md-tags">
              <el-tag v-for="s in displayedMatched" :key="s" type="success" effect="plain">{{ s }}</el-tag>
            </div>
          </div>
          <div class="md-section">
            <h4><el-icon style="color:var(--color-danger);"><WarningFilled /></el-icon> 待补充技能</h4>
            <div class="md-tags">
              <el-tag v-for="s in displayedMissing" :key="s" type="danger" effect="plain">{{ s }}</el-tag>
            </div>
          </div>
          <div class="md-section">
            <h4><el-icon style="color:var(--color-brand);"><Connection /></el-icon> 匹配岗位</h4>
            <div class="md-tags">
              <el-tag v-for="j in jobOptions" :key="j.id" :type="j.id === selectedJobId ? 'primary' : 'info'" effect="plain" class="match-job-tag" @click="selectJob(j.id)">{{ j.title }}</el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Resume -->
      <div class="dash-card">
        <div class="dash-card-header"><span class="dash-card-title">简历原件</span></div>
        <div class="dash-card-body">
          <div v-if="talent.resumeFile" class="md-resume">
            <div class="md-resume-file">
              <el-icon style="font-size:32px;color:var(--color-brand);"><Document /></el-icon>
              <div>
                <div class="md-resume-name">{{ talent.resumeFile }}</div>
                <div class="md-resume-size">上传于 {{ talent.uploadDate || '2026-06-15' }}</div>
              </div>
              <div class="resume-actions">
                <el-button size="small" @click="openResumePreview">查看</el-button>
                <el-button type="primary" size="small" @click="downloadResume">下载</el-button>
              </div>
            </div>
            <el-divider />
            <div class="md-resume-preview">
              <h5>简历内容预览</h5>
              <div class="md-resume-text">
                <p><strong>{{ talent.name }}</strong></p>
                <p>{{ talent.experience }} · {{ talent.education }}</p>
                <p>当前岗位：{{ talent.position }}</p>
                <p>技能：{{ talent.matched.join("、") }}</p>
                <p style="margin-top:12px;">工作经历摘要：具备 {{ talent.experience }} 相关工作经验，在 {{ talent.position }} 领域有深入实践。熟悉 {{ talent.matched.slice(0,3).join("、") }} 等技术栈。参与过多个大型项目的架构设计与核心开发，具备良好的团队协作和问题解决能力。</p>
              </div>
            </div>
          </div>
          <div v-else class="jm-empty" style="padding:32px;">
            <el-icon style="font-size:36px;color:var(--color-border);"><Upload /></el-icon>
            <p style="margin-top:8px;">暂未上传简历原件</p>
            <el-button type="primary" size="small" style="margin-top:12px;">
              <el-icon><Upload /></el-icon> 上传简历
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <div class="dash-card" style="margin-top:16px;">
      <div class="dash-card-header">
        <span class="dash-card-title">匹配解释</span>
        <el-button type="primary" :loading="explaining" :disabled="explaining" @click="generateExplanation">{{ explanation ? '重新生成' : '生成解释' }}</el-button>
      </div>
      <div class="dash-card-body">
        <div v-if="explaining" class="explanation-live" role="status" aria-live="polite">
          <div class="explanation-live-head"><span class="live-pulse"></span><strong>{{ explanationStage }}</strong><span>{{ explanationProgress }}%</span></div>
          <el-progress :percentage="explanationProgress" :show-text="false" />
          <p>{{ explanationDraft }}</p>
          <small>正在基于该岗位的要求与候选人已保存的技能证据生成可审计分析。</small>
        </div>
        <el-empty v-else-if="!explanation" description="选择岗位后，基于已落库的匹配证据生成可审计解释" :image-size="72" />
        <template v-else>
          <el-alert :title="explanation.summary" type="info" :closable="false" show-icon />
          <el-alert
            v-for="warning in explanation.warnings" :key="warning" :title="warning"
            type="warning" :closable="false" show-icon style="margin-top:10px;"
          />
          <div class="md-section"><h4>匹配优势</h4><p v-for="item in explanation.strengths" :key="item.title" class="explanation-claim"><strong>{{ item.title }}：</strong>{{ cleanExplanation(item.explanation) }} <el-popover v-for="evidenceId in item.evidence_ids" :key="evidenceId" trigger="hover" placement="top" :width="360"><template #reference><button class="evidence-index" type="button" @click="jumpToEvidence(evidenceId)">{{ evidenceIndex(evidenceId) }}</button></template><EvidencePopover :evidence="evidenceForId(evidenceId)" /></el-popover></p></div>
          <div class="md-section"><h4>能力缺口</h4><p v-for="item in explanation.gaps" :key="item.title" class="explanation-claim"><strong>{{ item.title }}：</strong>{{ cleanExplanation(item.explanation) }} <el-popover v-for="evidenceId in item.evidence_ids" :key="evidenceId" trigger="hover" placement="top" :width="360"><template #reference><button class="evidence-index" type="button" @click="jumpToEvidence(evidenceId)">{{ evidenceIndex(evidenceId) }}</button></template><EvidencePopover :evidence="evidenceForId(evidenceId)" /></el-popover></p></div>
          <div class="md-section" v-if="explanation.risks.length"><h4>风险提示</h4><p v-for="item in explanation.risks" :key="item.title" class="explanation-claim"><strong>{{ item.title }}：</strong>{{ cleanExplanation(item.explanation) }} <el-popover v-for="evidenceId in item.evidence_ids" :key="evidenceId" trigger="hover" placement="top" :width="360"><template #reference><button class="evidence-index" type="button" @click="jumpToEvidence(evidenceId)">{{ evidenceIndex(evidenceId) }}</button></template><EvidencePopover :evidence="evidenceForId(evidenceId)" /></el-popover></p></div>
          <div class="md-section" v-if="explanation.interview_suggestions.length"><h4>面试建议</h4><p v-for="item in explanation.interview_suggestions" :key="item">{{ item }}</p></div>
          <el-tag size="small" type="info">{{ explanation.generation_mode === 'llm' ? '模型解释' : '确定性模板解释' }}</el-tag>
          <el-collapse v-if="explanation.evidence.length" v-model="evidenceCollapse" class="evidence-collapse">
            <el-collapse-item name="sources">
              <template #title><div class="evidence-collapse-title"><strong>证据来源</strong><span>{{ explanation.evidence.length }} 条已核验证据</span></div></template>
              <div class="evidence-ledger">
                <p class="evidence-ledger-hint">悬浮解释中的索引可查看摘要，点击索引可定位到对应来源。</p>
                <article v-for="evidence in explanation.evidence" :id="`evidence-${evidence.id}`" :key="evidence.id" :class="{ active: selectedEvidence?.id === evidence.id }">
                  <span class="evidence-source-type">{{ evidenceSourceLabel(evidence) }}</span><strong>{{ evidence.skill_name }}</strong><p>{{ evidence.evidence_text }}</p><small>{{ evidenceLocation(evidence) }}</small>
                  <el-button v-if="evidence.evidence_type === 'resume_skill'" text type="primary" @click="openEvidenceResume(evidence)">打开简历原件</el-button>
                </article>
              </div>
            </el-collapse-item>
          </el-collapse>
        </template>
      </div>
    </div>

    <!-- Bottom: Basic info -->
    <div class="dash-card" style="margin-top:16px;">
      <div class="dash-card-header"><span class="dash-card-title">基本信息</span><el-button text type="primary" @click="openTalentDetails">查看详情</el-button></div>
      <div class="dash-card-body">
        <el-descriptions :column="4" border size="default">
          <el-descriptions-item label="姓名">{{ talent.name }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ displayPhone }}</el-descriptions-item>
          <el-descriptions-item label="电子邮箱">{{ displayEmail }}</el-descriptions-item>
          <el-descriptions-item label="当前/期望岗位">{{ talent.position }}</el-descriptions-item>
          <el-descriptions-item label="工作年限">{{ talent.experience }}</el-descriptions-item>
          <el-descriptions-item label="学历">{{ talent.education }}</el-descriptions-item>
          <el-descriptions-item label="当前岗位匹配度">{{ displayScore }}%</el-descriptions-item>
          <el-descriptions-item label="匹配岗位">{{ displayJobTitle }}</el-descriptions-item>
          <el-descriptions-item label="已具备技能">{{ displayedMatched.length }} 项</el-descriptions-item>
          <el-descriptions-item label="待补充技能">{{ displayedMissing.length }} 项</el-descriptions-item>
          <el-descriptions-item label="所在部门">{{ talent.department || '待确认' }}</el-descriptions-item>
          <el-descriptions-item label="所在城市">{{ talent.location || '待确认' }}</el-descriptions-item>
          <el-descriptions-item label="现任公司">{{ talent.company || '待确认' }}</el-descriptions-item>
          <el-descriptions-item label="简历上传时间">{{ talent.uploadDate || '待确认' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </div>

    <el-dialog v-model="resumePreviewVisible" class="resume-workbench-dialog fixed-scroll-dialog" modal-class="global-dark-overlay" append-to-body title="简历原件" width="min(1180px, 96vw)" top="4vh" destroy-on-close @closed="releaseResumePreview">
      <div class="resume-toolbar">
        <div><el-button :icon="ZoomOut" circle :disabled="resumeZoom <= .5" aria-label="缩小简历" @click="changeResumeZoom(-.25)" /><strong>{{ Math.round(resumeZoom * 100) }}%</strong><el-button :icon="ZoomIn" circle :disabled="resumeZoom >= 2.5" aria-label="放大简历" @click="changeResumeZoom(.25)" /><el-button @click="resumeZoom = 1">适合窗口</el-button></div>
        <span>按住 Ctrl 滚动鼠标也可缩放</span>
      </div>
      <div v-if="selectedEvidence" class="resume-evidence-focus"><span>{{ evidenceIndex(`match_evidence:${selectedEvidence.id}`) }}</span><div><strong>{{ selectedEvidence.skill_name }} · 简历来源</strong><p>{{ selectedEvidence.evidence_text }}</p><small>{{ evidenceLocation(selectedEvidence) }}</small></div></div>
      <div v-if="resumePreviewUrl" class="resume-preview-dialog" @wheel.ctrl.prevent="handleResumeWheel">
        <iframe v-if="isPdfPreview || isTextPreview" :src="resumePreviewUrl" title="简历原件预览" :style="documentPreviewStyle"></iframe>
        <img v-else-if="isImagePreview" :src="resumePreviewUrl" alt="简历原件预览" :style="imagePreviewStyle" />
        <pre v-else class="resume-text-preview" :style="{ fontSize: `${13 * resumeZoom}px` }">{{ talentDetails?.parsed_text || '此文件类型暂不支持浏览器原件预览，请下载后查看。' }}</pre>
      </div>
      <el-alert v-if="!isBrowserPreview" title="当前文件格式无法在浏览器中保持原件版式，已展示解析文本；可下载原文件查看。" type="info" :closable="false" show-icon />
      <template #footer><el-button @click="downloadResume">下载原件</el-button><el-button type="primary" @click="resumePreviewVisible = false">关闭</el-button></template>
    </el-dialog>

    <el-dialog v-model="talentDetailVisible" class="talent-editor-dialog fixed-scroll-dialog" modal-class="global-dark-overlay" append-to-body title="候选人完整信息" width="min(960px, 94vw)" top="5vh" @closed="cancelTalentEdit">
      <div v-if="talentDetails" class="talent-detail-dialog">
        <div class="detail-dialog-toolbar"><div><strong>人才资料</strong><span>自动识别缺失的信息可由管理员补充</span></div><div v-if="!talentEditing" class="detail-dialog-actions"><el-button class="dialog-primary-action" type="primary" @click="startTalentEdit">编辑资料</el-button></div></div>
        <el-form v-if="talentEditing" :model="talentForm" label-position="top" class="talent-edit-form">
          <el-form-item label="姓名" required><el-input v-model="talentForm.name" maxlength="100" /></el-form-item>
          <el-form-item label="联系电话"><el-input v-model="talentForm.phone" maxlength="40" /></el-form-item>
          <el-form-item label="电子邮箱"><el-input v-model="talentForm.email" maxlength="160" /></el-form-item>
          <el-form-item label="当前或期望岗位"><el-input v-model="talentForm.current_position" maxlength="120" /></el-form-item>
          <el-form-item label="工作经历"><el-input v-model="talentForm.experience" maxlength="100" /></el-form-item>
          <el-form-item label="最高学历"><el-input v-model="talentForm.education" maxlength="100" /></el-form-item>
          <el-form-item label="所在部门"><el-input v-model="talentForm.department" maxlength="100" /></el-form-item>
          <el-form-item label="现任公司"><el-input v-model="talentForm.company" maxlength="150" /></el-form-item>
          <el-form-item label="所在城市"><el-input v-model="talentForm.location" maxlength="100" /></el-form-item>
        </el-form>
        <el-descriptions v-else :column="3" border><el-descriptions-item label="姓名">{{ talentDetails.name }}</el-descriptions-item><el-descriptions-item label="联系电话">{{ talentDetails.phone || '电话待补充' }}</el-descriptions-item><el-descriptions-item label="电子邮箱">{{ talentDetails.email || '邮箱待补充' }}</el-descriptions-item><el-descriptions-item label="文件大小">{{ formatFileSize(talentDetails.file_size) }}</el-descriptions-item><el-descriptions-item label="文件类型">{{ contentTypeLabel(talentDetails.content_type) }}</el-descriptions-item><el-descriptions-item label="当前或期望岗位">{{ talentDetails.position }}</el-descriptions-item><el-descriptions-item label="现任公司">{{ talentDetails.company || '公司待补充' }}</el-descriptions-item><el-descriptions-item label="所在部门">{{ talentDetails.department }}</el-descriptions-item><el-descriptions-item label="所在城市">{{ talentDetails.location || '地点待补充' }}</el-descriptions-item></el-descriptions>
        <section><h4>识别到的技能与证据</h4><div class="detail-skill-list"><article v-for="skill in talentDetails.skills" :key="skill.name"><strong>{{ skill.name }}</strong><span>{{ skillCategoryLabel(skill.category) }} · 置信度 {{ Math.round(skill.confidence * 100) }}%</span><p>{{ skill.evidence_text || '未保留原文片段' }}</p></article></div></section>
        <section><h4>简历解析文本</h4><pre class="resume-text-preview">{{ talentDetails.parsed_text || '暂无可展示的解析文本。' }}</pre></section>
      </div>
      <template #footer><template v-if="talentEditing"><el-button @click="cancelTalentEdit">取消</el-button><el-button class="dialog-primary-action" type="primary" :loading="talentSaving" @click="saveTalentDetails">保存资料</el-button></template><el-button v-else class="dialog-primary-action" type="primary" @click="talentDetailVisible = false">关闭</el-button></template>
    </el-dialog>

    <el-dialog v-model="admissionVisible" class="admission-dialog fixed-scroll-dialog" modal-class="global-dark-overlay" append-to-body title="录用并加入企业人才池" width="min(620px, 92vw)" top="8vh">
      <div class="admission-intro"><span>录用流程</span><strong>候选人 → 自动分配工号 → 企业员工目录 → 企业人才池</strong><p>完成后，该人才可立即参与企业内部岗位匹配与职业规划分析。</p></div>
      <el-form :model="admissionForm" label-position="top" class="admission-form">
        <el-form-item label="候选人"><el-input :model-value="talentDetails?.name || talent?.name" disabled /></el-form-item>
        <el-form-item label="入职部门" required><el-select v-model="admissionForm.department" :loading="admissionDepartmentsLoading" filterable placeholder="请选择企业部门" style="width:100%"><el-option v-for="department in admissionDepartments" :key="department.id" :label="department.name" :value="department.name"><span>{{ department.name }}</span><small class="department-option-code">{{ department.code }}</small></el-option></el-select></el-form-item>
        <el-form-item label="入职岗位" required><el-input v-model="admissionForm.current_position" maxlength="120" placeholder="例如：Java 开发工程师" /></el-form-item>
        <el-form-item label="入职职级"><el-select v-model="admissionForm.level" style="width:100%"><el-option label="实习生" value="intern" /><el-option label="初级" value="junior" /><el-option label="中级" value="mid" /><el-option label="高级" value="senior" /><el-option label="专家" value="expert" /></el-select></el-form-item>
        <el-form-item label="工作城市"><el-input v-model="admissionForm.location" maxlength="100" placeholder="例如：合肥" /></el-form-item>
      </el-form>
      <el-alert title="企业工号将在确认录用后自动生成，无需手工填写。" type="info" :closable="false" show-icon />
      <template #footer><el-button @click="admissionVisible = false">取消</el-button><el-button class="dialog-primary-action" type="primary" :loading="admitting" @click="admitCandidate">确认录用并加入人才池</el-button></template>
    </el-dialog>
  </div>

  <div v-else-if="!loading" class="jm-empty jm-empty-fill">
    <el-icon style="font-size:40px;color:var(--color-border);"><Warning /></el-icon>
    <p style="margin-top:12px;">未找到该人才信息</p>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, CircleCheck, WarningFilled, Connection, Document, Upload, Warning, Phone, Message, ZoomIn, ZoomOut } from "@element-plus/icons-vue";
import FavoriteButton from "@/components/common/FavoriteButton.vue";
import DataState from "@/components/common/DataState.vue";
import EvidencePopover from "@/components/matching/EvidencePopover.vue";
import { useTalentStore } from "@/stores/talents";
import { useHistoryStore } from "@/stores/history";
import { dataProvider } from "@/data";
import { contentTypeLabel, levelLabel, skillCategoryLabel } from "@/utils/displayLabels";
import type { EnterpriseDepartment, JobSummary, MatchEvidence, MatchExplanation, TalentDetail, TalentMatch, TalentUpdatePayload } from "@/domain/types";

const route = useRoute();
const router = useRouter();
const store = useTalentStore();
const historyStore = useHistoryStore();
const { talents, loading, error } = storeToRefs(store);
const explanation = ref<MatchExplanation | null>(null);
const explaining = ref(false);
const explanationProgress = ref(0);
const explanationStage = ref("");
const explanationDraft = ref("");
const jobOptions = ref<JobSummary[]>([]);
const jobsLoading = ref(false);
const selectedJobId = ref<number | null>(null);
const activeMatch = ref<TalentMatch | null>(null);
const talentDetails = ref<TalentDetail | null>(null);
const talentDetailVisible = ref(false);
const resumePreviewVisible = ref(false);
const resumePreviewUrl = ref("");
const resumePreviewContentType = ref("");
const resumeZoom = ref(1);
const selectedEvidence = ref<MatchEvidence | null>(null);
const evidenceCollapse = ref<string[]>([]);
const talentEditing = ref(false);
const talentSaving = ref(false);
const admissionVisible = ref(false);
const admitting = ref(false);
const admissionDepartments = ref<EnterpriseDepartment[]>([]);
const admissionDepartmentsLoading = ref(false);
const admissionForm = reactive({ department: "", current_position: "", level: "junior", location: "" });
const talentForm = reactive<TalentUpdatePayload>({ name: "", phone: "", email: "", current_position: "", experience: "", education: "", department: "", company: "", location: "" });
onMounted(async () => {
  await store.load();
  if (!talent.value) return;
  selectedJobId.value = talent.value.targetJobIds?.[0] ?? null;
  await Promise.all([loadJobOptions(), loadTalentDetails()]);
  hydrateSelectedMatch();
  try {
    await historyStore.record({
      type: "match",
      targetId: talent.value.match_id,
      title: `${talent.value.name}的匹配报告`,
      description: `${displayJobTitle.value} · 匹配度 ${displayScore.value}%`,
      source: "人才匹配",
      tags: [...talent.value.matched, ...talent.value.missing].slice(0, 5),
      url: `/matching/${talent.value.resume_id}`,
    });
  } catch {
    ElMessage.warning("匹配报告已打开，但浏览足迹记录失败");
  }
});
const talent = computed(() => {
  const id = Number(route.params.resumeId);
  return talents.value.find((t) => t.resume_id === id) || null;
});
const displayedMatched = computed(() => activeMatch.value?.matched ?? talent.value?.matched ?? []);
const displayedMissing = computed(() => activeMatch.value?.missing ?? talent.value?.missing ?? []);
const displayScore = computed(() => activeMatch.value?.score ?? talent.value?.score ?? 0);
const displayJobTitle = computed(() => activeMatch.value?.job_title ?? talent.value?.targetJobs?.[0] ?? "当前岗位");
const displayPhone = computed(() => talentDetails.value?.phone || talent.value?.phone || "电话待补充");
const displayEmail = computed(() => talentDetails.value?.email || talent.value?.email || "邮箱待补充");
const groupedJobOptions = computed(() => {
  const groups = new Map<string, JobSummary[]>();
  jobOptions.value.forEach((job) => {
    const level = job.level?.trim() || "职级待补充";
    groups.set(level, [...(groups.get(level) || []), job]);
  });
  return [...groups.entries()].map(([level, jobs]) => ({ level, jobs }));
});
const isPdfPreview = computed(() => resumePreviewContentType.value.includes("pdf"));
const isImagePreview = computed(() => resumePreviewContentType.value.startsWith("image/"));
const isTextPreview = computed(() => resumePreviewContentType.value.startsWith("text/"));
const isBrowserPreview = computed(() => isPdfPreview.value || isImagePreview.value || isTextPreview.value);
const imagePreviewStyle = computed(() => ({ width: `${resumeZoom.value * 100}%`, maxWidth: "none" }));
const documentPreviewStyle = computed(() => ({ width: `${100 / resumeZoom.value}%`, height: `${66 / resumeZoom.value}vh`, transform: `scale(${resumeZoom.value})`, transformOrigin: "top left" }));

async function loadJobOptions() {
  jobsLoading.value = true;
  try {
    const page = await dataProvider.jobs.list({ page: 1, pageSize: 100, status: "open" });
    jobOptions.value = page.items;
    if (!selectedJobId.value && page.items[0]) selectedJobId.value = page.items[0].id;
  } catch (exception) {
    ElMessage.warning(exception instanceof Error ? exception.message : "岗位列表加载失败");
  } finally { jobsLoading.value = false; }
}

async function loadTalentDetails() {
  if (!talent.value) return;
  try {
    talentDetails.value = await dataProvider.talents.getDetails(Number(talent.value.resume_id));
  } catch (exception) {
    // Detail data is progressive enhancement; the primary matching workflow remains usable.
    ElMessage.warning(exception instanceof Error ? exception.message : "简历详情加载失败");
  }
}

function hydrateSelectedMatch() {
  if (!selectedJobId.value) return;
  activeMatch.value = talentDetails.value?.matches.find((item) => item.job_id === selectedJobId.value) ?? null;
}

async function matchSelectedJob() {
  if (!talent.value || !selectedJobId.value) return;
  explanation.value = null;
  try {
    const matches = await dataProvider.talents.matchJobs(Number(talent.value.resume_id), [selectedJobId.value]);
    activeMatch.value = matches[0] ?? null;
    if (!activeMatch.value) ElMessage.warning("所选岗位没有可用于匹配的技能要求");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "岗位匹配失败");
  }
}

async function selectJob(jobId: number) {
  if (selectedJobId.value === jobId && activeMatch.value) return;
  selectedJobId.value = jobId;
  await matchSelectedJob();
}

async function downloadResume() {
  if (!talent.value?.resumeFile) return;
  await dataProvider.talents.download(Number(talent.value.resume_id), talent.value.resumeFile);
}

async function openResumePreview() {
  if (!talent.value?.resumeFile) return;
  releaseResumePreview();
  try {
    const preview = await dataProvider.talents.preview(Number(talent.value.resume_id));
    resumePreviewUrl.value = preview.url;
    resumePreviewContentType.value = preview.contentType.toLowerCase();
    resumeZoom.value = 1;
    resumePreviewVisible.value = true;
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "简历预览加载失败");
  }
}

function releaseResumePreview() {
  if (resumePreviewUrl.value) URL.revokeObjectURL(resumePreviewUrl.value);
  resumePreviewUrl.value = "";
  resumePreviewContentType.value = "";
  selectedEvidence.value = null;
}

function changeResumeZoom(delta: number) {
  resumeZoom.value = Math.min(2.5, Math.max(.5, Number((resumeZoom.value + delta).toFixed(2))));
}

function handleResumeWheel(event: WheelEvent) {
  changeResumeZoom(event.deltaY < 0 ? .25 : -.25);
}

function cleanExplanation(value: string) {
  return value.replace(/\s*[（(]?match_evidence:\d+[）)]?/gi, "").replace(/\s{2,}/g, " ").trim();
}

function evidenceForId(evidenceId: string) {
  const id = Number(evidenceId.split(":").pop());
  return explanation.value?.evidence.find((item) => item.id === id)
    || activeMatch.value?.evidence?.find((item) => item.id === id)
    || null;
}

function evidenceIndex(evidenceId: string) {
  const evidence = evidenceForId(evidenceId);
  if (!evidence) return "[?]";
  const sameType = (explanation.value?.evidence || []).filter((item) => item.evidence_type === evidence.evidence_type);
  const index = sameType.findIndex((item) => item.id === evidence.id) + 1;
  return `[${evidence.evidence_type === "resume_skill" ? "R" : "J"}${index || 1}]`;
}

function evidenceSourceLabel(evidence: MatchEvidence) {
  return evidence.evidence_type === "resume_skill" ? "简历原文" : "岗位 JD";
}

function evidenceLocation(evidence: MatchEvidence) {
  const source = evidence.source_ref;
  if (evidence.evidence_type === "resume_skill") {
    const line = source.line_start ? `第 ${source.line_start}${source.line_end && source.line_end !== source.line_start ? `–${source.line_end}` : ""} 行` : "原文位置未标注";
    return `${source.filename || talent.value?.resumeFile || "简历原件"} · ${line}`;
  }
  return `${source.job_title || displayJobTitle.value} · ${source.department || "部门待补充"} · ${levelLabel(String(source.level || ""))}`;
}

async function jumpToEvidence(evidenceId: string) {
  const evidence = evidenceForId(evidenceId);
  if (!evidence) return;
  selectedEvidence.value = evidence;
  if (evidence.evidence_type === "resume_skill") {
    await openEvidenceResume(evidence);
    return;
  }
  evidenceCollapse.value = ["sources"];
  await nextTick();
  document.getElementById(`evidence-${evidence.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function openEvidenceResume(evidence: MatchEvidence) {
  selectedEvidence.value = evidence;
  await openResumePreview();
  selectedEvidence.value = evidence;
}

async function openTalentDetails() {
  if (!talentDetails.value) await loadTalentDetails();
  if (talentDetails.value) {
    talentEditing.value = false;
    talentDetailVisible.value = true;
  }
}

function startTalentEdit() {
  if (!talentDetails.value) return;
  Object.assign(talentForm, {
    name: talentDetails.value.name === "姓名待补充" ? "" : talentDetails.value.name,
    phone: talentDetails.value.phone || "",
    email: talentDetails.value.email || "",
    current_position: talentDetails.value.position?.includes("待补充") ? "" : talentDetails.value.position,
    experience: talentDetails.value.experience?.includes("待补充") ? "" : talentDetails.value.experience,
    education: talentDetails.value.education?.includes("待补充") ? "" : talentDetails.value.education,
    department: talentDetails.value.department?.includes("待补充") ? "" : talentDetails.value.department,
    company: talentDetails.value.company || "",
    location: talentDetails.value.location || "",
  });
  talentEditing.value = true;
}

function cancelTalentEdit() {
  talentEditing.value = false;
}

async function saveTalentDetails() {
  if (!talent.value) return;
  if (!talentForm.name.trim()) {
    ElMessage.warning("请填写候选人姓名；无法确认时可填写“姓名待补充”");
    return;
  }
  talentSaving.value = true;
  try {
    talentDetails.value = await dataProvider.talents.updateDetails(Number(talent.value.resume_id), { ...talentForm, name: talentForm.name.trim() });
    await store.refresh();
    talentEditing.value = false;
    ElMessage.success("人才资料已保存");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "人才资料保存失败");
  } finally {
    talentSaving.value = false;
  }
}

async function openAdmissionDialog() {
  admissionDepartmentsLoading.value = true;
  try {
    admissionDepartments.value = (await dataProvider.internalTransfer.listDepartments()).filter((item) => item.status === "active");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "企业部门加载失败");
    return;
  } finally {
    admissionDepartmentsLoading.value = false;
  }
  admissionForm.department = talentDetails.value?.department?.includes("待补充") ? "" : talentDetails.value?.department || "";
  if (!admissionDepartments.value.some((item) => item.name === admissionForm.department)) admissionForm.department = "";
  admissionForm.current_position = talentDetails.value?.position?.includes("待补充") ? "" : talentDetails.value?.position || "";
  admissionForm.location = talentDetails.value?.location || "";
  admissionForm.level = "junior";
  talentDetailVisible.value = false;
  nextTick(() => { admissionVisible.value = true; });
}

async function admitCandidate() {
  if (!talent.value) return;
  if (!admissionForm.department.trim() || !admissionForm.current_position.trim()) {
    ElMessage.warning("请填写入职部门和入职岗位");
    return;
  }
  admitting.value = true;
  try {
    const admitted = await dataProvider.internalTransfer.admitResume(Number(talent.value.resume_id), {
      department: admissionForm.department.trim(),
      current_position: admissionForm.current_position.trim(),
      level: admissionForm.level,
      location: admissionForm.location.trim() || null,
    });
    admissionVisible.value = false;
    talentDetailVisible.value = false;
    await ElMessageBox.confirm(
      `已为 ${admitted.name} 分配企业工号 ${admitted.employee_no}，并写入企业员工目录和企业人才池。`,
      "录用完成",
      { confirmButtonText: "进入企业人才池", cancelButtonText: "留在当前页面", type: "success" },
    );
    await router.push({ path: "/career", query: { tab: "talents" } });
  } catch (exception) {
    if (exception === "cancel" || exception === "close") return;
    ElMessage.error(exception instanceof Error ? exception.message : "候选人录用失败");
  } finally {
    admitting.value = false;
  }
}

function formatFileSize(bytes: number) {
  if (!bytes) return "未知";
  return bytes < 1024 * 1024 ? `${Math.round(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function progressCopy(progress: number, status: string) {
  if (status === "queued") return "已收到请求，正在调取岗位与简历的匹配证据";
  if (progress < 35) return "正在核验技能覆盖和缺口";
  if (progress < 85) return "正在生成针对该岗位的面试建议与风险提示";
  return "正在整理可审计的匹配结论";
}

async function generateExplanation() {
  if (!talent.value) return;
  const matchId = activeMatch.value?.id ?? talent.value.match_id;
  const jobTitle = activeMatch.value?.job_title ?? talent.value.targetJobs?.[0] ?? talent.value.position;
  const matched = displayedMatched.value;
  const missing = displayedMissing.value;
  explaining.value = true;
  explanation.value = null;
  explanationProgress.value = 4;
  explanationStage.value = "已开始生成匹配解释";
  explanationDraft.value = `${talent.value.name} 与“${jobTitle}”的即时读数：已覆盖 ${matched.length} 项技能${matched.length ? `（${matched.slice(0, 3).join("、")}）` : ""}，待验证或补足 ${missing.length} 项${missing.length ? `（${missing.slice(0, 3).join("、")}）` : ""}。`;
  try {
    explanation.value = await dataProvider.talents.explain(Number(matchId), (progress, status) => {
      explanationProgress.value = Math.max(progress, 4);
      explanationStage.value = progressCopy(progress, status);
    });
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "匹配解释生成失败");
  } finally {
    explaining.value = false;
    explanationDraft.value = "";
  }
}

onBeforeUnmount(releaseResumePreview);
</script>

<style scoped>
.match-skill-header,
.explanation-live-head,
.resume-actions,
.match-job-picker {
  display: flex;
  align-items: center;
}

.match-skill-header { justify-content: space-between; gap: 12px; }
.match-job-picker { gap: 12px; color: var(--text-secondary); font-size: 14px; font-weight: 600; }
.match-job-picker .el-select { width: min(330px, 48vw); }
.md-contact { display: flex; flex-wrap: wrap; gap: 9px 18px; margin-top: 8px; color: var(--text-secondary); font-size: 13px; }
.md-contact span { display: inline-flex; align-items: center; gap: 5px; }
.md-contact .el-icon { color: var(--color-brand); }
.md-header-actions { display:flex; align-items:center; gap:10px; flex-wrap:wrap; justify-content:flex-end; }
.admit-main-action { min-width:168px; box-shadow:0 8px 20px rgba(79,110,246,.22); font-weight:700; }
.department-option-code { float:right; margin-left:16px; color:var(--text-muted); font-family:var(--font-mono); }
:global(.hierarchy-job-popper .el-select-group__title) { height: auto; padding: 8px 14px 5px; color: var(--text-muted); font-size: 12px; font-weight: 700; letter-spacing: .04em; }
:global(.hierarchy-job-popper .el-select-dropdown__item) { height: auto; min-height: 56px; margin: 2px 7px; padding: 7px 10px; border-radius: 7px; line-height: 1.35; }
:global(.hierarchy-job-popper .el-select-dropdown__item.is-selected) { background: var(--color-brand-light); }
:global(.job-option-title) { color: var(--text-primary); font-size: 15px; font-weight: 700; }
:global(.job-option-meta) { display: flex; gap: 7px; margin-top: 4px; color: var(--text-secondary); font-size: 12px; }
:global(.job-option-meta span) { padding: 1px 6px; border: 1px solid var(--color-border-light); border-radius: 999px; background: var(--color-bg-elevated); }
.match-snapshot { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 14px; padding: 10px 12px; border-left: 3px solid var(--color-brand); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; background: var(--color-brand-light); color: var(--text-secondary); font-size: 13px; }
.match-snapshot strong { color: var(--text-primary); }
.match-job-tag { cursor: pointer; transition: transform var(--duration-fast), box-shadow var(--duration-fast); }
.match-job-tag:hover { transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.resume-actions { gap: 8px; margin-left: auto; }

.explanation-live { padding: 18px; border: 1px solid rgba(79, 110, 246, .2); border-radius: var(--radius-md); background: linear-gradient(135deg, var(--color-brand-light), var(--color-bg-elevated)); }
.explanation-live-head { gap: 8px; justify-content: space-between; color: var(--text-secondary); font-size: 13px; }
.explanation-live-head strong { flex: 1; color: var(--text-primary); }
.live-pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--color-brand); box-shadow: 0 0 0 0 rgba(79, 110, 246, .45); animation: explanation-pulse 1.5s infinite; }
.explanation-live :deep(.el-progress) { margin-top: 12px; }
.explanation-live p { margin: 14px 0 8px; color: var(--text-primary); line-height: 1.8; }
.explanation-live small { color: var(--text-muted); }
.explanation-claim { color: var(--text-primary); line-height: 1.9; }
.evidence-index { display: inline-flex; align-items: center; margin: 0 3px; padding: 1px 6px; border: 1px solid rgba(79, 110, 246, .28); border-radius: 999px; background: var(--color-brand-light); color: var(--color-brand); font: 700 11px/1.65 var(--font-mono); cursor: pointer; vertical-align: .08em; transition: transform var(--duration-fast), box-shadow var(--duration-fast); }
.evidence-index:hover,.evidence-index:focus-visible { transform: translateY(-1px); box-shadow: 0 3px 10px rgba(79, 110, 246, .18); outline: none; }
.evidence-collapse { margin-top: 22px; border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); overflow: hidden; }
.evidence-collapse :deep(.el-collapse-item__header) { height: 52px; padding: 0 15px; border-bottom: 0; background: var(--color-bg-muted); }
.evidence-collapse :deep(.el-collapse-item__wrap) { border-bottom: 0; }
.evidence-collapse :deep(.el-collapse-item__content) { padding: 0 14px 14px; }
.evidence-collapse-title { display: flex; align-items: center; gap: 10px; }
.evidence-collapse-title strong { color: var(--text-primary); font-size: 14px; }
.evidence-collapse-title span { color: var(--text-muted); font-size: 12px; font-weight: 400; }
.evidence-ledger { padding-top: 3px; }
.evidence-ledger-hint { margin: 0 0 8px; color: var(--text-muted); font-size: 12px; }
.evidence-ledger article { position: relative; margin-top: 10px; padding: 12px 14px 12px 110px; border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); background: var(--color-bg-muted); transition: border-color var(--duration-fast), box-shadow var(--duration-fast); }
.evidence-ledger article.active { border-color: var(--color-brand); box-shadow: 0 0 0 3px rgba(79, 110, 246, .10); }
.evidence-source-type { position: absolute; top: 13px; left: 14px; width: 78px; color: var(--color-brand); font-size: 12px; font-weight: 700; }
.evidence-ledger article strong { color: var(--text-primary); }
.evidence-ledger article p { margin: 5px 0 2px; color: var(--text-secondary); line-height: 1.65; }
.evidence-ledger article small { color: var(--text-muted); }
.evidence-ledger article .el-button { margin-left: 10px; }

.resume-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 12px; padding: 9px 12px; border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); background: var(--color-bg-elevated); }
.resume-toolbar > div { display: flex; align-items: center; gap: 9px; }
.resume-toolbar strong { min-width: 48px; text-align: center; font: 700 13px var(--font-mono); }
.resume-toolbar > span { color: var(--text-muted); font-size: 12px; }
.resume-evidence-focus { display: flex; gap: 11px; margin-bottom: 12px; padding: 11px 13px; border-left: 3px solid var(--color-brand); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; background: var(--color-brand-light); }
.resume-evidence-focus > span { align-self: flex-start; color: var(--color-brand); font: 700 12px var(--font-mono); }
.resume-evidence-focus strong,.resume-evidence-focus p,.resume-evidence-focus small { display: block; }
.resume-evidence-focus p { margin: 4px 0; color: var(--text-secondary); }
.resume-evidence-focus small { color: var(--text-muted); }
.resume-preview-dialog { min-height: min(66vh, 680px); max-height: min(70vh, 740px); border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); overflow: auto; background: #dfe3eb; }
.resume-preview-dialog iframe { display: block; border: 0; }
.resume-preview-dialog img { display: block; height: auto; margin: 0 auto; transition: width 160ms ease; }
:global(.global-dark-overlay) { position: fixed !important; inset: 0 !important; background: rgba(12, 18, 32, .76) !important; backdrop-filter: blur(2px); }
:global(.fixed-scroll-dialog) { height: min(820px, 90vh); margin-bottom: 0 !important; display: flex; flex-direction: column; overflow: hidden; border-radius: 14px; box-shadow: 0 24px 80px rgba(0, 0, 0, .32); }
:global(.fixed-scroll-dialog .el-dialog__header),:global(.fixed-scroll-dialog .el-dialog__footer) { flex: 0 0 auto; }
:global(.fixed-scroll-dialog .el-dialog__body) { min-height: 0; flex: 1 1 auto; overflow-y: auto; padding-top: 10px; }
.detail-dialog-toolbar { position: sticky; top: -10px; z-index: 2; display: flex; align-items: center; justify-content: space-between; gap: 16px; margin: -10px 0 18px; padding: 12px 0; border-bottom: 1px solid var(--color-border-light); background: var(--color-bg-elevated); }
.detail-dialog-toolbar strong,.detail-dialog-toolbar span { display: block; }
.detail-dialog-toolbar span { margin-top: 3px; color: var(--text-muted); font-size: 12px; }
.detail-dialog-actions { display:flex; align-items:center; gap:10px; }
:global(.dialog-primary-action) { min-width: 96px; transition: transform .16s ease, box-shadow .16s ease, background-color .16s ease !important; }
:global(.dialog-primary-action:hover) { transform: translateY(-1px); box-shadow: 0 7px 18px rgba(79,110,246,.25); }
:global(.dialog-primary-action:active) { transform: translateY(0) scale(.98); box-shadow: 0 2px 8px rgba(79,110,246,.2); }
.talent-edit-form { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0 14px; }
.talent-edit-form :deep(.el-form-item) { margin-bottom: 15px; }
.talent-edit-form :deep(.el-form-item__label) { color: var(--text-secondary); font-weight: 600; }
.resume-text-preview { max-height: min(60vh, 600px); margin: 0; padding: 18px; overflow: auto; color: var(--text-secondary); font: 13px/1.8 var(--font-mono); white-space: pre-wrap; }
.talent-detail-dialog section { margin-top: 22px; }
.talent-detail-dialog h4 { margin-bottom: 10px; color: var(--text-primary); font-size: 14px; }
.detail-skill-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.detail-skill-list article { padding: 12px; border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); background: var(--color-bg-muted); }
.detail-skill-list strong,.detail-skill-list span { display: block; }
.detail-skill-list span { margin-top: 3px; color: var(--text-muted); font-size: 12px; }
.detail-skill-list p { margin: 8px 0 0; color: var(--text-secondary); font-size: 12px; line-height: 1.6; }
.admission-intro { margin-bottom:20px; padding:18px 20px; border:1px solid #dce4ff; border-radius:12px; background:linear-gradient(135deg,#f6f8ff,#fff); }
.admission-intro span { display:block; color:var(--color-brand); font-size:12px; font-weight:800; letter-spacing:.12em; }
.admission-intro strong { display:block; margin-top:7px; color:var(--text-primary); font-size:16px; }
.admission-intro p { margin:8px 0 0; color:var(--text-secondary); font-size:13px; line-height:1.7; }
.admission-form { display:grid; grid-template-columns:1fr 1fr; gap:0 16px; }
.admission-form .el-form-item:first-child { grid-column:1 / -1; }

@keyframes explanation-pulse { 70% { box-shadow: 0 0 0 7px rgba(79, 110, 246, 0); } 100% { box-shadow: 0 0 0 0 rgba(79, 110, 246, 0); } }
@media (max-width: 640px) { .match-skill-header { align-items: flex-start; flex-direction: column; } .match-job-picker { align-items: flex-start; flex-direction: column; width: 100%; } .match-job-picker .el-select { width: 100%; } .detail-skill-list,.talent-edit-form,.admission-form { grid-template-columns: 1fr; } .admission-form .el-form-item:first-child { grid-column:auto; } .detail-dialog-actions { flex-wrap:wrap; justify-content:flex-end; } .resume-toolbar { align-items: flex-start; flex-direction: column; } .evidence-ledger article { padding-left: 14px; padding-top: 38px; } }
</style>

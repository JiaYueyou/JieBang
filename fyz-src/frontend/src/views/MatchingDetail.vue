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
        <div class="md-meta">
          <el-tag size="small">{{ talent.experience }}</el-tag>
          <el-tag size="small" type="info">{{ talent.education }}</el-tag>
          <el-tag v-if="talent.isNew" size="small" type="danger">NEW</el-tag>
        </div>
      </div>
      <FavoriteButton type="resume" :target-id="talent.id" :title="talent.name" show-label />
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
            <el-select v-model="selectedJobId" size="small" :loading="jobsLoading" @change="matchSelectedJob">
              <el-option v-for="job in jobOptions" :key="job.id" :label="job.title" :value="job.id">
                <span>{{ job.title }}</span><small>{{ job.department }}</small>
              </el-option>
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
          <div class="md-section"><h4>匹配优势</h4><p v-for="item in explanation.strengths" :key="item.title"><strong>{{ item.title }}：</strong>{{ item.explanation }}</p></div>
          <div class="md-section"><h4>能力缺口</h4><p v-for="item in explanation.gaps" :key="item.title"><strong>{{ item.title }}：</strong>{{ item.explanation }}</p></div>
          <div class="md-section" v-if="explanation.risks.length"><h4>风险提示</h4><p v-for="item in explanation.risks" :key="item.title"><strong>{{ item.title }}：</strong>{{ item.explanation }}</p></div>
          <div class="md-section" v-if="explanation.interview_suggestions.length"><h4>面试建议</h4><p v-for="item in explanation.interview_suggestions" :key="item">{{ item }}</p></div>
          <el-tag size="small" type="info">{{ explanation.generation_mode === 'llm' ? '模型解释' : '确定性模板解释' }}</el-tag>
        </template>
      </div>
    </div>

    <!-- Bottom: Basic info -->
    <div class="dash-card" style="margin-top:16px;">
      <div class="dash-card-header"><span class="dash-card-title">基本信息</span><el-button text type="primary" @click="openTalentDetails">查看详情</el-button></div>
      <div class="dash-card-body">
        <el-descriptions :column="4" border size="default">
          <el-descriptions-item label="姓名">{{ talent.name }}</el-descriptions-item>
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

    <el-dialog v-model="resumePreviewVisible" title="简历原件" width="min(1040px, 94vw)" destroy-on-close @closed="releaseResumePreview">
      <div v-if="resumePreviewUrl" class="resume-preview-dialog">
        <iframe v-if="isPdfPreview || isTextPreview" :src="resumePreviewUrl" title="简历原件预览"></iframe>
        <img v-else-if="isImagePreview" :src="resumePreviewUrl" alt="简历原件预览" />
        <pre v-else class="resume-text-preview">{{ talentDetails?.parsed_text || '此文件类型暂不支持浏览器原件预览，请下载后查看。' }}</pre>
      </div>
      <el-alert v-if="!isBrowserPreview" title="当前文件格式无法在浏览器中保持原件版式，已展示解析文本；可下载原文件查看。" type="info" :closable="false" show-icon />
      <template #footer><el-button @click="downloadResume">下载原件</el-button><el-button type="primary" @click="resumePreviewVisible = false">关闭</el-button></template>
    </el-dialog>

    <el-dialog v-model="talentDetailVisible" title="候选人完整信息" width="min(920px, 94vw)">
      <div v-if="talentDetails" class="talent-detail-dialog">
        <el-descriptions :column="3" border><el-descriptions-item label="姓名">{{ talentDetails.name }}</el-descriptions-item><el-descriptions-item label="文件大小">{{ formatFileSize(talentDetails.file_size) }}</el-descriptions-item><el-descriptions-item label="文件类型">{{ talentDetails.content_type || '未知' }}</el-descriptions-item><el-descriptions-item label="当前岗位">{{ talentDetails.position }}</el-descriptions-item><el-descriptions-item label="公司 / 部门">{{ talentDetails.company || '待确认' }} / {{ talentDetails.department }}</el-descriptions-item><el-descriptions-item label="地点">{{ talentDetails.location || '待确认' }}</el-descriptions-item></el-descriptions>
        <section><h4>识别到的技能与证据</h4><div class="detail-skill-list"><article v-for="skill in talentDetails.skills" :key="skill.name"><strong>{{ skill.name }}</strong><span>{{ skill.category }} · 置信度 {{ Math.round(skill.confidence * 100) }}%</span><p>{{ skill.evidence_text || '未保留原文片段' }}</p></article></div></section>
        <section><h4>简历解析文本</h4><pre class="resume-text-preview">{{ talentDetails.parsed_text || '暂无可展示的解析文本。' }}</pre></section>
      </div>
    </el-dialog>
  </div>

  <div v-else-if="!loading" class="jm-empty jm-empty-fill">
    <el-icon style="font-size:40px;color:var(--color-border);"><Warning /></el-icon>
    <p style="margin-top:12px;">未找到该人才信息</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { useRoute } from "vue-router";
import { ArrowLeft, CircleCheck, WarningFilled, Connection, Document, Upload, Warning } from "@element-plus/icons-vue";
import FavoriteButton from "@/components/common/FavoriteButton.vue";
import DataState from "@/components/common/DataState.vue";
import { useTalentStore } from "@/stores/talents";
import { useHistoryStore } from "@/stores/history";
import { dataProvider } from "@/data";
import type { JobSummary, MatchExplanation, TalentDetail, TalentMatch } from "@/domain/types";

const route = useRoute();
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
const isPdfPreview = computed(() => resumePreviewContentType.value.includes("pdf"));
const isImagePreview = computed(() => resumePreviewContentType.value.startsWith("image/"));
const isTextPreview = computed(() => resumePreviewContentType.value.startsWith("text/"));
const isBrowserPreview = computed(() => isPdfPreview.value || isImagePreview.value || isTextPreview.value);

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
    resumePreviewVisible.value = true;
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "简历预览加载失败");
  }
}

function releaseResumePreview() {
  if (resumePreviewUrl.value) URL.revokeObjectURL(resumePreviewUrl.value);
  resumePreviewUrl.value = "";
  resumePreviewContentType.value = "";
}

async function openTalentDetails() {
  if (!talentDetails.value) await loadTalentDetails();
  if (talentDetails.value) talentDetailVisible.value = true;
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
.match-job-picker { gap: 8px; color: var(--text-muted); font-size: 12px; }
.match-job-picker .el-select { width: min(240px, 42vw); }
.match-job-picker :deep(.el-select-dropdown__item) small { display: block; color: var(--text-muted); font-size: 11px; }
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

.resume-preview-dialog { min-height: min(66vh, 680px); border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); overflow: hidden; background: var(--color-bg-muted); }
.resume-preview-dialog iframe { width: 100%; height: min(66vh, 680px); border: 0; }
.resume-preview-dialog img { display: block; max-width: 100%; max-height: min(66vh, 680px); margin: auto; }
.resume-text-preview { max-height: min(60vh, 600px); margin: 0; padding: 18px; overflow: auto; color: var(--text-secondary); font: 13px/1.8 var(--font-mono); white-space: pre-wrap; }
.talent-detail-dialog section { margin-top: 22px; }
.talent-detail-dialog h4 { margin-bottom: 10px; color: var(--text-primary); font-size: 14px; }
.detail-skill-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.detail-skill-list article { padding: 12px; border: 1px solid var(--color-border-light); border-radius: var(--radius-sm); background: var(--color-bg-muted); }
.detail-skill-list strong,.detail-skill-list span { display: block; }
.detail-skill-list span { margin-top: 3px; color: var(--text-muted); font-size: 12px; }
.detail-skill-list p { margin: 8px 0 0; color: var(--text-secondary); font-size: 12px; line-height: 1.6; }

@keyframes explanation-pulse { 70% { box-shadow: 0 0 0 7px rgba(79, 110, 246, 0); } 100% { box-shadow: 0 0 0 0 rgba(79, 110, 246, 0); } }
@media (max-width: 640px) { .match-skill-header { align-items: flex-start; flex-direction: column; } .match-job-picker .el-select { width: min(100%, 320px); } .detail-skill-list { grid-template-columns: 1fr; } }
</style>

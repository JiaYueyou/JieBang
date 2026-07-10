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
                <el-input v-model="jdForm.department" placeholder="如：研发中心 · 后台开发组" />
              </el-form-item>
              <el-form-item :label="jdMode === 'req' ? '核心技能要求' : '目标人才特征'">
                <el-input v-model="jdForm.skillsInput" type="textarea" :rows="3"
                  :placeholder="jdMode === 'req' ? '用逗号分隔技能，如：Java, Spring Boot, MySQL, Redis' : '描述目标人才特征，如：5年Java经验，精通微服务，有AI项目经验'" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="generating" style="width:100%;height:42px;" @click="generateJD">
                  <el-icon><MagicStick /></el-icon> 智能生成 JD
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </div>

        <!-- Right: Preview -->
        <div class="dash-card" style="display:flex;flex-direction:column;">
          <div class="dash-card-header">
            <span class="dash-card-title">JD 预览</span>
            <span class="dash-card-badge" v-if="generated">{{ generated.title }}</span>
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
                  <span class="jd-salary">{{ generated.salary_range }}</span>
                </div>
                <el-alert v-if="generationWarning" :title="generationWarning" type="warning" :closable="false" show-icon />
                <div class="jd-section"><h4>工作职责</h4><ul><li v-for="(r,i) in generated.responsibilities" :key="i">{{ r }}</li></ul></div>
                <div class="jd-section"><h4>任职要求</h4><ul><li v-for="(r,i) in generated.requirements" :key="i">{{ r }}</li></ul></div>
                <div class="jd-section"><h4>加分技能</h4><div style="display:flex;gap:6px;flex-wrap:wrap;"><el-tag v-for="s in generated.bonus_skills" :key="s" size="small" type="success">{{ s }}</el-tag></div></div>
              </div>
              <div class="jd-preview-actions">
                <el-button @click="copyJD"><el-icon><CopyDocument /></el-icon> 复制</el-button>
                <el-button @click="openDetail(generated, true)"><el-icon><Edit /></el-icon> 编辑草稿</el-button>
                <el-button type="primary" @click="publishFromPreview"><el-icon><Check /></el-icon> 发布岗位</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Published jobs -->
      <div class="dash-card jm-published" style="margin-top:16px;">
        <div class="dash-card-header">
          <span class="dash-card-title">已发布岗位</span>
          <span class="dash-card-badge">{{ publishedJobs.length }} 个</span>
        </div>
        <div class="dash-card-body" style="padding-top:0;">
          <el-table :data="publishedJobs" style="width:100%" size="default" stripe>
            <el-table-column prop="title" label="岗位名称" min-width="180" />
            <el-table-column prop="department" label="部门" width="140" align="center" />
            <el-table-column prop="headcount" label="招聘人数" width="90" align="center" />
            <el-table-column prop="status" label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'open' ? 'success' : 'info'" size="small">
                  {{ row.status === 'open' ? '招聘中' : '草稿' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="发布日期" width="120" align="center" />
            <el-table-column label="操作" width="190" align="center">
              <template #default="{ row }">
                <div class="table-actions">
                  <FavoriteButton type="job" :target-id="row.id" :title="row.title" compact />
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
        </div>
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
import { ref, reactive, computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { Plus, TrendCharts, MagicStick, Document, Search, CopyDocument, Check, ArrowDown, View, Edit, Delete } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import FavoriteButton from "@/components/common/FavoriteButton.vue";
import { useJobStore } from "@/stores/jobs";
import DataState from "@/components/common/DataState.vue";
import type { CapabilityChange, EmergingJob, GeneratedJDDraft, JobSummary } from "@/domain/types";

const tab = ref<"publish" | "insight">("publish");

// ── Tab A ──
const jdMode = ref<"req" | "profile">("req");
const generating = ref(false);
const generated = ref<JobSummary | null>(null);
const generationWarning = ref("");
const jdForm = reactive({ title: "", level: "", department: "", skillsInput: "" });
const store = useJobStore();
const router = useRouter();
const {
  jobs: publishedJobs,
  emergingJobs,
  capabilityChanges,
  insightQuality,
  insightLoading,
  insightError,
  loading,
  error,
} = storeToRefs(store);
onMounted(() => Promise.all([store.load(), store.loadInsights()]));

async function generateJD() {
  if (!jdForm.title) { ElMessage.warning("请先输入岗位名称"); return; }
  generating.value = true;
  try {
    const draft = await store.generateJD({
      mode: jdMode.value === "req" ? "requirements" : "profile",
      title: jdForm.title,
      level: jdForm.level || undefined,
      department: jdForm.department || undefined,
      skills_input: jdForm.skillsInput,
    });
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
  navigator.clipboard.writeText(
    `【${jd.title}】\n${jd.department} · ${jd.level} · ${jd.salary_range}\n\n工作职责：\n${jd.responsibilities.map((r:string,i:number)=>`${i+1}. ${r}`).join("\n")}\n\n任职要求：\n${jd.requirements.map((r:string,i:number)=>`${i+1}. ${r}`).join("\n")}\n\n加分技能：${jd.bonus_skills.join("、")}`
  );
  ElMessage.success("已复制到剪贴板");
}

async function publishFromPreview() {
  if (!generated.value) return;
  await store.create(toPublishPayload(generated.value));
  ElMessage.success("岗位发布成功");
  generated.value = null;
  generationWarning.value = "";
  jdForm.title = "";
  jdForm.skillsInput = "";
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
  jdMode.value = "req";
  jdForm.title = job.name;
  jdForm.level = "mid";
  jdForm.skillsInput = job.core_skills.join(", ");
  ElMessage.success("已填入岗位发布表单，请补充部门后生成 JD");
}

function prepareJDUpdate(change: CapabilityChange) {
  tab.value = "publish";
  jdMode.value = "req";
  jdForm.title = change.job;
  jdForm.skillsInput = [
    ...change.added.map((skill) => `新增：${skill}`),
    ...change.modified.map((skill) => `强化：${skill}`),
    ...change.removed.map((skill) => `待移除：${skill}`),
  ].join(", ");
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
</style>

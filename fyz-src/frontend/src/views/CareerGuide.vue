<template>
  <div>
    <DataState :loading="isAnalyzing" :error="error" @retry="startAnalyze" />
    <div class="dash-card cg-hero-card anim-fade-up" style="margin-bottom:16px;">
      <div class="dash-card-body" style="padding:20px 24px;">
        <div class="cg-primary-grid">
          <div class="cg-input-main">
            <label class="cg-label">输入员工当前技能</label>
            <el-input
              v-model="skillInput"
              type="textarea"
              :rows="3"
              placeholder="描述员工技能情况，如：Java 3年，Spring Boot，MySQL，Redis，略懂 Python 和 Docker，有 2 个后台项目经验"
              size="large"
              class="cg-textarea"
            />
            <div class="cg-hint">示例：Java 3年, Spring Boot, MySQL, Redis, 略懂 Python, 带过 5 人团队</div>
          </div>
          <div class="cg-upload-panel">
            <div class="cg-panel-title">补充输入</div>
            <div class="cg-panel-desc">可上传简历或项目经历，辅助完善技能画像。</div>
            <el-upload
              v-model:file-list="uploadFiles"
              :auto-upload="false"
              accept=".pdf,.docx,.md,.txt"
              :limit="3"
              drag
              class="cg-upload"
            >
              <el-icon style="font-size:22px;color:var(--color-brand);margin-bottom:4px;"><Upload /></el-icon>
              <div class="cg-upload-text">上传简历/经历</div>
              <div class="cg-upload-hint">PDF / Word / MD</div>
            </el-upload>
          </div>
        </div>

        <div class="cg-enterprise-panel">
          <div class="cg-enterprise-head">
            <div>
              <div class="cg-section-title">导入企业内部技术栈与需求岗位（可选）</div>
              <div class="cg-section-desc">不填写也可以直接分析；填写后会优先识别内部可转岗位与补课路径。</div>
            </div>
            <span class="cg-optional-badge">可选</span>
          </div>
          <div class="cg-enterprise-body">
            <div class="cg-ent-row">
              <div class="cg-ent-input">
                <label class="cg-sub-label">企业内部技术栈</label>
                <el-input v-model="enterpriseTech" type="textarea" :rows="3"
                  placeholder="如：Spring Cloud, K8s, 阿里云, DataWorks, 自研RPC框架"
                  class="cg-ent-textarea" />
              </div>
              <div class="cg-ent-input">
                <label class="cg-sub-label">内部需求岗位（逗号分隔）</label>
                <el-input v-model="enterpriseJobs" type="textarea" :rows="3"
                  placeholder="如：AI应用开发, 大数据工程师, DevOps"
                  class="cg-ent-textarea" />
              </div>
              <div class="cg-ent-upload">
                <label class="cg-sub-label">企业文件</label>
                <el-upload
                  v-model:file-list="entUploadFiles"
                  :auto-upload="false"
                  accept=".pdf,.docx,.md,.txt"
                  :limit="2"
                  drag
                  class="cg-upload"
                >
                  <el-icon style="font-size:20px;color:var(--color-brand);margin-bottom:3px;"><Upload /></el-icon>
                  <div class="cg-upload-text">上传文件</div>
                  <div class="cg-upload-hint">自动解析填入</div>
                </el-upload>
              </div>
            </div>
          </div>
        </div>

        <div class="cg-action-bar">
          <div class="cg-action-copy">
            <span class="cg-action-kicker">分析前检查</span>
            <span>员工技能或简历至少提供一项；企业技术栈和内部需求岗位为可选补充。</span>
          </div>
          <button class="cg-analyze-btn" :disabled="isAnalyzing" @click="startAnalyze">
            <el-icon><Search /></el-icon>
            <span>分析可转岗位</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Analyzing -->
    <div v-if="isAnalyzing" class="dash-card anim-fade-up" style="margin-bottom:16px;">
      <div class="dash-card-body" style="padding:32px;text-align:center;">
        <el-icon class="is-loading" style="font-size:28px;color:var(--color-brand);"><Loading /></el-icon>
        <p style="margin-top:12px;color:var(--text-muted);">AI 任务已创建，正在结合技能图谱分析；模型较忙时会自动返回模板方案。</p>
      </div>
    </div>

    <el-alert
      v-for="warning in displayWarnings" :key="warning" :title="warning"
      type="warning" :closable="false" show-icon style="margin-bottom:8px;"
    />

    <template v-if="results.length > 0 && !isAnalyzing">
      <div class="match-stats-row anim-fade-up">
        <div class="match-stat"><span class="ms-num">{{ results.length }}</span><span class="ms-label">可转岗位</span></div>
        <div class="match-stat"><span class="ms-num green">{{ highPotential.length }}</span><span class="ms-label">补课后 ≥85%</span></div>
        <div class="match-stat"><span class="ms-num blue">{{ avgGap }} 周</span><span class="ms-label">平均学习周期</span></div>
      </div>

      <div class="cg-results anim-fade-up anim-delay-1">
        <div class="dash-card cg-result-card" v-for="(item, i) in results" :key="i">
          <div class="dash-card-header">
            <div class="cg-result-top">
              <span class="cg-rank" :class="{ top: i < 2 }">{{ item.rank }}</span>
              <div class="cg-result-title">
                <span class="cg-job-name">{{ item.job }}</span>
                <span class="cg-rec">推荐度 {{ item.recommendScore }}%</span>
                <el-tag v-if="item.internal" size="small" type="warning" effect="dark">内部需求</el-tag>
              </div>
              <FavoriteButton type="job" :target-id="item.job_id" :title="item.job" compact />
              <div class="cg-match-delta">
                <div class="cg-match-chip before">{{ item.currentMatch }}%</div>
                <el-icon><ArrowRight /></el-icon>
                <div class="cg-match-chip after">{{ item.afterMatch }}%</div>
                <span class="cg-match-label">补课前 → 补课后</span>
              </div>
            </div>
          </div>
          <div class="dash-card-body" style="padding-top:12px;">
            <div class="cg-skill-block">
              <span class="cg-skill-label has">已具备</span>
              <div class="cg-skill-tags">
                <el-tag v-for="s in item.existing" :key="s" size="small" type="success" effect="plain">{{ s }}</el-tag>
              </div>
            </div>
            <div class="cg-skill-block">
              <span class="cg-skill-label miss">需补充</span>
              <div class="cg-learning-list">
                <div class="cg-learning-item" v-for="plan in item.learningPlan" :key="plan.skill">
                  <div class="cg-li-header">
                    <span class="cg-li-skill">{{ plan.skill }}</span>
                    <el-tag size="small" :type="plan.difficulty === 'easy' ? 'success' : plan.difficulty === 'medium' ? 'warning' : 'danger'">
                      {{ getDifficultyLabel(plan.difficulty) }} · {{ plan.time }}
                    </el-tag>
                  </div>
                  <div class="cg-li-resources">
                    <span v-for="r in plan.resources" :key="r">{{ r }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="cg-result-footer">
              <div class="cg-project">
                <el-icon><MagicStick /></el-icon>
                <span>建议实战项目：{{ item.suggestedProject }}</span>
              </div>
              <div class="cg-total-time">
                预计总周期：<strong>{{ item.totalTime }}</strong>
                <el-button text type="primary" size="small" style="margin-left:8px;">详细学习计划 →</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-if="!isAnalyzing && results.length === 0 && !hasSearched" class="dash-card anim-fade-up anim-delay-2">
      <div class="dash-card-body" style="padding:48px 20px;text-align:center;">
        <div class="placeholder-icon indigo" style="margin:0 auto 16px;"><el-icon><Guide /></el-icon></div>
        <h2 style="font-weight:600;margin-bottom:6px;">AI 转岗顾问</h2>
        <p style="color:var(--text-muted);max-width:420px;margin:0 auto 20px;">输入员工当前技能或上传简历，Agent 综合分析内部技术栈与市场岗位图谱，推荐最优转岗路径并生成个性化学习计划。</p>
        <div class="placeholder-tags" style="justify-content:center;">
          <span class="tag">技能图谱匹配</span><span class="tag">学习路径规划</span><span class="tag">内部需求岗位</span><span class="tag">周期预估</span>
        </div>
      </div>
    </div>

    <div v-if="hasSearched && results.length === 0 && !isAnalyzing" class="jm-empty" style="padding:60px 20px;">
      <el-icon style="font-size:40px;color:var(--color-border);"><Search /></el-icon>
      <p style="margin-top:12px;">暂无可转岗位推荐，请尝试输入更详细的技能描述</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { Search, ArrowRight, Loading, MagicStick, Guide, Upload } from "@element-plus/icons-vue";
import type { UploadFile } from "element-plus";
import { ElMessage } from "element-plus";
import FavoriteButton from "@/components/common/FavoriteButton.vue";
import DataState from "@/components/common/DataState.vue";
import { useCareerStore } from "@/stores/career";

const skillInput = ref("");
const enterpriseTech = ref("");
const enterpriseJobs = ref("");
const hasSearched = ref(false);
const store = useCareerStore();
const { data: results, loading: isAnalyzing, error, warnings, agentStatus } = storeToRefs(store);
const uploadFiles = ref<UploadFile[]>([]);
const entUploadFiles = ref<UploadFile[]>([]);

const highPotential = computed(() => results.value.filter(r => r.afterMatch >= 85));
const displayWarnings = computed(() => {
  const messages = warnings.value.map((item) => item.trim()).filter(Boolean);
  if (agentStatus.value === "degraded" && messages.length === 0) {
    messages.push("AI 增强暂未完成，已展示可继续使用的规则学习路径。");
  }
  return [...new Set(messages)];
});
const avgGap = computed(() => {
  if (results.value.length === 0) return 0;
  const total = results.value.reduce((sum: number, r: any) => {
    const weeks = parseInt(r.totalTime) || 0;
    return sum + weeks;
  }, 0);
  return Math.round(total / results.value.length);
});

function getDifficultyLabel(difficulty: string) {
  const labels: Record<string, string> = {
    easy: "入门",
    medium: "进阶",
    hard: "深入",
  };
  return labels[difficulty] || difficulty;
}

async function startAnalyze() {
  const resumeFiles = uploadFiles.value.flatMap((item) => item.raw ? [item.raw] : []);
  if (!skillInput.value.trim() && resumeFiles.length === 0) {
    ElMessage.warning("请填写员工技能或至少上传一份简历");
    return;
  }
  if (skillInput.value.length > 6000 || enterpriseTech.value.length > 6000) {
    ElMessage.warning("技能与企业技术栈文本均不能超过 6000 字符");
    return;
  }
  hasSearched.value = true;
  await store.analyze({
    skillText: skillInput.value,
    enterpriseTech: enterpriseTech.value,
    enterpriseJobs: enterpriseJobs.value.split(",").map((item) => item.trim()).filter(Boolean),
    resumeFiles,
    enterpriseFiles: entUploadFiles.value.flatMap((item) => item.raw ? [item.raw] : []),
  });
}
</script>

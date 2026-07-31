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
        <p>{{ talent.position }} · 匹配度 {{ talent.score }}%</p>
        <div class="md-meta">
          <el-tag size="small">{{ talent.experience }}</el-tag>
          <el-tag size="small" type="info">{{ talent.education }}</el-tag>
          <el-tag v-if="talent.isNew" size="small" type="danger">NEW</el-tag>
        </div>
      </div>
      <FavoriteButton type="resume" :target-id="talent.id" :title="talent.name" show-label />
      <div class="md-score-lg">
        <div class="score-ring-lg" :style="{ '--pct': `${talent.score}%` }"><span>{{ talent.score }}%</span></div>
        <div class="md-score-label">综合匹配度</div>
      </div>
    </div>

    <!-- Content grid -->
    <div class="md-grid">
      <!-- Left: Skills & gap -->
      <div class="dash-card">
        <div class="dash-card-header"><span class="dash-card-title">技能分析</span></div>
        <div class="dash-card-body">
          <div class="md-section">
            <h4><el-icon style="color:var(--color-success);"><CircleCheck /></el-icon> 已匹配技能</h4>
            <div class="md-tags">
              <el-tag v-for="s in talent.matched" :key="s" type="success" effect="plain">{{ s }}</el-tag>
            </div>
          </div>
          <div class="md-section">
            <h4><el-icon style="color:var(--color-danger);"><WarningFilled /></el-icon> 待补充技能</h4>
            <div class="md-tags">
              <el-tag v-for="s in talent.missing" :key="s" type="danger" effect="plain">{{ s }}</el-tag>
            </div>
          </div>
          <div class="md-section">
            <h4><el-icon style="color:var(--color-brand);"><Connection /></el-icon> 匹配岗位</h4>
            <div class="md-tags">
              <el-tag v-for="j in talent.targetJobs" :key="j" type="primary" effect="plain">{{ j }}</el-tag>
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
              <el-button type="primary" size="small" style="margin-left:auto;" @click="downloadResume">下载</el-button>
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
        <el-empty v-if="!explanation" description="基于已落库的匹配证据生成可审计解释" :image-size="72" />
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
      <div class="dash-card-header"><span class="dash-card-title">基本信息</span></div>
      <div class="dash-card-body">
        <el-descriptions :column="4" border size="default">
          <el-descriptions-item label="姓名">{{ talent.name }}</el-descriptions-item>
          <el-descriptions-item label="当前/期望岗位">{{ talent.position }}</el-descriptions-item>
          <el-descriptions-item label="工作年限">{{ talent.experience }}</el-descriptions-item>
          <el-descriptions-item label="学历">{{ talent.education }}</el-descriptions-item>
          <el-descriptions-item label="匹配度">{{ talent.score }}%</el-descriptions-item>
          <el-descriptions-item label="匹配岗位数">{{ talent.targetJobs?.length || 1 }}</el-descriptions-item>
          <el-descriptions-item label="已具备技能">{{ talent.matched.length }} 项</el-descriptions-item>
          <el-descriptions-item label="待补充技能">{{ talent.missing.length }} 项</el-descriptions-item>
        </el-descriptions>
      </div>
    </div>
  </div>

  <div v-else-if="!loading" class="jm-empty jm-empty-fill">
    <el-icon style="font-size:40px;color:var(--color-border);"><Warning /></el-icon>
    <p style="margin-top:12px;">未找到该人才信息</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { storeToRefs } from "pinia";
import { useRoute } from "vue-router";
import { ArrowLeft, CircleCheck, WarningFilled, Connection, Document, Upload, Warning } from "@element-plus/icons-vue";
import FavoriteButton from "@/components/common/FavoriteButton.vue";
import DataState from "@/components/common/DataState.vue";
import { useTalentStore } from "@/stores/talents";
import { useHistoryStore } from "@/stores/history";
import { dataProvider } from "@/data";
import type { MatchExplanation } from "@/domain/types";

const route = useRoute();
const store = useTalentStore();
const historyStore = useHistoryStore();
const { talents, loading, error } = storeToRefs(store);
const explanation = ref<MatchExplanation | null>(null);
const explaining = ref(false);
onMounted(async () => {
  await store.load();
  if (!talent.value) return;
  try {
    await historyStore.record({
      type: "match",
      targetId: talent.value.match_id,
      title: `${talent.value.name}的匹配报告`,
      description: `${talent.value.position} · 综合匹配度 ${talent.value.score}%`,
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

async function downloadResume() {
  if (!talent.value?.resumeFile) return;
  await dataProvider.talents.download(Number(talent.value.resume_id), talent.value.resumeFile);
}

async function generateExplanation() {
  if (!talent.value) return;
  explaining.value = true;
  try {
    explanation.value = await dataProvider.talents.explain(Number(talent.value.match_id));
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "匹配解释生成失败");
  } finally { explaining.value = false; }
}
</script>

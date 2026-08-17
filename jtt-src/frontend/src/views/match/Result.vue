<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { MatchResult } from '@/types'
import { mockMatchResults } from '@/mock/data/match'
import { pageData } from '@/stores/pageContext'
import { useMatchStore } from '@/stores/match'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const matchStore = useMatchStore()
const result = ref<MatchResult | null>(null)
const optimizing = ref(false)

onMounted(() => {
  const key = `${route.params.resumeId}_${route.params.positionId}`
  result.value = mockMatchResults[key] ?? mockMatchResults['r-1_ep-1']!
})
watch(result, (r) => { pageData.match = r }, { immediate: true })
onUnmounted(() => {
  if (pageData.match?.id === result.value?.id) pageData.match = null
})

const getScoreColor = (score: number) => {
  if (score >= 85) return '#16a34a'
  if (score >= 70) return '#4f6ef6'
  return '#f59e0b'
}

const fetchTailorSuggestions = async () => {
  if (!result.value || optimizing.value) return
  optimizing.value = true
  try {
    const positionCtx = {
      name: result.value.positionName,
      missingSkills: result.value.gapAnalysis.missingSkills.map((s: any) => s.name),
      weakSkills: result.value.gapAnalysis.weakSkills.map((s: any) => s.name),
      matchSkills: result.value.gapAnalysis.matchSkills.map((s: any) => s.name),
    }
    const fetched = await matchStore.fetchAiSuggestions(
      String(result.value.resumeId), positionCtx
    )
    const aiSuggestions = fetched.map((s: any) => ({ ...s, id: `ai-${s.id}` }))
    result.value.suggestions = [...aiSuggestions, ...result.value.suggestions.filter(
      (s: any) => !s.id.startsWith('ai-')
    )]
    ElMessage.success(`AI 已生成 ${aiSuggestions.length} 条优化建议`)
  } catch {
    ElMessage.error('AI 优化请求失败，请稍后重试')
  } finally {
    optimizing.value = false
  }
}
</script>

<template>
  <div class="result-page" v-if="result">
    <div class="score-hero">
      <div class="score-circle" :style="{ borderColor: getScoreColor(result.totalScore) }">
        <span class="score-num">{{ result.totalScore }}</span>
        <span class="score-label">匹配分</span>
      </div>
      <div class="score-info">
        <h3>{{ result.resumeName }} → {{ result.positionName }}</h3>
        <p>匹配日期：{{ result.matchDate }}</p>
        <div class="score-actions">
          <el-button type="primary" :loading="optimizing" @click="fetchTailorSuggestions">
            {{ optimizing ? 'AI 分析中...' : '一键优化简历' }}
          </el-button>
          <el-button @click="router.push(`/resume/editor/${result.resumeId}`)">手动编辑</el-button>
        </div>
      </div>
    </div>

    <div class="result-body">
      <!-- [P2] 匹配推理链 —— AI 推理过程可解释 -->
      <el-card class="res-card" v-if="result.reasoningChain?.length">
        <template #header><span class="card-title">🧠 匹配推理链</span></template>
        <div class="reasoning-timeline">
          <div v-for="(step, i) in result.reasoningChain" :key="i" class="reasoning-step">
            <div class="rs-icon">{{ step.icon }}</div>
            <div class="rs-content">
              <div class="rs-title">{{ step.title }}</div>
              <div class="rs-detail">{{ step.detail }}</div>
            </div>
          </div>
        </div>
      </el-card>

      <el-card class="res-card">
        <template #header><span class="card-title">差距分析</span></template>
        <div class="gap-section">
          <h5 class="gap-subtitle">缺失技能</h5>
          <div class="gap-tags">
            <el-tag v-for="sk in result.gapAnalysis.missingSkills" :key="sk.id" type="danger" effect="plain">{{ sk.name }}</el-tag>
            <span v-if="result.gapAnalysis.missingSkills.length === 0" class="no-data">无</span>
          </div>
        </div>
        <div class="gap-section">
          <h5 class="gap-subtitle">需加强技能</h5>
          <div class="gap-tags">
            <el-tag v-for="sk in result.gapAnalysis.weakSkills" :key="sk.id" type="warning" effect="plain">{{ sk.name }}</el-tag>
            <span v-if="result.gapAnalysis.weakSkills.length === 0" class="no-data">无</span>
          </div>
        </div>
        <div class="gap-section">
          <h5 class="gap-subtitle">匹配技能</h5>
          <div class="gap-tags">
            <el-tag v-for="sk in result.gapAnalysis.matchSkills" :key="sk.id" type="success" effect="plain">{{ sk.name }}</el-tag>
          </div>
        </div>
      </el-card>

      <el-card class="res-card" v-if="result.suggestions.length > 0">
        <template #header><span class="card-title">智能优化建议</span></template>
        <div v-for="sg in result.suggestions" :key="sg.id" class="suggestion-item">
          <div class="sg-header">
            <span class="sg-section-tag">{{ sg.section }}</span>
            <el-tag :type="sg.changeType === 'small' ? 'success' : 'warning'" size="small" effect="plain">
              {{ sg.changeType === 'small' ? '小改' : '大改' }}
            </el-tag>
          </div>
          <p class="sg-reason">{{ sg.reason }}</p>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.result-page { max-width: 900px; margin: 0 auto; }

.score-hero {
  display: flex;
  align-items: center;
  gap: 32px;
  background: #fff;
  padding: 32px;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin-bottom: 24px;
}

.score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  border: 6px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.score-num { font-size: 36px; font-weight: 800; color: var(--ink); }
.score-label { font-size: 13px; color: var(--muted); }

.score-info h3 { font-size: 18px; font-weight: 700; margin-bottom: 6px; }
.score-info p { font-size: 13px; color: var(--muted); margin-bottom: 14px; }
.score-actions { display: flex; gap: 8px; }

.result-body { display: flex; flex-direction: column; gap: 16px; }

.res-card { margin-bottom: 0; }
.card-title { font-size: 15px; font-weight: 600; }

.gap-section { margin-bottom: 16px; }
.gap-subtitle { font-size: 13px; font-weight: 600; color: var(--ink); margin-bottom: 8px; }
.gap-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.no-data { font-size: 13px; color: var(--weak); }

.suggestion-item { padding: 12px 0; border-bottom: 1px solid var(--hairline); }
.suggestion-item:last-child { border-bottom: none; }
.sg-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.sg-section-tag { font-size: 12px; padding: 2px 8px; background: var(--canvas); border-radius: 4px; color: var(--muted); }
.sg-reason { font-size: 13px; color: var(--ink); line-height: 1.5; }

/* [P2] 推理链时间线 */
.reasoning-timeline { padding: 4px 0; }
.reasoning-step { display: flex; gap: 12px; position: relative; padding-bottom: 16px; }
.reasoning-step:last-child { padding-bottom: 0; }
.reasoning-step:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 13px; top: 30px; bottom: 0;
  width: 2px;
  background: var(--hairline);
}
.rs-icon {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--brand-light);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
  z-index: 1;
}
.rs-content { flex: 1; min-width: 0; padding-top: 3px; }
.rs-title { font-size: 13px; font-weight: 600; color: var(--ink); margin-bottom: 2px; }
.rs-detail { font-size: 12px; color: var(--muted); line-height: 1.6; }
</style>

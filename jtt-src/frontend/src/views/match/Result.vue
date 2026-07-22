<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { MatchResult } from '@/types'
import { mockMatchResults } from '@/mock/data/match'
import { pageData } from '@/stores/pageContext'

const route = useRoute()
const router = useRouter()
const result = ref<MatchResult | null>(null)

onMounted(() => {
  const key = `${route.params.resumeId}_${route.params.positionId}`
  result.value = mockMatchResults[key] ?? mockMatchResults['r-1_ep-1']!
})
// Share match result with AI assistant
watch(result, (r) => { pageData.match = r }, { immediate: true })
onUnmounted(() => {
  if (pageData.match?.id === result.value?.id) pageData.match = null
})

const getScoreColor = (score: number) => {
  if (score >= 80) return 'var(--success)'
  if (score >= 50) return 'var(--warning)'
  return 'var(--danger)'
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
          <el-button type="primary" @click="router.push(`/resume/tailor/${result.resumeId}/${result.positionId}`)">一键优化简历</el-button>
          <el-button @click="router.push(`/resume/editor/${result.resumeId}`)">手动编辑</el-button>
        </div>
      </div>
    </div>

    <div class="result-body">
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
</style>

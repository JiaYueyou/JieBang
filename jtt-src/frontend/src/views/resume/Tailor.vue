<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { ImprovementSuggestion, JobPosition } from '@/types'
import { mockTailorSuggestions } from '@/mock/data/tailor'
import { mockPositions } from '@/mock/data/positions'

const route = useRoute()
const suggestions = ref<ImprovementSuggestion[]>([])
const position = ref<JobPosition | null>(null)
const matchScore = ref(68)

onMounted(() => {
  const resumeId = route.params.resumeId as string
  const positionId = route.params.positionId as string
  const key = `${resumeId}_${positionId}`
  suggestions.value = JSON.parse(JSON.stringify(mockTailorSuggestions[key] || mockTailorSuggestions['r-1_ep-1'] || []))
  position.value = mockPositions.find((p) => p.id === positionId) || null
})

const toggleSuggestion = (sg: ImprovementSuggestion) => {
  sg.accepted = !sg.accepted
}

const applyAll = () => {
  const count = suggestions.value.filter((s) => s.accepted).length
  if (count === 0) {
    ElMessage.warning('请至少选择一条建议')
    return
  }
  ElMessage.success(`已将 ${count} 条优化应用到简历，已另存为新版本`)
}

const rejectAll = () => {
  suggestions.value.forEach((s) => (s.accepted = false))
}
</script>

<template>
  <div class="tailor-page">
    <div class="tailor-header">
      <h3>AI 辅助简历优化</h3>
      <div class="tailor-meta">
        <span>匹配度 {{ matchScore }}%</span>
        <el-tag v-if="matchScore >= 40" type="success" size="small">可优化</el-tag>
        <el-tag v-else type="danger" size="small">匹配度过低，不建议优化</el-tag>
      </div>
    </div>

    <div v-if="matchScore < 40" class="blocked">
      <el-empty description="匹配度过低（< 40%），简历与岗位领域差异较大，不建议修改">
        <el-button type="primary">返回匹配结果</el-button>
      </el-empty>
    </div>

    <div v-else class="tailor-body">
      <!-- Left: suggestions -->
      <div class="suggestions-panel">
        <div class="panel-head">
          <span>优化建议 ({{ suggestions.length }}条)</span>
          <div>
            <el-button text size="small" type="danger" @click="rejectAll">全部拒绝</el-button>
            <el-button text size="small" type="success" @click="applyAll">全部接受并保存</el-button>
          </div>
        </div>

        <div class="suggestion-list">
          <div
            v-for="sg in suggestions"
            :key="sg.id"
            class="sg-card"
            :class="{ accepted: sg.accepted }"
          >
            <div class="sg-header">
              <span class="sg-section">{{ sg.section === 'skills' ? '技能' : sg.section === 'workExperience' ? '工作经历' : sg.section === 'selfEvaluation' ? '自我评价' : sg.section }}</span>
              <el-tag :type="sg.changeType === 'small' ? 'success' : 'warning'" size="small" effect="plain">
                {{ sg.changeType === 'small' ? '小改' : '大改' }}
              </el-tag>
            </div>
            <p class="sg-reason">{{ sg.reason }}</p>
            <div class="sg-diff">
              <div class="diff-line removed">
                <span class="diff-prefix">-</span>
                <span>{{ sg.original }}</span>
              </div>
              <div class="diff-line added">
                <span class="diff-prefix">+</span>
                <span>{{ sg.suggested }}</span>
              </div>
            </div>
            <div class="sg-footer">
              <el-button
                :type="sg.accepted ? 'success' : 'default'"
                :plain="!sg.accepted"
                size="small"
                @click="toggleSuggestion(sg)"
              >
                {{ sg.accepted ? '已接受' : '接受' }}
              </el-button>
              <el-button v-if="!sg.accepted" text size="small" type="danger">拒绝</el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: position reference -->
      <div class="reference-panel" v-if="position">
        <div class="ref-card">
          <h4>{{ position.name }}</h4>
          <div class="ref-section">
            <span class="ref-label">必备技能</span>
            <div class="ref-chips">
              <span v-for="sk in position.requiredSkills" :key="sk.id" class="ref-chip required">{{ sk.name }}</span>
            </div>
          </div>
          <div class="ref-section">
            <span class="ref-label">加分技能</span>
            <div class="ref-chips">
              <span v-for="sk in position.preferredSkills" :key="sk.id" class="ref-chip preferred">{{ sk.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tailor-page { max-width: 1100px; margin: 0 auto; }

.tailor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  padding: 16px 24px;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin-bottom: 20px;
}

.tailor-header h3 { font-size: 18px; font-weight: 700; }
.tailor-meta { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--muted); }

.blocked { padding: 60px 0; }

.tailor-body {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 20px;
}

.suggestions-panel {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--hairline);
  font-size: 14px;
  font-weight: 600;
}

.suggestion-list { padding: 16px; }

.sg-card {
  padding: 16px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  margin-bottom: 12px;
  transition: all 0.2s;
}

.sg-card.accepted {
  border-color: var(--brand);
  background: var(--brand-light);
}

.sg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.sg-section { font-size: 13px; font-weight: 600; color: var(--ink); }
.sg-reason { font-size: 12px; color: var(--muted); margin-bottom: 10px; }

.sg-diff {
  background: #fafafa;
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 12px;
}

.diff-line {
  font-size: 13px;
  line-height: 1.5;
  padding: 2px 0;
}

.diff-line.removed {
  color: var(--danger);
  text-decoration: line-through;
}

.diff-line.added {
  color: var(--brand);
}

.diff-prefix {
  display: inline-block;
  width: 16px;
  font-weight: 700;
}

.sg-footer {
  display: flex;
  align-items: center;
  gap: 8px;
}

.reference-panel { position: sticky; top: 20px; }

.ref-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 20px;
}

.ref-card h4 { font-size: 16px; font-weight: 700; margin-bottom: 16px; }

.ref-section { margin-bottom: 14px; }

.ref-label { font-size: 12px; font-weight: 600; color: var(--muted); display: block; margin-bottom: 8px; }

.ref-chips { display: flex; flex-wrap: wrap; gap: 6px; }

.ref-chip {
  padding: 5px 10px;
  border-radius: 14px;
  font-size: 12px;
  font-weight: 500;
}

.ref-chip.required { background: var(--brand-light); color: var(--brand); }
.ref-chip.preferred { background: var(--canvas); color: var(--muted); border: 1px solid var(--hairline); }
</style>

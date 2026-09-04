<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { ImprovementSuggestion, JobPosition } from '@/types'
import { tailorApi } from '@/api/tailor'
import { positionsApi } from '@/api/positions'
import { matchApi } from '@/api/match'
import { useMatchStore } from '@/stores/match'

const route = useRoute()
const matchStore = useMatchStore()
const suggestions = ref<ImprovementSuggestion[]>([])
const position = ref<JobPosition | null>(null)
const matchScore = ref(68)
const loading = ref(true)

onMounted(async () => {
  const resumeId = route.params.resumeId as string
  const positionId = route.params.positionId as string
  try {
    const [posRes, matchRes]: any = await Promise.all([
      positionsApi.getDetail(positionId),
      matchApi.getResult(resumeId, positionId),
    ])
    position.value = posRes.data || null
    matchScore.value = matchRes.data?.totalScore ?? 68

    // 从岗位参考构造上下文，AI 生成向岗位靠齐的优化建议
    if (position.value) {
      const positionCtx = {
        name: position.value.name,
        requiredSkills: position.value.requiredSkills.map((s: any) => s.name),
        preferredSkills: position.value.preferredSkills.map((s: any) => s.name),
      }
      suggestions.value = await matchStore.fetchAiSuggestions(resumeId, positionCtx) ?? []
    }
  } catch {
    ElMessage.warning('数据加载失败，使用默认数据')
  } finally {
    loading.value = false
  }
})

const toggleSuggestion = (sg: ImprovementSuggestion) => {
  sg.accepted = !sg.accepted
}

const applyAll = async () => {
  const accepted = suggestions.value.filter((s) => s.accepted)
  if (accepted.length === 0) {
    ElMessage.warning('请至少选择一条建议')
    return
  }
  try {
    await tailorApi.applyAll(route.params.resumeId as string, accepted)
    ElMessage.success(`已将 ${accepted.length} 条优化应用到简历，已另存为新版本`)
  } catch {
    ElMessage.error('应用失败，请稍后重试')
  }
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

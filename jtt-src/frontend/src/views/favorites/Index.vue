<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useFavoritesStore } from '@/stores/favorites'

const router = useRouter()
const favoritesStore = useFavoritesStore()
const activeTab = ref('position')

onMounted(() => favoritesStore.fetchAll())

const handleRemove = async (favId: number, title: string) => {
  try {
    await ElMessageBox.confirm(`确定移除收藏「${title}」吗？`, '提示', { type: 'warning' })
    await favoritesStore.remove(favId)
    ElMessage.success('已移除收藏')
  } catch { /* 取消 */ }
}

const goPosition = (id: string) => router.push(`/positions/${id}`)
const goLearning = () => router.push('/learning')

const resourceTypeLabels: Record<string, string> = {
  course: '课程', book: '书籍', article: '文章', project: '项目', video: '视频',
}
</script>

<template>
  <div class="favorites-page">
    <div class="page-header">
      <div>
        <h2>我的收藏</h2>
        <p class="sub">共 {{ favoritesStore.totalCount }} 项收藏</p>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="fav-tabs">
      <!-- Tab 1: 岗位 -->
      <el-tab-pane name="position">
        <template #label>
          <span>岗位 <el-badge :value="favoritesStore.positionCount" :hidden="favoritesStore.positionCount === 0" /></span>
        </template>
        <div v-if="favoritesStore.positionFavs.length > 0" class="fav-grid">
          <div
            v-for="fav in favoritesStore.positionFavs"
            :key="fav.id"
            class="fav-card"
            @click="goPosition(fav.item_id)"
          >
            <div class="fav-card-body">
              <div class="fav-card-header">
                <h4>{{ fav.title }}</h4>
                <el-tag
                  v-if="fav.metadata?.category"
                  size="small"
                  :type="fav.metadata.category === 'new' ? 'success' : ''"
                >
                  {{ fav.metadata.category === 'new' ? '新兴' : '既有' }}
                </el-tag>
              </div>
              <p v-if="fav.summary" class="fav-summary">{{ fav.summary }}</p>
              <div v-if="fav.metadata?.salary_range" class="fav-salary">{{ fav.metadata.salary_range }}</div>
              <div v-if="fav.metadata?.skills?.length" class="fav-skills">
                <el-tag v-for="sk in fav.metadata.skills.slice(0, 5)" :key="sk" size="small" round>{{ sk }}</el-tag>
                <span v-if="fav.metadata.skills.length > 5" class="more">+{{ fav.metadata.skills.length - 5 }}</span>
              </div>
            </div>
            <div class="fav-card-actions" @click.stop>
              <el-button text size="small" type="danger" @click="handleRemove(fav.id, fav.title)">取消收藏</el-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-tab">
          <el-empty description="暂无收藏岗位">
            <el-button type="primary" @click="router.push('/positions')">去探索岗位</el-button>
          </el-empty>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 学习资料 -->
      <el-tab-pane name="learning_resource">
        <template #label>
          <span>学习资料 <el-badge :value="favoritesStore.resourceCount" :hidden="favoritesStore.resourceCount === 0" /></span>
        </template>
        <div v-if="favoritesStore.resourceFavs.length > 0" class="fav-grid">
          <div
            v-for="fav in favoritesStore.resourceFavs"
            :key="fav.id"
            class="fav-card"
          >
            <div class="fav-card-body">
              <div class="fav-card-header">
                <h4>{{ fav.title }}</h4>
                <el-tag size="small" type="success">
                  {{ resourceTypeLabels[fav.metadata?.type] || fav.metadata?.type || '资料' }}
                </el-tag>
              </div>
              <p v-if="fav.summary" class="fav-summary">{{ fav.summary }}</p>
              <div class="fav-meta">
                <span v-if="fav.metadata?.platform">平台: {{ fav.metadata.platform }}</span>
              </div>
              <div v-if="fav.metadata?.url" class="fav-link">
                <a :href="fav.metadata.url" target="_blank" @click.stop>查看资源</a>
              </div>
            </div>
            <div class="fav-card-actions" @click.stop>
              <el-button text size="small" type="danger" @click="handleRemove(fav.id, fav.title)">取消收藏</el-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-tab">
          <el-empty description="暂无收藏的学习资料">
            <el-button type="primary" @click="goLearning">去学习路径发现资料</el-button>
          </el-empty>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 错题 -->
      <el-tab-pane name="quiz_error">
        <template #label>
          <span>错题 <el-badge :value="favoritesStore.errorCount" :hidden="favoritesStore.errorCount === 0" /></span>
        </template>
        <div v-if="favoritesStore.errorFavs.length > 0" class="error-list">
          <div
            v-for="fav in favoritesStore.errorFavs"
            :key="fav.id"
            class="error-card"
          >
            <div class="error-header">
              <h4>{{ fav.metadata?.question || fav.title }}</h4>
              <el-button text size="small" type="danger" @click="handleRemove(fav.id, fav.title)">移除</el-button>
            </div>
            <div class="error-body">
              <div class="error-answer wrong">
                <span class="error-label">你的答案</span>
                <span>{{ fav.metadata?.user_answer || '未作答' }}</span>
              </div>
              <div class="error-answer correct">
                <span class="error-label">正确答案</span>
                <span>{{ fav.metadata?.correct_answer || '-' }}</span>
              </div>
            </div>
            <div v-if="fav.metadata?.explanation" class="error-explanation">
              {{ fav.metadata.explanation }}
            </div>
          </div>
        </div>
        <div v-else class="empty-tab">
          <el-empty description="暂无错题记录">
            <el-button type="primary" @click="goLearning">去学习测试</el-button>
          </el-empty>
        </div>
      </el-tab-pane>

      <!-- Tab 4: AI知识点 -->
      <el-tab-pane name="knowledge_point">
        <template #label>
          <span>AI知识点 <el-badge :value="favoritesStore.knowledgeCount" :hidden="favoritesStore.knowledgeCount === 0" /></span>
        </template>
        <div v-if="favoritesStore.knowledgeFavs.length > 0" class="fav-grid">
          <div
            v-for="fav in favoritesStore.knowledgeFavs"
            :key="fav.id"
            class="fav-card"
          >
            <div class="fav-card-body">
              <div class="fav-card-header">
                <h4>{{ fav.title }}</h4>
                <el-tag size="small" type="warning">AI生成</el-tag>
              </div>
              <p v-if="fav.summary" class="fav-summary">{{ fav.summary }}</p>
              <div v-if="fav.metadata?.related_skills?.length" class="fav-skills">
                <el-tag v-for="sk in fav.metadata.related_skills" :key="sk" size="small" round>{{ sk }}</el-tag>
              </div>
            </div>
            <div class="fav-card-actions" @click.stop>
              <el-button text size="small" type="danger" @click="handleRemove(fav.id, fav.title)">取消收藏</el-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-tab">
          <el-empty description="AI生成知识点即将上线">
            <p class="coming-soon-hint">AI 智能体功能即将上线，届时可自动生成并收藏知识点</p>
          </el-empty>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.favorites-page { max-width: 1200px; margin: 0 auto; }

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.page-header h2 { font-size: 20px; font-weight: 700; }
.sub { font-size: 13px; color: var(--muted); margin-top: 4px; }

.fav-tabs {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 0 20px 20px;
}

.fav-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 16px;
}

.fav-card {
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.15s;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.fav-card:hover { box-shadow: var(--shadow-hover); }

.fav-card-body { padding: 16px 20px; flex: 1; }

.fav-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.fav-card-header h4 { font-size: 15px; font-weight: 600; }

.fav-summary {
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fav-salary {
  font-size: 13px;
  font-weight: 600;
  color: var(--danger);
  margin-bottom: 6px;
}

.fav-skills { display: flex; gap: 4px; flex-wrap: wrap; }
.fav-skills .more { font-size: 12px; color: var(--muted); line-height: 24px; }

.fav-meta { font-size: 12px; color: var(--weak); margin-top: 8px; }

.fav-link { margin-top: 8px; }
.fav-link a { font-size: 13px; color: var(--brand); text-decoration: none; }
.fav-link a:hover { text-decoration: underline; }

.fav-card-actions {
  border-top: 1px solid var(--hairline);
  padding: 8px 12px;
  display: flex;
  justify-content: flex-end;
}

/* Error cards */
.error-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.error-card {
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  padding: 20px;
}

.error-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}
.error-header h4 { font-size: 14px; font-weight: 600; flex: 1; line-height: 1.5; }

.error-body {
  display: flex;
  gap: 20px;
  margin-bottom: 10px;
}

.error-answer {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
}
.error-answer.wrong { color: #ef4444; }
.error-answer.correct { color: #22c55e; }

.error-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.error-explanation {
  font-size: 12px;
  color: #a16207;
  background: #fefce8;
  padding: 8px 12px;
  border-radius: 8px;
  line-height: 1.5;
}

/* Empty states */
.empty-tab { padding: 60px 0; }

.coming-soon-hint {
  font-size: 13px;
  color: var(--muted);
  margin-top: 8px;
}
</style>

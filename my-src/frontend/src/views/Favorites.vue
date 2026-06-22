<template>
  <div class="favorites-page">
    <DataState :loading="loading" :error="error" @retry="store.refresh()" />
    <div class="favorites-workbench anim-fade-up">
      <div class="favorites-tabs" role="tablist" aria-label="收藏类型">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          class="favorites-tab"
          :class="{ active: activeType === tab.value }"
          type="button"
          role="tab"
          :aria-selected="activeType === tab.value"
          @click="activeType = tab.value"
        >
          <el-icon><component :is="tab.icon" /></el-icon>
          {{ tab.label }}
          <span>{{ tab.count }}</span>
        </button>
      </div>

      <div class="favorites-tools">
        <div class="favorites-search">
          <el-icon><Search /></el-icon>
          <input v-model.trim="keyword" type="search" placeholder="搜索岗位、候选人或技能…" />
          <button v-if="keyword" type="button" title="清除搜索" @click="keyword = ''">
            <el-icon><CircleClose /></el-icon>
          </button>
          <kbd>⌘ K</kbd>
        </div>

        <el-select v-model="sortBy" class="favorites-sort" aria-label="排序方式">
          <template #prefix><el-icon><Sort /></el-icon></template>
          <el-option label="最近收藏" value="recent" />
          <el-option label="匹配度优先" value="match" />
          <el-option label="名称排序" value="name" />
        </el-select>

        <div class="view-switch" aria-label="视图切换">
          <button type="button" :class="{ active: viewMode === 'grid' }" title="卡片视图" @click="viewMode = 'grid'">
            <el-icon><Grid /></el-icon>
          </button>
          <button type="button" :class="{ active: viewMode === 'list' }" title="列表视图" @click="viewMode = 'list'">
            <el-icon><List /></el-icon>
          </button>
        </div>
      </div>
    </div>

    <div v-if="selectedIds.length" class="bulk-bar anim-scale-in">
      <div>
        <span class="bulk-check"><el-icon><Check /></el-icon></span>
        已选择 <strong>{{ selectedIds.length }}</strong> 项
      </div>
      <div class="bulk-actions">
        <button type="button" @click="selectedIds = []">取消选择</button>
        <button class="danger" type="button" @click="removeSelected">
          <el-icon><Delete /></el-icon>
          取消收藏
        </button>
      </div>
    </div>

    <div v-if="filteredFavorites.length" class="favorites-content anim-fade-up anim-delay-2">
      <div class="content-meta">
        <span>共 {{ filteredFavorites.length }} 项结果</span>
        <button type="button" @click="toggleSelectAll">
          {{ allVisibleSelected ? "取消全选" : "选择当前结果" }}
        </button>
      </div>

      <div class="favorites-grid" :class="{ 'list-mode': viewMode === 'list' }">
        <article
          v-for="item in filteredFavorites"
          :key="`${item.target_type}-${item.id}`"
          class="favorite-card"
          :class="[
            item.target_type,
            { selected: selectedIds.includes(item.id), 'list-card': viewMode === 'list' },
          ]"
          @click="openDetail(item)"
        >
          <button
            class="select-control"
            :class="{ checked: selectedIds.includes(item.id) }"
            type="button"
            :aria-label="selectedIds.includes(item.id) ? '取消选择' : '选择'"
            @click.stop="toggleSelect(item.id)"
          >
            <el-icon v-if="selectedIds.includes(item.id)"><Check /></el-icon>
          </button>

          <div class="card-accent"></div>
          <div class="card-main">
            <div class="card-top">
              <div class="entity-mark" :class="item.target_type">
                <span v-if="item.target_type === 'resume'">{{ item.title.slice(0, 1) }}</span>
                <el-icon v-else><Briefcase /></el-icon>
              </div>
              <div class="entity-title">
                <div class="entity-kicker">
                  {{ item.target_type === "job" ? item.company : item.subtitle }}
                  <span v-if="item.urgent" class="urgent-dot">急招</span>
                </div>
                <h2>{{ item.title }}</h2>
                <p v-if="item.target_type === 'resume'">{{ item.company }}</p>
              </div>
              <button class="star-button" type="button" title="取消收藏" @click.stop="removeFavorite(item)">
                <el-icon><StarFilled /></el-icon>
              </button>
            </div>

            <div class="card-facts">
              <template v-if="item.target_type === 'job'">
                <span><el-icon><Location /></el-icon>{{ item.location }}</span>
                <span><el-icon><Money /></el-icon>{{ item.salary }}</span>
                <span><el-icon><OfficeBuilding /></el-icon>{{ item.experience }}</span>
              </template>
              <template v-else>
                <span><el-icon><User /></el-icon>{{ item.experience }}</span>
                <span><el-icon><School /></el-icon>{{ item.education }}</span>
                <span><el-icon><Location /></el-icon>{{ item.location }}</span>
              </template>
            </div>

            <div class="skill-row">
              <span v-for="skill in item.skills.slice(0, 4)" :key="skill">{{ skill }}</span>
              <span v-if="item.skills.length > 4" class="skill-more">+{{ item.skills.length - 4 }}</span>
            </div>

            <div class="card-note">
              <el-icon><EditPen /></el-icon>
              <span>{{ item.note || "添加备注，记录关注原因…" }}</span>
            </div>
          </div>

          <div class="card-side">
            <div class="match-score" :class="scoreTone(item.match)">
              <strong>{{ item.match }}%</strong>
              <span>{{ item.target_type === "job" ? "画像匹配" : "岗位匹配" }}</span>
              <div><i :style="{ width: `${item.match}%` }"></i></div>
            </div>
            <div class="card-actions">
              <button type="button" @click.stop="openDetail(item)">
                <el-icon><View /></el-icon>
                查看详情
              </button>
              <button class="primary-action" type="button" @click.stop="handlePrimaryAction(item)">
                <el-icon><Connection /></el-icon>
                {{ item.target_type === "job" ? "查看画像" : "发起匹配" }}
              </button>
            </div>
            <span class="saved-time"><el-icon><Clock /></el-icon>{{ item.savedAt }} 收藏</span>
          </div>
        </article>
      </div>
    </div>

    <div v-else class="favorites-empty anim-fade-up">
      <div class="empty-orbit">
        <el-icon><Star /></el-icon>
      </div>
      <h2>{{ keyword ? "没有找到匹配的收藏" : "这个收藏夹还是空的" }}</h2>
      <p>{{ keyword ? "换个关键词，或切换到其他收藏分类试试。" : "在岗位和人才页面点击星标，重要线索就会汇集到这里。" }}</p>
      <el-button v-if="keyword" type="primary" @click="keyword = ''">清除搜索</el-button>
      <el-button v-else type="primary" @click="$router.push('/jobs')">去发现岗位</el-button>
    </div>

    <el-drawer v-model="drawerVisible" :size="drawerSize" destroy-on-close>
      <template #header>
        <div v-if="selectedItem" class="drawer-title">
          <span>{{ selectedItem.target_type === "job" ? "岗位收藏详情" : "候选人收藏详情" }}</span>
          <small>收藏于 {{ selectedItem.savedAt }}</small>
        </div>
      </template>

      <div v-if="selectedItem" class="favorite-drawer">
        <div class="drawer-hero">
          <div class="entity-mark large" :class="selectedItem.target_type">
            <span v-if="selectedItem.target_type === 'resume'">{{ selectedItem.title.slice(0, 1) }}</span>
            <el-icon v-else><Briefcase /></el-icon>
          </div>
          <div>
            <p>{{ selectedItem.target_type === "job" ? selectedItem.company : selectedItem.subtitle }}</p>
            <h2>{{ selectedItem.title }}</h2>
            <span>{{ selectedItem.location }} · {{ selectedItem.experience }}</span>
          </div>
          <div class="drawer-score">{{ selectedItem.match }}<small>%</small></div>
        </div>

        <div class="drawer-section">
          <div class="drawer-section-title">核心技能</div>
          <div class="drawer-skills">
            <span v-for="skill in selectedItem.skills" :key="skill">{{ skill }}</span>
          </div>
        </div>

        <div class="drawer-section">
          <div class="drawer-section-title">收藏备注</div>
          <el-input
            v-model="selectedItem.note"
            type="textarea"
            :rows="4"
            resize="none"
            placeholder="记录关注原因、下一步安排或沟通要点…"
          />
          <div class="drawer-note-hint">备注仅自己可见，并会随收藏记录保存。</div>
        </div>

        <div class="drawer-section">
          <div class="drawer-section-title">建议下一步</div>
          <div class="next-step-card">
            <span class="next-step-icon"><el-icon><MagicStick /></el-icon></span>
            <div>
              <strong>{{ selectedItem.target_type === "job" ? "基于岗位画像筛选人才" : "与目标岗位进行智能匹配" }}</strong>
              <p>
                {{
                  selectedItem.target_type === "job"
                    ? "从人才池中快速定位技能覆盖度较高的候选人。"
                    : "生成技能覆盖、能力差距与面试问题建议。"
                }}
              </p>
            </div>
          </div>
        </div>

        <div class="drawer-footer">
          <el-button @click="removeFavorite(selectedItem)">取消收藏</el-button>
          <el-button type="primary" @click="handlePrimaryAction(selectedItem)">
            {{ selectedItem.target_type === "job" ? "查看岗位画像" : "发起人才匹配" }}
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { ElMessage, ElMessageBox } from "element-plus";
import { useRouter } from "vue-router";
import { useFavoriteStore } from "@/stores/favorites";
import DataState from "@/components/common/DataState.vue";
import type { FavoriteRecord, FavoriteTargetType } from "@/domain/types";

type FavoriteType = FavoriteTargetType;
type FilterType = "all" | FavoriteType;
type ViewMode = "grid" | "list";

const router = useRouter();
const store = useFavoriteStore();
const { records: favorites, loading, error } = storeToRefs(store);
const activeType = ref<FilterType>("all");
const keyword = ref("");
const sortBy = ref("recent");
const viewMode = ref<ViewMode>("grid");
const selectedIds = ref<number[]>([]);
const drawerVisible = ref(false);
const selectedItem = ref<FavoriteRecord | null>(null);
const drawerSize = computed(() => (window.innerWidth < 768 ? "100%" : "520px"));
onMounted(() => store.load());
watch(drawerVisible, async (visible) => {
  if (!visible && selectedItem.value) {
    await store.updateNote(selectedItem.value.id, selectedItem.value.note);
  }
});

const jobCount = computed(() => favorites.value.filter((item) => item.target_type === "job").length);
const talentCount = computed(() => favorites.value.filter((item) => item.target_type === "resume").length);

const tabs = computed(() => [
  { label: "全部收藏", value: "all" as FilterType, icon: "Collection", count: favorites.value.length },
  { label: "岗位", value: "job" as FilterType, icon: "Briefcase", count: jobCount.value },
  { label: "候选人", value: "resume" as FilterType, icon: "User", count: talentCount.value },
]);

const filteredFavorites = computed(() => {
  const normalizedKeyword = keyword.value.toLowerCase();
  const result = favorites.value.filter((item) => {
    const typeMatches = activeType.value === "all" || item.target_type === activeType.value;
    const searchable = [item.title, item.subtitle, item.company, item.location, ...item.skills].join(" ").toLowerCase();
    return typeMatches && (!normalizedKeyword || searchable.includes(normalizedKeyword));
  });

  return [...result].sort((a, b) => {
    if (sortBy.value === "match") return b.match - a.match;
    if (sortBy.value === "name") return a.title.localeCompare(b.title, "zh-CN");
    return b.savedOrder - a.savedOrder;
  });
});

const allVisibleSelected = computed(
  () =>
    filteredFavorites.value.length > 0 &&
    filteredFavorites.value.every((item) => selectedIds.value.includes(item.id)),
);

function scoreTone(score: number) {
  if (score >= 90) return "excellent";
  if (score >= 85) return "good";
  return "steady";
}

function toggleSelect(id: number) {
  selectedIds.value = selectedIds.value.includes(id)
    ? selectedIds.value.filter((itemId) => itemId !== id)
    : [...selectedIds.value, id];
}

function toggleSelectAll() {
  const visibleIds = filteredFavorites.value.map((item) => item.id);
  if (allVisibleSelected.value) {
    selectedIds.value = selectedIds.value.filter((id) => !visibleIds.includes(id));
    return;
  }
  selectedIds.value = [...new Set([...selectedIds.value, ...visibleIds])];
}

function openDetail(item: FavoriteRecord) {
  selectedItem.value = item;
  drawerVisible.value = true;
}

async function removeFavorite(item: FavoriteRecord) {
  try {
    await ElMessageBox.confirm(`确定取消收藏“${item.title}”吗？`, "取消收藏", {
      confirmButtonText: "确认取消",
      cancelButtonText: "保留",
      type: "warning",
    });
    await store.removeMany([item.id]);
    selectedIds.value = selectedIds.value.filter((id) => id !== item.id);
    drawerVisible.value = false;
    ElMessage.success("已取消收藏");
  } catch {
    // User kept the favorite.
  }
}

async function removeSelected() {
  try {
    await ElMessageBox.confirm(`确定取消收藏已选择的 ${selectedIds.value.length} 项内容吗？`, "批量取消收藏", {
      confirmButtonText: "确认取消",
      cancelButtonText: "保留",
      type: "warning",
    });
    await store.removeMany(selectedIds.value);
    selectedIds.value = [];
    ElMessage.success("已批量取消收藏");
  } catch {
    // User cancelled the operation.
  }
}

function handlePrimaryAction(item: FavoriteRecord) {
  drawerVisible.value = false;
  if (item.target_type === "resume") {
    router.push(`/matching/${item.target_id}`);
    return;
  }
  router.push("/jobs");
  ElMessage.info(`正在前往“${item.title}”岗位画像`);
}
</script>

<style scoped>
.favorites-page {
  --favorite-ink: #22263a;
  --favorite-soft: #f3f5ff;
  position: relative;
  max-width: 1440px;
  margin: 0 auto;
}

.favorites-page::before {
  content: "";
  position: fixed;
  top: 60px;
  right: 0;
  width: 380px;
  height: 260px;
  background: radial-gradient(circle at top right, rgba(79, 110, 246, 0.09), transparent 68%);
  pointer-events: none;
}

.favorites-workbench {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 10px;
  margin-bottom: 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  box-shadow: var(--shadow-xs);
}

.favorites-tabs,
.favorites-tools,
.view-switch,
.bulk-actions,
.card-actions {
  display: flex;
  align-items: center;
}

.favorites-tabs {
  gap: 4px;
}

.favorites-tab {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 38px;
  padding: 0 13px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
  transition: 0.2s var(--ease-out);
}

.favorites-tab span {
  min-width: 20px;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--color-bg-muted);
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 14px;
}

.favorites-tab:hover {
  color: var(--favorite-ink);
  background: var(--color-bg-muted);
}

.favorites-tab.active {
  background: var(--color-brand-light);
  color: var(--color-brand);
}

.favorites-tab.active span {
  background: rgba(79, 110, 246, 0.12);
  color: var(--color-brand);
}

.favorites-tools {
  flex: 1;
  justify-content: flex-end;
  gap: 8px;
}

.favorites-search {
  display: flex;
  align-items: center;
  gap: 8px;
  width: min(320px, 42%);
  height: 38px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 9px;
  background: var(--color-bg-muted);
  color: var(--text-muted);
  transition: 0.2s var(--ease-out);
}

.favorites-search:focus-within {
  border-color: var(--color-brand);
  background: #fff;
  box-shadow: 0 0 0 3px var(--color-brand-light);
}

.favorites-search input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
}

.favorites-search input::placeholder {
  color: var(--text-placeholder);
}

.favorites-search button {
  display: flex;
  border: 0;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.favorites-search kbd {
  padding: 1px 5px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: #fff;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 14px;
}

.favorites-sort {
  width: 136px;
}

.view-switch {
  gap: 2px;
  padding: 3px;
  border-radius: 9px;
  background: var(--color-bg-muted);
}

.view-switch button {
  display: grid;
  width: 31px;
  height: 31px;
  place-items: center;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.view-switch button.active {
  background: #fff;
  color: var(--color-brand);
  box-shadow: var(--shadow-xs);
}

.bulk-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 9px 12px;
  margin-bottom: 14px;
  border: 1px solid rgba(79, 110, 246, 0.18);
  border-radius: var(--radius-md);
  background: var(--color-brand-subtle);
  color: var(--text-secondary);
  font-size: 14px;
}

.bulk-bar > div:first-child {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bulk-check {
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border-radius: 7px;
  background: var(--color-brand);
  color: white;
}

.bulk-actions {
  gap: 6px;
}

.bulk-actions button {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 10px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 14px;
}

.bulk-actions button:hover {
  background: #fff;
}

.bulk-actions .danger {
  color: var(--color-danger);
}

.content-meta {
  display: flex;
  justify-content: space-between;
  margin: 0 2px 9px;
  color: var(--text-muted);
  font-size: 14px;
}

.content-meta button {
  border: 0;
  background: transparent;
  color: var(--color-brand);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 14px;
}

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 13px;
}

.favorites-grid.list-mode {
  grid-template-columns: 1fr;
}

.favorite-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 132px;
  min-height: 226px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  cursor: pointer;
  transition: 0.25s var(--ease-out);
}

.favorite-card::after {
  content: "";
  position: absolute;
  inset: 0;
  border: 1px solid transparent;
  border-radius: inherit;
  pointer-events: none;
  transition: 0.2s var(--ease-out);
}

.favorite-card:hover {
  border-color: rgba(79, 110, 246, 0.28);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.favorite-card:hover::after {
  border-color: rgba(79, 110, 246, 0.08);
}

.favorite-card.selected {
  border-color: var(--color-brand);
  box-shadow: 0 0 0 3px var(--color-brand-light);
}

.favorite-card.list-card {
  grid-template-columns: minmax(0, 1fr) 170px;
  min-height: 190px;
}

.card-accent {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 3px;
  background: linear-gradient(180deg, var(--color-brand), #8fa8f4);
  opacity: 0;
  transition: 0.2s var(--ease-out);
}

.favorite-card.resume .card-accent {
  background: linear-gradient(180deg, var(--color-success), #8fd9bc);
}

.favorite-card:hover .card-accent,
.favorite-card.selected .card-accent {
  opacity: 1;
}

.select-control {
  position: absolute;
  z-index: 2;
  top: 11px;
  left: 11px;
  display: grid;
  width: 20px;
  height: 20px;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.9);
  color: white;
  cursor: pointer;
  opacity: 0;
  transition: 0.2s var(--ease-out);
}

.favorite-card:hover .select-control,
.select-control.checked {
  opacity: 1;
}

.select-control.checked {
  border-color: var(--color-brand);
  background: var(--color-brand);
}

.card-main {
  min-width: 0;
  padding: 21px 18px 16px 20px;
}

.card-top {
  display: flex;
  align-items: flex-start;
  gap: 11px;
}

.entity-mark {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  place-items: center;
  border-radius: 12px;
  background: var(--color-brand-light);
  color: var(--color-brand);
  font-size: 16px;
  font-weight: 700;
}

.entity-mark.resume {
  background: linear-gradient(145deg, #eaf9f3, #d9f4e9);
  color: var(--color-success);
}

.entity-mark.large {
  width: 52px;
  height: 52px;
  flex-basis: 52px;
  border-radius: 15px;
  font-size: 20px;
}

.entity-title {
  min-width: 0;
  flex: 1;
}

.entity-kicker {
  overflow: hidden;
  color: var(--text-muted);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entity-title h2 {
  overflow: hidden;
  margin-top: 2px;
  color: var(--favorite-ink);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.02em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entity-title p {
  overflow: hidden;
  margin-top: 1px;
  color: var(--text-muted);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.urgent-dot {
  display: inline-flex;
  padding: 1px 5px;
  margin-left: 5px;
  border-radius: 4px;
  background: var(--color-warning-light);
  color: var(--color-warning);
  font-size: 14px;
  font-weight: 700;
}

.star-button {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  place-items: center;
  border: 0;
  border-radius: 8px;
  background: var(--color-warning-light);
  color: var(--color-warning);
  cursor: pointer;
  transition: 0.2s var(--ease-out);
}

.star-button:hover {
  background: var(--color-warning);
  color: white;
  transform: rotate(-8deg) scale(1.04);
}

.card-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  margin: 15px 0 10px;
  color: var(--text-secondary);
  font-size: 14px;
}

.card-facts span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.card-facts .el-icon {
  color: var(--text-muted);
}

.skill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  min-height: 25px;
}

.skill-row span,
.drawer-skills span {
  padding: 3px 8px;
  border: 1px solid var(--color-border-light);
  border-radius: 6px;
  background: var(--color-bg-muted);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
}

.skill-row .skill-more {
  border-style: dashed;
  background: transparent;
  color: var(--text-muted);
}

.card-note {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding-top: 11px;
  margin-top: 11px;
  border-top: 1px dashed var(--color-border);
  color: var(--text-muted);
  font-size: 14px;
  font-style: italic;
}

.card-note span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-side {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  padding: 18px 14px;
  border-left: 1px solid var(--color-border-light);
  background:
    linear-gradient(180deg, rgba(79, 110, 246, 0.035), transparent 55%),
    #fcfcfe;
}

.match-score {
  margin-bottom: 14px;
  text-align: center;
}

.match-score strong {
  display: block;
  color: var(--color-brand);
  font-family: var(--font-mono);
  font-size: 23px;
  letter-spacing: -0.05em;
}

.match-score.good strong {
  color: var(--color-success);
}

.match-score.steady strong {
  color: var(--color-warning);
}

.match-score span {
  display: block;
  margin-top: -2px;
  color: var(--text-muted);
  font-size: 14px;
}

.match-score > div {
  height: 3px;
  margin-top: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--color-bg-muted);
}

.match-score i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: currentColor;
}

.match-score.excellent {
  color: var(--color-brand);
}

.match-score.good {
  color: var(--color-success);
}

.match-score.steady {
  color: var(--color-warning);
}

.card-actions {
  flex-direction: column;
  gap: 6px;
}

.card-actions button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  width: 100%;
  min-height: 30px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: #fff;
  color: var(--text-secondary);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
  transition: 0.18s var(--ease-out);
}

.card-actions button:hover {
  border-color: var(--color-brand);
  color: var(--color-brand);
}

.card-actions .primary-action {
  border-color: var(--color-brand);
  background: var(--color-brand);
  color: white;
}

.card-actions .primary-action:hover {
  background: var(--color-brand-hover);
  color: white;
  box-shadow: 0 4px 12px rgba(79, 110, 246, 0.2);
}

.saved-time {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 10px;
  color: var(--text-muted);
  font-size: 14px;
}

.favorites-empty {
  display: flex;
  min-height: 430px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-xl);
  background: rgba(255, 255, 255, 0.55);
  text-align: center;
}

.empty-orbit {
  display: grid;
  width: 74px;
  height: 74px;
  margin-bottom: 18px;
  place-items: center;
  border: 1px solid rgba(79, 110, 246, 0.15);
  border-radius: 50%;
  background: var(--color-brand-light);
  color: var(--color-brand);
  font-size: 28px;
  box-shadow: 0 0 0 12px rgba(79, 110, 246, 0.04);
}

.favorites-empty h2 {
  font-size: 17px;
}

.favorites-empty p {
  max-width: 360px;
  margin: 7px 0 18px;
  color: var(--text-muted);
  font-size: 14px;
}

.drawer-title {
  display: flex;
  flex-direction: column;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 700;
}

.drawer-title small {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 400;
}

.favorite-drawer {
  padding: 0 3px 18px;
}

.drawer-hero {
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 18px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background:
    radial-gradient(circle at top right, rgba(79, 110, 246, 0.12), transparent 42%),
    var(--color-bg-elevated);
}

.drawer-hero > div:nth-child(2) {
  min-width: 0;
  flex: 1;
}

.drawer-hero p {
  color: var(--text-muted);
  font-size: 14px;
}

.drawer-hero h2 {
  margin: 2px 0;
  font-size: 17px;
}

.drawer-hero span {
  color: var(--text-secondary);
  font-size: 14px;
}

.drawer-score {
  color: var(--color-brand);
  font-family: var(--font-mono);
  font-size: 28px;
  font-weight: 700;
}

.drawer-score small {
  font-size: 14px;
}

.drawer-section {
  margin-top: 22px;
}

.drawer-section-title {
  margin-bottom: 10px;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 700;
}

.drawer-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.drawer-note-hint {
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 14px;
}

.next-step-card {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 13px;
  border: 1px solid rgba(79, 110, 246, 0.12);
  border-radius: var(--radius-md);
  background: var(--color-brand-subtle);
}

.next-step-icon {
  display: grid;
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  place-items: center;
  border-radius: 9px;
  background: var(--color-brand);
  color: white;
}

.next-step-card strong {
  font-size: 14px;
}

.next-step-card p {
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.6;
}

.drawer-footer {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 8px;
  padding-top: 16px;
  margin-top: 24px;
  border-top: 1px solid var(--color-border-light);
}

@media (max-width: 1180px) {
  .favorites-workbench {
    align-items: stretch;
    flex-direction: column;
  }

  .favorites-tools {
    justify-content: flex-start;
  }

  .favorites-search {
    width: auto;
    flex: 1;
  }

  .favorites-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .favorites-tabs {
    overflow-x: auto;
  }

  .favorites-tab {
    white-space: nowrap;
  }

  .favorites-tools {
    flex-wrap: wrap;
  }

  .favorites-search {
    width: 100%;
    flex-basis: 100%;
  }

  .favorite-card,
  .favorite-card.list-card {
    grid-template-columns: 1fr;
  }

  .card-side {
    display: grid;
    grid-template-columns: 86px 1fr;
    gap: 12px;
    border-top: 1px solid var(--color-border-light);
    border-left: 0;
  }

  .match-score {
    margin: 0;
  }

  .saved-time {
    display: none;
  }

  .bulk-bar {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

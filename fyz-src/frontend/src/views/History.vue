<template>
  <div class="history-page">
    <DataState :loading="loading" :error="error" @retry="store.refresh()" />
    <section class="history-toolbar anim-fade-up">
      <div class="history-tabs" role="tablist" aria-label="足迹分类">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          type="button"
          :class="{ active: activeType === tab.value }"
          @click="activeType = tab.value"
        >
          <el-icon><component :is="tab.icon" /></el-icon>
          {{ tab.label }}
          <span>{{ tab.count }}</span>
        </button>
      </div>

      <div class="history-inline-stats" aria-label="浏览足迹概览">
        <span>
          <el-icon><Calendar /></el-icon>
          <strong>{{ todayCount }}</strong>
          <em>今日浏览</em>
        </span>
        <i></i>
        <span>
          <el-icon><Aim /></el-icon>
          <strong>{{ uniqueTargetCount }}</strong>
          <em>独立目标</em>
        </span>
      </div>

      <div class="history-tools">
        <div class="history-search">
          <el-icon><Search /></el-icon>
          <input v-model.trim="keyword" type="search" placeholder="搜索标题、公司、技能或关键词…" />
          <button v-if="keyword" type="button" title="清除搜索" @click="keyword = ''">
            <el-icon><CircleClose /></el-icon>
          </button>
        </div>

        <el-select v-model="dateRange" class="history-range" aria-label="时间范围">
          <template #prefix><el-icon><Calendar /></el-icon></template>
          <el-option label="全部时间" value="all" />
          <el-option label="今天" value="today" />
          <el-option label="近 7 天" value="week" />
          <el-option label="近 30 天" value="month" />
        </el-select>

        <button class="clear-button" type="button" :disabled="records.length === 0" @click="clearHistory">
          <el-icon><Delete /></el-icon>
          清空记录
        </button>
      </div>
    </section>

    <div class="history-layout anim-fade-up anim-delay-2">
      <main class="history-stream">
        <div class="stream-meta">
          <span>筛选出 {{ filteredRecords.length }} 条记录</span>
          <span>按浏览时间倒序</span>
        </div>

        <template v-if="groupedRecords.length">
          <section v-for="group in groupedRecords" :key="group.key" class="history-day">
            <div class="day-heading">
              <div>
                <span class="day-dot"></span>
                <h2>{{ group.label }}</h2>
                <small>{{ group.date }}</small>
              </div>
              <span>{{ group.items.length }} 条活动</span>
            </div>

            <div class="day-timeline">
              <article
                v-for="item in group.items"
                :key="item.id"
                class="history-entry"
                :class="item.type"
                @click="openRecord(item)"
              >
                <div class="entry-time">{{ item.time }}</div>

                <div class="entry-marker">
                  <el-icon><component :is="typeMeta[item.type].icon" /></el-icon>
                </div>

                <div class="entry-card">
                  <div class="entry-main">
                    <div class="entry-topline">
                      <span class="entry-type">{{ typeMeta[item.type].label }}</span>
                      <span v-if="item.badge" class="entry-badge">{{ item.badge }}</span>
                      <span class="entry-source">{{ item.source }}</span>
                    </div>

                    <h3>{{ item.title }}</h3>
                    <p>{{ item.description }}</p>

                    <div v-if="item.tags.length" class="entry-tags">
                      <span v-for="tag in item.tags" :key="tag">{{ tag }}</span>
                    </div>
                  </div>

                  <div class="entry-actions">
                    <FavoriteButton
                      v-if="item.type === 'job'"
                      type="job"
                      :target-id="numericTargetId(item)"
                      :title="item.title"
                      compact
                    />
                    <FavoriteButton
                      v-if="item.type === 'resume'"
                      type="resume"
                      :target-id="numericTargetId(item)"
                      :title="item.title"
                      compact
                    />
                    <button class="revisit-button" type="button" @click.stop="openRecord(item)">
                      {{ actionLabel(item.type) }}
                      <el-icon><ArrowRight /></el-icon>
                    </button>
                    <button class="entry-more" type="button" title="删除此记录" @click.stop="removeRecord(item)">
                      <el-icon><Delete /></el-icon>
                    </button>
                  </div>
                </div>
              </article>
            </div>
          </section>
        </template>

        <div v-else class="history-empty">
          <div class="empty-radar">
            <el-icon><Clock /></el-icon>
          </div>
          <h2>{{ keyword || activeType !== "all" || dateRange !== "all" ? "没有符合条件的浏览记录" : "暂时还没有浏览足迹" }}</h2>
          <p>
            {{
              keyword || activeType !== "all" || dateRange !== "all"
                ? "调整分类、时间范围或搜索关键词后再试试。"
                : "访问岗位、人才匹配和技能图谱后，浏览记录会自动出现在这里。"
            }}
          </p>
          <el-button
            v-if="keyword || activeType !== 'all' || dateRange !== 'all'"
            type="primary"
            @click="resetFilters"
          >
            重置筛选
          </el-button>
          <el-button v-else type="primary" @click="$router.push('/dashboard')">返回工作台</el-button>
        </div>

        <div v-if="filteredRecords.length > pageSize" class="history-pagination">
          <span>共 {{ filteredRecords.length }} 条足迹</span>
          <el-pagination
            v-model:current-page="currentPage"
            size="small"
            background
            layout="prev, pager, next"
            :page-size="pageSize"
            :total="filteredRecords.length"
          />
        </div>
      </main>

      <aside class="history-aside">
        <section class="aside-card insight-card">
          <div class="aside-label">本周浏览画像</div>
          <h3>你的关注正聚焦在<br /><strong>AI 应用与后端人才</strong></h3>
          <div class="focus-bars">
            <div v-for="focus in focusStats" :key="focus.label">
              <span>{{ focus.label }}</span>
              <div><i :style="{ width: `${focus.percent}%` }"></i></div>
              <strong>{{ focus.count }}</strong>
            </div>
          </div>
        </section>

        <section class="aside-card">
          <div class="aside-head">
            <div>
              <div class="aside-label">高频访问</div>
              <h3>最近反复查看</h3>
            </div>
            <el-icon><TrendCharts /></el-icon>
          </div>
          <button
            v-for="item in frequentRecords"
            :key="item.title"
            class="frequent-item"
            type="button"
            @click="openRecord(item.record)"
          >
            <span class="frequent-icon" :class="item.record.type">
              <el-icon><component :is="typeMeta[item.record.type].icon" /></el-icon>
            </span>
            <span>
              <strong>{{ item.title }}</strong>
              <small>最近浏览 {{ item.count }} 次</small>
            </span>
            <el-icon class="frequent-arrow"><ArrowRight /></el-icon>
          </button>
        </section>

        <section class="privacy-note">
          <el-icon><Lock /></el-icon>
          <div>
            <strong>足迹仅自己可见</strong>
            <p>系统默认保留最近 50 条记录，可随时删除或清空。</p>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { ElMessage, ElMessageBox } from "element-plus";
import { useRouter } from "vue-router";
import FavoriteButton from "@/components/common/FavoriteButton.vue";
import { useHistoryStore } from "@/stores/history";
import DataState from "@/components/common/DataState.vue";
import type { HistoryRecord, HistoryType } from "@/domain/types";

type FilterType = "all" | HistoryType;
type DateRange = "all" | "today" | "week" | "month";

const router = useRouter();
const store = useHistoryStore();
const { records, insights, loading, error } = storeToRefs(store);
const activeType = ref<FilterType>("all");
const dateRange = ref<DateRange>("all");
const keyword = ref("");
const currentPage = ref(1);
const pageSize = 8;

const typeMeta: Record<HistoryType, { label: string; icon: string }> = {
  job: { label: "岗位", icon: "Briefcase" },
  resume: { label: "候选人", icon: "User" },
  search: { label: "搜索", icon: "Search" },
  graph: { label: "技能图谱", icon: "Share" },
  match: { label: "匹配报告", icon: "DataAnalysis" },
};

onMounted(() => store.load());

const tabs = computed(() => [
  { label: "全部", value: "all" as FilterType, icon: "Collection", count: records.value.length },
  ...(["job", "resume", "search", "graph", "match"] as HistoryType[]).map((type) => ({
    label: typeMeta[type].label,
    value: type as FilterType,
    icon: typeMeta[type].icon,
    count: records.value.filter((item) => item.type === type).length,
  })),
]);

const todayCount = computed(() => records.value.filter((item) => item.dateKey === "today").length);
const uniqueTargetCount = computed(() => new Set(records.value.map((item) => item.targetId || item.title)).size);

const filteredRecords = computed(() => {
  const query = keyword.value.toLowerCase();
  const allowedDates: Record<DateRange, string[]> = {
    all: ["today", "yesterday", "week", "month"],
    today: ["today"],
    week: ["today", "yesterday", "week"],
    month: ["today", "yesterday", "week", "month"],
  };

  return records.value.filter((item) => {
    const typeMatches = activeType.value === "all" || item.type === activeType.value;
    const dateMatches = allowedDates[dateRange.value].includes(item.dateKey);
    const searchable = [item.title, item.description, item.source, ...item.tags].join(" ").toLowerCase();
    return typeMatches && dateMatches && (!query || searchable.includes(query));
  });
});

const pagedRecords = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return filteredRecords.value.slice(start, start + pageSize);
});

const groupedRecords = computed(() => {
  const order = ["today", "yesterday", "week", "month"];
  const labels: Record<string, string> = {
    today: "今天",
    yesterday: "昨天",
    week: "本周更早",
    month: "本月更早",
  };

  return order
    .map((key) => {
      const items = pagedRecords.value.filter((item) => item.dateKey === key);
      return { key, label: labels[key], date: items[0]?.date || "", items };
    })
    .filter((group) => group.items.length);
});

watch([activeType, dateRange, keyword], () => {
  currentPage.value = 1;
});

const focusStats = computed(() => insights.value.focusStats);

const frequentRecords = computed(() => {
  return insights.value.frequentRecords.flatMap((item) => {
    const record = records.value.find((candidate) => candidate.id === item.history_id);
    return record ? [{ count: item.count, record, title: record.title }] : [];
  });
});

function numericTargetId(item: HistoryRecord): number {
  return typeof item.targetId === "number" ? item.targetId : item.id;
}

function actionLabel(type: HistoryType) {
  const labels: Record<HistoryType, string> = {
    job: "再次查看",
    resume: "查看人才",
    search: "重新搜索",
    graph: "打开图谱",
    match: "查看报告",
  };
  return labels[type];
}

function openRecord(item: HistoryRecord) {
  router.push(item.url);
}

async function removeRecord(item: HistoryRecord) {
  try {
    await ElMessageBox.confirm(`确定删除“${item.title}”的浏览记录吗？`, "删除足迹", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await store.remove(item.id);
    currentPage.value = Math.min(
      currentPage.value,
      Math.max(1, Math.ceil(filteredRecords.value.length / pageSize)),
    );
    ElMessage.success("浏览记录已删除");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "浏览记录删除失败");
  }
}

async function clearHistory() {
  try {
    await ElMessageBox.confirm("清空后无法恢复，确定删除全部浏览记录吗？", "清空浏览足迹", {
      confirmButtonText: "全部清空",
      cancelButtonText: "保留记录",
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await store.clear();
    currentPage.value = 1;
    ElMessage.success("浏览足迹已清空");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "浏览足迹清空失败");
  }
}

function resetFilters() {
  activeType.value = "all";
  dateRange.value = "all";
  keyword.value = "";
  currentPage.value = 1;
}
</script>

<style scoped>
.history-page {
  position: relative;
  max-width: 1440px;
  margin: 0 auto;
}

.history-page::before {
  content: "";
  position: fixed;
  top: 60px;
  right: 0;
  width: 420px;
  height: 300px;
  background: radial-gradient(circle at top right, rgba(91, 157, 245, 0.1), transparent 68%);
  pointer-events: none;
}

.history-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px;
  margin-bottom: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  box-shadow: var(--shadow-xs);
}

.history-tabs,
.history-inline-stats,
.history-tools {
  display: flex;
  align-items: center;
}

.history-tabs {
  gap: 3px;
}

.history-tabs button {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 11px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  transition: all var(--duration-fast) var(--ease-out);
}

.history-tabs button:hover {
  background: var(--color-bg-muted);
  color: var(--text-primary);
}

.history-tabs button.active {
  background: var(--color-info-light);
  color: var(--color-info);
}

.history-tabs button span {
  min-width: 18px;
  padding: 1px 5px;
  border-radius: 999px;
  background: rgba(91, 157, 245, 0.1);
  font-family: var(--font-mono);
  font-size: 14px;
  text-align: center;
}

.history-inline-stats {
  flex-shrink: 0;
  gap: 10px;
  padding: 0 4px;
  color: var(--color-info);
}

.history-inline-stats > span {
  display: flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}

.history-inline-stats strong {
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 15px;
}

.history-inline-stats em {
  color: var(--text-muted);
  font-size: 14px;
  font-style: normal;
}

.history-inline-stats > i {
  width: 1px;
  height: 20px;
  background: var(--color-border);
}

.history-tools {
  flex: 1;
  justify-content: flex-end;
  gap: 8px;
}

.history-search {
  display: flex;
  align-items: center;
  gap: 8px;
  width: min(310px, 42%);
  height: 36px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 9px;
  background: var(--color-bg-muted);
  color: var(--text-muted);
  transition: all var(--duration-fast) var(--ease-out);
}

.history-search:focus-within {
  border-color: var(--color-info);
  background: white;
  box-shadow: 0 0 0 3px var(--color-info-light);
}

.history-search input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
}

.history-search input::placeholder {
  color: var(--text-placeholder);
}

.history-search button {
  display: flex;
  border: 0;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.history-range {
  width: 126px;
}

.clear-button {
  display: flex;
  align-items: center;
  gap: 5px;
  height: 36px;
  padding: 0 11px;
  border: 1px solid var(--color-border);
  border-radius: 9px;
  background: white;
  color: var(--text-secondary);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
  transition: all var(--duration-fast) var(--ease-out);
}

.clear-button:hover:not(:disabled) {
  border-color: rgba(232, 93, 93, 0.35);
  background: var(--color-danger-light);
  color: var(--color-danger);
}

.clear-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.history-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 20px;
}

.history-stream {
  min-width: 0;
}

.history-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 54px;
  padding: 10px 14px;
  margin-top: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  color: var(--text-muted);
  font-size: 14px;
}

.history-pagination :deep(.el-pager li.is-active) {
  background: var(--color-brand);
}

.stream-meta {
  display: flex;
  justify-content: space-between;
  padding: 0 2px;
  margin-bottom: 10px;
  color: var(--text-muted);
  font-size: 14px;
}

.history-day + .history-day {
  margin-top: 22px;
}

.day-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 3px 12px 34px;
}

.day-heading > div {
  display: flex;
  align-items: center;
  gap: 7px;
}

.day-heading h2 {
  font-size: 16px;
  font-weight: 700;
}

.day-heading small,
.day-heading > span {
  color: var(--text-muted);
  font-size: 14px;
}

.day-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--color-info);
  box-shadow: 0 0 0 5px var(--color-info-light);
}

.day-timeline {
  position: relative;
}

.day-timeline::before {
  content: "";
  position: absolute;
  top: 10px;
  bottom: 10px;
  left: 57px;
  width: 2px;
  background: linear-gradient(var(--color-border), var(--color-border-light));
}

.history-entry {
  position: relative;
  display: grid;
  grid-template-columns: 38px 40px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
}

.history-entry + .history-entry {
  margin-top: 12px;
}

.entry-time {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 14px;
  text-align: right;
}

.entry-marker {
  z-index: 1;
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 3px solid var(--color-bg-base);
  border-radius: 11px;
  background: var(--color-info-light);
  color: var(--color-info);
  font-size: 15px;
}

.history-entry.job .entry-marker {
  background: var(--color-brand-light);
  color: var(--color-brand);
}

.history-entry.resume .entry-marker {
  background: var(--color-success-light);
  color: var(--color-success);
}

.history-entry.search .entry-marker {
  background: var(--color-warning-light);
  color: var(--color-warning);
}

.history-entry.graph .entry-marker {
  background: #f0edff;
  color: #7c6ff7;
}

.history-entry.match .entry-marker {
  background: var(--color-danger-light);
  color: var(--color-danger);
}

.entry-card {
  display: flex;
  align-items: center;
  gap: 18px;
  min-width: 0;
  padding: 18px 17px 18px 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.entry-card:hover {
  border-color: rgba(91, 157, 245, 0.3);
  box-shadow: var(--shadow-md);
  transform: translateX(2px);
}

.entry-main {
  min-width: 0;
  flex: 1;
}

.entry-topline {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 5px;
}

.entry-type {
  color: var(--color-info);
  font-size: 14px;
  font-weight: 700;
}

.history-entry.job .entry-type {
  color: var(--color-brand);
}

.history-entry.resume .entry-type {
  color: var(--color-success);
}

.history-entry.search .entry-type {
  color: var(--color-warning);
}

.history-entry.graph .entry-type {
  color: #7c6ff7;
}

.history-entry.match .entry-type {
  color: var(--color-danger);
}

.entry-badge {
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--color-success-light);
  color: var(--color-success);
  font-size: 14px;
  font-weight: 700;
}

.entry-source {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 14px;
}

.entry-main h3 {
  overflow: hidden;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entry-main p {
  overflow: hidden;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entry-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 11px;
}

.entry-tags span {
  padding: 3px 9px;
  border-radius: 6px;
  background: var(--color-bg-muted);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
}

.entry-actions {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
}

.revisit-button,
.entry-more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 34px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: white;
  color: var(--text-secondary);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
  transition: all var(--duration-fast) var(--ease-out);
}

.revisit-button {
  padding: 0 12px;
}

.revisit-button:hover {
  border-color: var(--color-info);
  color: var(--color-info);
}

.entry-more {
  width: 34px;
  color: var(--text-muted);
  opacity: 0;
}

.entry-card:hover .entry-more {
  opacity: 1;
}

.entry-more:hover {
  border-color: rgba(232, 93, 93, 0.3);
  background: var(--color-danger-light);
  color: var(--color-danger);
}

.history-aside {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.aside-card {
  padding: 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-elevated);
}

.insight-card {
  overflow: hidden;
  background:
    radial-gradient(circle at top right, rgba(79, 110, 246, 0.13), transparent 42%),
    linear-gradient(155deg, #ffffff, #f8f9ff);
}

.aside-label {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.aside-card h3 {
  margin-top: 5px;
  font-size: 16px;
  line-height: 1.55;
}

.insight-card h3 strong {
  color: var(--color-brand);
}

.focus-bars {
  display: flex;
  flex-direction: column;
  gap: 13px;
  margin-top: 18px;
}

.focus-bars > div {
  display: grid;
  grid-template-columns: 78px 1fr 22px;
  gap: 9px;
  align-items: center;
}

.focus-bars span {
  color: var(--text-secondary);
  font-size: 14px;
}

.focus-bars div div {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--color-bg-muted);
}

.focus-bars i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--color-brand), var(--color-info));
}

.focus-bars strong {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 14px;
  text-align: right;
}

.aside-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 11px;
  border-bottom: 1px solid var(--color-border-light);
}

.aside-head > .el-icon {
  color: var(--color-brand);
}

.frequent-item {
  display: flex;
  align-items: center;
  gap: 11px;
  width: 100%;
  padding: 13px 0;
  border: 0;
  border-bottom: 1px solid var(--color-border-light);
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.frequent-item:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.frequent-icon {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  place-items: center;
  border-radius: 8px;
  background: var(--color-brand-light);
  color: var(--color-brand);
}

.frequent-icon.resume {
  background: var(--color-success-light);
  color: var(--color-success);
}

.frequent-icon.graph {
  background: #f0edff;
  color: #7c6ff7;
}

.frequent-item > span:nth-child(2) {
  min-width: 0;
  flex: 1;
}

.frequent-item strong,
.frequent-item small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.frequent-item strong {
  color: var(--text-primary);
  font-size: 14px;
}

.frequent-item small {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 14px;
}

.frequent-arrow {
  color: var(--text-muted);
  transition: transform var(--duration-fast) var(--ease-out);
}

.frequent-item:hover .frequent-arrow {
  color: var(--color-brand);
  transform: translateX(2px);
}

.privacy-note {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  padding: 16px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  color: var(--text-muted);
}

.privacy-note > .el-icon {
  margin-top: 2px;
  color: var(--color-success);
}

.privacy-note strong {
  color: var(--text-secondary);
  font-size: 14px;
}

.privacy-note p {
  margin-top: 2px;
  font-size: 14px;
  line-height: 1.6;
}

.history-empty {
  display: flex;
  min-height: 470px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-xl);
  background: rgba(255, 255, 255, 0.55);
  text-align: center;
}

.empty-radar {
  display: grid;
  width: 72px;
  height: 72px;
  margin-bottom: 18px;
  place-items: center;
  border: 1px solid rgba(91, 157, 245, 0.18);
  border-radius: 50%;
  background: var(--color-info-light);
  color: var(--color-info);
  font-size: 27px;
  box-shadow: 0 0 0 12px rgba(91, 157, 245, 0.04);
}

.history-empty h2 {
  font-size: 19px;
}

.history-empty p {
  max-width: 360px;
  margin: 7px 0 18px;
  color: var(--text-muted);
  font-size: 14px;
}

@media (max-width: 1180px) {
  .history-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .history-tabs {
    overflow-x: auto;
  }

  .history-inline-stats em {
    display: none;
  }

  .history-tools {
    justify-content: flex-start;
  }

  .history-search {
    width: auto;
    flex: 1;
  }
}

@media (max-width: 900px) {
  .history-layout {
    grid-template-columns: 1fr;
  }

  .history-aside {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .privacy-note {
    grid-column: 1 / -1;
  }
}

@media (max-width: 768px) {
  .history-tools {
    flex-wrap: wrap;
  }

  .history-inline-stats {
    order: 2;
    width: 100%;
    justify-content: flex-end;
    padding: 3px 2px 0;
  }

  .history-inline-stats em {
    display: inline;
  }

  .history-tools {
    order: 3;
  }

  .history-search {
    width: 100%;
    flex-basis: 100%;
  }

  .day-heading {
    padding-left: 0;
  }

  .day-timeline::before,
  .entry-time {
    display: none;
  }

  .history-entry {
    grid-template-columns: 32px minmax(0, 1fr);
  }

  .entry-card {
    align-items: flex-start;
    flex-direction: column;
  }

  .entry-actions {
    width: 100%;
  }

  .revisit-button {
    flex: 1;
  }

  .entry-more {
    opacity: 1;
  }

  .history-aside {
    grid-template-columns: 1fr;
  }

  .privacy-note {
    grid-column: auto;
  }
}
</style>

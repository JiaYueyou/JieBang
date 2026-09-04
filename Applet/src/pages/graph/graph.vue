<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import {
  apiGraphPanorama,
  apiGraphSearch,
  apiGraphExpand,
} from '@/api/graph'
import type { GraphNode, GraphEdge, GraphSubgraph } from '@/api/graph'
import SkillGraph from '@/components/SkillGraph.vue'
import AppTabBar from '@/components/AppTabBar.vue'
import EmptyState from '@/components/EmptyState.vue'

const statusBarHeight = uni.getWindowInfo().statusBarHeight

const keyword = ref('')
const view = ref<GraphSubgraph>({ nodes: [], edges: [] })
const highlights = ref<string[]>([])
const selected = ref<GraphNode | null>(null)
const loading = ref(true)
const depthLimited = ref(false)
const firstLoaded = ref(false)

const PANORAMA_LIMIT = 300

onShow(() => {
  uni.hideTabBar({ animation: false })
  if (!firstLoaded.value) resetView()
})

async function resetView() {
  loading.value = true
  selected.value = null
  highlights.value = []
  keyword.value = ''
  try {
    const pano = await apiGraphPanorama()
    firstLoaded.value = true
    depthLimited.value = pano.nodes.length > PANORAMA_LIMIT
    view.value = pano
  } catch (e) {
    uni.showToast({ title: e instanceof Error ? e.message : '图谱加载失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

async function onSearch() {
  const kw = keyword.value.trim()
  if (!kw) {
    resetView()
    return
  }
  loading.value = true
  try {
    const sub = await apiGraphSearch(kw)
    if (!sub.nodes.length) {
      uni.showToast({ title: '未找到相关节点', icon: 'none' })
      return
    }
    selected.value = null
    view.value = sub
    highlights.value = sub.nodes.map((n) => n.id)
    depthLimited.value = false
    firstLoaded.value = true
  } catch (e) {
    uni.showToast({ title: e instanceof Error ? e.message : '搜索失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}

async function expandSelected() {
  if (!selected.value) return
  const id = selected.value.id
  try {
    uni.showLoading({ title: '展开中', mask: true })
    const sub = await apiGraphExpand(id)
    uni.hideLoading()
    depthLimited.value = false
    mergeSubgraph(sub)
  } catch (e) {
    uni.hideLoading()
    uni.showToast({ title: e instanceof Error ? e.message : '展开失败', icon: 'none' })
  }
}

function mergeSubgraph(sub: GraphSubgraph) {
  const map = new Map(view.value.nodes.map((n) => [n.id, n]))
  let added = 0
  for (const n of sub.nodes) {
    if (!map.has(n.id)) {
      map.set(n.id, n)
      added++
    }
  }
  const ekeys = new Set(view.value.edges.map((e) => `${e.source}->${e.target}`))
  const edges = view.value.edges.slice()
  for (const e of sub.edges) {
    const k = `${e.source}->${e.target}`
    if (!ekeys.has(k) && map.has(e.source) && map.has(e.target)) {
      ekeys.add(k)
      edges.push(e)
    }
  }
  if (added === 0) uni.showToast({ title: '该节点已是全展开状态', icon: 'none' })
  view.value = { nodes: [...map.values()], edges }
}

function onSelect(node: GraphNode) {
  selected.value = selected.value?.id === node.id ? selected.value : node
}

function clearSelected() {
  selected.value = null
}

const displayNodes = computed(() =>
  depthLimited.value ? view.value.nodes.filter((n) => n.layer <= 3) : view.value.nodes,
)
const displayEdges = computed(() => {
  if (!depthLimited.value) return view.value.edges
  const ids = new Set(displayNodes.value.map((n) => n.id))
  return view.value.edges.filter((e) => ids.has(e.source) && ids.has(e.target))
})

const TYPE_NAMES: Record<string, string> = {
  root: '技术领域',
  position: '岗位',
  domain_branch: '领域分支',
  skillset_branch: '技能集',
  module: '知识模块',
  knowledge: '知识点',
}

function typeName(t: string) {
  return TYPE_NAMES[t] ?? t
}

const legend = [
  { label: 'L1 领域', color: '#122d6e' },
  { label: 'L2 岗位', color: '#2f47b8' },
  { label: 'L3 分支', color: '#3f5ae0' },
  { label: 'L4 技能集', color: '#7893de' },
  { label: 'L5 知识', color: '#b4c2f2' },
]
</script>

<template>
  <view class="graph-page">
    <view class="page-head" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="head-row">
        <view>
          <text class="page-title">技能图谱</text>
          <text class="page-sub">五层技能森林 · 点按节点查看与下钻</text>
        </view>
        <view class="reset-btn" @tap="resetView">
          <uni-icons type="refreshempty" size="16" color="#4f6ef6" />
          <text>重置</text>
        </view>
      </view>

      <view class="search-box">
        <uni-icons type="search" size="18" color="#989eae" />
        <input
          v-model="keyword"
          class="search-input"
          placeholder="搜索技能 / 岗位 / 知识点"
          placeholder-class="search-placeholder"
          confirm-type="search"
          @confirm="onSearch"
        />
        <view class="search-go" @tap="onSearch">搜索</view>
      </view>
    </view>

    <view v-if="!loading && displayNodes.length" class="graph-stats">
      <text>{{ depthLimited ? '仅展示 L1-L3 层' : '全景视图' }}</text>
      <text class="dot">·</text>
      <text>{{ displayNodes.length }} 节点</text>
      <text class="dot">·</text>
      <text>{{ displayEdges.length }} 关系</text>
    </view>

    <view v-if="loading" class="graph-skeleton card">
      <view class="skeleton" style="width: 40%; height: 28rpx; margin: 24rpx 32rpx 0" />
      <view class="skeleton" style="width: 90%; height: 600rpx; margin: 28rpx 32rpx" />
    </view>

    <SkillGraph
      v-else-if="displayNodes.length"
      :nodes="displayNodes"
      :edges="displayEdges"
      :highlights="highlights"
      :selected-id="selected?.id ?? null"
      @select="onSelect"
    />

    <EmptyState
      v-else
      icon="link"
      title="图谱数据为空"
      desc="请确认后端已启动并完成图谱同步"
    >
      <view class="btn-primary" style="margin-top: 32rpx; padding: 0 60rpx" @tap="resetView">重新加载</view>
    </EmptyState>

    <!-- 图例 -->
    <view class="legend">
      <view v-for="l in legend" :key="l.label" class="legend-item">
        <view class="legend-dot" :style="{ background: l.color }" />
        <text>{{ l.label }}</text>
      </view>
    </view>

    <!-- 节点信息卡 -->
    <view v-if="selected" class="node-card card fade-up">
      <view class="node-head">
        <view class="node-title-wrap">
          <text class="node-name">{{ selected.label }}</text>
          <view class="node-chips">
            <text class="chip brand">{{ typeName(selected.type) }}</text>
            <text class="chip">L{{ selected.layer }}</text>
          </view>
        </view>
        <view class="node-close" @tap="clearSelected">
          <uni-icons type="closeempty" size="16" color="#989eae" />
        </view>
      </view>
      <view class="node-actions">
        <view class="node-action primary" @tap="expandSelected">下钻展开</view>
      </view>
    </view>

    <AppTabBar current="graph" />
  </view>
</template>

<style lang="scss" scoped>
.graph-page {
  min-height: 100vh;
  padding-bottom: calc(200rpx + env(safe-area-inset-bottom));
}

.page-head {
  padding: 24rpx 32rpx 0;
}

.head-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.page-title {
  display: block;
  font-size: 40rpx;
  font-weight: 700;
  color: $text-1;
  letter-spacing: -0.02em;
}

.page-sub {
  display: block;
  margin-top: 4rpx;
  font-size: 24rpx;
  color: $text-3;
}

.reset-btn {
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 12rpx 24rpx;
  border-radius: $radius-full;
  background: $brand-light;
  color: $brand;
  font-size: 24rpx;
  font-weight: 600;

  &:active { opacity: 0.8; }
}

.search-box {
  display: flex;
  align-items: center;
  gap: 14rpx;
  margin-top: 24rpx;
  padding: 0 12rpx 0 26rpx;
  height: 84rpx;
  border-radius: $radius-md;
  background: $card;
  border: 1rpx solid $border;
  box-shadow: $shadow-sm;
}

.search-input {
  flex: 1;
  font-size: 28rpx;
  color: $text-1;
}

.search-placeholder {
  color: $placeholder;
}

.search-go {
  padding: 14rpx 30rpx;
  border-radius: 14rpx;
  background: linear-gradient(135deg, $brand, #7b8ff7);
  color: #fff;
  font-size: 26rpx;
  font-weight: 600;
}

.graph-stats {
  display: flex;
  align-items: center;
  gap: 10rpx;
  margin: 20rpx 44rpx 14rpx;
  font-size: 22rpx;
  color: $text-3;

  .dot { color: $placeholder; }
}

.graph-skeleton {
  margin: 0 32rpx;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx 24rpx;
  margin: 20rpx 44rpx 0;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8rpx;
  font-size: 22rpx;
  color: $text-2;
}

.legend-dot {
  width: 14rpx;
  height: 14rpx;
  border-radius: 50%;
}

.node-card {
  position: fixed;
  left: 32rpx;
  right: 32rpx;
  bottom: calc(140rpx + env(safe-area-inset-bottom));
  z-index: 60;
  padding: 28rpx 32rpx;
  box-shadow: $shadow-lg;
}

.node-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.node-title-wrap {
  flex: 1;
  min-width: 0;
}

.node-name {
  display: block;
  font-size: 32rpx;
  font-weight: 700;
  color: $text-1;
}

.node-chips {
  display: flex;
  gap: 10rpx;
  margin-top: 10rpx;
}

.node-close {
  padding: 8rpx;
}

.node-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 24rpx;
}

.node-action {
  flex: 1;
  text-align: center;
  padding: 20rpx 0;
  border-radius: $radius-md;
  font-size: 26rpx;
  font-weight: 600;

  &.primary {
    background: linear-gradient(135deg, $brand, #7b8ff7);
    color: #fff;
    box-shadow: 0 6rpx 20rpx $brand-glow;
  }

  &:active { transform: scale(0.98); }
}
</style>

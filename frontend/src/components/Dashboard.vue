<script setup>
import { ref, reactive, watch, nextTick, onBeforeUnmount } from 'vue'
import * as api from '../api.js'
import QuestionDetailModal from './QuestionDetailModal.vue'
import AiAnalysisModal from './AiAnalysisModal.vue'

const props = defineProps({
  theme: { type: String, default: 'light' },
  visible: { type: Boolean, default: false },
})

const emit = defineEmits(['go-workspace', 'push-toast', 'open-image'])

// ---- 统计数据 ----
const stats = ref(null)
const statsLoading = ref(false)

// ---- 待复习题目列表 ----
const reviewItems = ref([])
const reviewTotal = ref(0)
const reviewLoading = ref(false)

// ---- 详情弹窗 ----
const detailOpen = ref(false)
const detailQuestion = ref(null)

// ---- AI 分析 ----
const selectMode = ref(false)
const selectedIds = reactive(new Set())
const aiModalOpen = ref(false)
const aiAnalysisResult = ref(null)
const aiAnalyzing = ref(false)

// ---- 图表 ----
const trendCanvas = ref(null)
const tagCanvas = ref(null)
let trendChart = null
let tagChart = null

// ---- 数据加载 ----
const loadStats = async () => {
  statsLoading.value = true
  try {
    const data = await api.fetchDashboardStats()
    stats.value = data
  } catch (e) {
    emit('push-toast', 'error', '加载统计数据失败')
  } finally {
    statsLoading.value = false
  }
}

const loadReviewItems = async () => {
  reviewLoading.value = true
  try {
    const data = await api.fetchErrorBank({ review_status: '待复习', page: 1, page_size: 10 })
    reviewItems.value = data.items || []
    reviewTotal.value = data.total || 0
  } catch (e) {
    emit('push-toast', 'error', '加载待复习题目失败')
  } finally {
    reviewLoading.value = false
  }
}

const loadAll = () => { loadStats(); loadReviewItems() }

// ---- 图表 ----
const initCharts = async () => {
  await nextTick()
  if (!window.Chart || !stats.value) return
  const isDark = props.theme === 'dark'
  const textColor = isDark ? 'rgba(255,255,255,0.6)' : 'rgba(15,23,42,0.6)'
  const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(15,23,42,0.05)'

  // 趋势图
  if (trendCanvas.value) {
    if (trendChart) trendChart.destroy()
    const dc = stats.value.daily_counts || []
    trendChart = new window.Chart(trendCanvas.value, {
      type: 'line',
      data: {
        labels: dc.map(d => d.date),
        datasets: [{
          label: '每日新增',
          data: dc.map(d => d.count),
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59,130,246,0.1)',
          borderWidth: 2, tension: 0.4, fill: true,
          pointBackgroundColor: '#3b82f6',
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: textColor, usePointStyle: true, boxWidth: 6 } } },
        scales: {
          x: { grid: { display: false }, ticks: { color: textColor } },
          y: { grid: { color: gridColor }, ticks: { color: textColor, stepSize: 1 }, beginAtZero: true },
        }
      }
    })
  }

  // 知识点环形图
  if (tagCanvas.value) {
    if (tagChart) tagChart.destroy()
    const ts = stats.value.tag_stats || []
    const colors = ['#6366f1', '#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#14b8a6', isDark ? '#334155' : '#cbd5e1']
    tagChart = new window.Chart(tagCanvas.value, {
      type: 'doughnut',
      data: {
        labels: ts.map(t => t.tag_name),
        datasets: [{ data: ts.map(t => t.count), backgroundColor: colors.slice(0, ts.length), borderWidth: 0, hoverOffset: 4 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '70%',
        plugins: { legend: { position: 'right', labels: { color: textColor, usePointStyle: true, boxWidth: 8 } } }
      }
    })
  }
}

// ---- 题目操作 ----
const getSummary = (q) => {
  const blocks = q.content_json || []
  const texts = blocks.filter(b => b.block_type === 'text').map(b => b.content || '')
  const joined = texts.join(' ').replace(/<[^>]+>/g, '')
  return joined.length > 100 ? joined.slice(0, 100) + '...' : joined
}

const openDetail = (q) => { detailQuestion.value = q; detailOpen.value = true }
const closeDetail = () => { detailOpen.value = false; detailQuestion.value = null }

const quickMarkStatus = async (q, status) => {
  try {
    const data = await api.updateReviewStatus(q.id, status)
    q.review_status = data.review_status
    emit('push-toast', 'success', `已标记为「${status}」`)
    if (status !== '待复习') {
      reviewItems.value = reviewItems.value.filter(x => x.id !== q.id)
      reviewTotal.value = Math.max(0, reviewTotal.value - 1)
    }
    loadStats()
  } catch (e) {
    emit('push-toast', 'error', '更新状态失败')
  }
}

const onDeleted = (id) => {
  reviewItems.value = reviewItems.value.filter(q => q.id !== id)
  reviewTotal.value = Math.max(0, reviewTotal.value - 1)
  closeDetail()
  loadStats()
}

const onAnswerSaved = (id, answer, updatedAt) => {
  const q = reviewItems.value.find(x => x.id === id)
  if (q) { q.user_answer = answer; q.updated_at = updatedAt }
}

const onReviewStatusChanged = (id, status, updatedAt) => {
  const q = reviewItems.value.find(x => x.id === id)
  if (q) { q.review_status = status; q.updated_at = updatedAt }
  if (status !== '待复习') {
    reviewItems.value = reviewItems.value.filter(x => x.id !== id)
    reviewTotal.value = Math.max(0, reviewTotal.value - 1)
  }
  loadStats()
}

// ---- AI 分析操作 ----
const toggleSelectMode = () => {
  selectMode.value = !selectMode.value
  if (!selectMode.value) selectedIds.clear()
}

const toggleSelect = (id) => {
  if (selectedIds.has(id)) selectedIds.delete(id)
  else selectedIds.add(id)
}

const selectAllReview = () => {
  for (const q of reviewItems.value) selectedIds.add(q.id)
}

const startAiAnalysis = async () => {
  if (!selectedIds.size) {
    emit('push-toast', 'error', '请先选择要分析的题目')
    return
  }
  aiAnalyzing.value = true
  aiModalOpen.value = true
  aiAnalysisResult.value = null
  try {
    const data = await api.requestAiAnalysis(Array.from(selectedIds))
    aiAnalysisResult.value = data.analysis
  } catch (e) {
    emit('push-toast', 'error', 'AI 分析失败: ' + (e instanceof Error ? e.message : String(e)))
    aiModalOpen.value = false
  } finally {
    aiAnalyzing.value = false
  }
}

const closeAiModal = () => {
  aiModalOpen.value = false
  aiAnalysisResult.value = null
}

// ---- 生命周期 ----
watch(() => props.visible, (v) => {
  if (v) { loadAll(); nextTick(initCharts) }
}, { immediate: true })

watch(() => [props.theme, stats.value], () => {
  if (props.visible && stats.value) nextTick(initCharts)
})

onBeforeUnmount(() => {
  if (trendChart) trendChart.destroy()
  if (tagChart) tagChart.destroy()
})
</script>

<template>
  <div class="relative min-h-full">
    <!-- 动态光晕 -->
    <div class="pointer-events-none absolute inset-0 z-0 overflow-hidden">
      <div class="absolute -top-[5%] right-[-5%] h-[45vw] w-[45vw] rounded-full bg-indigo-500/10 mix-blend-multiply blur-[120px] dark:bg-indigo-600/15 dark:mix-blend-screen"></div>
      <div class="absolute -bottom-[10%] left-[-10%] h-[35vw] w-[35vw] rounded-full bg-cyan-400/10 mix-blend-multiply blur-[100px] dark:bg-cyan-600/10 dark:mix-blend-screen"></div>
    </div>

    <div class="container relative z-10 mx-auto max-w-6xl px-4 py-8 sm:px-8">
      <!-- 页面标题 -->
      <div class="mb-10 flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div class="mb-2 inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-600 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-300">
            <i class="fa-solid fa-chart-pie animate-pulse"></i> 学习数据中心
          </div>
          <h2 class="text-3xl font-black tracking-tight text-slate-900 sm:text-4xl dark:text-white">我的错题本</h2>
          <p class="mt-2 text-sm font-medium text-slate-500 dark:text-slate-400">
            <i class="fa-solid fa-brain text-indigo-500"></i> 追踪复习进度，掌握薄弱环节
          </p>
        </div>
        <button @click="emit('go-workspace')" class="btn-primary group h-12 px-8 shadow-xl shadow-blue-500/20">
          <i class="fa-solid fa-plus-circle transition-transform group-hover:rotate-90"></i> 录入新题目
        </button>
      </div>

      <!-- 统计卡片 -->
      <div v-if="statsLoading" class="mb-8 flex justify-center py-12">
        <div class="h-10 w-10 animate-spin rounded-full border-4 border-indigo-500/20 border-t-indigo-500"></div>
      </div>
      <div v-else class="mb-8 grid grid-cols-1 gap-5 sm:grid-cols-3">
        <div class="rounded-2xl border border-slate-200/60 bg-white/60 p-6 shadow-sm backdrop-blur-xl dark:border-white/10 dark:bg-[#0A0A0F]/60">
          <div class="mb-2 flex items-center justify-between text-sm font-bold text-slate-500 dark:text-slate-400">
            待复习 <i class="fa-solid fa-clock text-orange-500"></i>
          </div>
          <div class="text-3xl font-black text-slate-900 dark:text-white">
            {{ stats?.review_stats?.['待复习'] || 0 }} <span class="ml-1 text-sm font-medium text-slate-400">道</span>
          </div>
        </div>
        <div class="rounded-2xl border border-slate-200/60 bg-white/60 p-6 shadow-sm backdrop-blur-xl dark:border-white/10 dark:bg-[#0A0A0F]/60">
          <div class="mb-2 flex items-center justify-between text-sm font-bold text-slate-500 dark:text-slate-400">
            复习中 <i class="fa-solid fa-spinner text-amber-500"></i>
          </div>
          <div class="text-3xl font-black text-slate-900 dark:text-white">
            {{ stats?.review_stats?.['复习中'] || 0 }} <span class="ml-1 text-sm font-medium text-slate-400">道</span>
          </div>
        </div>
        <div class="rounded-2xl border border-slate-200/60 bg-white/60 p-6 shadow-sm backdrop-blur-xl dark:border-white/10 dark:bg-[#0A0A0F]/60">
          <div class="mb-2 flex items-center justify-between text-sm font-bold text-slate-500 dark:text-slate-400">
            已掌握 <i class="fa-solid fa-circle-check text-emerald-500"></i>
          </div>
          <div class="text-3xl font-black text-slate-900 dark:text-white">
            {{ stats?.review_stats?.['已掌握'] || 0 }} <span class="ml-1 text-sm font-medium text-slate-400">道</span>
          </div>
        </div>
      </div>

      <!-- 图表区 -->
      <div class="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div class="rounded-2xl border border-slate-200/60 bg-white/60 p-6 shadow-sm backdrop-blur-xl lg:col-span-2 dark:border-white/10 dark:bg-[#0A0A0F]/60">
          <h3 class="mb-4 flex items-center gap-2 text-sm font-black text-slate-700 dark:text-slate-300">
            <i class="fa-solid fa-chart-line text-blue-500"></i> 最近 7 天新增趋势
          </h3>
          <div class="relative h-[220px] w-full"><canvas ref="trendCanvas"></canvas></div>
        </div>
        <div class="rounded-2xl border border-slate-200/60 bg-white/60 p-6 shadow-sm backdrop-blur-xl dark:border-white/10 dark:bg-[#0A0A0F]/60">
          <h3 class="mb-4 flex items-center gap-2 text-sm font-black text-slate-700 dark:text-slate-300">
            <i class="fa-solid fa-tags text-indigo-500"></i> 知识点分布
          </h3>
          <div v-if="stats?.tag_stats?.length" class="relative flex h-[220px] w-full justify-center"><canvas ref="tagCanvas"></canvas></div>
          <div v-else class="flex h-[220px] items-center justify-center text-sm text-slate-400">暂无标签数据</div>
        </div>
      </div>

      <!-- 待复习题目列表 -->
      <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h3 class="flex items-center gap-2 text-lg font-black text-slate-900 dark:text-white">
          <i class="fa-solid fa-clock text-orange-500"></i> 待复习题目
          <span v-if="reviewTotal" class="ml-2 rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-bold text-orange-600 dark:bg-orange-500/10 dark:text-orange-400">{{ reviewTotal }}</span>
        </h3>
        <div v-if="reviewItems.length" class="flex items-center gap-2">
          <button @click="toggleSelectMode"
            class="rounded-lg border px-3 py-1.5 text-xs font-bold transition-all"
            :class="selectMode ? 'border-blue-500 bg-blue-50 text-blue-600 dark:border-blue-400/30 dark:bg-blue-500/10 dark:text-blue-400' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-white/10 dark:bg-white/5 dark:text-slate-400'">
            <i class="fa-solid mr-1" :class="selectMode ? 'fa-xmark' : 'fa-list-check'"></i>
            {{ selectMode ? '取消选择' : '选择题目' }}
          </button>
          <template v-if="selectMode">
            <button @click="selectAllReview" class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-600 transition-all hover:bg-slate-50 dark:border-white/10 dark:bg-white/5 dark:text-slate-400">
              全选
            </button>
            <button @click="startAiAnalysis" :disabled="!selectedIds.size || aiAnalyzing"
              class="rounded-lg bg-gradient-to-r from-indigo-500 to-blue-600 px-4 py-1.5 text-xs font-bold text-white shadow-md shadow-indigo-500/20 transition-all hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed">
              <i class="fa-solid fa-wand-magic-sparkles mr-1" :class="{ 'animate-spin': aiAnalyzing }"></i>
              AI 错题分析 <span v-if="selectedIds.size">({{ selectedIds.size }})</span>
            </button>
          </template>
        </div>
      </div>

      <div v-if="reviewLoading" class="flex justify-center py-16">
        <div class="h-12 w-12 animate-spin rounded-full border-4 border-blue-500/20 border-t-blue-500"></div>
      </div>

      <div v-else-if="!reviewItems.length" class="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50/50 py-20 dark:border-white/5 dark:bg-white/5">
        <i class="fa-solid fa-circle-check mb-4 text-4xl text-emerald-400"></i>
        <p class="text-lg font-black text-slate-900 dark:text-white">全部搞定了</p>
        <p class="mt-1 text-sm text-slate-500">没有待复习的题目，继续保持</p>
      </div>

      <div v-else class="space-y-4">
        <div v-for="q in reviewItems" :key="q.id"
          @click="selectMode ? toggleSelect(q.id) : openDetail(q)"
          class="group cursor-pointer rounded-2xl border border-slate-200/60 bg-white/80 p-5 shadow-sm backdrop-blur-md transition-all hover:-translate-y-0.5 hover:shadow-lg dark:border-white/10 dark:bg-[#0A0A0F]/60"
          :class="{ 'ring-2 ring-indigo-500/50 border-indigo-300 dark:border-indigo-500/40': selectMode && selectedIds.has(q.id) }">
          <div class="flex items-start gap-4">
            <!-- 选择复选框 -->
            <div v-if="selectMode" class="flex shrink-0 items-center pt-1" @click.stop="toggleSelect(q.id)">
              <div class="flex h-5 w-5 items-center justify-center rounded-md border-2 transition-all"
                :class="selectedIds.has(q.id) ? 'border-indigo-500 bg-indigo-500 text-white' : 'border-slate-300 dark:border-slate-600'">
                <i v-if="selectedIds.has(q.id)" class="fa-solid fa-check text-[10px]"></i>
              </div>
            </div>
            <div class="min-w-0 flex-1">
              <div class="mb-3 flex flex-wrap items-center gap-2">
                <span v-if="q.subject" class="rounded-lg bg-blue-50 px-2.5 py-1 text-[10px] font-black text-blue-600 dark:bg-blue-500/10 dark:text-blue-300">{{ q.subject }}</span>
                <span class="rounded-lg bg-slate-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-widest text-slate-500 dark:bg-white/5 dark:text-slate-400">{{ q.question_type }}</span>
                <span v-for="tag in (q.knowledge_tags || []).slice(0, 3)" :key="tag" class="rounded-lg border border-indigo-500/20 bg-indigo-500/5 px-2 py-0.5 text-[10px] font-bold text-indigo-600 dark:text-indigo-300">{{ tag }}</span>
                <span class="ml-auto text-[10px] font-bold text-slate-400">{{ q.created_at ? new Date(q.created_at).toLocaleDateString() : '' }}</span>
              </div>
              <p class="line-clamp-2 text-sm font-bold leading-relaxed text-slate-700 group-hover:text-slate-900 dark:text-slate-300 dark:group-hover:text-white">{{ getSummary(q) }}</p>
            </div>
            <div class="flex shrink-0 gap-2" @click.stop>
              <button @click="quickMarkStatus(q, '复习中')" class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-[10px] font-black text-amber-600 transition-all hover:bg-amber-100 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-400" title="标记为复习中">
                <i class="fa-solid fa-spinner mr-1"></i>复习中
              </button>
              <button @click="quickMarkStatus(q, '已掌握')" class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-[10px] font-black text-emerald-600 transition-all hover:bg-emerald-100 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-400" title="标记为已掌握">
                <i class="fa-solid fa-circle-check mr-1"></i>已掌握
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <QuestionDetailModal
      :open="detailOpen"
      :question="detailQuestion"
      @close="closeDetail"
      @open-image="(src) => emit('open-image', src)"
      @deleted="onDeleted"
      @answer-saved="onAnswerSaved"
      @review-status-changed="onReviewStatusChanged"
      @push-toast="(type, msg) => emit('push-toast', type, msg)"
    />

    <!-- AI 分析弹窗 -->
    <AiAnalysisModal
      :open="aiModalOpen"
      :loading="aiAnalyzing"
      :analysis="aiAnalysisResult"
      @close="closeAiModal"
    />
  </div>
</template>

<style scoped>
.container {
  animation: dashEntry 0.8s cubic-bezier(0.2, 0, 0, 1) both;
}
@keyframes dashEntry {
  from { opacity: 0; transform: scale(0.98) translateY(20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
</style>
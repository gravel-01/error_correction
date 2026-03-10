<script setup>

defineProps({
  splitEnabled: { type: Boolean, default: false },
  exportEnabled: { type: Boolean, default: false },
  splitting: { type: Boolean, default: false },
  splitCompleted: { type: Boolean, default: false },
})

const emit = defineEmits(['split', 'export', 'save-to-db', 'reset'])
</script>

<template>
  <div class="mt-10 flex flex-wrap items-center justify-center gap-5 relative z-10">
    <!-- 主操作按钮：引入超级炫酷的炫彩发光效果 -->
    <button
      type="button"
      class="group relative inline-flex h-12 items-center justify-center sm:w-auto w-full disabled:cursor-not-allowed disabled:opacity-50"
      :disabled="!splitEnabled"
      @click="emit('split')"
    >
      <!-- 背景光晕 (悬浮时放大并提亮) -->
      <div
        class="absolute -inset-px rounded-xl bg-gradient-to-r from-[#44BCFF] via-[#FF44EC] to-[#FF675E] blur-md transition-all duration-500 opacity-40 group-hover:opacity-80 group-hover:-inset-1 group-hover:blur-lg"
        :class="!splitEnabled && 'hidden'"
      ></div>
      <!-- 按钮本体 -->
      <span class="relative inline-flex h-full w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-8 text-sm font-bold text-white shadow-xl transition-all duration-200 group-hover:bg-blue-700 dark:border dark:border-white/10 dark:bg-slate-900 dark:shadow-none dark:group-hover:bg-slate-800">
        <template v-if="splitting">
          <i class="fa-solid fa-circle-notch fa-spin text-blue-200"></i>
          <span class="tracking-wide">正在驱动 AI 分割...</span>
        </template>
        <template v-else-if="splitCompleted">
          <i class="fa-solid fa-circle-check text-emerald-400"></i>
          <span class="tracking-wide">解析已完成</span>
        </template>
        <template v-else>
          <i class="fa-solid fa-wand-magic-sparkles text-blue-200 dark:text-fuchsia-300"></i>
          <span class="tracking-wide">启动 AI 智能分割</span>
        </template>
      </span>
    </button>

    <!-- 导出按钮：翡翠色玻璃质感 -->
    <button
      type="button"
      class="group relative inline-flex h-12 items-center justify-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-50/80 px-6 text-sm font-bold text-emerald-700 shadow-sm backdrop-blur-md transition-all duration-300 hover:bg-emerald-100 hover:shadow-emerald-500/20 focus:outline-none focus:ring-4 focus:ring-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300 dark:hover:bg-emerald-500/20 dark:hover:shadow-[0_0_20px_rgba(16,185,129,0.2)]"
      :disabled="!exportEnabled"
      @click="emit('export')"
    >
      <i class="fa-solid fa-file-export transition-transform group-hover:-translate-y-0.5"></i>
      导出错题本
    </button>

    <!-- 导入错题库按钮：靛蓝色玻璃质感 -->
    <button
      type="button"
      class="group relative inline-flex h-12 items-center justify-center gap-2 rounded-xl border border-indigo-500/30 bg-indigo-50/80 px-6 text-sm font-bold text-indigo-700 shadow-sm backdrop-blur-md transition-all duration-300 hover:bg-indigo-100 hover:shadow-indigo-500/20 focus:outline-none focus:ring-4 focus:ring-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-50 dark:border-indigo-500/20 dark:bg-indigo-500/10 dark:text-indigo-300 dark:hover:bg-indigo-500/20 dark:hover:shadow-[0_0_20px_rgba(99,102,241,0.2)]"
      :disabled="!exportEnabled"
      @click="emit('save-to-db')"
    >
      <i class="fa-solid fa-database transition-transform group-hover:-translate-y-0.5"></i>
      导入错题库
    </button>

    <!-- 重置按钮：暗黑微透光质感 -->
    <button
      type="button"
      class="group inline-flex h-12 items-center justify-center gap-2 rounded-xl border border-slate-200/60 bg-white/60 px-6 text-sm font-bold text-slate-700 shadow-sm backdrop-blur-md transition-all duration-300 hover:bg-slate-50 hover:text-slate-900 focus:outline-none focus:ring-4 focus:ring-slate-200/50 dark:border-slate-700/60 dark:bg-slate-800/60 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-white dark:focus:ring-slate-800/50"
      @click="emit('reset')"
    >
      <i class="fa-solid fa-arrow-rotate-left transition-transform group-hover:-rotate-180 duration-500"></i>
      重新开始
    </button>
  </div>
</template>
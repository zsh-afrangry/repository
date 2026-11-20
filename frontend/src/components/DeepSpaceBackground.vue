<script setup lang="ts">
/**
 * 全站统一深空视觉背景套件 (DeepSpaceBackground)
 *
 * 对应文档：docs/17_账单模块视觉重构与体验优化方案.md
 *
 * 整合：
 * 1. 渐变底色 (KnowledgeMapBackground)
 * 2. 动态引力粒子星图 (StarfieldBackground)
 * 3. 柔和氛围光晕 (AmbientGlow)
 * 4. 几何网格底纹 (GridDecoration)
 *
 * 供首页、Notes、Bills 及后续新模块一键声明式复用。
 */
import KnowledgeMapBackground from './KnowledgeMapBackground.vue'
import StarfieldBackground from './StarfieldBackground.vue'
import AmbientGlow from './ui/AmbientGlow.vue'
import GridDecoration from './ui/GridDecoration.vue'

withDefaults(defineProps<{
  stars?: boolean
  interactive?: boolean
  glow?: boolean
  grid?: boolean
}>(), {
  stars: true,
  interactive: true,
  glow: true,
  grid: false,
})
</script>

<template>
  <div class="deep-space-background-suite" aria-hidden="true">
    <KnowledgeMapBackground />
    <StarfieldBackground v-if="stars" :interactive="interactive" />
    <GridDecoration v-if="grid" />
    <AmbientGlow v-if="glow" />
  </div>
</template>

<style scoped>
.deep-space-background-suite {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}
</style>

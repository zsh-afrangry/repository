<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import KnowledgeMapBackground from '@/components/KnowledgeMapBackground.vue'

const route = useRoute()
const isCollapsed = ref(false)

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}
</script>

<template>
  <div class="tradesim-layout">
    <KnowledgeMapBackground />
    <el-container class="tradesim-shell">
      <el-aside :width="isCollapsed ? '64px' : '200px'" class="tradesim-sidebar">
        <div class="tradesim-sidebar-logo" @click="toggleCollapse">
          <span class="tradesim-logo-icon">📈</span>
          <span v-if="!isCollapsed" class="tradesim-logo-text">TradeSim</span>
        </div>

        <el-menu
          :default-active="route.path"
          :collapse="isCollapsed"
          :collapse-transition="true"
          router
          class="tradesim-sidebar-menu"
        >
          <el-menu-item index="/tradesim/simulate">
            <el-icon><DataLine /></el-icon>
            <template #title>网格回测</template>
          </el-menu-item>
          <el-menu-item index="/tradesim/yearline">
            <el-icon><TrendCharts /></el-icon>
            <template #title>年线策略</template>
          </el-menu-item>
          <el-menu-item index="/tradesim/dashboard">
            <el-icon><Star /></el-icon>
            <template #title>收藏库</template>
          </el-menu-item>
        </el-menu>

        <button type="button" class="tradesim-sidebar-collapse-btn" @click="toggleCollapse">
          <el-icon>
            <ArrowLeft v-if="!isCollapsed" />
            <ArrowRight v-else />
          </el-icon>
        </button>
      </el-aside>

      <el-main class="tradesim-main-content">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<style scoped>
.tradesim-layout,
.tradesim-shell {
  min-height: 100vh;
}

.tradesim-layout {
  position: relative;
  isolation: isolate;
  background: transparent;
}

.tradesim-shell {
  position: relative;
  z-index: 1;
  background: transparent;
}

.tradesim-sidebar {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #2c3e50;
  transition: width 0.3s;
}

.tradesim-sidebar-logo {
  display: flex;
  align-items: center;
  height: 60px;
  padding: 0 20px;
  color: #fff;
  cursor: pointer;
  border-bottom: 1px solid rgb(255 255 255 / 10%);
  white-space: nowrap;
  overflow: hidden;
}

.tradesim-logo-icon {
  flex-shrink: 0;
  font-size: 24px;
}

.tradesim-logo-text {
  margin-left: 10px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
}

.tradesim-sidebar-menu {
  flex: 1;
  border-right: none;
  background: #2c3e50;
  --el-menu-bg-color: #2c3e50;
  --el-menu-text-color: #bdc3c7;
  --el-menu-active-color: #fff;
  --el-menu-hover-bg-color: #34495e;
  --el-menu-item-height: 52px;
}

.tradesim-sidebar-collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 48px;
  color: #bdc3c7;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-top: 1px solid rgb(255 255 255 / 10%);
  transition: background-color 0.2s, color 0.2s;
}

.tradesim-sidebar-collapse-btn:hover {
  color: #fff;
  background: #34495e;
}

.tradesim-main-content {
  position: relative;
  z-index: 1;
  min-width: 0;
  padding: 0;
  overflow: auto;
  background: transparent;
}
</style>

import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import './styles/main.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('./views/Dashboard.vue'),
    },
    {
      path: '/bills',
      name: 'bills',
      component: () => import('./views/Bills.vue'),
    },
    {
      // 储物间：存放从主界面撤下的静态界面草稿（纯静态，不接后端数据）。
      path: '/vault',
      name: 'vault',
      component: () => import('./views/Vault.vue'),
    },
    { path: '/Transformer', redirect: '/notes/transformer' },
    { path: '/Database', redirect: '/notes/database' },
    { path: '/CNN', redirect: '/notes/cnn' },
    { path: '/MachineLearning', redirect: '/notes/machine-learning' },
    { path: '/notes', component: () => import('./views/Notes.vue') },
    { path: '/notes/:topicId', component: () => import('./views/Notes.vue') },
    { path: '/notes/:topicId/units/:unitId', component: () => import('./views/Notes.vue') },
    {
      path: '/tradesim',
      component: () => import('./features/tradesim/layouts/TradeSimLayout.vue'),
      children: [
        {
          path: '',
          redirect: '/tradesim/simulate',
        },
        {
          path: 'simulate',
          name: 'tradesim-simulate',
          component: () => import('./features/tradesim/views/TradeSimSimulator.vue'),
        },
        {
          path: 'dashboard',
          name: 'tradesim-dashboard',
          component: () => import('./features/tradesim/views/TradeSimDashboard.vue'),
        },
        {
          path: 'detail/:id',
          name: 'tradesim-detail',
          component: () => import('./features/tradesim/views/TradeSimDetail.vue'),
        },
        {
          path: 'yearline',
          name: 'tradesim-yearline',
          component: () => import('./features/tradesim/views/TradeSimYearLine.vue'),
        },
      ],
    },
  ],
})

const app = createApp(App)
app.use(ElementPlus)
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}
app.use(router)
app.mount('#app')

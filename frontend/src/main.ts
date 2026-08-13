import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
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
      path: '/Transformer',
      name: 'transformer',
      component: () => import('./views/Notes.vue'),
    },
    {
      path: '/Database',
      name: 'database-notes',
      component: () => import('./views/Notes.vue'),
    },
    {
      path: '/CNN',
      name: 'cnn-notes',
      component: () => import('./views/Notes.vue'),
    },
    {
      path: '/MachineLearning',
      name: 'machine-learning-notes',
      component: () => import('./views/Notes.vue'),
    },
    {
      path: '/notes',
      redirect: '/Transformer',
    },
  ],
})

const app = createApp(App)
app.use(router)
app.mount('#app')

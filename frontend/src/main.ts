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
  ],
})

const app = createApp(App)
app.use(router)
app.mount('#app')

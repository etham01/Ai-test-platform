import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import ExecutionDetailView from '@/views/ExecutionDetailView.vue'
import ExecutionsView from '@/views/ExecutionsView.vue'
import PageDetailView from '@/views/PageDetailView.vue'
import PagesView from '@/views/PagesView.vue'
import ProjectOverviewView from '@/views/ProjectOverviewView.vue'
import ProjectSettingsView from '@/views/ProjectSettingsView.vue'
import ProjectShellView from '@/views/ProjectShellView.vue'
import ProjectsView from '@/views/ProjectsView.vue'
import RequirementsView from '@/views/RequirementsView.vue'
import ScriptsView from '@/views/ScriptsView.vue'
import TestCasesView from '@/views/TestCasesView.vue'
import WorkflowsView from '@/views/WorkflowsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', redirect: '/projects' },
        {
          path: 'projects',
          name: 'projects',
          component: ProjectsView,
          meta: { title: '项目' },
        },
        {
          path: 'projects/:projectId',
          component: ProjectShellView,
          children: [
            {
              path: '',
              redirect: (to) => `/projects/${to.params.projectId}/overview`,
            },
            {
              path: 'overview',
              component: ProjectOverviewView,
              meta: { title: '项目概览' },
            },
            {
              path: 'pages',
              component: PagesView,
              meta: { title: '页面采集' },
            },
            {
              path: 'pages/:pageId',
              component: PageDetailView,
              props: true,
              meta: { title: '页面详情' },
            },
            {
              path: 'workflows',
              component: WorkflowsView,
              meta: { title: '业务流程' },
            },
            {
              path: 'requirements',
              component: RequirementsView,
              meta: { title: '测试需求' },
            },
            {
              path: 'cases',
              component: TestCasesView,
              meta: { title: '测试用例' },
            },
            {
              path: 'scripts',
              component: ScriptsView,
              meta: { title: '测试脚本' },
            },
            {
              path: 'executions',
              component: ExecutionsView,
              meta: { title: '执行与报告' },
            },
            {
              path: 'executions/:executionId',
              component: ExecutionDetailView,
              props: true,
              meta: { title: '执行详情' },
            },
            {
              path: 'settings',
              component: ProjectSettingsView,
              meta: { title: '项目设置' },
            },
          ],
        },
      ],
    },
  ],
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : '智能测试平台'
  document.title = `${title} · SmartTest`
})

export default router

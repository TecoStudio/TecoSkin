<template>
  <div class="oauth-authorize-page auth-shell">
    <div class="bg-orb orb-a"></div>
    <div class="bg-orb orb-b"></div>

    <div class="authorize-card auth-panel">
      <div class="authorize-header">
        <h1>授权登录</h1>
        <p>外部应用正在请求访问你的 vSkin 账号</p>
      </div>

      <template v-if="loading">
        <el-skeleton :rows="5" animated />
      </template>

      <template v-else>
        <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon />

        <div v-else class="app-info">
          <div class="oauth-request-title">{{ requesterName }} 请求以 {{ siteTitle }} 账号登录</div>
          <div class="oauth-scope-list">
            <div class="scope-item" v-for="item in scopeItems" :key="item.key">
              <strong>{{ item.label }}</strong>
              <span>{{ item.description }}</span>
            </div>
          </div>
        </div>

        <div class="actions" v-if="!errorMessage">
          <el-button v-if="!isLogged" type="primary" size="large" @click="goLogin">先登录账号</el-button>
          <template v-else>
            <el-button size="large" @click="deny" :loading="submitting">拒绝</el-button>
            <el-button type="primary" size="large" @click="approve" :loading="submitting">同意授权</el-button>
          </template>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const submitting = ref(false)
const errorMessage = ref('')

const requesterName = ref('第三方应用')
const siteTitle = ref(localStorage.getItem('site_title_cache') || localStorage.getItem('site_name_cache') || 'vSkin')
const clientId = ref('')
const redirectUri = ref('')
const state = ref('')
const scope = ref('userinfo')
const scopeItems = ref([])

const isLogged = computed(() => !!localStorage.getItem('jwt'))

function authHeaders() {
  const token = localStorage.getItem('jwt')
  return token ? { Authorization: 'Bearer ' + token } : {}
}

function currentQueryString() {
  const q = new URLSearchParams(route.query)
  return q.toString()
}

function goLogin() {
  const redirectPath = `/oauth/authorize?${currentQueryString()}`
  router.push({ path: '/login', query: { redirect: redirectPath } })
}

async function loadAuthorizeInfo() {
  loading.value = true
  errorMessage.value = ''
  try {
    const queryClientId = Number(route.query.client_id || 0)
    const queryRedirectUri = String(route.query.redirect_uri || '')
    const queryState = String(route.query.state || '')
    const queryScope = String(route.query.scope || 'userinfo')

    if (!queryClientId || !queryRedirectUri) {
      errorMessage.value = '缺少 client_id 或 redirect_uri 参数'
      return
    }

    const res = await axios.get('/oauth/authorize/check', {
      params: {
        client_id: queryClientId,
        redirect_uri: queryRedirectUri,
        state: queryState,
        scope: queryScope,
      },
    })

    requesterName.value = res.data.requester_name || '第三方应用'
  siteTitle.value = res.data.site_title || res.data.site_name || 'vSkin'
    clientId.value = String(res.data.app_id)
    redirectUri.value = res.data.redirect_uri
    state.value = res.data.state || ''
    scope.value = res.data.scope || 'userinfo'
    scopeItems.value = res.data.scope_items || []
  } catch (e) {
    errorMessage.value = e.response?.data?.detail || '授权请求无效'
  } finally {
    loading.value = false
  }
}

async function submitDecision(approved) {
  if (!isLogged.value) {
    goLogin()
    return
  }

  submitting.value = true
  try {
    const res = await axios.post(
      '/oauth/authorize/decision',
      {
        client_id: Number(clientId.value),
        redirect_uri: redirectUri.value,
        state: state.value,
        scope: scope.value,
        approved,
      },
      { headers: authHeaders() },
    )

    const redirectUrl = res.data?.redirect_url
    if (!redirectUrl) {
      ElMessage.error('未获取到跳转地址')
      return
    }
    window.location.href = redirectUrl
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '授权失败')
  } finally {
    submitting.value = false
  }
}

function approve() {
  submitDecision(true)
}

function deny() {
  submitDecision(false)
}

onMounted(loadAuthorizeInfo)
</script>

<style scoped>
.oauth-authorize-page {
  position: relative;
  overflow: hidden;
}

.bg-orb {
  position: absolute;
  border-radius: 9999px;
  filter: blur(6px);
  opacity: 0.35;
}

.orb-a {
  width: 340px;
  height: 340px;
  background: #8ebadb;
  left: -60px;
  top: -40px;
}

.orb-b {
  width: 320px;
  height: 320px;
  background: #b5c5db;
  right: -80px;
  bottom: -60px;
}

.authorize-card {
  position: relative;
  z-index: 1;
  max-width: 680px;
}

.authorize-header h1 {
  margin: 0;
  font-size: 30px;
  color: var(--color-heading);
}

.authorize-header p {
  margin: 8px 0 22px;
  color: var(--color-text-light);
}

.app-info {
  margin-bottom: 16px;
}

.oauth-request-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-heading);
  margin-bottom: 12px;
}

.oauth-scope-list {
  display: grid;
  gap: 10px;
}

.scope-item {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 10px;
}

.scope-item strong {
  color: var(--color-heading);
}

.scope-item span {
  color: var(--color-text-light);
  font-size: 13px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 22px;
}

@media (max-width: 680px) {
  .authorize-card {
    padding: 20px;
  }

  .actions {
    flex-direction: column;
  }
}
</style>

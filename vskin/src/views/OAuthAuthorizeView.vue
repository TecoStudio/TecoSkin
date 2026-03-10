<template>
  <div class="oauth-authorize-page">
    <div class="bg-orb orb-a"></div>
    <div class="bg-orb orb-b"></div>

    <div class="authorize-card">
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
          <div class="info-row"><span>应用名称</span><strong>{{ appName }}</strong></div>
          <div class="info-row"><span>AppID</span><strong>{{ clientId }}</strong></div>
          <div class="info-row"><span>回调地址</span><strong class="mono">{{ redirectUri }}</strong></div>
        </div>

        <div class="scope-tip" v-if="!errorMessage">
          授权后，该应用可读取你的基础账号信息（ID、邮箱、用户名）。
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

const appName = ref('')
const clientId = ref('')
const redirectUri = ref('')
const state = ref('')

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

    if (!queryClientId || !queryRedirectUri) {
      errorMessage.value = '缺少 client_id 或 redirect_uri 参数'
      return
    }

    const res = await axios.get('/oauth/authorize/check', {
      params: {
        client_id: queryClientId,
        redirect_uri: queryRedirectUri,
        state: queryState,
      },
    })

    appName.value = res.data.client_name || '未命名应用'
    clientId.value = String(res.data.app_id)
    redirectUri.value = res.data.redirect_uri
    state.value = res.data.state || ''
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
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: radial-gradient(circle at 0% 0%, #ffe8be 0%, #fff7ec 40%, #f8f1e8 100%);
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
  background: #f9bb74;
  left: -60px;
  top: -40px;
}

.orb-b {
  width: 320px;
  height: 320px;
  background: #8ac9ff;
  right: -80px;
  bottom: -60px;
}

.authorize-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 640px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 20px;
  box-shadow: 0 14px 48px rgba(52, 35, 13, 0.16);
  backdrop-filter: blur(10px);
  padding: 28px;
}

.authorize-header h1 {
  margin: 0;
  font-size: 30px;
  color: #3b2a14;
}

.authorize-header p {
  margin: 8px 0 22px;
  color: #6e5d49;
}

.app-info {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #f1dfc8;
  border-radius: 10px;
}

.info-row span {
  color: #7a6a58;
}

.info-row strong {
  color: #2d2418;
  text-align: right;
}

.mono {
  font-family: "Consolas", "Courier New", monospace;
  font-size: 12px;
  word-break: break-all;
}

.scope-tip {
  margin-top: 6px;
  color: #7e5a1d;
  background: #fff7e3;
  border: 1px solid #ffe1a7;
  border-radius: 10px;
  padding: 12px;
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

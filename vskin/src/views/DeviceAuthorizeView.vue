<template>
  <div class="device-authorize-page auth-shell">
    <div class="bg-orb orb-a"></div>
    <div class="bg-orb orb-b"></div>

    <div class="device-card auth-panel">
      <div class="device-header">
        <h1>设备授权</h1>
        <p>在这里输入启动器显示的用户代码，然后确认是否允许该设备登录你的账号。</p>
      </div>

      <el-form class="device-form" @submit.prevent>
        <el-form-item label="用户代码">
          <el-input
            v-model="userCodeInput"
            maxlength="9"
            placeholder="例如 ABCD-EFGH"
            @keyup.enter="submitUserCode"
          />
        </el-form-item>
        <div class="device-form-actions">
          <el-button type="primary" :loading="loading" @click="submitUserCode">验证代码</el-button>
        </div>
      </el-form>

      <el-alert v-if="errorMessage" :title="errorMessage" type="error" :closable="false" show-icon />

      <template v-if="loading">
        <el-skeleton :rows="5" animated />
      </template>

      <template v-else-if="preview">
        <div class="device-summary">
          <div class="device-code-line">
            <span>用户代码</span>
            <strong>{{ preview.user_code }}</strong>
          </div>
          <div class="device-title">{{ preview.requester_name || 'USTBL' }} 正在请求访问 {{ preview.site_title || preview.site_name || 'vSkin' }}</div>
          <div class="device-status" :class="preview.status">{{ statusText }}</div>
          <div class="oauth-scope-list">
            <div class="scope-item" v-for="item in preview.scope_items || []" :key="item.key">
              <strong>{{ item.label }}</strong>
              <span>{{ item.description }}</span>
            </div>
          </div>
        </div>

        <div class="actions" v-if="preview.status === 'pending'">
          <el-button v-if="!isLogged" type="primary" size="large" @click="goLogin">先登录账号</el-button>
          <template v-else>
            <el-button size="large" @click="submitDecision(false)" :loading="submitting">拒绝</el-button>
            <el-button type="primary" size="large" @click="submitDecision(true)" :loading="submitting">同意授权</el-button>
          </template>
        </div>

        <el-alert
          v-else-if="preview.status === 'approved'"
          title="该设备已授权，可以返回启动器继续登录。"
          type="success"
          :closable="false"
          show-icon
        />

        <el-alert
          v-else-if="preview.status === 'denied'"
          title="该设备授权已被拒绝。"
          type="warning"
          :closable="false"
          show-icon
        />
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

const userCodeInput = ref('')
const loading = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const preview = ref(null)

const isLogged = computed(() => !!localStorage.getItem('jwt'))
const statusText = computed(() => {
  const status = preview.value?.status
  if (status === 'approved') return '已授权'
  if (status === 'denied') return '已拒绝'
  if (status === 'consumed') return '已完成'
  return '等待确认'
})

function authHeaders() {
  const token = localStorage.getItem('jwt')
  return token ? { Authorization: 'Bearer ' + token } : {}
}

function normalizeUserCode(value) {
  const compact = String(value || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8)
  if (compact.length <= 4) return compact
  return `${compact.slice(0, 4)}-${compact.slice(4)}`
}

function goLogin() {
  router.push({ path: '/login', query: { redirect: `/device?user_code=${encodeURIComponent(userCodeInput.value)}` } })
}

async function loadPreview(userCode) {
  const normalized = normalizeUserCode(userCode)
  if (!normalized || normalized.length !== 9) {
    preview.value = null
    errorMessage.value = '请输入完整的用户代码'
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    const res = await axios.get('/oauth/device/authorize/check', {
      params: { user_code: normalized },
    })
    preview.value = res.data
    userCodeInput.value = res.data.user_code || normalized
  } catch (e) {
    preview.value = null
    errorMessage.value = e.response?.data?.detail || '设备授权请求无效'
  } finally {
    loading.value = false
  }
}

function submitUserCode() {
  const normalized = normalizeUserCode(userCodeInput.value)
  userCodeInput.value = normalized
  router.replace({ path: '/device', query: normalized ? { user_code: normalized } : {} })
  if (normalized.length === 9) {
    loadPreview(normalized)
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
      '/oauth/device/authorize/decision',
      {
        user_code: userCodeInput.value,
        approved,
      },
      { headers: authHeaders() },
    )
    if (preview.value) {
      preview.value.status = res.data?.status || (approved ? 'approved' : 'denied')
    }
    ElMessage.success(approved ? '授权已确认，请返回启动器继续登录' : '已拒绝该设备授权')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提交授权结果失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  const initialCode = normalizeUserCode(route.query.user_code || '')
  if (initialCode) {
    userCodeInput.value = initialCode
    loadPreview(initialCode)
  }
})
</script>

<style scoped>
.device-authorize-page {
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

.device-card {
  position: relative;
  z-index: 1;
  max-width: 720px;
}

.device-header h1 {
  margin: 0;
  font-size: 30px;
  color: var(--color-heading);
}

.device-header p {
  margin: 8px 0 22px;
  color: var(--color-text-light);
}

.device-form {
  margin-bottom: 16px;
}

.device-form-actions {
  display: flex;
  justify-content: flex-end;
}

.device-summary {
  display: grid;
  gap: 14px;
  margin-top: 10px;
}

.device-code-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 12px;
}

.device-code-line span {
  color: var(--color-text-light);
}

.device-code-line strong {
  font-size: 18px;
  letter-spacing: 0.08em;
  color: var(--color-heading);
}

.device-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-heading);
}

.device-status {
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  background: #ecf5ff;
  color: #2f6db3;
}

.device-status.approved {
  background: #edf8f1;
  color: #287d4d;
}

.device-status.denied {
  background: #fff4e8;
  color: #bc6b16;
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
  .device-card {
    padding: 20px;
  }

  .device-code-line {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .actions {
    flex-direction: column;
  }
}
</style>
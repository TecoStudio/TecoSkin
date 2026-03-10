<template>
  <div class="oauth-admin-section animate-fade-in">
    <div class="page-header">
      <div class="page-header-content">
        <div class="page-header-icon"><Link /></div>
        <div class="page-header-text">
          <h2>OAuth 2 应用管理</h2>
          <p class="subtitle">为外部平台创建 appid、secret 和回调地址</p>
        </div>
      </div>
      <div class="page-header-actions">
        <el-button type="primary" :icon="Plus" @click="openCreateDialog">新增应用</el-button>
      </div>
    </div>

    <el-card class="surface-card mb-6" shadow="never">
      <template #header>
        <div class="card-header-flex">
          <span>接口地址与样例</span>
          <el-button text :icon="Refresh" @click="loadData">刷新</el-button>
        </div>
      </template>
      <div class="meta-grid">
        <div class="meta-item">
          <div class="meta-label">授权地址</div>
          <el-input readonly :model-value="meta.authorize_endpoint" />
        </div>
        <div class="meta-item">
          <div class="meta-label">令牌地址</div>
          <el-input readonly :model-value="meta.token_endpoint" />
        </div>
        <div class="meta-item">
          <div class="meta-label">用户信息地址</div>
          <el-input readonly :model-value="meta.userinfo_endpoint" />
        </div>
        <div class="meta-item">
          <div class="meta-label">回调地址样例</div>
          <el-input readonly :model-value="meta.sample_redirect_uri" />
        </div>
      </div>
    </el-card>

    <el-card class="surface-card" shadow="never">
      <template #header>
        <div class="card-header-flex">
          <span>已创建应用（appid 从 1 开始）</span>
          <el-tag type="info" effect="plain">共 {{ apps.length }} 个</el-tag>
        </div>
      </template>

      <el-table :data="apps" style="width: 100%" empty-text="暂无 OAuth 应用">
        <el-table-column prop="app_id" label="AppID" width="100" />
        <el-table-column prop="client_name" label="应用名称" min-width="180">
          <template #default="{ row }">
            <span>{{ row.client_name || '未命名应用' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="redirect_uri" label="回调 URL" min-width="280" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button size="small" type="warning" @click="resetSecret(row)">重置 Secret</el-button>
            <el-button size="small" type="danger" @click="removeApp(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑 OAuth 应用' : '新增 OAuth 应用'" width="560px">
      <el-form label-position="top" :model="form">
        <el-form-item label="应用名称">
          <el-input v-model="form.client_name" placeholder="例如：论坛登录" />
        </el-form-item>
        <el-form-item label="回调 URL">
          <el-input v-model="form.redirect_uri" placeholder="https://your-app.example.com/oauth/callback" />
          <p class="hint-text">必须是完整的 http(s) 地址，并与外部应用配置完全一致。</p>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="secretDialogVisible" title="请保存新的 Client Secret" width="560px">
      <p class="secret-tip">安全提示：该 secret 仅会在当前窗口完整展示一次。</p>
      <el-input readonly :model-value="newSecret" />
      <template #footer>
        <el-button @click="copySecret">复制 Secret</el-button>
        <el-button type="primary" @click="secretDialogVisible = false">我已保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Link, Plus, Refresh } from '@element-plus/icons-vue'

const apps = ref([])
const meta = reactive({
  authorize_endpoint: '',
  token_endpoint: '',
  userinfo_endpoint: '',
  sample_redirect_uri: 'https://your-app.example.com/oauth/callback',
})

const dialogVisible = ref(false)
const secretDialogVisible = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const currentAppId = ref(null)
const newSecret = ref('')

const form = reactive({
  client_name: '',
  redirect_uri: '',
})

const authHeaders = () => ({ Authorization: 'Bearer ' + localStorage.getItem('jwt') })

async function loadData() {
  try {
    const [metaRes, appsRes] = await Promise.all([
      axios.get('/admin/oauth/meta', { headers: authHeaders() }),
      axios.get('/admin/oauth/apps', { headers: authHeaders() }),
    ])
    Object.assign(meta, metaRes.data || {})
    apps.value = (appsRes.data || []).sort((a, b) => Number(a.app_id) - Number(b.app_id))
  } catch (e) {
    ElMessage.error('加载 OAuth 应用失败')
  }
}

function openCreateDialog() {
  isEditing.value = false
  currentAppId.value = null
  form.client_name = ''
  form.redirect_uri = meta.sample_redirect_uri || 'https://your-app.example.com/oauth/callback'
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEditing.value = true
  currentAppId.value = row.app_id
  form.client_name = row.client_name || ''
  form.redirect_uri = row.redirect_uri || ''
  dialogVisible.value = true
}

async function submitForm() {
  if (!form.redirect_uri) {
    ElMessage.warning('请填写回调 URL')
    return
  }

  saving.value = true
  try {
    if (isEditing.value && currentAppId.value) {
      await axios.put(`/admin/oauth/apps/${currentAppId.value}`, form, { headers: authHeaders() })
      ElMessage.success('OAuth 应用已更新')
    } else {
      const res = await axios.post('/admin/oauth/apps', form, { headers: authHeaders() })
      newSecret.value = res.data?.client_secret || ''
      if (newSecret.value) secretDialogVisible.value = true
      ElMessage.success('OAuth 应用已创建')
    }
    dialogVisible.value = false
    await loadData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function resetSecret(row) {
  try {
    await ElMessageBox.confirm(
      `确认重置 AppID ${row.app_id} 的 Secret？旧 Secret 将立即失效。`,
      '确认操作',
      { type: 'warning' },
    )
    const res = await axios.post(`/admin/oauth/apps/${row.app_id}/reset-secret`, {}, { headers: authHeaders() })
    newSecret.value = res.data?.client_secret || ''
    secretDialogVisible.value = true
    ElMessage.success('Secret 已重置')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '重置失败')
    }
  }
}

async function removeApp(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除 AppID ${row.app_id}？该应用已有的授权令牌将同时失效。`,
      '危险操作',
      { type: 'warning' },
    )
    await axios.delete(`/admin/oauth/apps/${row.app_id}`, { headers: authHeaders() })
    ElMessage.success('OAuth 应用已删除')
    await loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

async function copySecret() {
  if (!newSecret.value) return
  try {
    await navigator.clipboard.writeText(newSecret.value)
    ElMessage.success('Secret 已复制')
  } catch (e) {
    ElMessage.error('复制失败，请手动复制')
  }
}

onMounted(loadData)
</script>

<style scoped>
@import "@/assets/styles/animations.css";
@import "@/assets/styles/layout.css";
@import "@/assets/styles/cards.css";
@import "@/assets/styles/headers.css";
@import "@/assets/styles/buttons.css";

.oauth-admin-section {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px 0;
}

.card-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.meta-label {
  font-size: 12px;
  color: var(--color-text-light);
  margin-bottom: 6px;
}

.mb-6 {
  margin-bottom: 24px;
}

.hint-text {
  margin: 6px 0 0 0;
  font-size: 12px;
  color: var(--color-text-light);
}

.secret-tip {
  color: var(--el-color-warning-dark-2);
  margin-bottom: 12px;
}

@media (max-width: 900px) {
  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>

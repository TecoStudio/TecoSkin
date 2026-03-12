<template>
  <div class="settings-section animate-fade-in">
    <div class="page-header">
      <div class="page-header-content">
        <div class="page-header-icon"><Message /></div>
        <div class="page-header-text">
          <h2>邮件服务设置</h2>
          <p class="subtitle">配置 SMTP 服务器以启用注册验证、找回密码等通知功能</p>
        </div>
      </div>
      <div class="page-header-actions">
        <el-button type="primary" :icon="Refresh" @click="loadSettings" plain class="hover-lift">
          刷新配置
        </el-button>
      </div>
    </div>

    <el-card class="surface-card" shadow="never">
      <template #header>
        <div class="card-header-flex">
          <div class="title-group">
            <el-icon><Postcard /></el-icon>
            <span>SMTP 与验证配置</span>
          </div>
          <el-button type="primary" size="small" @click="saveSettings" :loading="saving" class="hover-lift">保存配置</el-button>
        </div>
      </template>

      <el-form label-position="top" :model="emailSettings">
        <div class="settings-group">
          <div class="group-title">验证功能</div>
          <el-row :gutter="40">
            <el-col :xs="24" :sm="12">
              <el-form-item label="启用邮件验证">
                <el-switch v-model="emailSettings.email_verify_enabled" />
                <p class="hint-text">开启后，用户注册和重置密码时必须通过邮件验证码确认身份。</p>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12" v-if="emailSettings.email_verify_enabled">
              <el-form-item label="验证码有效期 (秒)">
                <el-input-number v-model="emailSettings.email_verify_ttl" :min="60" :step="60" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <el-divider />

        <div class="settings-group">
          <div class="group-title">SMTP 服务器</div>
          <el-row :gutter="20">
            <el-col :xs="24" :sm="18">
              <el-form-item label="服务器地址">
                <el-input v-model="emailSettings.smtp_host" placeholder="smtp.example.com" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="6">
              <el-form-item label="端口">
                <el-input v-model="emailSettings.smtp_port" placeholder="465" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="20">
            <el-col :xs="24" :sm="12">
              <el-form-item label="用户名 (通常为邮箱地址)">
                <el-input v-model="emailSettings.smtp_user" placeholder="user@example.com" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="密码 / 授权码">
                <el-input v-model="emailSettings.smtp_password" type="password" show-password placeholder="留空则不修改原有密码" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="20">
            <el-col :xs="24" :sm="12">
              <el-form-item label="使用 SSL/TLS 加密">
                <el-switch v-model="emailSettings.smtp_ssl" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="12">
              <el-form-item label="发件人显示名称">
                <el-input v-model="emailSettings.smtp_sender" placeholder="SkinServer <no-reply@example.com>" />
                <p class="hint-text">发件人在邮件客户端中显示的名称及回复地址。</p>
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <el-divider />

        <div class="settings-group">
          <div class="group-title">邮件内容模板</div>
          <el-form-item label="HTML 模板">
            <el-input
              v-model="emailSettings.email_template_html"
              type="textarea"
              :rows="12"
              placeholder="留空则使用系统默认模板"
            />
            <div class="template-actions">
              <el-button size="small" type="primary" plain @click="applyDefaultTemplate">使用默认模板</el-button>
            </div>
            <p class="hint-text">可用占位符：{{site_title}}、{{code}}、{{action_title}}、{{ttl_minutes}}。</p>
          </el-form-item>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { Refresh, Message, Postcard } from '@element-plus/icons-vue'

const emailSettings = reactive({
  email_verify_enabled: false,
  email_verify_ttl: 300,
  smtp_host: '',
  smtp_port: '465',
  smtp_user: '',
  smtp_password: '',
  smtp_ssl: true,
  smtp_sender: '',
  email_template_html: ''
})

const saving = ref(false)
const authHeaders = () => ({ Authorization: 'Bearer ' + localStorage.getItem('jwt') })

const defaultEmailTemplate = `<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{site_title}} 邮件验证</title>
  </head>
  <body style="margin:0; padding:0; background:#f4f7fb; font-family:'Microsoft YaHei UI','PingFang SC',sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7fb; padding:24px 12px;">
      <tr>
        <td align="center">
          <table width="640" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 10px 30px rgba(35,64,95,0.12);">
            <tr>
              <td style="background:linear-gradient(135deg,#2f78ba,#4f9ad8); padding:24px 32px; color:#ffffff;">
                <div style="font-size:18px; font-weight:700; letter-spacing:0.5px;">{{site_title}}</div>
                <div style="font-size:14px; opacity:0.9; margin-top:6px;">{{action_title}}</div>
              </td>
            </tr>
            <tr>
              <td style="padding:28px 32px 8px; color:#1f2a36;">
                <h2 style="margin:0 0 12px; font-size:22px;">您好，</h2>
                <p style="margin:0 0 16px; font-size:14px; line-height:1.7; color:#4a5a6a;">
                  您正在进行 <strong>{{action_title}}</strong> 操作，请使用以下验证码完成验证：
                </p>
                <div style="background:#f1f6fc; border:1px solid #d7e4f2; border-radius:12px; padding:16px; text-align:center;">
                  <span style="font-size:28px; letter-spacing:6px; color:#2f78ba; font-weight:700;">{{code}}</span>
                </div>
                <p style="margin:16px 0 0; font-size:13px; color:#6a7b8c;">验证码有效期约 {{ttl_minutes}} 分钟，请尽快完成验证。</p>
                <p style="margin:10px 0 0; font-size:12px; color:#9aa7b4;">如果这不是您本人操作，请忽略此邮件。</p>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 32px 28px; color:#9aa7b4; font-size:12px;">此邮件由 {{site_title}} 自动发送，请勿直接回复。</td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>`

async function loadSettings() {
  try {
    const res = await axios.get('/admin/settings/email', { headers: authHeaders() })
    if (res.data) {
      Object.assign(emailSettings, res.data)
      emailSettings.smtp_password = '' // Don't show password
    }
  } catch (e) {
    ElMessage.error('加载邮件设置失败')
  }
}

async function saveSettings() {
  saving.value = true
  try {
    await axios.post('/admin/settings/email', emailSettings, { headers: authHeaders() })
    ElMessage.success('设置已保存')
    emailSettings.smtp_password = '' // Clear password field after save
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

function applyDefaultTemplate() {
  emailSettings.email_template_html = defaultEmailTemplate
  ElMessage.success('已填充默认模板')
}

onMounted(loadSettings)
</script>

<style scoped>
@import "@/assets/styles/animations.css";
@import "@/assets/styles/layout.css";
@import "@/assets/styles/cards.css";
@import "@/assets/styles/headers.css";
@import "@/assets/styles/buttons.css";

.settings-section {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px 0;
}

.card-header-flex { display: flex; justify-content: space-between; align-items: center; }
.card-header-flex .title-group { display: flex; align-items: center; gap: 8px; font-weight: 600; color: var(--color-heading); }

.settings-group { padding: 10px 0; }
.group-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-light);
  margin-bottom: 20px;
  border-left: 4px solid var(--el-color-primary);
  padding-left: 12px;
}

.template-actions {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
}

.hint-text { font-size: 12px; color: var(--color-text-light); line-height: 1.5; margin-top: 4px; }
</style>
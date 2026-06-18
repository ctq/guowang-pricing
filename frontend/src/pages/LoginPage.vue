<script setup lang="ts">
import { onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchQRCode, queryStatus } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const emit = defineEmits<{ (e: 'close'): void }>()

const authStore = useAuthStore()
const qrImgSrc = '/api/auth/qrcode-image'
const code = ref('')
const loading = ref(true)
const expired = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function loadCode() {
  loading.value = true
  expired.value = false
  try {
    const data = await fetchQRCode()
    code.value = data.code
    startPoll()
  } catch {
    ElMessage.error('获取验证码失败')
  } finally {
    loading.value = false
  }
}

function startPoll() {
  stopPoll()
  pollTimer = setInterval(async () => {
    try {
      const res = await queryStatus(code.value)
      if (res.status === 'logged_in' && res.token) {
        authStore.setToken(res.token)
        stopPoll()
        emit('close')
        return
      }
      if (res.status === 'expired') {
        stopPoll()
        expired.value = true
      }
    } catch {
      // ignore
    }
  }, 2000)
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function refresh() {
  loadCode()
}

onUnmounted(() => stopPoll())
loadCode()
</script>

<template>
  <div class="login-overlay" @click.self="emit('close')">
    <div class="login-card">
      <button class="close-btn" @click="emit('close')">&times;</button>
      <h2>微信扫码登录</h2>
      <div class="qrcode-area">
        <div v-if="loading" class="qrcode-placeholder">加载中...</div>
        <img v-else :src="qrImgSrc" alt="公众号二维码" class="qrcode-img" />
        <div v-if="expired" class="qrcode-overlay">
          <p>验证码已过期</p>
          <button class="btn-blue" @click="refresh">刷新</button>
        </div>
      </div>
      <div class="code-area">
        <p class="code-tip">扫码关注公众号，发送验证码</p>
        <div class="code-display">{{ code }}</div>
        <p class="code-hint">完成登录</p>
        <p class="code-sub" v-if="!expired">有效期 5 分钟，请尽快操作</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.login-card {
  position: relative;
  background: #ffffff;
  padding: 40px;
  text-align: center;
  min-width: 360px;
  border: 1px solid var(--border);
}

.close-btn {
  position: absolute;
  top: 8px;
  right: 12px;
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--label);
}

.login-card h2 {
  margin: 0 0 20px;
  font-size: 20px;
  color: var(--text);
}

.qrcode-area {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 220px;
}

.qrcode-img {
  width: 220px;
  height: 220px;
}

.qrcode-placeholder {
  color: var(--label);
  font-size: 14px;
}

.qrcode-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255,255,255,0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.qrcode-overlay p {
  margin: 0;
  font-size: 14px;
  color: var(--label);
}

.code-area {
  margin-top: 20px;
}

.code-tip {
  margin: 0 0 8px;
  font-size: 14px;
  color: var(--label);
}

.code-display {
  display: inline-block;
  font-size: 36px;
  font-weight: 700;
  letter-spacing: 8px;
  color: var(--sg-green);
  padding: 8px 24px;
  border: 2px dashed var(--sg-green);
  background: var(--readonly-bg);
}

.code-hint {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--text);
}

.code-sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--label);
}
</style>

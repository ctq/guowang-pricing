<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, DocumentAdd, Edit, Finished, Close, EditPen } from '@element-plus/icons-vue'

import { listFiles, readFile, writeFile, renameFile, createFile, deleteFile, type FileInfo } from '../api/requirements'

const loading = ref(false)
const saving = ref(false)
const editing = ref(false)
const files = ref<FileInfo[]>([])
const currentFile = ref('')
const content = ref('')
const savedContent = ref('')

onMounted(async () => {
  await loadFileList()
})

async function loadFileList() {
  try {
    files.value = await listFiles()
  } catch {
    ElMessage.error('加载文件列表失败')
  }
}

async function selectFile(name: string) {
  if (editing.value && content.value !== savedContent.value) {
    try {
      await ElMessageBox.confirm('当前修改未保存，是否放弃？', '提示')
    } catch {
      return
    }
  }
  editing.value = false
  currentFile.value = name
  loading.value = true
  try {
    const c = await readFile(name)
    content.value = c
    savedContent.value = c
  } catch {
    ElMessage.error('读取文件失败')
  } finally {
    loading.value = false
  }
}

async function startEdit() {
  editing.value = true
}

async function cancelEdit() {
  editing.value = false
  content.value = savedContent.value
}

async function save() {
  saving.value = true
  try {
    await writeFile(currentFile.value, content.value)
    savedContent.value = content.value
    editing.value = false
    ElMessage.success('已保存')
    await loadFileList()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleRename() {
  try {
    const { value } = await ElMessageBox.prompt('新文件名', '重命名', {
      inputValue: currentFile.value,
      inputPattern: /\.md$/,
      inputErrorMessage: '文件名必须以 .md 结尾',
    })
    if (!value || value === currentFile.value) return
    await renameFile(currentFile.value, value)
    ElMessage.success('重命名成功')
    currentFile.value = value
    await loadFileList()
  } catch {
    // cancelled
  }
}

async function handleCreate() {
  try {
    const { value } = await ElMessageBox.prompt('文件名', '新建需求文档', {
      inputPattern: /\.md$/,
      inputErrorMessage: '文件名必须以 .md 结尾',
    })
    if (!value) return
    await createFile(value)
    ElMessage.success('已创建')
    await loadFileList()
    await selectFile(value)
  } catch {
    // cancelled
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm(`确定删除「${currentFile.value}」？`, '删除', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteFile(currentFile.value)
    ElMessage.success('已删除')
    currentFile.value = ''
    content.value = ''
    savedContent.value = ''
    await loadFileList()
  } catch {
    ElMessage.error('删除失败')
  }
}
</script>

<template>
  <div class="req-page">
    <div class="req-sidebar">
      <div class="sidebar-header">
        <span>需求文档</span>
        <el-button class="sidebar-add-btn" :icon="DocumentAdd" size="small" @click="handleCreate" />
      </div>
      <div class="sidebar-list">
        <div
          v-for="f in files"
          :key="f.name"
          class="file-item"
          :class="{ active: f.name === currentFile }"
          @click="selectFile(f.name)"
        >
          <span class="file-icon">#</span>
          <span class="file-name">{{ f.name }}</span>
        </div>
        <div v-if="!files.length" class="empty-hint">暂无 .md 文件</div>
      </div>
    </div>
    <div class="req-main">
      <div v-if="!currentFile" class="empty-state">请从左侧选择一个文件</div>
      <template v-else>
        <div class="req-toolbar">
          <span class="req-filename">{{ currentFile }}</span>
          <div class="req-actions">
            <el-button v-if="!editing" class="btn-blue" :icon="Edit" size="small" @click="startEdit">编辑</el-button>
            <el-button v-if="!editing" class="btn-blue" :icon="EditPen" size="small" @click="handleRename">重命名</el-button>
            <el-button v-if="!editing" class="btn-blue btn-danger" :icon="Delete" size="small" @click="handleDelete">删除</el-button>
            <template v-if="editing">
              <el-button class="btn-blue" :icon="Close" size="small" @click="cancelEdit">取消</el-button>
              <el-button class="btn-blue" :icon="Finished" size="small" :loading="saving" @click="save">保存</el-button>
            </template>
          </div>
        </div>
        <div class="req-editor">
          <div v-if="loading" class="req-loading">加载中...</div>
          <MdEditor
            v-else
            v-model="content"
            :previewOnly="!editing"
            language="zh-CN"
            theme="light"
            :showCodeRowNumber="true"
            editorId="requirements-editor"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.req-page {
  display: flex;
  height: 100%;
  gap: 16px;
}

.req-sidebar {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--card-bg);
  border: 1px solid var(--border);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  line-height: 20px;
  padding: 9px 16px;
  background: var(--sg-green);
}

.sidebar-add-btn.el-button {
  --el-button-size: 24px;
  color: #ffffff;
  background: transparent;
  border: 1px solid rgba(255,255,255,0.4);
  padding: 0;
}

.sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text);
  border: 1px solid transparent;
  transition: background 0.15s;
}

.file-item:hover {
  background: var(--readonly-bg);
}

.file-item.active {
  background: var(--readonly-bg);
  border-color: var(--sg-green);
  font-weight: 600;
}

.file-icon {
  color: var(--sg-green);
  font-weight: 700;
  font-size: 14px;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-hint {
  color: var(--label);
  font-size: 13px;
  text-align: center;
  padding: 24px 8px;
}

.req-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--label);
  font-size: 15px;
  background: var(--card-bg);
  border: 1px solid var(--border);
}

.req-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-bottom: none;
  flex-shrink: 0;
}

.req-filename {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.req-actions {
  display: flex;
  gap: 6px;
}

.req-editor {
  flex: 1;
  min-height: 0;
  background: #ffffff;
  border: 1px solid var(--border);
  overflow: auto;
}

.req-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--label);
  font-size: 14px;
}

.btn-danger.el-button {
  border-color: #c45656;
  background: #c45656;
}

.btn-danger.el-button:hover {
  border-color: #a04545;
  background: #a04545;
}

/* override md-editor-v3 height for scroll */
.req-editor :deep(.md-editor) {
  height: 100% !important;
}
</style>

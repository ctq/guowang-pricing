<script setup lang="ts">
/**
 * 国网价格分在线测算系统 - 主页面组件
 * 提供项目参数录入、开标记录导入/粘贴、评分测算与结果展示等功能。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { DataLine, Document, Download, Finished, Plus, Refresh, Upload, User, Grid } from '@element-plus/icons-vue'
import { ElMessage, type UploadProps } from 'element-plus'
import { calculate, exportXlsx, fetchMethods, importXlsx } from './api/pricing'
import { useAuthStore } from './stores/auth'
import { useCalculatorStore } from './stores/calculator'
import LoginPage from './pages/LoginPage.vue'
import RequirementsPage from './pages/RequirementsPage.vue'
import MultiSheetCalculator from './components/MultiSheetCalculator.vue'

const authStore = useAuthStore()
const store = useCalculatorStore()

const loginOpen = ref(false)

// 页面切换
const currentPage = ref<'calculator' | 'multi-sheet' | 'requirements'>('calculator')

// 界面状态
const loading = ref(false)          // 测算请求加载中
const imported = ref(false)         // 是否已导入开标记录（控制测算按钮启用）
const traceOpen = ref(false)        // 计算过程抽屉可见
const mappingOpen = ref(false)      // 列映射弹窗可见
const pasteOpen = ref(false)        // 快速粘贴弹窗可见
const pasteText = ref('')           // 粘贴文本内容
const mappingColumns = ref<string[]>([])    // 识别到的 Excel 列名
const mappingPreview = ref<Record<string, string>[]>([])  // 导入预览数据
const bidderColumn = ref('')        // 手动映射的投标人列
const priceColumn = ref('')         // 手动映射的报价列
const a01FloatingType = ref('')     // A01 算法浮动方向（1=上浮, -1=下浮）

// 省份列表（固定维护）
const provinces = [
  '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江', '上海', '江苏', '浙江', '安徽',
  '福建', '江西', '山东', '河南', '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
  '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆', '其他',
]

// 按排名升序排列的结果行
const resultRows = computed(() => {
  const rows = store.result?.rows ?? []
  return [...rows].sort((a, b) => {
    if (a.rank === null && b.rank === null) return 0
    if (a.rank === null) return 1
    if (b.rank === null) return -1
    return a.rank - b.rank
  })
})

// 基准价折扣率（百分比格式）
const benchmarkDiscountRate = computed(() => formatPercent(store.result?.discount_rate))
const benchmarkDiscountValue = computed(() => benchmarkDiscountRate.value === '-' ? '-' : benchmarkDiscountRate.value.replace('%', ''))

// 当前算法可见的参数条目：非 A01 时隐藏 round_scale，A01 按固定顺序排列
const visibleParamEntries = computed(() => {
  const entries = Object.entries(store.params)
  if (store.methodCode !== 'A01') {
    return entries.filter(([key]) => !isFloatingTypeParam(key))
  }
  const order = ['w1', 'w2', 'n1', 'c', 'n2', 'round_scale']
  return [...entries].sort(([left], [right]) => {
    const leftIndex = order.indexOf(left)
    const rightIndex = order.indexOf(right)
    if (leftIndex === -1 && rightIndex === -1) return 0
    if (leftIndex === -1) return 1
    if (rightIndex === -1) return -1
    return leftIndex - rightIndex
  })
})

// 表格行数据：有结果时展示结果，否则显示导入的原始数据
const resultTableRows = computed(() => {
  if (store.result) return resultRows.value
  return store.bids.map(row => ({
    ...row,
    score: null,
    rank: null,
    participated: Boolean(row.bid_price),
    used_for_benchmark: false,
    remark: '',
  }))
})

const canCalculate = computed(() => imported.value)

/**
 * 将小数转为百分比字符串
 */
function formatPercent(value: string | null | undefined) {
  if (value === null || value === undefined || value === '') return '-'
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return value
  return `${(parsed * 100).toFixed(2)}%`
}

/**
 * 计算单条报价相对于包限价的折扣率
 */
function formatBidDiscount(value: string | null | undefined) {
  if (!value || value === '不开标') return '-'
  const ceiling = Number(store.project.ceiling_price)
  const bid = Number(value)
  if (!Number.isFinite(ceiling) || ceiling <= 0 || !Number.isFinite(bid)) return '-'
  return ((bid / ceiling) * 100).toFixed(2)
}

function parameterLabel(key: string) {
  return key === 'round_scale' ? '浮动类型' : key
}

/** 算法参数输入框的占位提示文本 */
function parameterPlaceholder(key: string) {
  if (isFloatingTypeParam(key)) return '请选择浮动类型'
  return `请输入${key}`
}

/** 是否为 A01 浮动类型参数 */
function isFloatingTypeParam(key: string) {
  return key === 'round_scale'
}

/**
 * 构建 API 请求负载，A01 额外注入浮动方向
 */
function payloadWithFloatingType(source = 'manual') {
  const payload = store.payload(source)
  if (store.methodCode === 'A01') {
    payload.params.float_direction = a01FloatingType.value
  }
  return payload
}

/**
 * 测算前校验：必填项目参数、算法参数是否填写完整
 */
function validateBeforeCalculate() {
  const requiredProjectFields: Array<[string, string | undefined]> = [
    ['网省', store.project.province],
    ['目标公司', store.project.target_company],
    ['包限价', store.project.ceiling_price],
    ['价格分占比', store.project.price_weight],
    ['评分规则', store.methodCode],
  ]
  const missingProjectField = requiredProjectFields.find(([, value]) => !String(value ?? '').trim())
  if (missingProjectField) {
    ElMessage.warning(`请填写${missingProjectField[0]}`)
    return false
  }

  if (store.methodCode === 'A01' && !a01FloatingType.value) {
    ElMessage.warning('请选择浮动类型')
    return false
  }

  const missingParam = Object.entries(store.params).find(([key, value]) => {
    if (isFloatingTypeParam(key)) return false
    return !String(value ?? '').trim()
  })
  if (missingParam) {
    ElMessage.warning(`请填写${parameterLabel(missingParam[0])}`)
    return false
  }

  return true
}

onMounted(async () => {
  store.methods = await fetchMethods()
  store.applyDefaults()
})

// 切换算法时重置计算结果与参数默认值
watch(() => store.methodCode, () => {
  store.applyDefaults()
  store.result = null
  a01FloatingType.value = ''
})

/** 添加空行报价 */
function addBid() {
  store.bids.push({ bidder_name: `投标人${store.bids.length + 1}`, bid_price: '' })
}

/** 删除指定行报价 */
function removeBid(index: number) {
  store.bids.splice(index, 1)
}

/** 应用手动列映射后的导入数据 */
function applyMappedImport() {
  if (!bidderColumn.value || !priceColumn.value) {
    ElMessage.warning('请选择投标人列和报价列')
    return
  }
  store.bids = mappingPreview.value
    .map(row => ({
      bidder_name: row[bidderColumn.value]?.trim() ?? '',
      bid_price: row[priceColumn.value]?.trim() ?? '',
    }))
    .filter(row => row.bidder_name || row.bid_price)
  store.result = null
  imported.value = true
  mappingOpen.value = false
  ElMessage.success(`已导入 ${store.bids.length} 条报价`)
}

/** 解析粘贴的 Tab/逗号分隔文本为报价列表 */
function applyPastedRows() {
  const rows = pasteText.value
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const parts = line.split(/\t|,|，/).map(item => item.trim())
      if (parts.length === 1) {
        return { bidder_name: `投标人${index + 1}`, bid_price: parts[0] }
      }
      return { bidder_name: parts[0], bid_price: parts[1] ?? '' }
    })
  if (!rows.length) {
    ElMessage.warning('没有可粘贴的报价数据')
    return
  }
  store.bids = rows
  store.result = null
  pasteText.value = ''
  pasteOpen.value = false
  ElMessage.success(`已粘贴 ${rows.length} 条报价`)
}

const MAX_FREE_USES = 5
const FREE_USE_KEY = 'bid_free_uses'

function getFreeUseCount(): number {
  return Number(localStorage.getItem(FREE_USE_KEY) || '0')
}

function incrementFreeUse() {
  localStorage.setItem(FREE_USE_KEY, String(getFreeUseCount() + 1))
}

/** 发起测算请求 */
async function runCalculate(source = 'manual') {
  if (!validateBeforeCalculate()) return
  if (!authStore.loggedIn && getFreeUseCount() >= MAX_FREE_USES) {
    ElMessage.warning(`试用已用完（${MAX_FREE_USES}次），请登录后继续使用`)
    loginOpen.value = true
    return
  }
  loading.value = true
  try {
    store.result = await calculate(payloadWithFloatingType(source))
    if (!authStore.loggedIn) {
      incrementFreeUse()
    }
    ElMessage.success('计算成功')
  } catch (error) {
    ElMessage.error((error as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? '计算失败')
  } finally {
    loading.value = false
  }
}

/** 导出测算结果为 Excel 文件 */
async function downloadResult() {
  if (!validateBeforeCalculate()) return
  try {
    await exportXlsx(payloadWithFloatingType())
  } catch {
    ElMessage.error('导出失败')
  }
}

/** 上传 Excel 开标记录文件后的预处理 */
const beforeUpload: UploadProps['beforeUpload'] = async (file) => {
  try {
    const data = await importXlsx(file)
    if (data.requires_mapping) {
      mappingColumns.value = data.columns
      mappingPreview.value = data.preview
      bidderColumn.value = data.columns[0] ?? ''
      priceColumn.value = data.columns[1] ?? ''
      mappingOpen.value = true
      ElMessage.warning(data.warnings[0] ?? '请手动选择列映射')
      return false
    }
    store.bids = data.rows
    store.result = null
    imported.value = true
    ElMessage.success(`已导入 ${data.rows.length} 条报价`)
  } catch (error) {
    ElMessage.error((error as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? '导入失败')
  }
  return false
}

/**
 * 表格行样式：目标公司行高亮
 */
function rowClassName({ row }: { row: any }) {
  if (store.project.target_company && row.bidder_name === store.project.target_company) {
    return 'target-row'
  }
  return ''
}
</script>

<template>
  <main class="app-shell">
    <header class="app-header">
      <span class="app-title">电算宝</span>
      <span class="app-slogan">一键测算报价得分</span>
      <nav class="app-nav">
        <button
          class="nav-btn"
          :class="{ active: currentPage === 'calculator' }"
          @click="currentPage = 'calculator'"
        >
          <el-icon><DataLine /></el-icon>测算
        </button>
        <button
          class="nav-btn"
          :class="{ active: currentPage === 'multi-sheet' }"
          @click="currentPage = 'multi-sheet'"
        >
          <el-icon><Grid /></el-icon>多表
        </button>
        <button
          class="nav-btn"
          :class="{ active: currentPage === 'requirements' }"
          @click="currentPage = 'requirements'"
        >
          <el-icon><Document /></el-icon>需求
        </button>
        <button
          v-if="!authStore.loggedIn"
          class="nav-btn login-btn"
          @click="loginOpen = true"
        >
          <el-icon><User /></el-icon>登录
        </button>
        <span v-else class="nav-btn logged-in" @click="authStore.logout()">
          <el-icon><User /></el-icon>已登录
        </span>
      </nav>
    </header>
    <LoginPage v-if="loginOpen" @close="loginOpen = false" />
    <RequirementsPage v-if="currentPage === 'requirements'" class="page-content" />
    <MultiSheetCalculator v-else-if="currentPage === 'multi-sheet'" class="page-content" />
    <div v-else class="workspace">
      <!-- 左侧：评标参数面板 -->
      <aside class="wire-panel params-panel">
        <h1>评标参数</h1>
        <!-- 开标记录导入区域（测算前必须导入） -->
        <div class="import-row">
          <el-upload :show-file-list="false" accept=".xlsx" :before-upload="beforeUpload">
            <el-button class="btn-blue" :icon="Upload">导入开标记录</el-button>
          </el-upload>
          <span v-if="!imported" class="import-hint">* 必须先导入开标记录才能开始测算</span>
          <span v-else class="import-hint imported">已导入开标记录</span>
        </div>

        <el-form label-position="top" class="wire-form">
          <!-- 基础项目信息 -->
          <el-form-item label="招标编号" required>
            <el-input v-model="store.project.tender_no" />
          </el-form-item>
          <el-form-item label="招标名称">
            <el-input v-model="store.project.tender_name" />
          </el-form-item>
          <div class="form-grid">
            <el-form-item label="网省" required>
              <el-select v-model="store.project.province" filterable>
                <el-option v-for="province in provinces" :key="province" :label="province" :value="province" />
              </el-select>
            </el-form-item>
            <el-form-item label="目标公司" required>
              <el-input v-model="store.project.target_company" />
            </el-form-item>
          </div>
            <!-- 包限价与价格分占比 -->
            <div class="form-grid">
              <el-form-item label="包限价" required>
                <el-input v-model="store.project.ceiling_price" />
              </el-form-item>
              <el-form-item label="价格分占比" required>
                <el-input v-model="store.project.price_weight" />
              </el-form-item>
            </div>
            <!-- 评分方法选择 -->
            <el-form-item label="评分规则" required>
            <el-select v-model="store.methodCode" filterable>
              <el-option v-for="method in store.methods" :key="method.code" :label="`${method.code} ${method.name}`" :value="method.code" />
            </el-select>
          </el-form-item>

          <!-- 算法参数区 -->
          <div class="param-divider" />
          <div class="form-grid param-grid">
            <el-form-item
              v-for="([paramKey]) in visibleParamEntries"
              :key="paramKey"
              :label="parameterLabel(paramKey)"
              :class="{ 'full-row-field': isFloatingTypeParam(paramKey) }"
              required
            >
              <!-- A01 浮动方向选择器 -->
              <el-select
                v-if="store.methodCode === 'A01' && isFloatingTypeParam(paramKey)"
                v-model="a01FloatingType"
                placeholder="请选择"
              >
                <el-option label="上浮：基准价=A2*(1+c)" value="1" />
                <el-option label="下浮：基准价=A2*(1-c)" value="-1" />
              </el-select>
              <el-input v-else v-model="store.params[paramKey]" :placeholder="parameterPlaceholder(paramKey)" />
            </el-form-item>
          </div>
          <el-button class="reset-button" :icon="Refresh" text @click="store.applyDefaults()">默认值</el-button>
        </el-form>
      </aside>

      <!-- 右侧：结果展示区 -->
      <section class="main-column">
        <!-- 测算结果摘要 -->
        <section class="wire-panel result-summary">
          <header class="result-header">
            <h2>测算结果</h2>
            <div class="result-actions">
              <el-button class="btn-blue secondary-action" :icon="DataLine" :disabled="!store.result" @click="traceOpen = true">过程</el-button>
              <el-button class="btn-blue" :icon="Finished" :loading="loading" :disabled="!canCalculate" @click="runCalculate()">测算</el-button>
            </div>
          </header>
          <!-- 2x4 结果指标网格 -->
          <div class="summary-grid">
            <div class="summary-item">
              <label>基准价</label>
              <el-input class="result-output" :model-value="store.result?.benchmark_price ?? ''" disabled />
            </div>
            <div class="summary-item">
              <label>基准价折扣率</label>
              <el-input class="result-output" :model-value="benchmarkDiscountValue === '-' ? '' : benchmarkDiscountValue" disabled />
            </div>
            <div class="summary-item">
              <label>投标人数量</label>
              <el-input class="result-output" :model-value="store.result?.bidder_count ?? ''" disabled />
            </div>
            <div class="summary-item">
              <label>有效报价数量</label>
              <el-input class="result-output" :model-value="store.result?.effective_count ?? ''" disabled />
            </div>
            <div class="summary-item">
              <label>目标公司排名</label>
              <el-input class="result-output" :model-value="store.result?.target.rank ?? ''" disabled />
            </div>
            <div class="summary-item">
              <label>与第1名分差</label>
              <el-input class="result-output" :model-value="store.result?.target.score_gap ?? ''" disabled />
            </div>
            <div class="summary-item">
              <label>折算后分差</label>
              <el-input class="result-output" :model-value="store.result?.target.weighted_gap ?? ''" disabled />
            </div>
            <div class="summary-item export-item">
              <div class="label-spacer" />
              <el-button class="btn-blue export-button" :icon="Download" :disabled="!store.result" @click="downloadResult">导出评分结果</el-button>
            </div>
          </div>
        </section>

        <!-- 排名详情表格 -->
        <section class="wire-panel ranking-panel">
          <header class="ranking-header">
            <h2>排名详情</h2>
            <div class="table-actions">
              <el-button class="btn-blue" :icon="Plus" @click="addBid">新增</el-button>
            </div>
          </header>
          <div class="ranking-table">
            <el-table :data="resultTableRows" height="100%" :row-class-name="rowClassName">
              <el-table-column label="投标人" align="center">
                <template #default="{ row, $index }">
                  <el-input v-if="!store.result" v-model="store.bids[$index].bidder_name" />
                  <span v-else>{{ row.bidder_name }}</span>
                </template>
              </el-table-column>
              <el-table-column label="报价" align="center">
                <template #default="{ row, $index }">
                  <el-input v-if="!store.result" v-model="store.bids[$index].bid_price" />
                  <span v-else>{{ row.bid_price ?? '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="score" label="价格分" align="center" />
              <el-table-column prop="rank" label="排名" align="center" />
              <el-table-column label="折扣率" align="center">
                <template #default="{ row }">{{ formatBidDiscount(row.bid_price) }}</template>
              </el-table-column>
              <el-table-column label="备注" align="center">
                <template #default="{ row, $index }">
                  <span>{{ row.remark }}</span>
                  <el-button v-if="!store.result" text type="danger" @click="removeBid($index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </section>
      </section>
    </div>

    <!-- 计算过程详情抽屉 -->
    <el-drawer v-model="traceOpen" title="详细计算逻辑" size="450px">
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item v-for="(value, key) in store.result?.debug" :key="key" :label="String(key)">
          {{ value }}
        </el-descriptions-item>
      </el-descriptions>
    </el-drawer>

    <!-- 导入列映射弹窗 -->
    <el-dialog v-model="mappingOpen" title="导入配置" width="500px">
      <el-form label-width="100px">
        <el-form-item label="投标人名称列">
          <el-select v-model="bidderColumn" style="width: 100%"><el-option v-for="col in mappingColumns" :key="col" :label="col" :value="col" /></el-select>
        </el-form-item>
        <el-form-item label="投标报价列">
          <el-select v-model="priceColumn" style="width: 100%"><el-option v-for="col in mappingColumns" :key="col" :label="col" :value="col" /></el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mappingOpen = false">取消</el-button>
        <el-button type="primary" @click="applyMappedImport">导入数据</el-button>
      </template>
    </el-dialog>

    <!-- 快速粘贴弹窗 -->
    <el-dialog v-model="pasteOpen" title="快速粘贴" width="500px">
      <el-input v-model="pasteText" type="textarea" :rows="10" placeholder="投标人名称 [Tab] 投标价格" />
      <template #footer>
        <el-button @click="pasteOpen = false">取消</el-button>
        <el-button type="primary" @click="applyPastedRows">确定</el-button>
      </template>
    </el-dialog>
  </main>
</template>

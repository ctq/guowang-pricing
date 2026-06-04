<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { DataLine, DocumentCopy, Download, Finished, Plus, Refresh, Upload } from '@element-plus/icons-vue'
import { ElMessage, type UploadProps } from 'element-plus'
import { calculate, exportXlsx, fetchMethods, importXlsx } from './api/pricing'
import { useCalculatorStore } from './stores/calculator'

const store = useCalculatorStore()
const loading = ref(false)
const traceOpen = ref(false)
const mappingOpen = ref(false)
const pasteOpen = ref(false)
const pasteText = ref('')
const mappingColumns = ref<string[]>([])
const mappingPreview = ref<Record<string, string>[]>([])
const bidderColumn = ref('')
const priceColumn = ref('')
const a01FloatingType = ref('')

const provinces = [
  '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江', '上海', '江苏', '浙江', '安徽',
  '福建', '江西', '山东', '河南', '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
  '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆', '其他',
]

const resultRows = computed(() => {
  const rows = store.result?.rows ?? []
  return [...rows].sort((a, b) => {
    if (a.rank === null && b.rank === null) return 0
    if (a.rank === null) return 1
    if (b.rank === null) return -1
    return a.rank - b.rank
  })
})
const benchmarkDiscountRate = computed(() => formatPercent(store.result?.discount_rate))
const benchmarkDiscountValue = computed(() => benchmarkDiscountRate.value === '-' ? '-' : benchmarkDiscountRate.value.replace('%', ''))
const benchmarkFormulaByMethod: Record<string, string> = {
  A01: '',
  A02: 'A1 * (1 + c)',
  A03: '所选平均值 * (1 + c)',
  A04: '(A2 + 次低价) / 2',
  A05: '最低有效报价',
  A06: '全部有效报价平均值',
  A07: 'A2 * (1 - a)',
  A08: 'A2 * (1 + c)',
}
const fixedBenchmarkFormula = computed(() => benchmarkFormulaByMethod[store.methodCode] ?? '')
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

function formatPercent(value: string | null | undefined) {
  if (value === null || value === undefined || value === '') return '-'
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return value
  return `${(parsed * 100).toFixed(2)}%`
}

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

function isFloatingTypeParam(key: string) {
  return key === 'round_scale'
}

function payloadWithFloatingType(source = 'manual') {
  const payload = store.payload(source)
  if (store.methodCode === 'A01') {
    payload.params.float_direction = a01FloatingType.value
  }
  return payload
}

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

watch(() => store.methodCode, () => {
  store.applyDefaults()
  store.result = null
  a01FloatingType.value = ''
})

function addBid() {
  store.bids.push({ bidder_name: `投标人${store.bids.length + 1}`, bid_price: '' })
}

function removeBid(index: number) {
  store.bids.splice(index, 1)
}

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
  mappingOpen.value = false
  ElMessage.success(`已导入 ${store.bids.length} 条报价`)
}

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

async function runCalculate(source = 'manual') {
  if (!validateBeforeCalculate()) return
  loading.value = true
  try {
    store.result = await calculate(payloadWithFloatingType(source))
    ElMessage.success('计算成功')
  } catch (error) {
    ElMessage.error((error as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? '计算失败')
  } finally {
    loading.value = false
  }
}

async function downloadResult() {
  if (!validateBeforeCalculate()) return
  try {
    await exportXlsx(payloadWithFloatingType())
  } catch {
    ElMessage.error('导出失败')
  }
}

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
    ElMessage.success(`已导入 ${data.rows.length} 条报价`)
  } catch (error) {
    ElMessage.error((error as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? '导入失败')
  }
  return false
}

function rowClassName({ row }: { row: any }) {
  if (store.project.target_company && row.bidder_name === store.project.target_company) {
    return 'target-row'
  }
  return ''
}
</script>

<template>
  <main class="app-shell">
    <div class="workspace">
      <aside class="wire-panel params-panel">
        <h1>评标参数</h1>
        <div class="import-row">
          <el-upload :show-file-list="false" accept=".xlsx" :before-upload="beforeUpload">
            <el-button class="btn-blue" :icon="Upload">导入开标记录</el-button>
          </el-upload>
        </div>

        <el-form label-position="top" class="wire-form">
          <div class="form-grid">
            <el-form-item label="招标编号">
              <el-input v-model="store.project.tender_no" />
            </el-form-item>
            <el-form-item label="网省">
              <el-select v-model="store.project.province" filterable>
                <el-option v-for="province in provinces" :key="province" :label="province" :value="province" />
              </el-select>
            </el-form-item>
          </div>
          <el-form-item label="招标名称">
            <el-input v-model="store.project.tender_name" />
          </el-form-item>
          <el-form-item label="目标公司">
            <el-input v-model="store.project.target_company" />
          </el-form-item>
          <div class="form-grid">
            <el-form-item label="包限价">
              <el-input v-model="store.project.ceiling_price" />
            </el-form-item>
            <el-form-item label="价格分占比">
              <el-input v-model="store.project.price_weight" />
            </el-form-item>
          </div>
          <el-form-item label="评分规则">
            <el-select v-model="store.methodCode" filterable>
              <el-option v-for="method in store.methods" :key="method.code" :label="`${method.code} ${method.name}`" :value="method.code" />
            </el-select>
          </el-form-item>

          <div class="param-divider" />
          <div class="form-grid param-grid">
            <el-form-item v-for="(_, key) in store.params" :key="key" :label="parameterLabel(String(key))">
              <el-select
                v-if="store.methodCode === 'A01' && isFloatingTypeParam(String(key))"
                v-model="a01FloatingType"
                placeholder="请选择"
              >
                <el-option label="A2 * (1+c)" value="1" />
                <el-option label="A2 * (1-c)" value="-1" />
              </el-select>
              <el-input
                v-else-if="isFloatingTypeParam(String(key))"
                :model-value="fixedBenchmarkFormula"
                disabled
              />
              <el-input v-else v-model="store.params[key]" />
            </el-form-item>
          </div>
          <el-button class="reset-button" :icon="Refresh" text @click="store.applyDefaults()">默认值</el-button>
        </el-form>
      </aside>

      <section class="main-column">
        <section class="wire-panel result-summary">
          <header class="result-header">
            <h2>测算结果</h2>
            <div class="result-actions">
              <el-button class="btn-blue secondary-action" :icon="DataLine" :disabled="!store.result" @click="traceOpen = true">过程</el-button>
              <el-button class="btn-blue" :icon="Finished" :loading="loading" @click="runCalculate()">测算</el-button>
            </div>
          </header>
          <div class="summary-grid">
            <div class="summary-item">
              <label>基准价</label>
              <strong>{{ store.result?.benchmark_price ?? '-' }}</strong>
            </div>
            <div class="summary-item">
              <label>基准价折扣率</label>
              <strong>{{ benchmarkDiscountValue }}</strong>
            </div>
            <div class="summary-item">
              <label>投标人数量</label>
              <strong>{{ store.result?.bidder_count ?? '-' }}</strong>
            </div>
            <div class="summary-item">
              <label>有效报价数量</label>
              <strong>{{ store.result?.effective_count ?? '-' }}</strong>
            </div>
            <div class="summary-item">
              <label>目标公司排名</label>
              <strong>{{ store.result?.target.rank ?? '-' }}</strong>
            </div>
            <div class="summary-item">
              <label>与第1名分差</label>
              <strong>{{ store.result?.target.score_gap ?? '-' }}</strong>
            </div>
            <div class="summary-item">
              <label>折算后分差</label>
              <strong>{{ store.result?.target.weighted_gap ?? '-' }}</strong>
            </div>
            <div class="summary-item export-item">
              <div class="label-spacer" />
              <el-button class="btn-blue export-button" :icon="Download" :disabled="!store.result" @click="downloadResult">导出评分结果</el-button>
            </div>
          </div>
        </section>

        <section class="wire-panel ranking-panel">
          <header class="ranking-header">
            <h2>排名详情</h2>
            <div class="table-actions">
              <el-button class="btn-blue" :icon="DocumentCopy" @click="pasteOpen = true">粘贴</el-button>
              <el-button class="btn-blue" :icon="Plus" @click="addBid">新增</el-button>
            </div>
          </header>
          <div class="ranking-table">
            <el-table :data="resultTableRows" height="100%" :row-class-name="rowClassName">
              <el-table-column label="投标人" min-width="150" align="center">
                <template #default="{ row, $index }">
                  <el-input v-if="!store.result" v-model="store.bids[$index].bidder_name" />
                  <span v-else>{{ row.bidder_name }}</span>
                </template>
              </el-table-column>
              <el-table-column label="报价" width="140" align="center">
                <template #default="{ row, $index }">
                  <el-input v-if="!store.result" v-model="store.bids[$index].bid_price" />
                  <span v-else>{{ row.bid_price ?? '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="score" label="价格分" width="110" align="center" />
              <el-table-column prop="rank" label="排名" width="90" align="center" />
              <el-table-column label="折扣率" width="110" align="center">
                <template #default="{ row }">{{ formatBidDiscount(row.bid_price) }}</template>
              </el-table-column>
              <el-table-column label="备注" min-width="130" align="center">
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

    <!-- 弹窗部分 -->
    <el-drawer v-model="traceOpen" title="详细计算逻辑" size="450px">
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item v-for="(value, key) in store.result?.debug" :key="key" :label="String(key)">
          {{ value }}
        </el-descriptions-item>
      </el-descriptions>
    </el-drawer>

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

    <el-dialog v-model="pasteOpen" title="快速粘贴" width="500px">
      <el-input v-model="pasteText" type="textarea" :rows="10" placeholder="投标人名称 [Tab] 投标价格" />
      <template #footer>
        <el-button @click="pasteOpen = false">取消</el-button>
        <el-button type="primary" @click="applyPastedRows">确定</el-button>
      </template>
    </el-dialog>
  </main>
</template>

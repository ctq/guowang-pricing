<script setup lang="ts">
/**
 * 多 Sheet 批量测算组件
 */
import { computed, onMounted, ref } from 'vue'
import {
  DataLine, Download, Finished, Plus, Refresh, Upload,
} from '@element-plus/icons-vue'
import { ElMessage, type UploadProps } from 'element-plus'
import {
  importXlsxMulti, calculateMulti, fetchMethods,
  type MethodInfo, type BidPayload, type SheetData, type SheetResult,
} from '../api/pricing'
import {
  PROVINCES, toDisplayPercent, getDefaultApiParams,
  formatPercent, formatBidDiscount, cleanNumericParams,
} from '../utils/helpers'

const loading = ref(false)
const importing = ref(false)
const sheets = ref<SheetData[]>([])
const fileName = ref('')
const methods = ref<MethodInfo[]>([])
const activeTab = ref('0')
const results = ref<SheetResult[] | null>(null)
const scoreGaps = ref<string[]>([])
const weightedGaps = ref<string[]>([])
const traceOpen = ref(false)
const traceData = ref<Record<string, unknown>>({})

interface SheetState {
  name: string
  methodCode: string
  params: Record<string, string>
  project: {
    tender_no: string
    tender_name?: string
    section_no: string
    package_no: string
    province: string
    ceiling_price?: string
    price_weight?: string
    target_company?: string
  }
  bids: BidPayload[]
}

const sheetStates = ref<SheetState[]>([])
const canBatchCalculate = computed(() => sheetStates.value.length > 0)
const hasResults = computed(() => results.value !== null && results.value.length > 0)

onMounted(async () => { methods.value = await fetchMethods() })

function getDefaultParams(code: string): Record<string, string> {
  return getDefaultApiParams(methods.value, code)
}

function initSheetState(sheet: SheetData, index: number) {
  const code = methods.value[0]?.code || 'A01'
  sheetStates.value[index] = {
    name: sheet.name,
    methodCode: code,
    params: getDefaultParams(code),
    project: {
      tender_no: `T${String(index + 1).padStart(3, '0')}`,
      tender_name: sheet.name,
      section_no: `S${String(index + 1).padStart(3, '0')}`,
      package_no: `P${String(index + 1).padStart(3, '0')}`,
      province: '浙江',
      ceiling_price: '200',
      price_weight: '40',
      target_company: sheet.rows[0]?.bidder_name || '',
    },
    bids: sheet.rows.map(r => ({ bidder_name: r.bidder_name, bid_price: r.bid_price })),
  }
}

const beforeUpload: UploadProps['beforeUpload'] = async (file) => {
  importing.value = true
  results.value = null
  try {
    const data = await importXlsxMulti(file)
    const validSheets = data.sheets.filter(s => s.rows.length > 0)
    if (!validSheets.length) {
      ElMessage.warning('未识别到任何有效报价数据')
      importing.value = false
      return false
    }
    fileName.value = file.name
    sheets.value = validSheets
    sheetStates.value = []
    validSheets.forEach((s, i) => initSheetState(s, i))
    activeTab.value = '0'
    ElMessage.success(`已导入 ${validSheets.length} 个 Sheet（已过滤 ${data.sheets.length - validSheets.length} 个空表）`)
  } catch (error: any) {
    const msg = error?.response?.data?.detail || error?.message || '导入失败'
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  } finally {
    importing.value = false
  }
  return false
}

function onMethodChange(index: number) {
  const st = sheetStates.value[index]
  if (st) st.params = getDefaultParams(st.methodCode)
}
function addBid(index: number) {
  const st = sheetStates.value[index]
  if (st) st.bids.push({ bidder_name: `投标人${st.bids.length + 1}`, bid_price: '' })
}
function removeBid(sheetIndex: number, bidIndex: number) {
  sheetStates.value[sheetIndex].bids.splice(bidIndex, 1)
}
function isFloatingTypeParam(key: string) { return key === 'round_scale' }
function parameterLabel(key: string) { return key === 'round_scale' ? '浮动类型' : key }

async function batchCalculate() {
  loading.value = true
  results.value = null
  scoreGaps.value = []
  weightedGaps.value = []
  try {
    const validSheets = sheetStates.value.filter(st => st.bids.length > 0)
    if (!validSheets.length) {
      ElMessage.warning('没有可测算的 Sheet（报价数据为空）')
      loading.value = false
      return
    }
    const payload = {
      sheets: validSheets.map(st => {
        const params = cleanNumericParams(st.params, st.methodCode)
        if (st.methodCode === 'A01' && ['1', '-1'].includes(params.round_scale)) {
          params.float_direction = params.round_scale
          params.round_scale = '4'
        }
        return {
          name: st.name,
          project: {
            ...st.project,
            ceiling_price: st.project.ceiling_price || undefined,
            price_weight: st.project.price_weight ? String(Number(st.project.price_weight) / 100) : undefined,
          },
          method_code: st.methodCode,
          params,
          bids: st.bids.map(b => ({ bidder_name: b.bidder_name, bid_price: b.bid_price })),
          source: 'multi_sheet',
        }
      }),
    }
    const res = await calculateMulti(payload)
    results.value = res.results
    scoreGaps.value = res.results.map((r: any) => String(r.target?.score_gap ?? ''))
    weightedGaps.value = res.results.map((r: any) => String(r.target?.weighted_gap ?? ''))
    ElMessage.success(`批量测算完成，共 ${res.results.length} 个 Sheet`)
  } catch (error: any) {
    const msg = error?.response?.data?.detail || error?.message || '批量测算失败'
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  } finally { loading.value = false }
}

function showTrace(row: SheetResult) {
  traceData.value = { ...row.debug, 评分方法: `${row.method_code} ${row.method_name}`, 基准价: row.benchmark_price }
  traceOpen.value = true
}

function resultForSheet(name: string): SheetResult | undefined {
  return results.value?.find(r => r.name === name)
}
</script>

<template>
  <div class="msc">
    <header class="msc-header">
      <div class="msc-header-left">
        <el-upload :show-file-list="false" accept=".xlsx" :before-upload="beforeUpload">
          <el-button class="btn-blue" :icon="Upload" :loading="importing">导入开标记录</el-button>
        </el-upload>
        <span v-if="fileName" class="msc-file-name">{{ fileName }}（{{ sheets.length }} 个 Sheet）</span>
        <span v-else class="msc-hint">支持多工作表 Excel</span>
      </div>
      <div class="msc-header-right">
        <el-button v-if="canBatchCalculate" class="btn-green" :icon="Finished" :loading="loading" @click="batchCalculate">批量测算</el-button>
      </div>
    </header>

    <div v-if="!sheets.length" class="msc-empty">
      <div class="msc-empty-icon"><el-icon :size="48"><Upload /></el-icon></div>
      <p class="msc-empty-title">导入 Excel 开标记录</p>
      <p class="msc-empty-desc">支持包含多个工作表的 Excel 文件，每个 Sheet 作为一个独立标段</p>
    </div>

    <template v-else>
      <el-tabs v-model="activeTab" type="border-card" class="msc-tabs">
        <el-tab-pane v-for="(sheet, si) in sheets" :key="si" :label="sheet.name" :name="String(si)">
          <template v-if="sheetStates[si]">
            <template v-if="!hasResults">
              <div class="param-grid">
                <div class="param-card">
                  <h3 class="card-title">项目参数</h3>
                  <el-form label-position="top" class="param-form">
                    <el-form-item label="招标编号">
                      <el-input v-model="sheetStates[si].project.tender_no" />
                    </el-form-item>
                    <div class="form-row">
                      <el-form-item label="网省">
                        <el-select v-model="sheetStates[si].project.province" filterable>
                          <el-option v-for="p in PROVINCES" :key="p" :label="p" :value="p" />
                        </el-select>
                      </el-form-item>
                      <el-form-item label="目标公司">
                        <el-input v-model="sheetStates[si].project.target_company" />
                      </el-form-item>
                    </div>
                    <div class="form-row">
                      <el-form-item label="包限价">
                        <el-input v-model="sheetStates[si].project.ceiling_price" />
                      </el-form-item>
                      <el-form-item label="价格分占比">
                        <el-input v-model="sheetStates[si].project.price_weight" />
                      </el-form-item>
                    </div>
                  </el-form>
                </div>
                <div class="param-card">
                  <h3 class="card-title">评分规则</h3>
                  <el-form label-position="top" class="param-form">
                    <el-form-item label="评分方法">
                      <el-select v-model="sheetStates[si].methodCode" @change="onMethodChange(si)">
                        <el-option v-for="m in methods" :key="m.code" :label="`${m.code} ${m.name}`" :value="m.code" />
                      </el-select>
                    </el-form-item>
                    <div class="form-row param-keys">
                      <el-form-item v-for="(val, key) in sheetStates[si].params" :key="key" :label="parameterLabel(key)" :class="{ 'full-row': isFloatingTypeParam(key) }">
                        <el-select v-if="sheetStates[si].methodCode === 'A01' && isFloatingTypeParam(key)" v-model="sheetStates[si].params[key]" placeholder="请选择">
                          <el-option label="上浮：基准价=A2*(1+c)" value="1" />
                          <el-option label="下浮：基准价=A2*(1-c)" value="-1" />
                        </el-select>
                        <el-input v-else v-model="sheetStates[si].params[key]" />
                      </el-form-item>
                    </div>
                    <el-button class="reset-btn" :icon="Refresh" text @click="sheetStates[si].params = getDefaultParams(sheetStates[si].methodCode)">默认值</el-button>
                  </el-form>
                </div>
              </div>
              <div class="bids-card">
                <div class="bids-header">
                  <h3 class="card-title">报价数据（{{ sheetStates[si].bids.length }} 条）</h3>
                  <el-button class="btn-blue" size="small" :icon="Plus" @click="addBid(si)">新增</el-button>
                </div>
                <el-table :data="sheetStates[si].bids" height="280" :row-class-name="({ row }: any) => row.bidder_name === sheetStates[si].project.target_company ? 'target-row' : ''">
                  <el-table-column label="投标人" align="center">
                    <template #default="{ row, $index }"><el-input v-model="sheetStates[si].bids[$index].bidder_name" /></template>
                  </el-table-column>
                  <el-table-column label="报价" align="center">
                    <template #default="{ row, $index }"><el-input v-model="sheetStates[si].bids[$index].bid_price" /></template>
                  </el-table-column>
                  <el-table-column label="操作" align="center" width="80">
                    <template #default="{ $index }"><el-button text type="danger" size="small" @click="removeBid(si, $index)">删除</el-button></template>
                  </el-table-column>
                </el-table>
              </div>
            </template>
            <template v-else>
              <div v-if="results && results[si]" :key="'r-' + si">
                <div class="result-summary-grid">
                  <div class="result-card"><label>基准价</label><span class="result-val">{{ results[si].benchmark_price }}</span></div>
                  <div class="result-card"><label>折扣率</label><span class="result-val">{{ formatPercent(results[si].discount_rate) }}</span></div>
                  <div class="result-card"><label>投标人</label><span class="result-val">{{ results[si].bidder_count }}</span></div>
                  <div class="result-card"><label>有效报价</label><span class="result-val">{{ results[si].effective_count }}</span></div>
                  <div class="result-card"><label>目标排名</label><span class="result-val">{{ results[si].target.rank ?? '-' }}</span></div>
                  <div class="result-card"><label>与第1名分差</label><span class="result-val">{{ scoreGaps[si] || '-' }}</span></div>
                  <div class="result-card"><label>折算后分差</label><span class="result-val">{{ weightedGaps[si] || '-' }}</span></div>
                </div>
                <div class="bids-card">
                  <h3 class="card-title">排名详情</h3>
                  <el-table :data="results[si].rows" height="300">
                    <el-table-column prop="rank" label="排名" align="center" width="60" />
                    <el-table-column prop="bidder_name" label="投标人" align="center" />
                    <el-table-column prop="bid_price" label="报价" align="center" />
                    <el-table-column prop="score" label="价格分" align="center" />
                    <el-table-column label="折扣率" align="center">
                      <template #default="{ row }">{{ formatBidDiscount(row.bid_price, sheetStates[si].project.ceiling_price) }}%</template>
                    </el-table-column>
                    <el-table-column prop="remark" label="备注" align="center" />
                  </el-table>
                </div>
              </div>
              <div v-else class="no-result">暂无此 Sheet 的测算结果</div>
            </template>
          </template>
        </el-tab-pane>
      </el-tabs>
    </template>

    <el-drawer v-model="traceOpen" title="详细计算逻辑" size="450px">
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item v-for="(value, key) in traceData" :key="String(key)" :label="String(key)">
          {{ String(value) }}
        </el-descriptions-item>
      </el-descriptions>
    </el-drawer>
  </div>
</template>

<style scoped>
.msc{display:flex;flex-direction:column;height:100%;gap:16px}
.msc-header{display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.msc-header-left{display:flex;align-items:center;gap:12px}
.msc-file-name{font-size:13px;color:var(--sg-green);font-weight:600}
.msc-hint{font-size:13px;color:var(--label)}
.msc-empty{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;border:2px dashed var(--border);background:var(--card-bg);min-height:400px}
.msc-empty-icon{color:var(--sg-green)}
.msc-empty-title{font-size:16px;font-weight:600;color:var(--text);margin:0}
.msc-empty-desc{font-size:13px;color:var(--label);margin:0}
.msc-tabs{flex:1;min-height:0}
.msc-tabs :deep(.el-tabs__header){margin:0}
.msc-tabs :deep(.el-tabs__item){font-size:13px;height:40px;line-height:40px}
.msc-tabs :deep(.el-tabs__item.is-active){color:var(--sg-green);font-weight:600}
.msc-tabs :deep(.el-tabs__active-bar){background:var(--sg-green)}
.param-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.param-card{border:1px solid var(--border);background:var(--card-bg);padding:16px}
.card-title{margin:0 0 12px;font-size:14px;font-weight:600;color:var(--sg-green);padding-bottom:8px;border-bottom:2px solid var(--sg-green)}
.param-form .el-form-item{margin-bottom:12px}
.param-form .el-form-item__label{font-size:12px;color:var(--label);padding-bottom:2px}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.param-keys{display:flex;flex-wrap:wrap;gap:8px}
.param-keys .el-form-item{flex:1;min-width:100px}
.param-keys .full-row{flex:0 0 100%}
.reset-btn{margin-top:-4px}
.bids-card{border:1px solid var(--border);background:var(--card-bg);padding:16px}
.bids-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.bids-header .card-title{margin:0;border:none;padding:0}
.result-summary-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.result-card{text-align:center;padding:16px 8px;border:1px solid var(--border);background:var(--card-bg)}
.result-card label{display:block;font-size:12px;color:var(--label);margin-bottom:4px}
.result-val{display:block;font-size:18px;font-weight:700;color:var(--sg-green)}
.result-card-action{display:flex;align-items:center;justify-content:center;gap:8px}
.no-result{text-align:center;padding:40px;color:var(--label);font-size:14px}
.btn-green.el-button{background:var(--sg-green);border-color:var(--sg-green);color:#fff}
.btn-green.el-button:hover{background:var(--sg-green-hover);border-color:var(--sg-green-hover)}
:deep(.el-table .target-row){--el-table-tr-bg-color:var(--readonly-bg)}
</style>

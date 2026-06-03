<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { DocumentCopy, Download, Plus, Refresh, Upload } from '@element-plus/icons-vue'
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

const provinces = [
  '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江', '上海', '江苏', '浙江', '安徽',
  '福建', '江西', '山东', '河南', '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
  '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆', '其他',
]

const resultRows = computed(() => {
  const rows = store.result?.rows ?? []
  return [...rows].sort((a, b) => {
    if (a.rank === null && b.rank === null) {
      return 0
    }
    if (a.rank === null) {
      return 1
    }
    if (b.rank === null) {
      return -1
    }
    return a.rank - b.rank
  })
})
const methodName = computed(() => store.selectedMethod ? `${store.selectedMethod.code} ${store.selectedMethod.name}` : '')
const benchmarkDiscountRate = computed(() => formatPercent(store.result?.discount_rate))

function formatPercent(value: string | null | undefined) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    return value
  }
  return `${(parsed * 100).toFixed(2)}%`
}

onMounted(async () => {
  store.methods = await fetchMethods()
  store.applyDefaults()
})

watch(() => store.methodCode, () => {
  store.applyDefaults()
  store.result = null
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
  loading.value = true
  try {
    store.result = await calculate(store.payload(source))
  } catch (error) {
    ElMessage.error((error as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? '计算失败')
  } finally {
    loading.value = false
  }
}

async function downloadResult() {
  try {
    await exportXlsx(store.payload())
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
</script>

<template>
  <main class="app-shell">
    <section class="topbar">
      <div>
        <h1>国网价格分在线测算系统</h1>
        <p>{{ methodName }}</p>
      </div>
      <div class="actions">
        <el-upload :show-file-list="false" accept=".xlsx" :before-upload="beforeUpload">
          <el-button :icon="Upload">导入</el-button>
        </el-upload>
        <el-button :icon="Download" :disabled="!store.result" @click="downloadResult">导出</el-button>
        <el-button type="primary" :loading="loading" @click="runCalculate()">计算</el-button>
      </div>
    </section>

    <section class="workspace">
      <aside class="panel side-panel">
        <el-tabs model-value="project" stretch>
          <el-tab-pane label="项目" name="project">
            <el-form label-position="top" class="compact-form">
              <el-form-item label="招标编号"><el-input v-model="store.project.tender_no" /></el-form-item>
              <el-form-item label="招标名称"><el-input v-model="store.project.tender_name" /></el-form-item>
              <div class="form-grid">
                <el-form-item label="分标编号"><el-input v-model="store.project.section_no" /></el-form-item>
                <el-form-item label="包号"><el-input v-model="store.project.package_no" /></el-form-item>
              </div>
              <div class="form-grid">
                <el-form-item label="省份">
                  <el-select v-model="store.project.province" filterable>
                    <el-option v-for="province in provinces" :key="province" :label="province" :value="province" />
                  </el-select>
                </el-form-item>
                <el-form-item label="目标公司"><el-input v-model="store.project.target_company" /></el-form-item>
              </div>
              <div class="form-grid">
                <el-form-item label="最高限价"><el-input v-model="store.project.ceiling_price" /></el-form-item>
                <el-form-item label="价格分占比">
                  <el-input v-model="store.project.price_weight">
                    <template #append>%</template>
                  </el-input>
                </el-form-item>
              </div>
              <el-form-item label="评分方法">
                <el-select v-model="store.methodCode" filterable>
                  <el-option v-for="method in store.methods" :key="method.code" :label="`${method.code} ${method.name}`" :value="method.code" />
                </el-select>
              </el-form-item>
            </el-form>
          </el-tab-pane>
          <el-tab-pane label="参数" name="params">
            <div class="param-title">
              <span>{{ store.selectedMethod?.name }}</span>
              <el-button :icon="Refresh" text @click="store.applyDefaults()">默认值</el-button>
            </div>
            <el-form label-position="top" class="compact-form">
              <el-form-item v-for="(_, key) in store.params" :key="key" :label="key">
                <el-input v-model="store.params[key]">
                  <template v-if="store.isPercentParam(String(key))" #append>%</template>
                </el-input>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </aside>

      <section class="panel data-panel">
        <div class="section-head">
          <div>
            <h2>报价明细</h2>
            <span>支持数字报价、空报价和“不开标”</span>
          </div>
          <div class="table-actions">
            <el-button :icon="DocumentCopy" @click="pasteOpen = true">粘贴</el-button>
            <el-button :icon="Plus" @click="addBid">新增</el-button>
          </div>
        </div>
        <el-table :data="store.bids" height="430" border>
          <el-table-column type="index" width="56" label="#" />
          <el-table-column label="投标人名称" min-width="180">
            <template #default="{ row }"><el-input v-model="row.bidder_name" /></template>
          </el-table-column>
          <el-table-column label="投标价格" min-width="160">
            <template #default="{ row }"><el-input v-model="row.bid_price" /></template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ $index }"><el-button text type="danger" @click="removeBid($index)">删除</el-button></template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel result-panel">
        <div class="section-head">
          <div>
            <h2>测算结果</h2>
            <span>{{ store.result ? '后端计算结果' : '等待计算' }}</span>
          </div>
          <el-button :disabled="!store.result" @click="traceOpen = true">过程</el-button>
        </div>
        <div class="metrics">
          <div><span>基准价</span><strong>{{ store.result?.benchmark_price ?? '-' }}</strong></div>
          <div><span>基准价折扣率</span><strong>{{ benchmarkDiscountRate }}</strong></div>
          <div><span>投标人数量</span><strong>{{ store.result?.bidder_count ?? '-' }}</strong></div>
          <div><span>有效投标人数量</span><strong>{{ store.result?.effective_count ?? '-' }}</strong></div>
          <div><span>目标公司报价排名</span><strong>{{ store.result?.target.rank ?? '-' }}</strong></div>
          <div><span>目标公司价格分</span><strong>{{ store.result?.target.score ?? '-' }}</strong></div>
          <div><span>目标公司与第1名的分差</span><strong>{{ store.result?.target.score_gap ?? '-' }}</strong></div>
          <div><span>折算后分差</span><strong>{{ store.result?.target.weighted_gap ?? '-' }}</strong></div>
        </div>
        <el-table :data="resultRows" height="360" border>
          <el-table-column prop="bidder_name" label="投标人" min-width="150" />
          <el-table-column prop="bid_price" label="报价" width="120" />
          <el-table-column prop="score" label="价格分" width="110" />
          <el-table-column prop="rank" label="排名" width="70" />
          <el-table-column label="参与" width="80">
            <template #default="{ row }"><el-tag :type="row.participated ? 'success' : 'info'">{{ row.participated ? '是' : '否' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="基准" width="80">
            <template #default="{ row }"><el-tag :type="row.used_for_benchmark ? 'primary' : 'info'">{{ row.used_for_benchmark ? '是' : '否' }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="140" />
        </el-table>
      </section>
    </section>

    <el-drawer v-model="traceOpen" title="计算过程" size="420px">
      <el-descriptions :column="1" border>
        <el-descriptions-item v-for="(value, key) in store.result?.debug" :key="key" :label="String(key)">
          {{ value }}
        </el-descriptions-item>
      </el-descriptions>
    </el-drawer>

    <el-dialog v-model="mappingOpen" title="手动映射 Excel 列" width="720px">
      <div class="mapping-grid">
        <el-form-item label="投标人列">
          <el-select v-model="bidderColumn">
            <el-option v-for="column in mappingColumns" :key="column" :label="column" :value="column" />
          </el-select>
        </el-form-item>
        <el-form-item label="报价列">
          <el-select v-model="priceColumn">
            <el-option v-for="column in mappingColumns" :key="column" :label="column" :value="column" />
          </el-select>
        </el-form-item>
      </div>
      <el-table :data="mappingPreview" height="280" border>
        <el-table-column v-for="column in mappingColumns" :key="column" :prop="column" :label="column" min-width="140" />
      </el-table>
      <template #footer>
        <el-button @click="mappingOpen = false">取消</el-button>
        <el-button type="primary" @click="applyMappedImport">导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="pasteOpen" title="粘贴报价明细" width="620px">
      <el-input
        v-model="pasteText"
        type="textarea"
        :rows="12"
        placeholder="每行一条：投标人名称	投标价格。也支持只粘贴报价，系统会自动生成投标人名称。"
      />
      <template #footer>
        <el-button @click="pasteOpen = false">取消</el-button>
        <el-button type="primary" @click="applyPastedRows">应用</el-button>
      </template>
    </el-dialog>
  </main>
</template>

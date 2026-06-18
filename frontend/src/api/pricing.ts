import axios from 'axios'

axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('bid_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface MethodInfo {
  code: string
  name: string
  defaults: Record<string, string>
}

export interface ProjectPayload {
  tender_no: string
  tender_name?: string
  section_no: string
  package_no: string
  province: string
  ceiling_price?: string
  price_weight?: string
  target_company?: string
}

export interface BidPayload {
  bidder_name: string
  bid_price: string | null
}

export interface CalculatePayload {
  project: ProjectPayload
  method_code: string
  params: Record<string, string>
  bids: BidPayload[]
  source: string
}

export interface ResultRow {
  rank: number | null
  bidder_name: string
  bid_price: string | null
  participated: boolean
  used_for_benchmark: boolean
  score: string | null
  remark: string
}

export interface CalculateResult {
  method_code: string
  method_name: string
  benchmark_price: string
  discount_rate: string | null
  bidder_count: number
  effective_count: number
  target: {
    found: boolean
    score: string | null
    rank: number | null
    score_gap: string | null
    weighted_gap: string | null
  }
  rows: ResultRow[]
  debug: Record<string, unknown>
}

export interface SheetData {
  name: string
  rows: BidPayload[]
  columns: string[]
}

export interface MultiSheetImportResult {
  sheets: SheetData[]
}

export interface SheetResult {
  name: string
  method_code: string
  method_name: string
  benchmark_price: string
  discount_rate: string | null
  bidder_count: number
  effective_count: number
  target: {
    found: boolean
    score: string | null
    rank: number | null
    score_gap: string | null
    weighted_gap: string | null
  }
  rows: ResultRow[]
  debug: Record<string, unknown>
}

export interface MultiCalculateResult {
  results: SheetResult[]
}

export async function fetchMethods() {
  const { data } = await axios.get<MethodInfo[]>('/api/methods')
  return data
}

export async function calculate(payload: CalculatePayload) {
  const { data } = await axios.post<CalculateResult>('/api/calculate', payload)
  return data
}

export async function importXlsx(file: File) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await axios.post<{
    rows: BidPayload[]
    mapping: Record<string, string>
    warnings: string[]
    requires_mapping: boolean
    columns: string[]
    preview: Record<string, string>[]
  }>('/api/import-xlsx', form)
  return data
}

export async function importXlsxMulti(file: File) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await axios.post<MultiSheetImportResult>('/api/import-xlsx-multi', form)
  return data
}

export async function calculateMulti(payload: {
  sheets: Array<{
    name: string
    project: ProjectPayload
    method_code: string
    params: Record<string, string>
    bids: BidPayload[]
    source: string
  }>
}) {
  const { data } = await axios.post<MultiCalculateResult>('/api/calculate-multi', payload)
  return data
}

export async function exportXlsx(payload: CalculatePayload) {
  const res = await axios.post('/api/export-xlsx', payload, { responseType: 'blob' })
  const disposition = res.headers['content-disposition'] ?? ''
  const match = disposition.match(/filename\*=UTF-8''(.+)/)
  const filename = match ? decodeURIComponent(match[1]) : `国网价格分测算_${payload.project.tender_no}_${payload.project.section_no}_${payload.project.package_no}.xlsx`
  const url = URL.createObjectURL(res.data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

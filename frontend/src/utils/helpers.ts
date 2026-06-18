export const PROVINCES = [
  '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江', '上海', '江苏', '浙江', '安徽',
  '福建', '江西', '山东', '河南', '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
  '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆', '其他',
]

export const PERCENT_PARAM_KEYS = new Set(['w1', 'w2', 'c'])

export function toDisplayPercent(value: string | undefined): string {
  if (value === undefined || value === '') return ''
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return value
  return (parsed * 100).toFixed(2)
}

export function toApiPercent(value: string | undefined): string {
  if (value === undefined || value === '') return ''
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return value
  return String(parsed / 100)
}

export function formatPercent(value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '-'
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return value
  return `${(parsed * 100).toFixed(2)}%`
}

export function formatBidDiscount(bidPrice: string | null | undefined, ceilingPrice: string | undefined): string {
  if (!bidPrice || !ceilingPrice) return '-'
  const p = Number(bidPrice)
  const c = Number(ceilingPrice)
  if (!Number.isFinite(p) || !Number.isFinite(c) || c <= 0) return '-'
  return ((p / c) * 100).toFixed(2)
}

export function getDefaultApiParams(methods: { code: string; defaults?: Record<string, string> }[], code: string): Record<string, string> {
  const m = methods.find(x => x.code === code)
  if (m?.defaults) {
    return Object.fromEntries(
      Object.entries(m.defaults).map(([k, v]) => [k, PERCENT_PARAM_KEYS.has(k) ? toDisplayPercent(v) : v]),
    )
  }
  return {}
}

export function applyFloatDirection(params: Record<string, string>, methodCode: string): Record<string, string> {
  if (methodCode === 'A01' && params.round_scale && ['1', '-1'].includes(params.round_scale)) {
    const { round_scale: _, ...rest } = params
    return { ...rest, float_direction: params.round_scale }
  }
  return params
}

export function cleanNumericParams(params: Record<string, string>, methodCode: string): Record<string, string> {
  const converted = Object.fromEntries(
    Object.entries(params).map(([k, v]) => [k, PERCENT_PARAM_KEYS.has(k) ? toApiPercent(v) : v]),
  )
  return applyFloatDirection(converted, methodCode)
}

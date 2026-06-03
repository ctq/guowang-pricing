import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import type { BidPayload, CalculatePayload, CalculateResult, MethodInfo, ProjectPayload } from '../api/pricing'

const PERCENT_PARAM_KEYS = new Set(['w1', 'w2', 'c'])

function toDisplayPercent(value: string | undefined) {
  if (value === undefined || value === '') {
    return ''
  }
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    return value
  }
  return (parsed * 100).toFixed(2)
}

function toApiPercent(value: string | undefined) {
  if (value === undefined || value === '') {
    return ''
  }
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    return value
  }
  return String(parsed / 100)
}

function displayParams(defaults: Record<string, string>) {
  return Object.fromEntries(
    Object.entries(defaults).map(([key, value]) => [
      key,
      PERCENT_PARAM_KEYS.has(key) ? toDisplayPercent(value) : value,
    ]),
  )
}

function apiParams(params: Record<string, string>) {
  return Object.fromEntries(
    Object.entries(params).map(([key, value]) => [
      key,
      PERCENT_PARAM_KEYS.has(key) ? toApiPercent(value) : value,
    ]),
  )
}

export const useCalculatorStore = defineStore('calculator', () => {
  const methods = shallowRef<MethodInfo[]>([])
  const methodCode = ref('A01')
  const project = ref<ProjectPayload>({
    tender_no: 'T001',
    tender_name: '',
    section_no: 'S001',
    package_no: 'P001',
    province: '浙江',
    ceiling_price: '200',
    price_weight: '40.00',
    target_company: '投标人1',
  })
  const params = ref<Record<string, string>>({})
  const bids = ref<BidPayload[]>([
    { bidder_name: '投标人1', bid_price: '180' },
    { bidder_name: '投标人2', bid_price: '190' },
    { bidder_name: '投标人3', bid_price: '200' },
    { bidder_name: '投标人4', bid_price: '210' },
    { bidder_name: '投标人5', bid_price: '不开标' },
  ])
  const result = shallowRef<CalculateResult | null>(null)

  const selectedMethod = computed(() => methods.value.find(item => item.code === methodCode.value))

  function applyDefaults() {
    params.value = displayParams(selectedMethod.value?.defaults ?? {})
  }

  function payload(source = 'manual'): CalculatePayload {
    const projectPayload = {
      ...project.value,
      price_weight: toApiPercent(project.value.price_weight),
    }
    return {
      project: projectPayload,
      method_code: methodCode.value,
      params: apiParams(params.value),
      bids: bids.value.filter(row => row.bidder_name || row.bid_price),
      source,
    }
  }

  function isPercentParam(key: string) {
    return PERCENT_PARAM_KEYS.has(key)
  }

  return { methods, methodCode, project, params, bids, result, selectedMethod, applyDefaults, payload, isPercentParam }
})

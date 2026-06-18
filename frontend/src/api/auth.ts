import axios from 'axios'

export interface QRCodeData {
  code: string
  qrcode_url: string
  expires_at: string
}

export async function fetchQRCode() {
  const { data } = await axios.post<QRCodeData>('/api/auth/qrcode')
  return data
}

export async function queryStatus(code: string) {
  const { data } = await axios.get<{ status: string; token?: string }>('/api/auth/status', {
    params: { code },
  })
  return data
}

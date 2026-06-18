import axios from 'axios'

export interface FileInfo {
  name: string
  size: number
  mtime: string
}

export async function listFiles() {
  const { data } = await axios.get<FileInfo[]>('/api/files')
  return data
}

export async function readFile(filename: string) {
  const { data } = await axios.get<{ content: string }>(`/api/files/${encodeURIComponent(filename)}`)
  return data.content
}

export async function writeFile(filename: string, content: string) {
  const { data } = await axios.put<{ status: string }>(`/api/files/${encodeURIComponent(filename)}`, { content })
  return data
}

export async function renameFile(oldName: string, newName: string) {
  const { data } = await axios.post<{ status: string }>(`/api/files/${encodeURIComponent(oldName)}/rename`, { new_name: newName })
  return data
}

export async function createFile(name: string) {
  const { data } = await axios.post<{ status: string }>('/api/files', { name })
  return data
}

export async function deleteFile(filename: string) {
  const { data } = await axios.delete<{ status: string }>(`/api/files/${encodeURIComponent(filename)}`)
  return data
}

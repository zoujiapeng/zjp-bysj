import axios, { AxiosError } from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 20_000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('student-care-token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && !String(error.config?.url).includes('/auth/login')) {
      localStorage.removeItem('student-care-token')
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  },
)

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg ?? '数据格式错误').join('；')
    }
    if (error.code === 'ECONNABORTED') return '请求超时，请检查服务状态'
    if (!error.response) return '无法连接服务器，请检查网络或后端服务'
  }
  return error instanceof Error ? error.message : '操作失败'
}

export async function downloadFile(url: string, filename: string): Promise<void> {
  const response = await api.get(url, { responseType: 'blob' })
  const blobUrl = URL.createObjectURL(response.data)
  const anchor = document.createElement('a')
  anchor.href = blobUrl
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(blobUrl)
}

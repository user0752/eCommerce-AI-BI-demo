import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      sessionStorage.removeItem('token')
      sessionStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default {
  async checkStatus() {
    const res = await api.get('/status')
    return res.data
  },

  async streamAsk(question, onEvent, abortSignal) {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token')
    const fetchOptions = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        question
      })
    }
    if (token) {
      fetchOptions.headers['Authorization'] = `Bearer ${token}`
    }
    if (abortSignal) {
      fetchOptions.signal = abortSignal
    }

    const response = await fetch('/api/chat/stream', fetchOptions)

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''

      for (const part of parts) {
        const dataLine = part.split('\n').find(l => l.startsWith('data: '))
        if (!dataLine) continue

        const data = dataLine.slice(6).trim()
        if (data === '[DONE]') {
          onEvent({ type: 'done' })
          return
        }

        try {
          const parsed = JSON.parse(data)
          if (parsed.type === 'thinking_start') {
            onEvent({ type: 'thinking_start' })
          } else if (parsed.type === 'thinking_content') {
            onEvent({ type: 'thinking_content', content: parsed.content || '' })
          } else if (parsed.type === 'thinking_end') {
            onEvent({ type: 'thinking_end' })
          } else if (parsed.type === 'content' || parsed.type === 'source') {
            onEvent({ type: 'content', content: parsed.content || '' })
          } else if (parsed.type === 'error') {
            onEvent({ type: 'error', content: parsed.content || '' })
          }
        } catch (e) {
          if (data) {
            onEvent({ type: 'content', content: data })
          }
        }
      }
    }

    onEvent({ type: 'done' })
  },

  async getSessions() {
    const res = await api.get('/sessions')
    return res.data
  },

  async getSession(id) {
    const res = await api.get(`/sessions/${id}`)
    return res.data
  },

  async createSession(data) {
    const res = await api.post('/sessions', data)
    return res.data
  },

  async updateSession(id, data) {
    const res = await api.put(`/sessions/${id}`, data)
    return res.data
  },

  async deleteSession(id) {
    await api.delete(`/sessions/${id}`)
  },

  async getAuditLogs(status = '', limit = 100) {
    const params = { limit }
    if (status) params.status = status
    const res = await api.get('/admin/audit-logs', { params })
    return res.data
  },

  async getFenceMetrics() {
    const res = await api.get('/admin/fence/metrics')
    return res.data
  },

  async getKnowledgeGaps() {
    const res = await api.get('/admin/knowledge/gaps')
    return res.data
  },

  async getDashboardRegionConsume() {
    const res = await api.get('/dashboard/region_consume')
    return res.data
  },

  async getDashboardProductFeature() {
    const res = await api.get('/dashboard/product_feature')
    return res.data
  },

  async getDashboardUserProfile() {
    const res = await api.get('/dashboard/user_profile')
    return res.data
  },

  async getDashboardInteraction() {
    const res = await api.get('/dashboard/interaction')
    return res.data
  },

  async login(data) {
    const res = await api.post('/auth/login', data)
    return res.data
  },

  async register(data) {
    const res = await api.post('/auth/register', data)
    return res.data
  },

  async getCaptcha() {
    const res = await api.get('/auth/captcha')
    return res.data
  },

  async getCurrentUser() {
    const res = await api.get('/auth/me')
    return res.data
  },

  async changePassword(data) {
    const res = await api.post('/auth/change-password', data)
    return res.data
  },

  async uploadAvatar(file) {
    const formData = new FormData()
    formData.append('avatar', file)
    const res = await api.post('/auth/upload-avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    return res.data
  },

  async updateProfile(data) {
    const res = await api.post('/auth/update-profile', data)
    return res.data
  }
}

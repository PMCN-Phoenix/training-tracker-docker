// 后端 API 客户端（FastAPI @ 8001）
const BASE_URL = 'http://127.0.0.1:8001/api'

async function request(path, options = {}) {
  const res = await fetch(BASE_URL + path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (body && body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* 非 JSON 响应，保留 statusText */
    }
    throw new Error(`请求失败 ${res.status}: ${detail}`)
  }
  return res.json()
}

export const api = {
  // 训练记录（按动作）
  exercise: (exercise, { startDate, endDate } = {}) => {
    const params = new URLSearchParams()
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)
    const qs = params.toString()
    return request(`/training/exercise/${encodeURIComponent(exercise)}${qs ? `?${qs}` : ''}`)
  },
  // PR 测试（按动作）
  prTests: ({ startDate, endDate } = {}) => {
    const params = new URLSearchParams()
    if (startDate) params.set('start_date', startDate)
    if (endDate) params.set('end_date', endDate)
    const qs = params.toString()
    return request(`/pr/tests${qs ? `?${qs}` : ''}`)
  },
  // 训练日历（训练日 + PR 日集合）
  calendar: () => request('/training/calendar'),
  // 感悟（可筛选）
  reflections: (filters = {}) => {
    const params = new URLSearchParams()
    if (filters.direction) params.set('direction', filters.direction)
    if (filters.tag) params.set('tag', filters.tag)
    if (filters.date) params.set('date', filters.date)
    const qs = params.toString()
    return request(`/reflections${qs ? `?${qs}` : ''}`)
  },
  // 单条感悟
  reflection: (id) => request(`/reflections/${id}`),
  // 统计
  stats: () => request('/reflections/stats'),
  // 按日全貌（训练 + 晨脉 + 意象）
  day: (date) => request(`/day/${date}`),
  // 创建感悟
  createReflection: (payload) =>
    request('/reflections', { method: 'POST', body: JSON.stringify(payload) }),
  // 更新感悟
  updateReflection: (id, payload) =>
    request(`/reflections/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  // 删除感悟
  deleteReflection: (id) => request(`/reflections/${id}`, { method: 'DELETE' }),
}

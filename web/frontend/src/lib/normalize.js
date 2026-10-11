// 数据适配层：后端 API 形状 → 组件形状（纯函数，可单测）
// 后端 session: { session_id, date, direction, time, sets:[{set_index, weight_kg, reps}] }
// 组件 session: { sessionId, date, direction, sets:[{w, r}] }
export const normalizeSessions = (data) => {
  const raw = (data && data.sessions) || []
  return raw.map((s) => ({
    sessionId: s.session_id,
    date: s.date,
    direction: s.direction,
    exercise: s.exercise || null,
    time: s.time,
    sets: (s.sets || []).map((st) => ({ w: st.weight_kg, r: st.reps })), // 顺序 = 后端已按 set_index 排序
  }))
}

// 后端 PR: tests = [{ test_no, date, session_id, points: [{weight_kg, max_reps}] }]
// 组件 PR: tests = [{ test_no, date, session_id, points: [[w, n], ...] }]
export const normalizePrTests = (data) => {
  const exercises = (data && data.exercises) || []
  return exercises.map((e) => ({
    exercise: e.exercise,
    direction: e.direction,
    tests: (e.tests || []).map((t) => ({
      test_no: t.test_no,
      date: t.date,
      session_id: t.session_id,
      points: (t.points || [])
        .map((p) => [p.weight_kg, p.max_reps])
        .sort((a, b) => (a[0] || 0) - (b[0] || 0)), // 组件内部统一按重量升序排列
    })),
  }))
}

// 感悟：后端 → 组件形状（保留原字段，补空默认值）
export const normalizeReflections = (list) =>
  (list || []).map((r) => ({
    id: r.id,
    date: r.date,
    direction: r.direction || '',
    exercise: r.exercise || null,
    setIndex: r.set_index || null,
    sessionId: r.session_id || null,
    content: r.content || '',
    title: r.title || '',
    tags: r.tags || [],
    source: r.source || '',
    time: r.time || '',
  }))

// 纯函数库：不依赖 DOM / React，可直接被 Node 单测
// 锚定键：date + exercise + setIndex 三键锚定（设计文档 D14）
export const pad2 = (n) => (n < 10 ? `0${n}` : `${n}`)
export const dateStr = (y, m, d) => `${y}-${pad2(m + 1)}-${pad2(d)}`
export const todayStr = () => {
  const d = new Date()
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}
export const anchorKey = (date, exercise, setIndex) => `${date}|${exercise}|${setIndex}`

// 感悟是否匹配到组行：无 setIndex 视为动作级/日级（恒匹配）；有 setIndex 需存在对应组
export const isMatched = (ref, sessions) => {
  if (!ref.setIndex) return true
  return sessions.some(
    (s) => s.exercise === ref.exercise && s.date === ref.date && s.sets && s.sets[ref.setIndex - 1],
  )
}

// PR 测试按日期升序编号（第 1 次 = 最早）
export const prSeries = (tests) =>
  (tests || [])
    .slice()
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((t, i) => ({ ...t, no: i + 1 }))

// 最近一次测试 = 编号最大的一条
export const latestPr = (tests) => {
  const s = prSeries(tests)
  return s.length ? s[s.length - 1] : null
}

// 当前最佳档 = 最近一次测试的最高档（最重）
export const bestPoint = (test) => {
  if (!test || !test.points || !test.points.length) return null
  return test.points.slice().sort((a, b) => b[0] - a[0])[0]
}

// 阶梯行 = 重量升序
export const ladderRows = (test) =>
  test && test.points ? test.points.slice().sort((a, b) => a[0] - b[0]) : []

// 迷你图数据（设计 D7 双线）：训练第一组重量实线 + PR 极限虚线红（PR 轮红点数标不连线）
export function miniChartData(sessions, tests) {
  const sorted = (sessions || []).slice().sort((a, b) => a.date.localeCompare(b.date))
  const pts = [] // 训练实线点 {date, w}
  const prpts = [] // PR 红点 {date, w, n}
  const testByDate = {}
  ;(tests || []).forEach((t) => {
    testByDate[t.date] = testByDate[t.date] || []
    testByDate[t.date].push(t)
  })
  sorted.forEach((s) => {
    const dayTests = testByDate[s.date]
    if (dayTests && dayTests.length) {
      dayTests.forEach((t) => {
        ;(t.points || []).forEach((p) => prpts.push({ date: s.date, w: p[0], n: p[1] }))
      })
    } else if (s.sets && s.sets.length) {
      pts.push({ date: s.date, w: s.sets[0].w })
    }
  })
  return { pts, prpts }
}

// PR 曲线坐标换算（weight → x，reps → y），供 SVG 使用
export function curveScale(allPoints, W, H, ML, MR, MT, MB) {
  const ws = allPoints.map((p) => p[0])
  const ns = allPoints.map((p) => p[1])
  const wmin = Math.min(...ws) - 3
  const wmax = Math.max(...ws) + 3
  const nmin = 0
  const nmax = Math.max(...ns) + 2
  const sx = (w) => ML + ((w - wmin) / (wmax - wmin)) * (W - ML - MR)
  const sy = (n) => H - MB - ((n - nmin) / (nmax - nmin)) * (H - MT - MB)
  return { sx, sy, wmin, wmax, nmin, nmax }
}

export const fmtW = (w) => `${w}kg`
export const fmtN = (n) => `${n} 次`

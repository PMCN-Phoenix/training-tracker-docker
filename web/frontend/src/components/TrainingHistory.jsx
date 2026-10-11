import { useMemo, useState } from 'react'
import { useUiStore } from '../store/useUiStore.js'
import { useExercise, usePrTests, useReflections } from '../api/hooks.js'
import { normalizeSessions, normalizePrTests, normalizeReflections } from '../lib/normalize.js'
import { latestPr, bestPoint, ladderRows, isMatched, miniChartData, fmtW, fmtN } from '../lib/utils.js'
import { DIR_NAME, GRAFANA } from '../const/exercises.js'

// 中栏：按动作 —— 动作标题 + Grafana 深链 + 迷你图 + PR 卡片 + 动作级感悟 + 待匹配 + 训练轮组行
export default function TrainingHistory() {
  const activeExercise = useUiStore((s) => s.activeExercise)
  const selected = useUiStore((s) => s.selected)
  const selectSet = useUiStore((s) => s.selectSet)
  const selectRef = useUiStore((s) => s.selectRef)
  const openDrawer = useUiStore((s) => s.openDrawer)
  const openForm = useUiStore((s) => s.openForm)

  const { data: exData } = useExercise(activeExercise)
  const { data: prData } = usePrTests()
  const { data: refData } = useReflections({})

  const sessions = useMemo(() => normalizeSessions(exData), [exData])
  const prTests = useMemo(() => {
    const n = normalizePrTests(prData)
    return n.find((e) => e.exercise === activeExercise) || { exercise: activeExercise, tests: [] }
  }, [prData, activeExercise])
  const reflections = useMemo(() => normalizeReflections(refData), [refData])

  const ex = { label: activeExercise, direction: (sessions[0] && sessions[0].direction) || prTests.direction || 'push' }
  const exRefs = reflections.filter((r) => r.exercise === activeExercise && !r.setIndex)
  const unmatched = reflections.filter((r) => r.exercise === activeExercise && r.setIndex && !isMatched(r, sessions))
  const sorted = sessions.slice().sort((a, b) => b.date.localeCompare(a.date))
  // 训练档 = 最近一次训练 session 的第一组重量
  const latestTrainW = sorted.length && sorted[0].sets.length ? sorted[0].sets[0].w : null

  return (
    <section className="col-mid">
      <div className="mid-head">
        <h2>{ex.label}</h2>
        <span className="dir">{DIR_NAME[ex.direction] || ''}</span>
        <a className="gfl" href={GRAFANA.exerciseUrl(ex.direction)} target="_blank" rel="noreferrer">
          在 Grafana 查看 →
        </a>
      </div>

      <MiniChart sessions={sessions} tests={prTests.tests} exercise={ex.label} />

      <PrCard tests={prTests.tests} trainW={latestTrainW} onOpenDrawer={() => openDrawer(ex.label)} />

      {exRefs.map((r) => (
        <div key={r.id} className="exref" onClick={() => selectRef(r.id)}>
          <span className="ic">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
            </svg>
          </span>
          <div>
            动作级感悟 · <b>{r.content}</b>
            <div className="meta">
              {r.date} {r.time} · {r.tags.join(' / ')}
            </div>
          </div>
        </div>
      ))}

      {unmatched.map((r) => (
        <div key={r.id} className="unmatch" onClick={() => selectRef(r.id)}>
          <span style={{ color: 'var(--dim)' }}>◷</span>
          <div>
            <b>第{r.setIndex}组感悟待匹配</b> · {r.content}
          </div>
          <span className="pend">未匹配到组</span>
        </div>
      ))}

      {!sorted.length && !unmatched.length && !exRefs.length && (
        <div className="empty-mid">
          暂无训练记录 —— 消息录入「{ex.label} 47.5kg×8」后这里出现历史组数×重量
        </div>
      )}

      {sorted.map((s) => (
        <div key={s.sessionId} className="session">
          <div className="shead">
            <span className="date">{s.date}</span>
            <span>{DIR_NAME[s.direction]}</span>
            <span className="n">{s.sets.length} 组</span>
          </div>
          {s.sets.map((st, idx) => {
            const setIndex = idx + 1
            const srs = reflections.filter(
              (r) => r.exercise === activeExercise && r.date === s.date && r.setIndex === setIndex,
            )
            const sel = selected.type === 'set' && selected.sessionId === s.sessionId && selected.setIndex === setIndex
            return (
              <div
                key={`${s.sessionId}-${setIndex}`}
                className={`set-row${sel ? ' sel' : ''}${srs.length ? ' has-r' : ''}`}
                onClick={() => selectSet(s.sessionId, setIndex)}
              >
                <span className="set-no">第{setIndex}组</span>
                <span className="set-w">{st.w}kg</span>
                <span className="set-reps">× {st.r} 次</span>
                <span className="set-tags">
                  {srs.length > 0 && (
                    <span className="note-ic">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                        <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
                      </svg>
                      {srs.length}
                    </span>
                  )}
                </span>
              </div>
            )
          })}
        </div>
      ))}
    </section>
  )
}

// 迷你图：训练第一组重量实线（蓝）+ PR 极限虚线（红，PR 轮红点连线）
function MiniChart({ sessions, tests, exercise }) {
  const { pts, prpts } = miniChartData(sessions, tests)
  if (!pts.length && !prpts.length) {
    return (
      <div className="mini-chart">
        <div className="mc-title">重量趋势 · 训练第一组实线 / PR 极限虚线</div>
        <div style={{ color: 'var(--dim)', fontSize: '11.5px', padding: '6px 0 4px' }}>暂无训练记录</div>
      </div>
    )
  }
  const all = pts.concat(prpts.map((p) => ({ w: p.w })))
  const wmin = Math.min(...all.map((p) => p.w)) - 2.5
  const wmax = Math.max(...all.map((p) => p.w)) + 2.5
  const W = 640
  const H = 74
  const ML = 34
  const MR = 34
  const MT = 10
  const MB = 18
  const sx = (w) => ML + ((w - wmin) / (wmax - wmin)) * (W - ML - MR)
  const sy = () => H - MB - 14 // 单行高度示意
  const lineD = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${sx(p.w)},${sy()}`).join(' ')
  const prD = prpts.map((p, i) => `${i === 0 ? 'M' : 'L'}${sx(p.w)},${sy()}`).join(' ')

  return (
    <div className="mini-chart">
      <div className="mc-title">重量趋势 · 训练第一组实线 / PR 极限虚线 · {exercise}</div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', display: 'block' }}>
        <line x1={sx(wmin)} y1={H - MB} x2={sx(wmax)} y2={H - MB} stroke="#33415a" />
        {pts.map((p, i) => (
          <circle key={`t${i}`} cx={sx(p.w)} cy={sy()} r="3.5" fill="#58a6ff" stroke="#0d1117" strokeWidth="1.2" />
        ))}
        {lineD && <path d={lineD} fill="none" stroke="#58a6ff" strokeWidth="2" />}
        {prD && <path d={prD} fill="none" stroke="#f85149" strokeWidth="1.8" strokeDasharray="4 3" opacity="0.85" />}
        {prpts.map((p, i) => (
          <circle key={`p${i}`} cx={sx(p.w)} cy={sy()} r="3.5" fill="#f85149" stroke="#0d1117" strokeWidth="1.2" />
        ))}
      </svg>
    </div>
  )
}

// PR 卡片：最近测试阶梯 + 当前最佳高亮 + 训练档 + 查看历史 PR → 抽屉
function PrCard({ tests, trainW, onOpenDrawer }) {
  const [open, setOpen] = useState(false)
  const latest = latestPr(tests)
  if (!latest) return null
  const best = bestPoint(latest)
  const rows = ladderRows(latest)

  return (
    <div className={`pr-card${open ? ' open' : ''}`}>
      <div className="pc-head" onClick={() => setOpen(!open)}>
        <span>PR · 最近 {latest.date}</span>
        <span>
          <b>当前最佳 {best ? `${best[0]}kg → ${best[1]} 次` : '–'}</b>
          {trainW ? `（训练档 ${trainW}kg）` : ''} ▾
        </span>
      </div>
      <div className="pc-body">
        {rows.map((p) => (
          <div key={p[0]} className={`pc-row${best && p[0] === best[0] ? ' best' : ''}`}>
            <span>{p[0]}kg</span>
            <span>{p[1]} 次</span>
          </div>
        ))}
        <div className="pc-hist">
          <button onClick={onOpenDrawer}>查看历史 PR →</button>
        </div>
      </div>
    </div>
  )
}

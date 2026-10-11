import { useState } from 'react'
import { useUiStore } from '../store/useUiStore.js'
import { usePrTests, useReflections, useCalendar } from '../api/hooks.js'
import { EXERCISES, DIR_NAME, DIR_ORDER } from '../const/exercises.js'
import { latestPr, bestPoint, ladderRows, dateStr, pad2 } from '../lib/utils.js'

// 左栏：按动作（列表 + PR 红标） / 按日（迷你日历）
export default function LeftNav() {
  const mode = useUiStore((s) => s.mode)
  const activeExercise = useUiStore((s) => s.activeExercise)
  const setExercise = useUiStore((s) => s.setExercise)
  const setPrPop = useUiStore((s) => s.setPrPop)
  const { data: prData } = usePrTests()
  const { data: reflections } = useReflections({})

  // PR 红标：该动作最近测过 PR（设计 D1：仅最近测 PR 才加细红标）
  const prByExercise = {}
  ;(prData?.exercises || []).forEach((e) => {
    prByExercise[e.exercise] = e.tests
  })

  const refByExercise = {}
  ;(reflections || []).forEach((r) => {
    if (r.exercise) refByExercise[r.exercise] = (refByExercise[r.exercise] || 0) + 1
  })

  if (mode === 'day') return <MiniCalendar />

  return (
    <aside className="col-left">
      {DIR_ORDER.map((dir) => (
        <div key={dir}>
          <div className="grp-label">{DIR_NAME[dir]}</div>
          {EXERCISES.filter((e) => e.direction === dir).map((e) => {
            const hasRef = (refByExercise[e.label] || 0) > 0
            const prOn = Boolean(latestPr(prByExercise[e.label]))
            return (
              <div
                key={e.id}
                className={`act${activeExercise === e.label ? ' on' : ''}${prOn ? ' pr-on' : ''}`}
                onClick={() => setExercise(e.label)}
                onMouseEnter={(ev) => {
                  if (prOn) setPrPop(e.label, true, { x: ev.clientX, y: ev.clientY })
                }}
                onMouseLeave={() => setPrPop(null, false)}
              >
                <span className="nm">
                  <span className="pr-dot" />
                  {e.label}
                </span>
                <span className="cnt">{hasRef ? refByExercise[e.label] : '–'}</span>
              </div>
            )
          })}
        </div>
      ))}
    </aside>
  )
}

// 迷你日历（按日模式左栏）：训练日蓝点 / 感悟日金点 / 双色 / 今天蓝框
function MiniCalendar() {
  const cal = useUiStore((s) => s.cal)
  const selectDay = useUiStore((s) => s.selectDay)
  const setMode = useUiStore((s) => s.setMode)
  const today = useUiStore((s) => s.today)
  const { data: calendar } = useCalendar()
  const { data: reflections } = useReflections({})

  const base = cal && cal.year ? cal : (() => {
    const d = new Date()
    return { year: d.getFullYear(), month: d.getMonth(), day: null }
  })()
  const [view, setView] = useState({ year: base.year, month: base.month })

  const trainDates = {}
  ;(calendar?.training_dates || []).forEach((d) => { trainDates[d] = 1 })
  const refDates = {}
  ;(reflections || []).forEach((r) => { refDates[r.date] = 1 })

  const selDate = cal?.day || null
  const first = new Date(view.year, view.month, 1).getDay()
  const daysInMonth = new Date(view.year, view.month + 1, 0).getDate()

  const go = (delta) => {
    let y = view.year
    let m = view.month + delta
    if (m < 0) { m = 11; y -= 1 }
    if (m > 11) { m = 0; y += 1 }
    setView({ year: y, month: m })
  }

  return (
    <aside className="col-left">
      <div className="cal">
        <div className="cal-head">
          <button onClick={() => go(-1)}>‹</button>
          <span>{view.year}年{view.month + 1}月</span>
          <button onClick={() => go(1)}>›</button>
        </div>
        <div className="cal-week">
          {['日', '一', '二', '三', '四', '五', '六'].map((w) => <span key={w}>{w}</span>)}
        </div>
        <div className="cal-grid">
          {Array.from({ length: first }).map((_, i) => <div key={`b${i}`} className="cal-day other" />)}
          {Array.from({ length: daysInMonth }).map((_, i) => {
            const d = i + 1
            const ds = dateStr(view.year, view.month, d)
            const isSel = selDate === ds
            const isToday = today === ds
            const hasTrain = Boolean(trainDates[ds])
            const hasRef = Boolean(refDates[ds])
            return (
              <div
                key={d}
                className={`cal-day${isSel ? ' sel' : ''}${isToday ? ' today' : ''}`}
                onClick={() => {
                  selectDay(ds)
                  setMode('day')
                  if (view.year !== base.year || view.month !== base.month) setView({ year: base.year, month: base.month })
                }}
              >
                {d}
                {(hasTrain || hasRef) && (
                  <span className="cal-dots">
                    {hasTrain && <i className="t" />}
                    {hasRef && <i className="r" />}
                  </span>
                )}
              </div>
            )
          })}
        </div>
      </div>
      <div style={{ color: 'var(--dim)', fontSize: '10.5px', padding: '8px 6px 0', lineHeight: 1.6 }}>
        <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}><i className="t" style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--blue)', display: 'inline-block' }} /> 训练日</span>
        {' '}
        <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}><i className="r" style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--gold-mid)', display: 'inline-block' }} /> 有感悟</span>
      </div>
    </aside>
  )
}

import { useUiStore } from '../store/useUiStore.js'
import { useDay } from '../api/hooks.js'
import { DIR_NAME, DIR_ORDER } from '../const/exercises.js'
import { normalizeReflections } from '../lib/normalize.js'
import { useMemo } from 'react'

// 中栏：按日模式 —— 当天全貌（按方向分组展示训练轮组行）
export default function DayView() {
  const cal = useUiStore((s) => s.cal)
  const selected = useUiStore((s) => s.selected)
  const selectSet = useUiStore((s) => s.selectSet)
  const { data } = useDay(cal?.day || null)

  const ds = cal?.day || null
  const sessions = data?.sessions || []
  const dayRefs = useMemo(() => normalizeReflections(data?.day_reflections), [data])

  if (!ds) {
    return (
      <section className="col-mid">
        <div className="empty-mid">请先在左侧日历选择日期</div>
      </section>
    )
  }

  const hasAny = sessions.length || dayRefs.length
  if (!hasAny) {
    return (
      <section className="col-mid">
        <div className="mid-head">
          <h2>{ds} · 当日全貌</h2>
          <span className="dir">按日模式</span>
        </div>
        <div className="empty-mid">
          这一天没有训练和感悟记录。
          <br />
          点日历其他日期，或切回「按动作」浏览历史。
        </div>
      </section>
    )
  }

  return (
    <section className="col-mid">
      <div className="mid-head">
        <h2>{ds} · 当日全貌</h2>
        <span className="dir">按日模式</span>
      </div>
      {DIR_ORDER.map((dir) => {
        const daySessions = sessions.filter((s) => s.direction === dir)
        if (!daySessions.length) return null
        return (
          <div key={dir} className="day-grp">
            <div className="dg-head">{DIR_NAME[dir]}</div>
            {daySessions.map((s) => (
              <div key={s.session_id} className="session">
                <div className="shead">
                  <span className="date">{s.date}</span>
                  <span>{s.exercise}</span>
                  <span className="n">{s.sets.length} 组</span>
                </div>
                {s.sets.map((st, idx) => {
                  const setIndex = idx + 1
                  const srs = dayRefs.filter((r) => r.setIndex === setIndex && r.exercise === s.exercise)
                  const sel = selected.type === 'set' && selected.sessionId === s.session_id && selected.setIndex === setIndex
                  return (
                    <div
                      key={`${s.session_id}-${setIndex}`}
                      className={`set-row${sel ? ' sel' : ''}${srs.length ? ' has-r' : ''}`}
                      onClick={() => selectSet(s.session_id, setIndex)}
                    >
                      <span className="set-no">第{setIndex}组</span>
                      <span className="set-w">{st.weight_kg}kg</span>
                      <span className="set-reps">× {st.reps} 次</span>
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
          </div>
        )
      })}
    </section>
  )
}

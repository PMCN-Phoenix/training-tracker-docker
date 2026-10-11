import { useMemo } from 'react'
import { useUiStore } from '../store/useUiStore.js'
import { useExercise, useDay, useReflections, useReflectionMutations } from '../api/hooks.js'
import { normalizeSessions, normalizeReflections } from '../lib/normalize.js'
import { DIR_NAME } from '../const/exercises.js'
import { isMatched } from '../lib/utils.js'
import { message } from 'antd'

// 右栏：与选中目标一一对应 + 筛选 + 补录
export default function RightSide() {
  const selected = useUiStore((s) => s.selected)
  const mode = useUiStore((s) => s.mode)
  const activeExercise = useUiStore((s) => s.activeExercise)
  const filters = useUiStore((s) => s.filters)
  const setFilters = useUiStore((s) => s.setFilters)
  const openForm = useUiStore((s) => s.openForm)
  const cal = useUiStore((s) => s.cal)
  const { remove } = useReflectionMutations()

  const { data: exData } = useExercise(activeExercise)
  const { data: dayData } = useDay(cal?.day || null)
  const { data: refData } = useReflections({})

  const allSessions = useMemo(() => normalizeSessions(exData), [exData])
  const daySessions = dayData?.sessions || []
  const dayRefs = useMemo(() => normalizeReflections(dayData?.day_reflections), [dayData])
  const reflections = useMemo(() => normalizeReflections(refData), [refData])

  // 会话池：动作历史 + 按日数据合并（按日模式点组行也能找到）
  const sessionPool = useMemo(() => {
    const map = new Map()
    allSessions.forEach((s) => map.set(s.sessionId, s))
    daySessions.forEach((s) => {
      if (!map.has(s.session_id)) {
        map.set(s.session_id, {
          sessionId: s.session_id,
          date: s.date,
          direction: s.direction,
          exercise: s.exercise,
          sets: (s.sets || []).map((st) => ({ w: st.weight_kg, r: st.reps })),
        })
      }
    })
    return Array.from(map.values())
  }, [allSessions, daySessions])

  const onDelete = (id) => {
    remove.mutate(id, {
      onSuccess: () => message.success('已删除'),
      onError: (e) => message.error(e.message),
    })
  }

  // 按日模式：日级视图（晨脉 + 意象 + 日级感悟 + 当天组级感悟）
  if (mode === 'day' && selected.type === 'day') {
    const ds = cal?.day
    const hr = dayData?.morning_hr?.length ? dayData.morning_hr[dayData.morning_hr.length - 1] : null
    const imagery = (dayData?.imagery_count || 0) > 0
    const drs = dayRefs.filter((r) => !r.exercise)
    const grp = dayRefs.filter((r) => r.setIndex)
    return (
      <aside className="col-right">
        <div className="side-head">侧栏 · 与选中目标一一对应</div>
        <div className="side-target">
          {ds} · 当天
          <span className="t-sub">日级感悟 + 晨脉 + 意象 + 组级感悟</span>
        </div>
        <div className="day-bio">
          <div className="b-row">
            <span>晨脉</span>
            <b>{hr ? `${hr.bpm} 次/分` : '未记录'}</b>
          </div>
          <div className="b-row">
            <span>意象打卡</span>
            <b>{imagery ? '✓ 已完成' : '未打卡'}</b>
          </div>
        </div>
        {drs.length ? drs.map((r) => <NoteCard key={r.id} r={r} tone="lo" onDelete={onDelete} />) : <SideEmpty text="当天无日级随笔" />}
        {grp.length > 0 && (
          <>
            <div className="dr-title" style={{ margin: '10px 0 6px' }}>当天组级感悟</div>
            {grp.map((r) => <NoteCard key={r.id} r={r} tone="hi" onDelete={onDelete} />)}
          </>
        )}
        <AddNoteBtn onOpen={() => openForm(null, { day: true })} label="训练日随笔" />
      </aside>
    )
  }

  // 组级：选中某组 → 该组感悟
  if (selected.type === 'set' && selected.sessionId) {
    const session = sessionPool.find((s) => s.sessionId === selected.sessionId)
    if (!session) {
      return (
        <aside className="col-right">
          <div className="side-head">侧栏 · 与选中目标一一对应</div>
          <SideEmpty text="点击中间任意一组训练记录，右侧显示那一组当时的感悟。" b="顺序：左栏选动作 → 中栏点某组 → 右侧看感悟。" />
        </aside>
      )
    }
    const st = session.sets[selected.setIndex - 1]
    const ex = session.exercise || activeExercise
    const srs = reflections.filter(
      (r) => r.exercise === ex && r.date === session.date && r.setIndex === selected.setIndex,
    )
    return (
      <aside className="col-right">
        <div className="side-head">侧栏 · 与选中目标一一对应</div>
        <div className="side-target">
          第{selected.setIndex}组 · {ex}
          <span className="t-sub">{session.date} · {st.w}kg × {st.r} 次</span>
        </div>
        {srs.length ? srs.map((r) => <NoteCard key={r.id} r={r} tone="hi" onDelete={onDelete} />) : <SideEmpty b={`这组没有感悟。发「${ex} 第${selected.setIndex}组 感悟：……」自动挂到这组。`} />}
        <AddNoteBtn onOpen={() => openForm(null, { exercise: ex, setIndex: selected.setIndex, date: session.date })} label={`${ex} 第${selected.setIndex}组`} />
      </aside>
    )
  }

  // 动作级
  if (selected.type === 'exercise' || (mode === 'ex' && (!selected.sessionId && selected.type === 'set'))) {
    const ex = selected.type === 'exercise' ? selected.exercise : activeExercise
    const ers = reflections.filter((r) => r.exercise === ex && !r.setIndex)
    return (
      <aside className="col-right">
        <div className="side-head">侧栏 · 与选中目标一一对应</div>
        <div className="side-target">
          {ex} · 动作级感悟
          <span className="t-sub">不绑定具体组，动作练完后的总结</span>
        </div>
        {ers.length ? ers.map((r) => <NoteCard key={r.id} r={r} tone="mid" onDelete={onDelete} />) : <SideEmpty b={`该动作暂无动作级感悟。发「${ex} 感悟：……」记录。`} />}
        <AddNoteBtn onOpen={() => openForm(null, { exercise: ex })} label={ex} />
      </aside>
    )
  }

  // 待匹配感悟
  if (selected.type === 'ref') {
    const rf = reflections.find((r) => r.id === selected.refId)
    if (rf) {
      return (
        <aside className="col-right">
          <div className="side-head">侧栏 · 与选中目标一一对应</div>
          <div className="side-target">
            待匹配感悟
            <span className="t-sub">{rf.exercise} · 第{rf.setIndex}组 · {rf.date}</span>
          </div>
          <div className="pend-card">
            <div className="p-title">{rf.content}</div>
            <div className="p-text">当天「{rf.exercise}」的第{rf.setIndex}组训练数据还没录入。</div>
            <div className="p-tip">宽松绑定：训练数据补录后自动转为正常组级感悟。</div>
          </div>
          <AddNoteBtn onOpen={() => openForm(null, { exercise: rf.exercise, setIndex: rf.setIndex, date: rf.date })} label={`${rf.exercise} 第${rf.setIndex}组`} />
        </aside>
      )
    }
  }

  return (
    <aside className="col-right">
      <div className="side-head">侧栏 · 与选中目标一一对应</div>
      <SideEmpty text="点击中间任意一组训练记录，右侧显示那一组当时的感悟。" b="顺序：左栏选动作 → 中栏点某组 → 右侧看感悟。" />
    </aside>
  )
}

function NoteCard({ r, tone, onDelete }) {
  const openForm = useUiStore((s) => s.openForm)
  return (
    <div className={`note-card ${tone || 'hi'}`}>
      <div className="n-date">
        {r.date} {r.time} · {r.source}{r.setIndex ? ` · 第${r.setIndex}组` : ''}
      </div>
      <div className="n-text">{r.content}</div>
      <div className="n-meta">
        <span className="n-tags">
          {(r.tags || []).map((t) => (
            <span key={t} className="n-tag">{t}</span>
          ))}
        </span>
        <span className="n-act">
          <button className="n-btn" onClick={() => openForm(r.id)}>编辑</button>
          <button className="n-btn danger" onClick={() => onDelete(r.id)}>删除</button>
        </span>
      </div>
    </div>
  )
}

function SideEmpty({ text, b }) {
  return (
    <div className="side-empty">
      {text && <>{text}<br /></>}
      {b && <b>{b}</b>}
    </div>
  )
}

function AddNoteBtn({ onOpen, label }) {
  return (
    <div className="add-note">
      <button onClick={onOpen}>+ 补录感悟 · {label}</button>
      <small>正式版：组间发消息「{label} 感悟：……」最快</small>
    </div>
  )
}

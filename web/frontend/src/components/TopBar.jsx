import { useUiStore } from '../store/useUiStore.js'
import { useReflections, useStats } from '../api/hooks.js'
import { GRAFANA } from '../const/exercises.js'

export default function TopBar() {
  const mode = useUiStore((s) => s.mode)
  const setMode = useUiStore((s) => s.setMode)
  const openPrFull = useUiStore((s) => s.openPrFull)

  const { data: stats } = useStats()
  const { data: reflections } = useReflections({})

  const total = stats?.total_count ?? reflections?.length ?? 0
  const today = stats?.today_count ?? 0
  const streak = stats?.consecutive_days ?? 0
  const exCount = stats?.exercise_count ?? 0

  return (
    <header className="top">
      <div className="brand">
        <div className="logo">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#1b120b" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 19V5M4 12h16" />
          </svg>
        </div>
        <div>
          <h1>训练感悟系统</h1>
          <small>training-tracker · 推拉蹲</small>
        </div>
      </div>
      <div className="stats">
        <div className="stat"><b className="a">{total}</b><span>感悟总数</span></div>
        <div className="stat"><b className="b">{today}</b><span>今日</span></div>
        <div className="stat"><b className="g">{streak}</b><span>连续天数</span></div>
        <div className="stat"><b className="a">{exCount}</b><span>覆盖动作</span></div>
      </div>
      <div className="sep" />
      <div className="mode-sw">
        <button className={mode === 'ex' ? 'on' : ''} onClick={() => setMode('ex')}>按动作</button>
        <button className={mode === 'day' ? 'on' : ''} onClick={() => setMode('day')}>按日</button>
      </div>
      <div className="right">
        <button className="btn primary" onClick={openPrFull}>PR 总览</button>
        <button className="btn" onClick={() => window.open(GRAFANA.overview(), '_blank')}>打开看板</button>
      </div>
    </header>
  )
}

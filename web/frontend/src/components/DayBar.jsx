import { useReflections } from '../api/hooks.js'
import { useUiStore } from '../store/useUiStore.js'

// 日级随笔条：最新一条训练日随笔 + 「写当日随笔」入口
export default function DayBar() {
  const openForm = useUiStore((s) => s.openForm)
  const selectDay = useUiStore((s) => s.selectDay)
  const { data: reflections } = useReflections({})

  const dayRefs = (reflections || []).filter((r) => !r.exercise)
  const latest = dayRefs.slice().sort((a, b) => b.date.localeCompare(a.date))[0]

  return (
    <div
      className="daybar"
      style={{ cursor: latest ? 'pointer' : 'default' }}
      onClick={() => {
        if (latest) selectDay(latest.date)
      }}
    >
      <span className="dot" />
      {latest ? (
        <span>
          训练日随笔 · <b>{latest.date}</b> —— {latest.content}
        </span>
      ) : (
        <span style={{ color: 'var(--dim)' }}>暂无训练日随笔 —— 发「推日 感悟：……」或点右侧按钮记录</span>
      )}
      <span className="more">{latest ? '点击查看当天全貌' : ''}</span>
      <button
        onClick={(e) => {
          e.stopPropagation()
          openForm(null, { day: true })
        }}
      >
        + 写当日随笔
      </button>
    </div>
  )
}

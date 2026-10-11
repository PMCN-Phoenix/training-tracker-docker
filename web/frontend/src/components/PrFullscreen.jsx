import { useUiStore } from '../store/useUiStore.js'
import { usePrTests } from '../api/hooks.js'
import { normalizePrTests } from '../lib/normalize.js'
import { latestPr, bestPoint } from '../lib/utils.js'
import { EXERCISES, DIR_NAME } from '../const/exercises.js'

// 全屏 PR 总览：成绩单网格（点卡片 → 打开该动作 PR 抽屉，同一套组件）
export default function PrFullscreen() {
  const prFullOpen = useUiStore((s) => s.prFullOpen)
  const closePrFull = useUiStore((s) => s.closePrFull)
  const openDrawer = useUiStore((s) => s.openDrawer)
  const { data: prData } = usePrTests()

  if (!prFullOpen) return null

  const byExercise = {}
  normalizePrTests(prData).forEach((e) => {
    byExercise[e.exercise] = e.tests
  })

  return (
    <div className="prfull">
      <div className="prfull-head">
        <h2>PR 总览 · 成绩单</h2>
        <span style={{ color: 'var(--dim)', fontSize: '12px' }}>数据读 ppl_pr_test</span>
        <button onClick={closePrFull}>返回</button>
      </div>
      <div className="prfull-body">
        {EXERCISES.map((e) => {
          const tests = byExercise[e.label]
          if (!tests || !tests.length) return null
          const latest = latestPr(tests)
          const best = bestPoint(latest)
          return (
            <div key={e.id} className="pf-card" onClick={() => openDrawer(e.label)}>
              <div className="pf-name">
                <span>{e.label}</span>
                <span style={{ fontSize: '10.5px', color: 'var(--dim)' }}>{DIR_NAME[e.direction]}</span>
              </div>
              <div className="pf-best">{best ? `${best[0]}kg → ${best[1]} 次` : '–'}</div>
              <div className="pf-mini">最近测试 {latest.date} · 共 {tests.length} 次</div>
              <div className="pf-btn">查看详情 →</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

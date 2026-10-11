import { useUiStore } from '../store/useUiStore.js'
import { usePrTests } from '../api/hooks.js'
import { latestPr, bestPoint, ladderRows } from '../lib/utils.js'

// 左栏 PR 红标 hover 浮层：完整 PR 阶梯列表 + 最高档高亮 + 「查看详情 →」进抽屉
export default function PrPop() {
  const prPop = useUiStore((s) => s.prPop)
  const openDrawer = useUiStore((s) => s.openDrawer)
  const { data: prData } = usePrTests()

  if (!prPop.visible || !prPop.ex) return null

  const tests = (prData?.exercises || []).find((e) => e.exercise === prPop.ex)?.tests
  const latest = latestPr(tests)
  if (!latest) return null

  const best = bestPoint(latest)
  const rows = ladderRows(latest)

  // 锚定鼠标：浮层放鼠标右侧，超出视口则放左侧
  const style = {
    left: prPop.x + 14,
    top: prPop.y - 8,
  }

  return (
    <div className="prpop" style={style}>
      <div className="pp-title">
        <span>{prPop.ex} · PR 阶梯</span>
        <span>最近 {latest.date}</span>
      </div>
      {rows.map((p) => (
        <div key={p[0]} className={`pp-row${best && p[0] === best[0] ? ' best' : ''}`}>
          <span>{p[0]}kg</span>
          <span>{p[1]} 次</span>
        </div>
      ))}
      <div className="pp-view">
        <button onClick={() => openDrawer(prPop.ex)}>查看详情 →</button>
      </div>
    </div>
  )
}

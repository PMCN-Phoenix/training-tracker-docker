import { useEffect, useMemo, useState } from 'react'
import { useUiStore } from '../store/useUiStore.js'
import { usePrTests, useExercise } from '../api/hooks.js'
import { normalizePrTests, normalizeSessions } from '../lib/normalize.js'
import { latestPr, bestPoint, ladderRows, curveScale } from '../lib/utils.js'
import { message } from 'antd'

const COLORS = ['#58a6ff', '#e8a23d', '#f85149', '#bc8cff', '#3fb950', '#7ee787']

// PR 抽屉：曲线（多系列对比）+ 当前最佳 + 全档阶梯 + 历史轮（点档位联动跳组行）
export default function PrDrawer() {
  const drawerEx = useUiStore((s) => s.drawerEx)
  const closeDrawer = useUiStore((s) => s.closeDrawer)
  const setMode = useUiStore((s) => s.setMode)
  const setExercise = useUiStore((s) => s.setExercise)
  const selectSet = useUiStore((s) => s.selectSet)

  const { data: prData } = usePrTests()
  const { data: exData } = useExercise(drawerEx || '')
  const [mode, setModeLocal] = useState('all')
  const [selA, setSelA] = useState(1)
  const [selB, setSelB] = useState(1)

  const exPr = useMemo(() => {
    const n = normalizePrTests(prData)
    return n.find((e) => e.exercise === drawerEx) || { exercise: drawerEx, tests: [] }
  }, [prData, drawerEx])

  const sessions = useMemo(() => normalizeSessions(exData), [exData])

  // 训练档 = 最近一次训练 session 的第一组重量（曲线上的绿色虚线标记）
  const trainW = useMemo(() => {
    if (!sessions.length || !sessions[0].sets.length) return null
    return sessions[0].sets[0].w
  }, [sessions])

  const tests = exPr.tests || []
  const latest = latestPr(tests)
  const best = bestPoint(latest)
  const rows = ladderRows(latest)

  useEffect(() => {
    if (tests.length > 1) setSelB(tests.length)
  }, [tests.length])

  if (!drawerEx) return null

  const jumpToSet = (w, date) => {
    const session = sessions.find((s) => s.exercise === drawerEx && s.date === date)
    const setIndex = session
      ? (session.sets.findIndex((st) => st.w === w) + 1) || 1
      : 1
    closeDrawer()
    setMode('ex')
    setExercise(drawerEx)
    selectSet(session ? session.sessionId : null, setIndex)
    message.success(`已跳到 ${date} ${drawerEx} 第${setIndex}组（${w}kg）`)
    setTimeout(() => {
      const el = document.querySelector('.set-row.sel')
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 80)
  }

  return (
    <>
      <div className="drawer-mask" onClick={closeDrawer} />
      <aside className="drawer">
        <div className="drawer-head">
          <h3>{drawerEx} · PR 详情</h3>
          <button onClick={closeDrawer}>✕</button>
        </div>
        <div className="drawer-body">
          <div className="pr-curve">
            <div className="pc-mode">
              <label>
                <input type="radio" name="pcmode" checked={mode === 'all'} onChange={() => setModeLocal('all')} /> 全部
              </label>
              <label>
                <input type="radio" name="pcmode" checked={mode === 'pair'} onChange={() => setModeLocal('pair')} /> 两两
              </label>
              <span>
                第
                <select value={selA} disabled={mode !== 'pair'} onChange={(e) => setSelA(Number(e.target.value))}>
                  {tests.map((t, i) => (
                    <option key={t.test_no} value={i + 1}>第 {i + 1} 次（{t.date}）</option>
                  ))}
                </select>
                 vs 第
                <select value={selB} disabled={mode !== 'pair'} onChange={(e) => setSelB(Number(e.target.value))}>
                  {tests.map((t, i) => (
                    <option key={t.test_no} value={i + 1}>第 {i + 1} 次（{t.date}）</option>
                  ))}
                </select>
                次
              </span>
            </div>
            <PrCurve tests={tests} mode={mode} selA={selA} selB={selB} trainW={trainW} />
          </div>

          <div className="dr-title">当前最佳 · 最近测试</div>
          <div className="dr-steps">
            {latest ? (
              <div className="step best">
                <span>{best[0]}kg</span>
                <span>{best[1]} 次（{latest.date}）</span>
              </div>
            ) : (
              <div style={{ color: 'var(--dim)' }}>暂无 PR 测试</div>
            )}
          </div>

          <div className="dr-title">全档阶梯（点档位跳组行）</div>
          <div className="dr-steps">
            {rows.map((p) => (
              <div
                key={p[0]}
                className={`step${best && p[0] === best[0] ? ' best' : ''}`}
                onClick={() => jumpToSet(p[0], latest.date)}
              >
                <span>{p[0]}kg</span>
                <span>{p[1]} 次</span>
              </div>
            ))}
          </div>

          <div className="dr-title">历史 PR 测试轮（点档位联动）</div>
          <div className="dr-hist">
            {tests
              .slice()
              .reverse()
              .map((t) => (
                <div key={t.test_no}>
                  <div className="h-date">{t.date} · 第 {t.test_no} 次</div>
                  {t.points.map((p) => (
                    <div key={`${t.test_no}-${p[0]}`} className="h-row" onClick={() => jumpToSet(p[0], t.date)}>
                      <span>{p[0]}kg × {p[1]} 次</span>
                      <span style={{ color: 'var(--dim)' }}>→</span>
                    </div>
                  ))}
                </div>
              ))}
          </div>
        </div>
      </aside>
    </>
  )
}

// 多系列 PR 曲线：每条测试一条线（第 N 次编号 = 日期升序）+ 全部/两两对比 + hover 提示
function PrCurve({ tests, mode, selA, selB, trainW }) {
  const [tip, setTip] = useState(null)
  const show = {}
  if (mode === 'all') tests.forEach((t, i) => { show[i] = true })
  else {
    show[selA - 1] = true
    show[selB - 1] = true
  }

  const allPoints = tests.flatMap((t) => t.points || [])
  if (!allPoints.length) return <div style={{ color: 'var(--dim)', fontSize: '11.5px', padding: '8px' }}>暂无 PR 数据</div>

  const W = 340
  const H = 190
  const ML = 32
  const MR = 12
  const MT = 10
  const MB = 22
  const { sx, sy, wmin, wmax, nmin, nmax } = curveScale(allPoints, W, H, ML, MR, MT, MB)

  const gridLines = []
  for (let g = 0; g <= 4; g++) {
    const wv = wmin + (g * (wmax - wmin)) / 4
    gridLines.push(
      <line key={`g${g}`} x1={sx(wv)} y1={sy(nmin)} x2={sx(wv)} y2={sy(nmax)} stroke="#1c2531" />,
    )
  }
  const step = Math.max(1, Math.round(nmax / 4))
  const hGrid = []
  for (let n = 0; n <= nmax; n += step) {
    hGrid.push(
      <line key={`h${n}`} x1={sx(wmin)} y1={sy(n)} x2={sx(wmax)} y2={sy(n)} stroke="#1c2531" />,
    )
  }

  return (
    <svg id="prSvg" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet" style={{ width: '100%', display: 'block' }}>
      {gridLines}
      {hGrid}
      <g fill="#5f6c7e" fontSize="9" fontFamily="ui-monospace,Consolas,monospace">
        {[0, 1, 2, 3, 4].map((g) => {
          const wv = wmin + (g * (wmax - wmin)) / 4
          return (
            <text key={`t${g}`} x={sx(wv)} y={H - MB + 12} textAnchor="middle">
              {Math.round(wv)}
            </text>
          )
        })}
      </g>

      {trainW && (
        <>
          <line x1={sx(trainW)} y1={sy(nmin)} x2={sx(trainW)} y2={sy(nmax)} stroke="#3fb950" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
          <text x={sx(trainW)} y={sy(nmin) + 11} textAnchor="middle" fontSize="9.5" fill="#3fb950">▼{trainW}</text>
        </>
      )}

      {tests.map((t, i) => {
        if (!show[i]) return null
        const d = (t.points || [])
          .map((p, k) => `${k === 0 ? 'M' : 'L'}${sx(p[0])},${sy(p[1])}`)
          .join(' ')
        return (
          <path key={`p${i}`} d={d} fill="none" stroke={COLORS[i % COLORS.length]} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        )
      })}
      {tests.map((t, i) => {
        if (!show[i]) return null
        return (t.points || []).map((p, k) => (
          <circle
            key={`c${i}-${k}`}
            className="pdot"
            cx={sx(p[0])}
            cy={sy(p[1])}
            r="4.5"
            fill={COLORS[i % COLORS.length]}
            stroke="#0d1117"
            strokeWidth="1.6"
            onMouseMove={(e) =>
              setTip({ text: `第${i + 1}次（${t.date}） · ${p[0]}kg · ${p[1]} 次`, x: e.clientX + 14, y: e.clientY - 24 })
            }
            onMouseLeave={() => setTip(null)}
          />
        ))
      })}
      {tip && (
        <div className="tip" style={{ left: tip.x, top: tip.y }}>
          {tip.text}
        </div>
      )}
    </svg>
  )
}

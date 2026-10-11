import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useUiStore } from './store/useUiStore.js'
import TopBar from './components/TopBar.jsx'
import DayBar from './components/DayBar.jsx'
import LeftNav from './components/LeftNav.jsx'
import TrainingHistory from './components/TrainingHistory.jsx'
import DayView from './components/DayView.jsx'
import RightSide from './components/RightSide.jsx'
import PrDrawer from './components/PrDrawer.jsx'
import PrFullscreen from './components/PrFullscreen.jsx'
import ReflectionForm from './components/ReflectionForm.jsx'
import PrPop from './components/PrPop.jsx'

export default function App() {
  const [params, setParams] = useSearchParams()
  const mode = useUiStore((s) => s.mode)
  const setMode = useUiStore((s) => s.setMode)

  // 首次进入：从 URL 恢复状态（刷新保持可分享，技术方案 T2）
  useEffect(() => {
    const m = params.get('mode')
    if (m === 'day') {
      const date = params.get('date')
      if (date) {
        setMode('day')
        useUiStore.getState().selectDay(date)
        const [y, mo, d] = date.split('-').map(Number)
        useUiStore.setState({ cal: { year: y, month: mo - 1, day: date } })
      }
    } else {
      const ex = params.get('exercise')
      if (ex) useUiStore.getState().setExercise(ex)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 状态变化 → 写回 URL
  useEffect(() => {
    const s = useUiStore.getState()
    const next = new URLSearchParams()
    if (s.mode === 'day' && s.cal && s.cal.day) {
      next.set('mode', 'day')
      next.set('date', s.cal.day)
    } else {
      next.set('mode', 'ex')
      next.set('exercise', s.activeExercise)
    }
    const qs = next.toString()
    if (params.toString() !== qs) setParams(next, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, useUiStore((s) => s.activeExercise), useUiStore((s) => s.cal && s.cal.day)])

  return (
    <div className="app">
      <TopBar />
      <DayBar />
      <div className="workbench">
        <LeftNav />
        <main className="col-mid">{mode === 'day' ? <DayView /> : <TrainingHistory />}</main>
        <RightSide />
      </div>
      <PrPop />
      <PrDrawer />
      <PrFullscreen />
      <ReflectionForm />
    </div>
  )
}

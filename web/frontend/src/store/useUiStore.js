import { create } from 'zustand'

// UI 状态（数据全部走 react-query；这里只存视图/交互状态）
export const useUiStore = create((set, get) => ({
  mode: 'ex', // 'ex' 按动作 | 'day' 按日
  activeExercise: '平板卧推',
  selected: { type: 'set', sessionId: null, setIndex: null }, // set | day | ref | exercise
  cal: { year: null, month: null, day: null }, // 按日模式选中日期（YYYY-MM-DD 存 day）
  filters: { direction: '', tag: '', date: '' },
  drawerEx: null, // PR 抽屉打开的动作
  prFullOpen: false, // PR 全屏总览
  formOpen: false, // 新建/编辑弹窗
  formEditId: null, // null=新建
  formPrefill: null, // { exercise, setIndex, date }
  prPop: { ex: null, visible: false, x: 0, y: 0 }, // 左栏 PR 红标浮层（锚定鼠标位置）
  today: (() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  })(),

  setMode: (mode) => set({ mode, selected: { type: mode === 'day' ? 'day' : 'set', sessionId: null, setIndex: null } }),
  setExercise: (label) => set({ activeExercise: label, selected: { type: 'set', sessionId: null, setIndex: null } }),
  selectSet: (sessionId, setIndex) => set({ selected: { type: 'set', sessionId, setIndex } }),
  selectDay: (date) => set({ selected: { type: 'day' }, cal: { ...get().cal, day: date } }),
  selectRef: (refId) => set({ selected: { type: 'ref', refId } }),
  setFilters: (filters) => set({ filters: { ...get().filters, ...filters } }),
  openDrawer: (ex) => set({ drawerEx: ex }),
  closeDrawer: () => set({ drawerEx: null }),
  openPrFull: () => set({ prFullOpen: true }),
  closePrFull: () => set({ prFullOpen: false }),
  openForm: (editId = null, prefill = null) => set({ formOpen: true, formEditId: editId, formPrefill: prefill }),
  closeForm: () => set({ formOpen: false, formEditId: null, formPrefill: null }),
  setPrPop: (ex, visible, pos = {}) => set({ prPop: { ex, visible, ...pos } }),
}))

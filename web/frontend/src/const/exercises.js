import { create } from 'zustand'

// 15 个训练动作（与后端 measurement 一一对应）
export const EXERCISES = [
  { id: 'ppl_push_bench_flat', direction: 'push', label: '平板卧推' },
  { id: 'ppl_push_bench_incline', direction: 'push', label: '上斜卧推' },
  { id: 'ppl_push_bench_close', direction: 'push', label: '窄距卧推' },
  { id: 'ppl_push_overhead_press', direction: 'push', label: '站姿推举' },
  { id: 'ppl_push_pec_deck', direction: 'push', label: '夹胸' },
  { id: 'ppl_pull_deadlift', direction: 'pull', label: '硬拉' },
  { id: 'ppl_pull_seated_row', direction: 'pull', label: '坐姿划船' },
  { id: 'ppl_pull_tbar_row', direction: 'pull', label: 'T杆划船' },
  { id: 'ppl_pull_lat_pulldown', direction: 'pull', label: '高位下拉' },
  { id: 'ppl_pull_barbell_curl', direction: 'pull', label: '杠铃弯举' },
  { id: 'ppl_squat_back_squat', direction: 'squat', label: '杠铃深蹲' },
  { id: 'ppl_squat_leg_press_hack', direction: 'squat', label: '倒蹬/哈克' },
  { id: 'ppl_squat_leg_extension', direction: 'squat', label: '腿屈伸' },
  { id: 'ppl_squat_leg_curl', direction: 'squat', label: '腿弯举' },
  { id: 'ppl_squat_calf_raise', direction: 'squat', label: '站姿提踵' },
]

export const DIR_NAME = { push: '推日', pull: '拉日', squat: '蹲日' }

export const DIR_ORDER = ['push', 'pull', 'squat']

// Grafana 面板映射（ppl-training.json 提取）：
// 总览 2000；推/拉/蹲：容量 2001/2003/2005，最重一组 2002/2004/2006；
// 时长 2007/2008；PR 2009/2010/2011；晨脉 2012。
export const GRAFANA = {
  base: 'http://127.0.0.1:3000/d/ppl-training-monitor/ppl-training-monitor?orgId=1',
  // 动作 → 深链面板：按方向取「最重一组重量」面板（动作详情最相关）
  exercisePanel: (direction) => ({ push: 2002, pull: 2004, squat: 2006 })[direction],
  // 顶栏「打开看板」= 总览
  overview: () => 'http://127.0.0.1:3000/d/ppl-training-monitor/ppl-training-monitor?orgId=1&viewPanel=2000',
  exerciseUrl: (direction) => {
    const panel = GRAFANA.exercisePanel(direction)
    return `http://127.0.0.1:3000/d/ppl-training-monitor/ppl-training-monitor?orgId=1&viewPanel=${panel}`
  },
}

export const labelOf = (exId) => {
  const e = EXERCISES.find((x) => x.id === exId)
  return e ? e.label : exId
}

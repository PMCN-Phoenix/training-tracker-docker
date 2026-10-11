// M3 单元测试：纯函数（utils.js / normalize.js）
// 运行：node _verify/m3_unit.mjs
import assert from 'node:assert/strict'
import {
  pad2, dateStr, todayStr, anchorKey, isMatched, prSeries, latestPr,
  bestPoint, ladderRows, miniChartData, curveScale,
} from '../web/frontend/src/lib/utils.js'
import {
  normalizeSessions, normalizePrTests, normalizeReflections,
} from '../web/frontend/src/lib/normalize.js'

let pass = 0
const ok = (name) => { pass += 1; console.log(`  PASS ${name}`) }

console.log('— 原子：日期/锚定 —')
assert.equal(pad2(3), '03'); ok('pad2 补零')
assert.equal(pad2(12), '12'); ok('pad2 不补')
assert.equal(dateStr(2026, 9, 5), '2026-10-05'); ok('dateStr 月份+1')
assert.match(todayStr(), /^\d{4}-\d{2}-\d{2}$/); ok('todayStr 格式')
assert.equal(anchorKey('2026-10-09', '平板卧推', 2), '2026-10-09|平板卧推|2'); ok('anchorKey 三键')

console.log('— 原子：感悟匹配 —')
const s1 = { exercise: '平板卧推', date: '2026-10-09', sets: [{ w: 47.5 }, { w: 47.5 }, { w: 47.5 }] }
const rf = (setIndex) => ({ exercise: '平板卧推', date: '2026-10-09', setIndex })
assert.equal(isMatched(rf(2), [s1]), true); ok('组号 2 匹配')
assert.equal(isMatched(rf(4), [s1]), false); ok('组号 4 不匹配')
assert.equal(isMatched(rf(null), [s1]), true); ok('动作级恒匹配')
assert.equal(isMatched(rf(1), []), false); ok('无训练记录不匹配')

console.log('— 单元：PR 编号 / 最佳档 / 阶梯 —')
const tests = [
  { date: '2026-10-10', points: [[50, 11], [55, 6], [60, 3]] },
  { date: '2026-10-09', points: [[40, 15], [45, 12], [50, 11]] },
]
const series = prSeries(tests)
assert.equal(series[0].no, 1); assert.equal(series[0].date, '2026-10-09'); ok('PR 按日期升序编号')
assert.equal(series[1].no, 2); ok('第 2 次编号')
assert.equal(latestPr(tests).date, '2026-10-10'); ok('最近测试 = 最新日期')
const best = bestPoint(latestPr(tests))
assert.deepEqual(best, [60, 3]); ok('当前最佳档 = 最重档')
const rows = ladderRows(latestPr(tests))
assert.deepEqual(rows, [[50, 11], [55, 6], [60, 3]]); ok('阶梯按重量升序')

console.log('— 单元：迷你图双线数据 —')
const sessions = [
  { date: '2026-10-09', sets: [{ w: 47.5, r: 8 }, { w: 47.5, r: 9 }] },
  { date: '2026-10-10', sets: [{ w: 50, r: 11 }, { w: 60, r: 3 }] },
]
const prs = [
  { date: '2026-10-10', points: [[50, 11], [55, 6], [60, 3]] },
]
const mc = miniChartData(sessions, prs)
assert.deepEqual(mc.pts.map((p) => p.w), [47.5]); ok('训练实线点 = 非 PR 轮第一组重量')
assert.equal(mc.prpts.length, 3); ok('PR 红点 = 测试档位数')
assert.equal(mc.prpts[2].w, 60); ok('PR 红点含最重档')

console.log('— 单元：曲线坐标换算 —')
const sc = curveScale([[40, 15], [60, 3]], 340, 190, 32, 12, 10, 22)
assert.ok(sc.sx(40) < sc.sx(60)); ok('重量越大 x 越大（左小右大）')
assert.ok(sc.sy(15) < sc.sy(3)); ok('次数越多 y 越小（上大下小）')
assert.ok(sc.sx(50) > sc.sx(sc.wmin) && sc.sx(50) < sc.sx(sc.wmax)); ok('中间档落在区间内')

console.log('— 交叉：normalize 后端形状 → 组件形状 —')
const ns = normalizeSessions({
  sessions: [
    { session_id: 'a', date: '2026-10-09', direction: 'push', exercise: '平板卧推', time: 't', sets: [{ set_index: 1, weight_kg: 47.5, reps: 8 }, { set_index: 2, weight_kg: 47.5, reps: 9 }] },
  ],
})
assert.deepEqual(ns[0], { sessionId: 'a', date: '2026-10-09', direction: 'push', exercise: '平板卧推', time: 't', sets: [{ w: 47.5, r: 8 }, { w: 47.5, r: 9 }] }); ok('session 形状转换')

const np = normalizePrTests({
  exercises: [
    { exercise: '平板卧推', direction: 'push', tests: [{ test_no: 1, date: '2026-10-09', session_id: 'p1', points: [{ weight_kg: 50, max_reps: 11 }, { weight_kg: 60, max_reps: 3 }] }] },
  ],
})
assert.deepEqual(np[0].tests[0].points, [[50, 11], [60, 3]]); ok('PR points 对象→数组')

const nr = normalizeReflections([
  { id: 'r1', date: '2026-10-09', direction: 'push', exercise: '平板卧推', set_index: 2, content: 'x', tags: ['发力感'], source: '消息', time: '19:00' },
])
assert.equal(nr[0].setIndex, 2); assert.deepEqual(nr[0].tags, ['发力感']); ok('感悟形状转换')

console.log(`\n结果：${pass} 项全部通过`)

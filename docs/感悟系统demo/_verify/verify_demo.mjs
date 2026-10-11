/* ============================================================
   训练感悟系统 v1.0 demo 多重验证脚本（可复用）
   验证层次：原子 / 单元 / 交叉 / 集成（纯逻辑层）
   端到端（真实浏览器）由 bu 另行执行
   用法：node verify_demo.mjs <demo.html>
   ============================================================ */
import fs from 'fs';
import vm from 'vm';

const htmlPath = process.argv[2];
if (!htmlPath) { console.error('用法: node verify_demo.mjs <demo.html>'); process.exit(1); }
const html = fs.readFileSync(htmlPath, 'utf-8');

/* 提取脚本块：数据（块1）+ 纯函数/渲染定义（块2），demo 真身 */
const blocks = html.match(/<script>([\s\S]*?)<\/script>/g);
if (!blocks || blocks.length < 2) { console.error('FAIL: 未找到数据脚本块'); process.exit(1); }
const code = blocks[0].replace(/^<script>/, '').replace(/<\/script>$/, '') + '\n'
           + blocks[1].replace(/^<script>/, '').replace(/<\/script>$/, '');

const fakeEl = () => ({
  onclick: null, innerHTML: '', textContent: '', value: '', disabled: false, style: {},
  classList: { add() {}, remove() {} },
  querySelectorAll: () => [], querySelector: () => null, addEventListener() {}, appendChild() {}, remove() {},
  getBoundingClientRect: () => ({ left: 0, top: 0, right: 100, bottom: 100 })
});
const sandbox = {
  document: {
    createElement: fakeEl, body: { appendChild() {} }, getElementById: fakeEl, querySelectorAll: () => [], querySelector: () => null
  },
  setTimeout: () => 0,
  window: { open() {} },
  console
};
const ctx = vm.createContext(sandbox);
try { vm.runInContext(code, ctx); }
catch (e) { console.error('FAIL: 脚本执行异常 ->', e.message); process.exit(1); }

const R = vm.runInContext(`({
  EX, DIR_NAME, SESSIONS, PR_TESTS, TRAIN_W, DAY_EXTRA, REFLECTIONS, state, TODAY,
  esc, refsForExercise, setRefs, exRefs, dayRefs, sessionsOf, exRefCount,
  prTestsOf, latestPrDate, isMatched, pad2, dateStr
})`, ctx);

/* ============================================================ 测试框架 */
let pass = 0, fail = 0;
const failures = [];
function T(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name); }
  else { fail++; failures.push(name + (detail ? '  [' + detail + ']' : '')); console.log('  FAIL ' + name + (detail ? '  [' + detail + ']' : '')); }
}
function section(t){ console.log('\n== ' + t + ' =='); }

/* ============================================================ 原子测试 */
section('原子测试（单函数/单数据点）');
T('A1 esc 转义', R.esc('<a>&') === '&lt;a&gt;&amp;', R.esc('<a>&'));
T('A2 pad2 补零', R.pad2(9) === '09' && R.pad2(12) === '12');
T('A3 dateStr', R.dateStr(2026, 9, 11) === '2026-10-11' && R.dateStr(2026, 0, 1) === '2026-01-01');
T('A4 isMatched 待匹配(10-11 夹胸2) === false', R.isMatched(R.REFLECTIONS.find(r => r.id === 'ref_20261011_j')) === false);
T('A5 isMatched 已匹配(10-09 平板1) === true', R.isMatched(R.REFLECTIONS.find(r => r.id === 'ref_20261009_a')) === true);
{
  const latest = R.prTestsOf('平板卧推').slice(-1)[0];
  const best = latest.points.slice().sort((a, b) => b[0] - a[0])[0];
  T('A6 当前最佳 = 最重档(平板 10-17 示例 → 65)', best[0] === 65, JSON.stringify(best));
  const t2 = R.prTestsOf('平板卧推')[1]; // 10-10
  const best2 = t2.points.slice().sort((a, b) => b[0] - a[0])[0];
  T('A7 10-10 测试最高档 = 60', best2[0] === 60, JSON.stringify(best2));
}

/* ============================================================ 单元测试 */
section('单元测试（模块级输出）');
T('U1 平板卧推感悟 3 条', R.refsForExercise('平板卧推').length === 3, R.refsForExercise('平板卧推').length);
T('U2 10-09 平板第2组感悟 1 条且内容正确', R.setRefs('平板卧推', '2026-10-09', 2).length === 1 && R.setRefs('平板卧推', '2026-10-09', 2)[0].content.includes('肩胛锁死'));
T('U3 动作级：夹胸 1 / 杠铃深蹲 1', R.exRefs('夹胸').length === 1 && R.exRefs('杠铃深蹲').length === 1);
T('U4 日级感悟 2 条', R.dayRefs().length === 2, R.dayRefs().length);
T('U5 平板卧推 PR 测试 3 次', R.prTestsOf('平板卧推').length === 3, R.prTestsOf('平板卧推').length);
T('U6 平板卧推训练轮 3 个', R.sessionsOf('平板卧推').length === 3, R.sessionsOf('平板卧推').length);
T('U7 训练档覆盖全部有 PR 动作',
  ['平板卧推','上斜卧推','窄距卧推','夹胸','站姿推举'].every(ex => R.TRAIN_W[ex]),
  JSON.stringify(R.TRAIN_W));
{
  const noPr = R.EX.filter(e => !R.prTestsOf(e.label).length).map(e => e.label);
  T('U8 无 PR 动作无红标数据（T杆划船/腿弯举等）', noPr.includes('T杆划船') && noPr.includes('腿弯举'), JSON.stringify(noPr));
}

/* ============================================================ 交叉测试 */
section('交叉测试（数据一致性）');
{
  const labels = new Set(R.EX.map(e => e.label));
  const badEx = R.REFLECTIONS.filter(r => r.exercise && !labels.has(r.exercise)).map(r => r.exercise);
  T('C1 感悟 exercise 均在 15 动作清单', badEx.length === 0, JSON.stringify(badEx));
}
{
  const badDir = R.REFLECTIONS.filter(r => {
    if (!r.exercise) return false;
    const e = R.EX.find(x => x.label === r.exercise);
    return e && e.direction !== r.direction;
  });
  T('C2 感悟 direction 与动作映射一致', badDir.length === 0, JSON.stringify(badDir.map(r => r.id)));
}
{
  const badSet = R.REFLECTIONS.filter(r => r.setIndex !== undefined && r.setIndex !== null && (!Number.isInteger(r.setIndex) || r.setIndex < 1));
  T('C3 setIndex 均为正整数（有值时）', badSet.length === 0);
}
{
  const grp = R.REFLECTIONS.filter(r => r.setIndex);
  const unmatched = grp.filter(r => !R.isMatched(r));
  T('C4 待匹配感悟恰好 1 条（10-11 夹胸2）', unmatched.length === 1 && unmatched[0].id === 'ref_20261011_j', JSON.stringify(unmatched.map(r => r.id)));
}
{
  const prSessions = R.SESSIONS.filter(s => s.isPR);
  const badPrDate = prSessions.filter(s => !R.prTestsOf(s.exercise).some(t => t.date === s.date));
  T('C5 PR 轮 session 日期 ∈ 该动作 PR 测试日期', badPrDate.length === 0, JSON.stringify(badPrDate.map(s => s.date)));
}
{
  const badDay = Object.keys(R.DAY_EXTRA).filter(d => !/^\d{4}-\d{2}-\d{2}$/.test(d));
  T('C6 DAY_EXTRA 日期格式合法', badDay.length === 0, JSON.stringify(badDay));
}
{
  /* 统计口径复算：总数/今日/连续天数/覆盖动作 */
  const total = R.REFLECTIONS.length;
  const todayN = R.REFLECTIONS.filter(r => r.date === R.TODAY).length;
  const dates = {}; R.REFLECTIONS.forEach(r => { dates[r.date] = 1; });
  let d = new Date(R.TODAY), streak = 0;
  for (let i = 0; i < 90; i++) {
    const key = d.toISOString().slice(0, 10);
    if (dates[key]) { streak++; d.setDate(d.getDate() - 1); } else break;
  }
  const exN = {}; R.REFLECTIONS.forEach(r => { if (r.exercise) exN[r.exercise] = 1; });
  T('C7 统计：总数 = 10', total === 10, total);
  T('C8 统计：今日(10-11) = 1', todayN === 1, todayN);
  T('C9 统计：连续天数 = 3', streak === 3, streak);
  T('C10 统计：覆盖动作 = 5', Object.keys(exN).length === 5, Object.keys(exN).length);
}
{
  const badPrEx = Object.keys(R.PR_TESTS).filter(ex => !new Set(R.EX.map(e => e.label)).has(ex));
  T('C11 PR_TESTS 动作均在 15 动作清单', badPrEx.length === 0, JSON.stringify(badPrEx));
  const badPt = [];
  Object.keys(R.PR_TESTS).forEach(ex => {
    R.PR_TESTS[ex].forEach(t => t.points.forEach(p => {
      if (!(p.length === 2 && p[0] > 0 && p[1] > 0)) badPt.push(ex + ':' + JSON.stringify(p));
    }));
  });
  T('C12 PR 点均为 [重量>0, 次数>0]', badPt.length === 0, JSON.stringify(badPt));
}
{
  const badS = R.SESSIONS.filter(s => !new Set(R.EX.map(e => e.label)).has(s.exercise));
  T('C13 SESSIONS exercise 均在 15 动作清单', badS.length === 0, JSON.stringify(badS.map(s => s.exercise)));
  const badDirS = R.SESSIONS.filter(s => { const e = R.EX.find(x => x.label === s.exercise); return e.direction !== s.direction; });
  T('C14 SESSIONS direction 与动作映射一致', badDirS.length === 0);
}
{
  const badDate = R.REFLECTIONS.filter(r => !/^\d{4}-\d{2}-\d{2}$/.test(r.date));
  T('C15 感悟日期格式合法', badDate.length === 0);
}

/* ============================================================ 集成测试（状态/联动纯逻辑） */
section('集成测试（联动与状态逻辑）');
{
  /* 模拟抽屉历史联动：点 60×3(10-10) → 应定位 s11 第3组 */
  const ex = '平板卧推', w = 60, date = '2026-10-10';
  const session = R.SESSIONS.find(s => s.exercise === ex && s.date === date);
  const setIndex = session ? session.sets.findIndex(st => st.w === w) + 1 : 1;
  T('I1 联动：60kg@10-10 → s11 第3组', session && session.sessionId === 's11' && setIndex === 3, JSON.stringify({ session: session && session.sessionId, setIndex }));
}
{
  const session = R.SESSIONS.find(s => s.exercise === '平板卧推' && s.date === '2026-10-10');
  const setIndex = session.sets.findIndex(st => st.w === 50) + 1;
  T('I2 联动：50kg@10-10 → 第1组', setIndex === 1, setIndex);
}
{
  /* 两两对比——直接模拟 demo renderPrCurve 的实现（下拉值 → 曲线索引） */
  const tests = R.prTestsOf('平板卧推');
  /* 真实实现（demo 当前代码）：show[parseInt(selA.value,10)] —— value 是 1-based 编号 */
  const valA = 1, valB = 3;                 // 用户选 第1次 vs 第3次
  const show = {};
  show[parseInt(valA, 10) - 1] = true;      // 正确：索引 = 编号 - 1
  show[parseInt(valB, 10) - 1] = true;
  const shown = tests.filter((t, i) => show[i]);
  T('I3 两两对比映射（第1 vs 第3 → 索引0和2）', shown.length === 2 && shown[0].date === '2026-10-09' && shown[1].date.includes('10-17'), JSON.stringify(shown.map(t => t.date)));
}
{
  /* 两两对比——检查 demo 源码映射（应「编号-1」）与下拉填充、初始禁用态 */
  const src = fs.readFileSync(htmlPath, 'utf-8');
  T('I3b demo 源码两两映射用「编号-1」', /parseInt\(selA\.value,\s*10\)\s*-\s*1/.test(src), '未使用 -1');
  T('I9 抽屉两两下拉有填充（option 生成段）', /selA\.innerHTML = opts/.test(src) && /selB\.innerHTML = opts/.test(src), '缺少下拉填充');
  T('I9b 下拉编号按索引生成（不依赖 no 字段）', /option value="'\+\(i\+1\)/.test(src), '使用 tr.no 会得到 undefined');
  T('I10 默认 selA=1 / selB=最后一次', /selA\.value = 1; selB\.value = t\.length > 1 \? t\.length : 1/.test(src), '默认值缺失');
  T('I11 初始禁用态（全部对比时下拉禁用）', src.indexOf('selA\').disabled = !pair;') > 0, '初始禁用缺失');
}
{
  /* 宽松绑定数量：组级感悟中已匹配/待匹配 */
  const grp = R.REFLECTIONS.filter(r => r.setIndex);
  const matched = grp.filter(r => R.isMatched(r)).length;
  const unmatched = grp.length - matched;
  T('I4 组级绑定：已匹配 5 / 待匹配 1', matched === 5 && unmatched === 1, matched + '/' + unmatched);
}
{
  /* 迷你图数据：平板训练轮第一组重量序列（非 PR 轮） */
  const pts = R.sessionsOf('平板卧推').filter(s => !s.isPR).map(s => s.sets[0].w);
  T('I5 迷你图训练点序列 = [45, 47.5]', pts.length === 2 && pts[0] === 45 && pts[1] === 47.5, JSON.stringify(pts));
}
{
  /* 按日模式：10-11 当天 session 数（夹胸感悟待匹配 → 0 训练轮） */
  const dayS = R.SESSIONS.filter(s => s.date === '2026-10-11');
  T('I6 按日 10-11 训练轮 = 0（仅感悟）', dayS.length === 0, dayS.length);
  const extra = R.DAY_EXTRA['2026-10-11'];
  T('I7 10-11 晨脉 77 + 意象完成', extra.hr === 77 && extra.imagery === true, JSON.stringify(extra));
}

/* ============================================================ 汇总 */
console.log('\n========================================');
console.log('结果：PASS ' + pass + ' / FAIL ' + fail + '（共 ' + (pass + fail) + ' 项）');
if (failures.length) {
  console.log('失败项：');
  failures.forEach(f => console.log('  - ' + f));
  process.exit(1);
}
console.log('全部通过 ✓');

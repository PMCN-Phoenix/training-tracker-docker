// -*- coding: utf-8 -*-
/* M1 验证：原子+单元+交叉 —— vm 沙箱执行 flows.json parse-training，断言感悟解析 */
import fs from 'fs';
import vm from 'vm';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const flowsPath = path.join(__dirname, '..', 'nodered_data', 'flows.json');
const flows = JSON.parse(fs.readFileSync(flowsPath, 'utf-8'));
const parse = flows.find(n => n.id === 'parse-training');
if (!parse) { console.error('FAIL: parse-training 不存在'); process.exit(1); }

const func = parse.func;
const ctx = vm.createContext({ Date, Math, parseFloat, parseInt, String, RegExp, isNaN });
const wrapped = vm.runInContext(`(function(msg){ ${func} })`, ctx, { filename: 'parse-training.js' });

let pass = 0, fail = 0;
const results = [];
function check(name, cond, detail = '') {
  if (cond) { pass++; results.push(`  PASS ${name}`); }
  else { fail++; results.push(`  FAIL ${name} ${detail}`); }
}

function run(text, opts = {}) {
  const msg = {
    payload: text,
    req: { query: { source: opts.source || 'phone', time: opts.time || '2026-10-11T09:00:00+08:00' } }
  };
  const out = wrapped(msg);
  return out; // [msg|null, msg|null]
}

const t = (ms, k) => ms.find(m => m.measurement === k);

// ================= 原子：单条组级感悟 =================
{
  const out = run('平板卧推 第2组 感悟：肩胛锁死更稳');
  const msg = out[0];
  const refs = msg.payload.filter(m => m.measurement === 'ppl_reflection');
  check('原子1: 组级消息产生 ppl_reflection', refs.length === 1);
  if (refs[0]) {
    check('原子2: exercise=平板卧推', refs[0].tags.exercise === '平板卧推', JSON.stringify(refs[0].tags));
    check('原子3: set_index=2', refs[0].tags.set_index === '2');
    check('原子4: direction=push', refs[0].tags.direction === 'push');
    check('原子5: content 剥离识别词与冒号', refs[0].fields.content === '肩胛锁死更稳', JSON.stringify(refs[0].fields));
    check('原子6: date=2026-10-11', refs[0].tags.date === '2026-10-11', refs[0].tags.date);
    check('原子7: id 格式 ref_YYYYMMDD_8hex', /^ref_\d{8}_[0-9a-f]{8}$/.test(refs[0].tags.id), refs[0].tags.id);
    check('原子8: 响应 refCount=1', msg.refCount === 1);
  }
}

// ================= 单元：动作级 =================
{
  const out = run('平板卧推 感悟：今天上胸感觉好');
  const msg = out[0];
  const refs = msg.payload.filter(m => m.measurement === 'ppl_reflection');
  check('单元1: 动作级产生 ppl_reflection', refs.length === 1);
  if (refs[0]) {
    check('单元2: exercise=平板卧推', refs[0].tags.exercise === '平板卧推');
    check('单元3: 无 set_index', refs[0].tags.set_index === undefined, JSON.stringify(refs[0].tags));
    check('单元4: content=今天上胸感觉好', refs[0].fields.content === '今天上胸感觉好');
  }
}

// ================= 单元：日级 =================
{
  const out = run('推日 感悟：整体状态一般，组间拉长到 3 分钟');
  const msg = out[0];
  const refs = msg.payload.filter(m => m.measurement === 'ppl_reflection');
  check('单元5: 日级产生 ppl_reflection', refs.length === 1);
  if (refs[0]) {
    check('单元6: 无 exercise', refs[0].tags.exercise === undefined, JSON.stringify(refs[0].tags));
    check('单元7: direction=push（推日推断）', refs[0].tags.direction === 'push');
    check('单元8: content 保留全文', refs[0].fields.content === '整体状态一般，组间拉长到 3 分钟', refs[0].fields.content);
  }
}

// ================= 单元：混录（训练+感悟同发） =================
{
  const out = run('平板卧推 47.5kg×8 第1组 感悟：这组最顺');
  const msg = out[0];
  const hasTrain = msg.payload.some(m => m.measurement === 'ppl_push_bench_flat');
  const refs = msg.payload.filter(m => m.measurement === 'ppl_reflection');
  check('单元9: 训练组照常解析', hasTrain);
  check('单元10: 感悟同时解析', refs.length === 1);
  if (refs[0]) {
    check('单元11: set_index=1', refs[0].tags.set_index === '1');
    check('单元12: session_id 顺带绑定', refs[0].tags.session_id === 's' + Date.parse('2026-10-11T09:00:00+08:00'));
    check('单元13: content=这组最顺', refs[0].fields.content === '这组最顺');
  }
  const train = msg.payload.find(m => m.measurement === 'ppl_push_bench_flat');
  check('单元14: 训练与感悟同一 session', train && train.tags.session_id === refs[0].tags.session_id);
}

// ================= 单元：纯感悟消息不 400 =================
{
  const out = run('感悟：今天状态差');
  const msg = out[0];
  check('单元15: 纯感悟消息走成功分支', msg !== null && msg.payload.some(m => m.measurement === 'ppl_reflection'));
}

// ================= 交叉：识别词变体 =================
{
  const r1 = run('平板卧推 心得：起桥要收紧')[0].payload.filter(m => m.measurement === 'ppl_reflection');
  const r2 = run('平板卧推 笔记：离心慢一点')[0].payload.filter(m => m.measurement === 'ppl_reflection');
  const r3 = run('平板卧推 reflection：good')[0].payload.filter(m => m.measurement === 'ppl_reflection');
  check('交叉1: 心得 识别', r1.length === 1 && r1[0].fields.content === '起桥要收紧');
  check('交叉2: 笔记 识别', r2.length === 1 && r2[0].fields.content === '离心慢一点');
  check('交叉3: reflection 识别（大小写）', r3.length === 1 && r3[0].fields.content === 'good');
}

// ================= 交叉：组号变体 =================
{
  const r1 = run('窄距卧推 第 3 组 感悟：握距再窄一点')[0].payload.filter(m => m.measurement === 'ppl_reflection');
  check('交叉4: 空格组号 第 3 组 → set_index=3', r1[0] && r1[0].tags.set_index === '3');
  const r2 = run('杠铃深蹲 第1组 感悟：膝盖稳定')[0].payload.filter(m => m.measurement === 'ppl_reflection');
  check('交叉5: 蹲动作 direction=squat', r2[0] && r2[0].tags.direction === 'squat');
  const r3 = run('硬拉 第1组 感悟：臀部发力')[0].payload.filter(m => m.measurement === 'ppl_reflection');
  check('交叉6: 拉动作 direction=pull', r3[0] && r3[0].tags.direction === 'pull');
}

// ================= 交叉：动作别名 =================
{
  const r1 = run('卧推 第2组 感悟：别名也能绑定')[0].payload.filter(m => m.measurement === 'ppl_reflection');
  check('交叉7: 别名「卧推」归一为 平板卧推', r1[0] && r1[0].tags.exercise === '平板卧推', r1[0] && r1[0].tags.exercise);
}

// ================= 交叉：无感悟消息不受影响 =================
{
  const out = run('杠铃深蹲 60kg×5 60kg×5 60kg×5');
  const msg = out[0];
  const refs = msg.payload.filter(m => m.measurement === 'ppl_reflection');
  check('交叉8: 纯训练消息不产生感悟', refs.length === 0);
  check('交叉9: 训练组数不受影响', msg.actionCount === 1 && msg.setCount === 3);
}

// ================= 交叉：content 冒号剥离 =================
{
  const r1 = run('平板卧推 第1组 感悟： 带空格冒号内容')[0].payload.filter(m => m.measurement === 'ppl_reflection');
  check('交叉10: 冒号+空格剥离', r1[0] && r1[0].fields.content === '带空格冒号内容', r1[0] && JSON.stringify(r1[0].fields));
}

// ================= 交叉：时间戳边界 =================
{
  const out = run('平板卧推 感悟：夜训记录', { time: '2026-10-11T23:59:59+08:00' });
  const refs = out[0].payload.filter(m => m.measurement === 'ppl_reflection');
  check('交叉11: 23:59:59 日期仍为当日', refs[0] && refs[0].tags.date === '2026-10-11');
}

console.log(`\nM1 验证：${pass} PASS / ${fail} FAIL`);
results.forEach(r => console.log(r));
process.exit(fail > 0 ? 1 : 0);

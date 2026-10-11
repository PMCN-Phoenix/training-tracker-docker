// M1 数据层验证：感悟解析（原子/单元/交叉）
// 运行: node _verify/m1_verify.mjs nodered_data/flows.json
import fs from 'fs';
import assert from 'assert';

const path = process.argv[2] || 'nodered_data/flows.json';
const flows = JSON.parse(fs.readFileSync(path, 'utf-8'));
const parseFn = flows.find(n => n.id === 'parse-training');
const formatFn = flows.find(n => n.id === 'format-ok');
assert(parseFn && formatFn, 'flows.json 缺少 parse-training/format-ok 节点');

const runParse = (text, ts) => {
  const f = new Function('msg', parseFn.func);
  const out = f({ payload: text, req: { query: { time: String(ts) } } });
  return out; // [成功msg, null] 或 [null, 失败msg]
};
const runFormat = (msg) => new Function('msg', formatFn.func)(msg);

let pass = 0, fail = 0;
const check = (name, cond, extra) => {
  if (cond) { pass++; }
  else { fail++; console.error('FAIL:', name, extra || ''); }
};
const findRef = (ms) => ms.find(m => m.measurement === 'ppl_reflection');
const findTrain = (ms, id) => ms.find(m => m.measurement === id);

// ---- 原子级：单条消息解析 ----
{
  const [msg] = runParse('平板卧推 第2组 感悟：肩胛锁死更稳', Date.parse('2026-10-11T03:00:00Z'));
  check('纯感悟-成功输出', Array.isArray(msg.payload));
  const ref = findRef(msg.payload);
  check('组级-1条感悟', msg.payload.filter(m => m.measurement === 'ppl_reflection').length === 1);
  check('组级-无训练', msg.payload.filter(m => m.measurement !== 'ppl_reflection').length === 0);
  check('组级-exercise', ref.tags.exercise === '平板卧推');
  check('组级-set_index', ref.tags.set_index === '2');
  check('组级-direction', ref.tags.direction === 'push');
  check('组级-content', ref.fields.content === '肩胛锁死更稳');
  check('组级-id格式', /^ref_\d{8}_[0-9a-f]{8}$/.test(ref.tags.id), ref.tags.id);
  check('组级-date', ref.tags.date === '2026-10-11', ref.tags.date);
}

// ---- 原子级：动作级 ----
{
  const [msg] = runParse('平板卧推 感悟：今天上胸感觉好', Date.parse('2026-10-11T04:00:00Z'));
  const ref = findRef(msg.payload);
  check('动作级-exercise', ref.tags.exercise === '平板卧推');
  check('动作级-无set_index', !('set_index' in ref.tags));
  check('动作级-content', ref.fields.content === '今天上胸感觉好');
  check('动作级-direction', ref.tags.direction === 'push');
}

// ---- 原子级：日级（带方向词） ----
{
  const [msg] = runParse('推日 感悟：整体状态一般', Date.parse('2026-10-11T05:00:00Z'));
  const ref = findRef(msg.payload);
  check('日级-无exercise', !('exercise' in ref.tags));
  check('日级-direction', ref.tags.direction === 'push');
  check('日级-无set_index', !('set_index' in ref.tags));
  check('日级-content', ref.fields.content === '整体状态一般');
}

// ---- 原子级：日级（无方向） ----
{
  const [msg] = runParse('感悟：今天状态差', Date.parse('2026-10-11T06:00:00Z'));
  const ref = findRef(msg.payload);
  check('日级无方向-direction', ref.tags.direction === 'other');
  check('日级无方向-exercise缺省', !('exercise' in ref.tags));
}

// ---- 单元级：时区日期（UTC 20:00 = 北京次日 04:00） ----
{
  const [msg] = runParse('平板卧推 感悟：跨日测试', Date.parse('2026-10-10T20:00:00Z'));
  const ref = findRef(msg.payload);
  check('时区-UTC20点算北京次日', ref.tags.date === '2026-10-11', ref.tags.date);
}

// ---- 单元级：content 分隔符清理 ----
{
  const [msg] = runParse('平板卧推 感悟:今天动作到位', Date.parse('2026-10-11T07:00:00Z'));
  check('分隔符-冒号半角', findRef(msg.payload).fields.content === '今天动作到位');
}
{
  const [msg] = runParse('平板卧推 感悟：  这组很顺  ', Date.parse('2026-10-11T08:00:00Z'));
  check('分隔符-首尾空白', findRef(msg.payload).fields.content === '这组很顺');
}
{
  const [msg] = runParse('平板卧推 心得：核心绷紧', Date.parse('2026-10-11T09:00:00Z'));
  check('识别词-心得', findRef(msg.payload).fields.content === '核心绷紧');
}
{
  const [msg] = runParse('平板卧推 reflection: tested', Date.parse('2026-10-11T10:00:00Z'));
  check('识别词-reflection', findRef(msg.payload).fields.content === 'tested');
}

// ---- 交叉级：混录（训练 + 感悟同消息） ----
{
  const [msg] = runParse('平板卧推 47.5kg×8 第1组 感悟：这组最顺', Date.parse('2026-10-11T11:00:00Z'));
  const train = findTrain(msg.payload, 'ppl_push_bench_flat');
  const ref = findRef(msg.payload);
  check('混录-训练1组', train && train.fields.weight_kg === 47.5 && train.fields.reps === 8);
  check('混录-训练set_index', train.tags.set_index === '1');
  check('混录-感悟set_index', ref.tags.set_index === '1');
  check('混录-session一致', ref.tags.session_id === train.tags.session_id, ref.tags.session_id);
  check('混录-direction', ref.tags.direction === 'push');
}

// ---- 交叉级：组号出现在感悟词后 = 动作级（不误捕） ----
{
  const [msg] = runParse('平板卧推 感悟：今天第2组最稳', Date.parse('2026-10-11T12:00:00Z'));
  const ref = findRef(msg.payload);
  check('组号后置-动作级', !('set_index' in ref.tags));
  check('组号后置-content完整', ref.fields.content === '今天第2组最稳');
}

// ---- 交叉级：纯训练消息不受影响 ----
{
  const [msg] = runParse('杠铃深蹲 100kg×5 3组', Date.parse('2026-10-11T13:00:00Z'));
  check('纯训练-无感悟', msg.payload.filter(m => m.measurement === 'ppl_reflection').length === 0);
  check('纯训练-深蹲解析', findTrain(msg.payload, 'ppl_squat_back_squat') !== undefined);
}

// ---- 单元级：失败路径（无法识别仍 400） ----
{
  const [, errMsg] = runParse('今天天气不错', Date.parse('2026-10-11T14:00:00Z'));
  check('无识别-失败分支', errMsg && errMsg.payload && errMsg.payload.ok === false);
}

// ---- 交叉级：响应文本 ----
{
  const [msg] = runParse('平板卧推 第2组 感悟：肩胛锁死更稳', Date.parse('2026-10-11T03:00:00Z'));
  const fmt = runFormat(msg);
  check('响应-纯感悟', fmt.payload.message.includes('1 条感悟（平板卧推·第2组）'), fmt.payload.message);
}
{
  const [msg] = runParse('平板卧推 47.5kg×8 第1组 感悟：这组最顺', Date.parse('2026-10-11T11:00:00Z'));
  const fmt = runFormat(msg);
  check('响应-混录', fmt.payload.message.includes('1 个动作 1 组') && fmt.payload.message.includes('1 条感悟（平板卧推·第1组）'), fmt.payload.message);
}

console.log(`M1 验证: ${pass} PASS / ${fail} FAIL`);
process.exit(fail === 0 ? 0 : 1);

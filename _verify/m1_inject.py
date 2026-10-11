# -*- coding: utf-8 -*-
"""M1 注入：给 flows.json parse-training 加感悟解析，format-ok 加感悟提示。
用法: python m1_inject.py <flows.json 路径>
安全: 先写 .bak 备份；只改两个 function 节点的 func 字段。
"""
import json, sys, shutil, os

path = sys.argv[1]
bak = path + ".bak"

# 幂等保护：已注入则跳过（防止重复注入）
with open(path, encoding="utf-8") as f:
    _check = f.read()
if "ppl_reflection" in _check:
    print("SKIP: flows.json 已包含 ppl_reflection，无需重复注入")
    sys.exit(0)

shutil.copyfile(path, bak)

with open(path, encoding="utf-8") as f:
    flows = json.load(f)

# ---- 感悟解析 JS 块（插入到 parse-training.func 的意象解析之后、measurements 判空之前）----
ref_js = r"""
// === 感悟解析（识别词：感悟/心得/笔记/reflection；组级/动作级/日级）===
var refWords = ['感悟', '心得', '笔记', 'reflection'];
var refPos = -1;
var refWord = '';
for (var rw = 0; rw < refWords.length; rw++) {
  var rp = msgText.indexOf(refWords[rw]);
  if (rp >= 0 && (refPos === -1 || rp < refPos)) { refPos = rp; refWord = refWords[rw]; }
}
var refCount = 0;
if (refPos >= 0) {
  var refContent = msgText.slice(refPos + refWord.length).replace(/^[\s:：,，。\-—>]+/, '').replace(/\s+$/, '');
  // 动作：取识别词前最近的动作出现（复用 occ 动作扫描结果）
  var refExercise = '';
  var refDir = 'other';
  for (var rk = 0; rk < occ.length; rk++) {
    if (occ[rk].end <= refPos) { refExercise = occ[rk].ex.label; refDir = occ[rk].ex.direction; }
  }
  // 组号：识别词前的"第N组"
  var refSetMatch = /第\s*(\d+)\s*组/.exec(msgText.slice(0, refPos));
  var refSetIndex = refSetMatch ? parseInt(refSetMatch[1], 10) : 0;
  // 日级方向：无动作时从推日/拉日/蹲日推断
  if (!refExercise) {
    var rdScan = /(推日|拉日|蹲日)/g;
    var rdm;
    while ((rdm = rdScan.exec(msgText.slice(0, refPos))) !== null) {
      if (rdm[1] === '推日') { refDir = 'push'; }
      else if (rdm[1] === '拉日') { refDir = 'pull'; }
      else if (rdm[1] === '蹲日') { refDir = 'squat'; }
    }
  }
  // date（本地 UTC+8）与 id（ref_YYYYMMDD_8hex）
  var refDate = new Date(ts + 8 * 3600 * 1000).toISOString().slice(0, 10);
  var refHex = ('00000000' + ts.toString(16)).slice(-8);
  var refId = 'ref_' + refDate.replace(/-/g, '') + '_' + refHex;
  var refTags = { id: refId, date: refDate, source: source, direction: refDir };
  if (refExercise) { refTags.exercise = refExercise; }
  if (refSetIndex > 0) { refTags.set_index = String(refSetIndex); }
  if (sessionId) { refTags.session_id = sessionId; }
  measurements.push({
    measurement: 'ppl_reflection',
    fields: { content: refContent, tags: '' },
    tags: refTags,
    timestamp: ts
  });
  refCount = 1;
  msg.refCount = refCount;
  msg.refExercise = refExercise;
  msg.refSetIndex = refSetIndex;
}
"""

# ---- format-ok 感悟提示 JS 块 ----
ref_fmt_js = r"""
if (msg.refCount > 0) { var rf = msg.refExercise ? ('（' + msg.refExercise + (msg.refSetIndex > 0 ? '·第' + msg.refSetIndex + '组' : '') + '）') : ''; parts.push(msg.refCount + ' 条感悟' + rf); }
"""

anchor_parse = "if (measurements.length === 0) {"
anchor_fmt = "if (msg.imgCount > 0) { parts.push('意象训练'); }"

done = []
for node in flows:
    if node.get("id") == "parse-training" and anchor_parse in node["func"]:
        node["func"] = node["func"].replace(anchor_parse, ref_js + "\n" + anchor_parse, 1)
        done.append("parse-training")
    if node.get("id") == "format-ok" and anchor_fmt in node["func"]:
        node["func"] = node["func"].replace(anchor_fmt, anchor_fmt + ref_fmt_js, 1)
        done.append("format-ok")

if len(done) != 2:
    print("FAIL: 锚点未全部命中:", done)
    sys.exit(1)

with open(path, "w", encoding="utf-8", newline="\n") as f:
    json.dump(flows, f, ensure_ascii=True, indent=1)

print("OK: injected ->", done, "| backup ->", bak)

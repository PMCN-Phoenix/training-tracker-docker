# 感悟系统 · 多重验证流程（固化）

> 规则：**每次产物交付前必须跑完这套验证，直到全部通过**。本目录是验证工具与结果留档。

## 五级验证定义

| 级别 | 内容 | 工具 |
|---|---|---|
| 原子测试 | 单函数/单数据点正确性（esc 转义、日期、锚定判定、最佳档口径…） | `verify_demo.mjs` |
| 单元测试 | 模块级输出（动作×感悟、训练轮、PR 测试、统计…） | `verify_demo.mjs` |
| 交叉测试 | 数据一致性（外键、日期格式、direction 映射、统计口径复算、宽松绑定…） | `verify_demo.mjs` |
| 集成测试 | 状态/联动纯逻辑（历史 PR 联动定位、两两对比映射、迷你图序列…） | `verify_demo.mjs` |
| 端到端验证 | 真实浏览器驱动完整操作流（模式切换/日历/抽屉/曲线/联动/弹窗…） | `e2e_test.html` + Chrome/Edge headless |

## 怎么跑

```powershell
# 1) 纯逻辑层（数据+函数直接从 demo 提取执行，不复制副本）
cd docs\感悟系统demo\_verify
node verify_demo.mjs "..\训练感悟系统-v1.0完整demo.html"
# 期望：结果：PASS N / FAIL 0（共 N 项）全部通过 ✓

# 2) 端到端（真实浏览器；需要 8099 服务存活）
python -m http.server 8099 --directory docs\感悟系统demo
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --disable-gpu --no-first-run --dump-dom --virtual-time-budget=30000 "http://127.0.0.1:8099/_verify/e2e_test.html"
# 期望：<pre id="result"> 末尾「端到端：全部通过 ✓」
```

稳定性要求：**端到端连续重跑 3 次全通过**才算合格；任何 FAIL → 修产物 → 全量重跑（纯逻辑 + 端到端）→ 直到全绿。

## 验证记录（v1.0 完整 demo，2026-10-11）

- 纯逻辑：**42/42 PASS**
- 端到端：**30/30 PASS，连续 3 轮全通过**

### 本流程抓到并修复的 bug（4 个，全部已修复）

| # | 位置 | 问题 | 修复 |
|---|---|---|---|
| 1 | `renderPrCurve` | 两两对比下拉编号（1-based）直接当数组索引（0-based），选「第1 vs 第3」会错显第2次、漏第3次 | `parseInt(value,10)-1` |
| 2 | `renderDrawer` | 「第 N 次 vs 第 M 次」下拉从未填充（select 空） | 按索引生成 option + 默认 第1 vs 最后 |
| 3 | `renderMid` | 中栏 PR 卡片「查看历史 PR →」按钮无点击绑定，抽屉只能从左栏红标进 | 绑定 `openDrawer`；pc-head 补展开/折叠 |
| 4 | `renderDrawer` | option value 用不存在的 `tr.no` 字段（undefined） | 改用索引 `i+1` 生成编号 |

## 以后每个模块（M1–M5）沿用

1. 模块完成 → 更新/新增对应断言 → 跑 `verify_demo.mjs`（原子/单元/交叉/集成）
2. 涉及交互的模块 → 扩展 `e2e_test.html` 步骤 → headless 跑端到端，连续 3 次
3. 全绿 → 自检截图 → commit + push → 交付
4. 任何 FAIL 不许带着交付，先修产物再重跑整套

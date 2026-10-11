// M3 集成测试：Edge headless dump 的 DOM 内容断言
// 用法：先跑 dump（PowerShell 调 msedge --dump-dom 落文件），再 node _verify/m3_integration.mjs <file>
import fs from 'node:fs'

const file = process.argv[2]
if (!file) {
  console.error('用法: node _verify/m3_integration.mjs <dom文件>')
  process.exit(2)
}
const t = fs.readFileSync(file, 'utf-8')

let pass = 0
const fail = []
const check = (name, cond) => {
  if (cond) { pass += 1; console.log(`  PASS ${name}`) }
  else fail.push(name)
}

// 顶栏
check('品牌标题 训练感悟系统', t.includes('训练感悟系统'))
check('模式切换 按动作', t.includes('按动作'))
check('模式切换 按日', t.includes('按日'))
check('PR 总览按钮', t.includes('PR 总览'))
check('打开看板按钮', t.includes('打开看板'))

// 左栏
check('动作导航 平板卧推', t.includes('平板卧推'))
check('动作导航 杠铃深蹲', t.includes('杠铃深蹲'))
check('方向组 推日', t.includes('推日'))
check('方向组 蹲日', t.includes('蹲日'))
check('PR 红标存在（pr-on class）', t.includes('pr-on') || t.includes('pr-dot'))

// 中栏
check('重量趋势标题', t.includes('重量趋势'))
check('PR 卡片（最近测试）', t.includes('PR · 最近'))
check('当前最佳档', t.includes('当前最佳'))
check('Grafana 深链', t.includes('Grafana 查看'))
check('组行 第1组', t.includes('第1组'))
check('重量单位 kg', t.includes('kg'))

// 右栏
check('侧栏标题', t.includes('侧栏 · 与选中目标一一对应'))

// React 挂载成功标志（id=root 有内容，非空根）
check('root 已渲染（不含空 div）', !/id="root"><\/div>/.test(t))

console.log(fail.length ? `\nFAIL: ${fail.join(' / ')}` : `\n结果：${pass} 项全部通过`)
process.exit(fail.length ? 1 : 0)

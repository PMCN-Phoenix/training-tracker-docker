// M4 端到端：真实浏览器 UI 补录感悟 → 库写入 + 当日 Markdown 同步 → 清理
import puppeteer from 'puppeteer-core'
import { execSync } from 'node:child_process'
import fs from 'node:fs'

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const URL = 'http://127.0.0.1:5174/'
const TEST_DATE = '2026-10-11'
const REPO = 'D:\\11.project\\iwen-codex\\codex-list\\training-tracker-docker'
const MD = `${REPO}\\docs\\记录\\训练感悟\\${TEST_DATE}.md`

let pass = 0
const fail = []
const check = (name, cond, extra = '') => {
  if (cond) { pass += 1; console.log(`  PASS ${name} ${extra}`) }
  else fail.push(name)
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function main() {
  // 前置清理：删测试日数据 + md
  try {
    const py = `D:\\6_code\\13_python\\1_python3.11.0\\python.exe`
    execSync(`"${py}" -c "import json,urllib.request; B='http://127.0.0.1:8001/api'; d=json.load(urllib.request.urlopen(B+'/reflections?date=${TEST_DATE}&limit=200')); [urllib.request.urlopen(urllib.request.Request(B+'/reflections/'+i['id'],method='DELETE')) for i in d['data']['items']]"`, { stdio: 'pipe' })
  } catch {}
  if (fs.existsSync(MD)) fs.unlinkSync(MD)

  const browser = await puppeteer.launch({
    executablePath: EDGE, headless: true,
    args: ['--disable-gpu', '--no-first-run', '--no-default-browser-check'],
  })
  const page = await browser.newPage()
  await page.setViewport({ width: 1440, height: 900 })
  page.on('pageerror', (e) => console.log(`  [pageerror] ${e.message}`))

  // 按动作模式打开平板卧推 → 点某组 → 右侧「补录感悟」
  await page.goto(URL + '?mode=ex&exercise=' + encodeURIComponent('平板卧推'), { waitUntil: 'networkidle2', timeout: 30000 })
  await page.waitForSelector('.set-row', { timeout: 15000 })
  await page.click('.set-row')
  await sleep(400)
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll('.add-note button')].find((b) => b.textContent.includes('补录'))
    if (btn) btn.click()
  })
  await sleep(400)
  const form = await page.$('.mask .dlg')
  check('补录表单弹出', Boolean(form))

  // 填内容并提交
  const ta = await page.$('textarea')
  check('表单有内容输入框', Boolean(ta))
  if (ta) {
    await ta.type('M4TEST UI端到端：这组起桥稳住后推起更顺。', { delay: 10 })
    // 表单预填了组行日期（9-23），改为测试日 2026-10-11（React 受控输入）
    await page.evaluate((d) => {
      const input = document.querySelector('.dlg input[type=date]')
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
      setter.call(input, d)
      input.dispatchEvent(new Event('input', { bubbles: true }))
    }, TEST_DATE)
    await page.evaluate(() => {
      const btn = [...document.querySelectorAll('.dlg button')].find((b) => /保存|提交|确定/.test(b.textContent))
      if (btn) btn.click()
    })
  }
  await sleep(1500)
  const formClosed = !(await page.$('.mask .dlg'))
  const msgs = await page.evaluate(() => [...document.querySelectorAll('.ant-message-notice, .ant-message')].map((m) => m.textContent))
  console.log(`  [debug] formClosed=${formClosed} msgs=${JSON.stringify(msgs)}`)
  check('表单提交后关闭', formClosed)

  // 库内验证
  const lib = JSON.parse(execSync(`"D:\\6_code\\13_python\\1_python3.11.0\\python.exe" -c "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8001/api/reflections?date=${TEST_DATE}&limit=200')); print(json.dumps(d['data']))"`, { encoding: 'utf-8' }))
  const items = lib.items || []
  const mine = items.find((i) => (i.content || '').includes('M4TEST UI端到端'))
  check('库内已写入 UI 感悟', Boolean(mine), mine ? mine.id : '')

  // md 验证
  check('md 文件已生成', fs.existsSync(MD))
  if (fs.existsSync(MD)) {
    const mdText = fs.readFileSync(MD, 'utf-8')
    check('md 含 UI 内容', mdText.includes('M4TEST UI端到端'))
    check('md 含动作', mdText.includes('平板卧推'))
    check('md 含组号', mdText.includes('组号'))
  }

  // 清理：删除库数据（触发 md 移除）
  if (mine) {
    execSync(`"D:\\6_code\\13_python\\1_python3.11.0\\python.exe" -c "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8001/api/reflections/${mine.id}',method='DELETE'))"`, { stdio: 'pipe' })
    await sleep(600)
    check('删除后 md 移除', !fs.existsSync(MD))
  }

  await browser.close()
  console.log(fail.length ? `\nFAIL: ${fail.join(' / ')}` : `\n结果：${pass} 项全部通过`)
  process.exit(fail.length ? 1 : 0)
}

main().catch((e) => {
  console.error('崩溃:', e)
  process.exit(1)
})

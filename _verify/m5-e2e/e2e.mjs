// M5 端到端：消息录入 → 库 → md → 生产页面显示 → 清理（全链路）
import puppeteer from 'puppeteer-core'
import { execSync } from 'node:child_process'
import fs from 'node:fs'

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const PY = 'D:\\6_code\\13_python\\1_python3.11.0\\python.exe'
const REPO = 'D:\\11.project\\iwen-codex\\codex-list\\training-tracker-docker'
const TEST_DATE = '2026-10-11'
const MD = `${REPO}\\docs\\记录\\训练感悟\\${TEST_DATE}.md`

let pass = 0
const fail = []
const check = (name, cond, extra = '') => {
  if (cond) { pass += 1; console.log(`  PASS ${name} ${extra}`) }
  else fail.push(name)
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const py = (code) => execSync(`"${PY}" -c "${code}"`, { encoding: 'utf-8' })

async function main() {
  // 前置清理
  try { py(`import json,urllib.request; B='http://127.0.0.1:8001/api'; d=json.load(urllib.request.urlopen(B+'/reflections?limit=100')); [urllib.request.urlopen(urllib.request.Request(B+'/reflections/'+i['id'],method='DELETE')) for i in d['data']['items']]`) } catch {}
  if (fs.existsSync(MD)) fs.unlinkSync(MD)
  try { execSync(`"${PY}" -c "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8001/api/reflections/markdown-sync',method='POST'))"`) } catch {}

  // 1. Node-RED 消息录入（训练组 + 感悟同条）
  const msg = '平板卧推 47.5kg×8 第1组 感悟：M5TEST 全链路：起桥稳住后推起更顺。'
  execSync(`"${PY}" -c "import urllib.request,urllib.parse; data='${msg}'.encode('utf-8'); req=urllib.request.Request('http://127.0.0.1:1880/add-training',data=data,headers={'Content-Type':'text/plain; charset=utf-8'}); print(urllib.request.urlopen(req,timeout=20).read().decode('utf-8'))"`, { stdio: 'pipe' })
  await sleep(2000)
  const lib = JSON.parse(py(`import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8001/api/reflections?limit=50')); print(json.dumps(d['data']))`))
  const mine = (lib.items || []).find((i) => (i.content || '').includes('M5TEST 全链路'))
  check('消息录入 → 库内感悟', Boolean(mine), mine ? mine.id : '')
  check('感悟带动作与组号', Boolean(mine) && mine.exercise === '平板卧推' && mine.set_index === 1)

  // 2. md 重同步 → 文件含内容
  execSync(`"${PY}" -c "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8001/api/reflections/markdown-sync',method='POST'))"`)
  check('md 文件生成', fs.existsSync(MD))
  if (fs.existsSync(MD)) {
    const t = fs.readFileSync(MD, 'utf-8')
    check('md 含感悟内容', t.includes('M5TEST 全链路'))
    check('md 含动作组号', t.includes('平板卧推') && t.includes('第1组'))
  }

  // 3. 生产页面（8001）按日模式 → 中栏训练 + 右栏感悟
  const browser = await puppeteer.launch({
    executablePath: EDGE, headless: true,
    args: ['--disable-gpu', '--no-first-run', '--no-default-browser-check'],
  })
  const page = await browser.newPage()
  await page.setViewport({ width: 1440, height: 900 })
  page.on('pageerror', (e) => console.log(`  [pageerror] ${e.message}`))
  await page.goto(`http://127.0.0.1:8001/?mode=day&date=${TEST_DATE}`, { waitUntil: 'networkidle2', timeout: 30000 })
  await sleep(1200)
  const sess = await page.$$('.col-mid .session')
  check('生产页渲染当天训练', sess.length >= 1, `${sess.length} 轮`)
  const midText = await page.$eval('.col-mid', (el) => el.innerText)
  check('中栏含平板卧推组', midText.includes('47.5kg'))
  // 右栏默认日级视图；点中栏该组行 → 右栏显示组级感悟
  const hasRight = await page.$('.col-right')
  check('右栏存在', Boolean(hasRight))
  const rowClicked = await page.evaluate(() => {
    const rows = [...document.querySelectorAll('.col-mid .set-row')]
    const target = rows.find((r) => r.innerText.includes('47.5kg'))
    if (target) { target.click(); return target.innerText.slice(0, 80) }
    return ''
  })
  check('点中栏组行', Boolean(rowClicked), rowClicked.replace(/\n/g, '|'))
  await sleep(800)
  const rightText2 = await page.$eval('.col-right', (el) => el.innerText)
  console.log(`  [debug] right2=${rightText2.slice(0, 300).replace(/\n/g, ' | ')}`)
  check('右栏显示组级感悟', rightText2.includes('M5TEST 全链路'))
  await browser.close()

  // 4. 清理
  if (mine) {
    py(`import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8001/api/reflections/${mine.id}',method='DELETE'))`)
    execSync(`"${PY}" -c "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8001/api/reflections/markdown-sync',method='POST'))"`)
  }
  const left = JSON.parse(py(`import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8001/api/reflections?limit=50')); print(json.dumps(d['data']))`))
  check('清理后库空', (left.items || []).length === 0)
  check('清理后 md 移除', !fs.existsSync(MD))

  console.log(fail.length ? `\nFAIL: ${fail.join(' / ')}` : `\n结果：${pass} 项全部通过`)
  process.exit(fail.length ? 1 : 0)
}

main().catch((e) => {
  console.error('崩溃:', e)
  process.exit(1)
})

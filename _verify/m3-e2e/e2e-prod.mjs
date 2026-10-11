// M3 生产模式端到端：8001 静态托管（SPA + API 同源）
import puppeteer from 'puppeteer-core'

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
let pass = 0
const fail = []
const check = (name, cond, extra = '') => {
  if (cond) { pass += 1; console.log(`  PASS ${name} ${extra}`) }
  else fail.push(name)
}

async function main() {
  const browser = await puppeteer.launch({
    executablePath: EDGE,
    headless: true,
    args: ['--disable-gpu', '--no-first-run', '--no-default-browser-check'],
  })
  const page = await browser.newPage()
  await page.setViewport({ width: 1440, height: 900 })
  page.on('pageerror', (e) => console.log(`  [pageerror] ${e.message}`))

  await page.goto('http://127.0.0.1:8001/?mode=ex&exercise=' + encodeURIComponent('平板卧推'), {
    waitUntil: 'networkidle2',
    timeout: 30000,
  })
  await page.waitForSelector('.set-row', { timeout: 15000 })
  check('生产页渲染组行', true)
  const head = await page.$eval('.mid-head h2', (el) => el.textContent)
  check('动作标题 = 平板卧推', head.includes('平板卧推'), head)
  const prCard = await page.$('.pr-card')
  check('PR 卡片存在', Boolean(prCard))
  await page.click('.set-row')
  await new Promise((r) => setTimeout(r, 500))
  const side = await page.$eval('.side-target', (el) => el.textContent)
  check('点组行 → 右栏联动', side.includes('第1组') && side.includes('平板卧推'), side.slice(0, 40))

  // 按日模式（生产）
  await page.goto('http://127.0.0.1:8001/?mode=day&date=2026-09-23', { waitUntil: 'networkidle2', timeout: 30000 })
  await new Promise((r) => setTimeout(r, 800))
  const cal = await page.$('.cal')
  check('按日模式迷你日历', Boolean(cal))
  const sess = await page.$$('.col-mid .session')
  check('按日渲染当天训练', sess.length >= 1)

  await browser.close()
  console.log(fail.length ? `\nFAIL: ${fail.join(' / ')}` : `\n结果：${pass} 项全部通过`)
  process.exit(fail.length ? 1 : 0)
}

main().catch((e) => {
  console.error('崩溃:', e)
  process.exit(1)
})

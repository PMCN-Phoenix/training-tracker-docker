// M3 端到端测试：真实 Edge 浏览器驱动（puppeteer-core）
// 覆盖：按动作渲染 → 左栏切动作 → 点组行 → 右栏联动 → PR 抽屉 → 两两对比 → 联动跳转 → 按日日历
import puppeteer from 'puppeteer-core'

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const URL = 'http://127.0.0.1:5174/'

let pass = 0
const fail = []
const check = (name, cond, extra = '') => {
  if (cond) { pass += 1; console.log(`  PASS ${name} ${extra}`) }
  else fail.push(name)
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function main() {
  const browser = await puppeteer.launch({
    executablePath: EDGE,
    headless: true,
    args: ['--disable-gpu', '--no-first-run', '--no-default-browser-check'],
  })
  const page = await browser.newPage()
  await page.setViewport({ width: 1440, height: 900 })
  page.on('console', (msg) => {
    if (msg.type() === 'error') console.log(`  [console.error] ${msg.text()}`)
  })
  page.on('pageerror', (e) => console.log(`  [pageerror] ${e.message}`))

  // ===== 按动作模式 =====
  await page.goto(URL + '?mode=ex&exercise=' + encodeURIComponent('平板卧推'), { waitUntil: 'networkidle2', timeout: 30000 })
  await page.waitForSelector('.set-row', { timeout: 15000 })
  check('中栏渲染训练轮组行', true)

  const midHead = await page.$eval('.mid-head h2', (el) => el.textContent)
  check('动作标题 = 平板卧推', midHead.includes('平板卧推'), midHead)

  const prCard = await page.$('.pr-card')
  check('PR 卡片存在', Boolean(prCard))
  const prBest = prCard ? await prCard.$eval('.pc-head', (el) => el.textContent) : ''
  check('PR 卡片含当前最佳', prBest.includes('当前最佳'), prBest.slice(0, 60))

  const mini = await page.$('.mini-chart')
  check('迷你图存在', Boolean(mini))

  // 左栏切动作
  await page.evaluate(() => {
    const acts = [...document.querySelectorAll('.act')]
    const t = acts.find((a) => a.textContent.includes('夹胸'))
    if (t) t.click()
  })
  await sleep(600)
  const head2 = await page.$eval('.mid-head h2', (el) => el.textContent)
  check('左栏点击切换动作 → 夹胸', head2.includes('夹胸'), head2)

  // 切回平板卧推 + 点第一组 → 右栏联动
  await page.evaluate(() => {
    const acts = [...document.querySelectorAll('.act')]
    const t = acts.find((a) => a.textContent.includes('平板卧推'))
    if (t) t.click()
  })
  await sleep(600)
  await page.waitForSelector('.set-row', { timeout: 10000 })
  await page.click('.set-row')
  await sleep(500)
  const sideTarget = await page.$eval('.side-target', (el) => el.textContent)
  const selRow = await page.$eval('.set-row.sel', (el) => el.textContent).catch(() => '(无选中行)')
  console.log(`  [debug] side-target="${sideTarget.slice(0, 60)}" sel-row="${selRow.slice(0, 60)}"`)
  check('点组行 → 右栏显示该组', sideTarget.includes('第1组') && sideTarget.includes('平板卧推'), sideTarget.slice(0, 60))

  // ===== PR 抽屉 =====
  await page.evaluate(() => {
    const btns = [...document.querySelectorAll('.top .btn')]
    const b = btns.find((x) => x.textContent.includes('PR 总览'))
    if (b) b.click()
  })
  await sleep(500)
  const pfCards = await page.$$('.pf-card')
  check('PR 全屏总览卡片 ≥ 5', pfCards.length >= 5, `${pfCards.length} 张`)
  await page.evaluate(() => {
    const c = document.querySelector('.pf-card')
    if (c) c.click()
  })
  await sleep(500)
  const drawer = await page.$('.drawer')
  check('点总览卡片 → 打开 PR 抽屉', Boolean(drawer))
  const svg = await page.$('#prSvg, .pr-curve svg')
  check('抽屉含 PR 曲线 SVG', Boolean(svg))
  const steps = await page.$$('.dr-steps .step')
  check('抽屉全档阶梯行 ≥ 2', steps.length >= 2, `${steps.length} 行`)

  // 两两对比控件
  const radios = await page.$$('input[name=pcmode]')
  check('曲线模式单选（全部/两两）', radios.length === 2)
  await page.evaluate(() => {
    const r = document.querySelector('input[name=pcmode][value=pair]')
    if (r) r.click()
  })
  await sleep(300)
  const selA = await page.$('.pc-mode select')
  check('两两模式出现下拉', Boolean(selA))

  // 关闭抽屉
  await page.evaluate(() => {
    const b = document.querySelector('.drawer-head button')
    if (b) b.click()
  })
  await sleep(300)

  // ===== 按日模式 =====
  await page.goto(URL + '?mode=day&date=2026-09-23', { waitUntil: 'networkidle2', timeout: 30000 })
  await sleep(800)
  const cal = await page.$('.cal')
  check('按日模式左栏 = 迷你日历', Boolean(cal))
  const daySessions = await page.$$('.col-mid .session')
  check('按日中栏渲染当天训练', daySessions.length >= 1, `${daySessions.length} 轮`)
  const calDots = await page.$$('.cal-day .cal-dots i')
  check('日历有打点', calDots.length >= 1, `${calDots.length} 个点`)

  // 点某天（当前月 10 号，2026-09-10 有训练/感悟则中栏更新）
  await page.evaluate(() => {
    const days = [...document.querySelectorAll('.cal-day')]
    const d = days.find((x) => x.textContent.trim() === '10' && !x.className.includes('other'))
    if (d) d.click()
  })
  await sleep(600)
  const headDay = await page.$eval('.mid-head h2', (el) => el.textContent)
  check('点日历日期 → 中栏更新为当天全貌', headDay.includes('· 当日全貌'), headDay)

  await browser.close()
  console.log(fail.length ? `\nFAIL: ${fail.join(' / ')}` : `\n结果：${pass} 项全部通过`)
  process.exit(fail.length ? 1 : 0)
}

main().catch((e) => {
  console.error('E2E 崩溃:', e)
  process.exit(1)
})

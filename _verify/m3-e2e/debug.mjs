// M3 调试：真实浏览器探查中栏为何无组行
import puppeteer from 'puppeteer-core'

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'

async function main() {
  const browser = await puppeteer.launch({
    executablePath: EDGE,
    headless: true,
    args: ['--disable-gpu', '--no-first-run', '--no-default-browser-check'],
  })
  const page = await browser.newPage()
  page.on('console', (msg) => console.log(`  [${msg.type()}] ${msg.text()}`))
  page.on('pageerror', (e) => console.log(`  [pageerror] ${e.message}`))
  page.on('response', (res) => {
    if (res.url().includes('8001')) console.log(`  [api] ${res.status()} ${res.url()}`)
  })

  await page.goto('http://127.0.0.1:5174/?mode=ex&exercise=' + encodeURIComponent('平板卧推'), {
    waitUntil: 'networkidle2',
    timeout: 30000,
  })
  await new Promise((r) => setTimeout(r, 3000))

  const mid = await page.$eval('.col-mid', (el) => el.innerHTML.slice(0, 600))
  console.log('--- col-mid 前 600 字符 ---')
  console.log(mid)

  const body = await page.$eval('body', (el) => el.innerText.slice(0, 500))
  console.log('--- body 文本前 500 ---')
  console.log(body)

  await browser.close()
}

main().catch((e) => {
  console.error('崩溃:', e)
  process.exit(1)
})

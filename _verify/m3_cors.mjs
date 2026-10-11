// M3 交叉补充：模拟浏览器跨域请求（带 Origin 头）验证 CORS
const BASE = 'http://127.0.0.1:8001/api'

async function main() {
  const paths = [
    '/training/exercise/%E5%B9%B3%E6%9D%BF%E5%8D%A7%E6%8E%A8',
    '/pr/tests',
    '/reflections?limit=50',
    '/training/calendar',
  ]
  for (const p of paths) {
    try {
      const res = await fetch(BASE + p, {
        headers: { Origin: 'http://127.0.0.1:5174' },
      })
      const text = await res.text()
      const cors = res.headers.get('access-control-allow-origin')
      console.log(`${p}\n  status=${res.status} cors=${cors} len=${text.length} head=${text.slice(0, 80)}`)
    } catch (e) {
      console.log(`${p}\n  FETCH ERROR: ${e.message}`)
    }
  }
}

main()

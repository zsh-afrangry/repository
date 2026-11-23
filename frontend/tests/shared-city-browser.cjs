/** Disposable browser checks for shared city; all API responses are fixtures.
 * 对应文档：docs/18_助手业务接口与共享数据.md「测试与脚本」。
 * Requires a frontend build and Playwright; never contacts production services.
 */
const assert = require('node:assert/strict')
const { createServer } = require('node:http')
const { readFile } = require('node:fs/promises')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')

const dist = path.resolve(__dirname, '../dist')
const mime = {'.js':'application/javascript', '.css':'text/css', '.html':'text/html', '.svg':'image/svg+xml', '.json':'application/json'}
const server = createServer(async (req, res) => {
  try {
    const pathname = new URL(req.url, 'http://127.0.0.1').pathname
    const name = pathname === '/' ? 'index.html' : pathname.slice(1)
    const file = path.resolve(dist, name)
    if (!file.startsWith(dist + path.sep)) throw Error('invalid static path')
    const content = await readFile(file)
    res.writeHead(200, {'Content-Type':mime[path.extname(file)] || 'application/octet-stream'}).end(content)
  } catch {res.writeHead(404).end()}
})

const weather = (id, location) => ({locationId:id, location, temp:21, condition:'晴', icon:'☀️',
  feel:21, humidity:55, wind:'微风', precip:'0', aqi:'42', forecast:[], updatedAt:'2026-11-23T12:00:00+08:00'})
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

;(async () => {
  server.listen(0, '127.0.0.1')
  await new Promise(resolve => server.once('listening', resolve))
  const base = `http://127.0.0.1:${server.address().port}`
  const browser = await chromium.launch({executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome', headless:true, args:['--no-sandbox']})
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000},timezoneId:'Asia/Shanghai'})
    const errors = [], requests = []
    page.on('pageerror', error => errors.push(error.message))
    let ownerName = '已确认地点甲', ownerUnavailable = false, ownerDelay = 0
    await page.addInitScript(() => {
      if (!sessionStorage.getItem('shared-city-seeded')) {
        localStorage.setItem('km.weather.locationId', '101010100')
        sessionStorage.setItem('shared-city-seeded', '1')
      }
    })
    await page.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url())
      if (url.origin !== base) return route.abort()
      if (!url.pathname.startsWith('/api/')) return route.continue()
      requests.push({path:url.pathname, method:request.method()})
      const json = (data,status=200) => route.fulfill({status,json:data})
      if (url.pathname === '/api/weather/owner') {
        if (ownerDelay) await sleep(ownerDelay)
        return ownerUnavailable ? json({detail:'暂时不可用'},503) : json(weather('101280109',ownerName))
      }
      if (url.pathname === '/api/weather/') {
        const id = url.searchParams.get('location') || '101280109'
        return json(weather(id, id === '101280601' ? '广东省 · 深圳市' : '网页旧地点'))
      }
      if (url.pathname.includes('/calendar-events')) return json([])
      return json({detail:'fixture unavailable'},503)
    })

    const label = page.locator('.weather-location-label')
    const open = () => page.locator('.weather-location-trigger').click()
    await page.goto(base, {waitUntil:'domcontentloaded'})
    await label.getByText('已确认地点甲').waitFor()
    assert.equal(await page.evaluate(() => localStorage.getItem('km.weather.locationId')), '101010100')

    await open()
    await page.getByRole('option', {name:/深圳/}).click()
    await label.getByText('广东省 · 深圳市').waitFor()
    assert.equal(await page.evaluate(() => localStorage.getItem('km.weather.mode')), 'local')
    const ownersBeforeReload = requests.filter(item => item.path === '/api/weather/owner').length
    await page.reload({waitUntil:'domcontentloaded'})
    await label.getByText('广东省 · 深圳市').waitFor()
    assert.equal(requests.filter(item => item.path === '/api/weather/owner').length, ownersBeforeReload)

    ownerName = '已确认地点乙'
    await open()
    await page.getByRole('button', {name:'跟随助手所在地'}).click()
    await label.getByText('已确认地点乙').waitFor()
    assert.equal(await page.evaluate(() => localStorage.getItem('km.weather.mode')), 'follow')

    ownerName = '已确认地点丙'
    await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')))
    await label.getByText('已确认地点丙').waitFor()

    ownerUnavailable = true
    await page.reload({waitUntil:'domcontentloaded'})
    await label.getByText('广东省 · 深圳市').waitFor()
    await page.getByText('暂时无法读取助手所在地，当前显示本浏览器上次选择的地点。').waitFor()
    ownerUnavailable = false
    await open()
    await page.getByRole('button', {name:'跟随助手所在地'}).click()
    await label.getByText('已确认地点丙').waitFor()

    // A slow prior follow request must not overwrite a newer explicit city choice.
    ownerDelay = 900
    await page.reload({waitUntil:'domcontentloaded'})
    await open()
    await page.getByRole('option', {name:/深圳/}).click()
    await label.getByText('广东省 · 深圳市').waitFor()
    await sleep(1100)
    assert.match(await label.innerText(), /深圳/)
    assert(requests.every(item => item.method === 'GET'), 'weather interactions must not write to the profile')
    assert.deepEqual(errors, [])
    for (const width of [1440, 320]) {
      await page.setViewportSize({width,height:900})
      await open()
      const menu = await page.locator('.weather-location-menu').boundingBox()
      const card = await page.locator('.weather-widget').boundingBox()
      assert(menu && card && menu.x >= card.x && menu.x + menu.width <= card.x + card.width,
        `weather menu must stay inside its card at width ${width}`)
      if (process.env.SCREENSHOT_PATH && width === 1440) await page.screenshot({path:process.env.SCREENSHOT_PATH})
      await page.keyboard.press('Escape')
    }
    console.log('PASS legacy preference, follow, independent selection, fallback, recovery and stale-request race')
  } finally {
    await browser.close()
    await new Promise(resolve => server.close(resolve))
  }
})().catch(error => {console.error(error); process.exitCode = 1})

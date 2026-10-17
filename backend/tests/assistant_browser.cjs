/**
 * 对应文档：docs/18_助手业务接口与共享数据.md「测试与脚本」。
 * Browser integration against disposable assistant_server.py + separate Vite.
 * No production database/model/QQ. Tests are under backend/tests by owner convention.
 */
const assert = require('node:assert/strict')
const { spawn } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')
const os = require('node:os')
const net = require('node:net')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'))
const repo = path.resolve(__dirname, '../..')
async function port() {const s = net.createServer(); await new Promise(r => s.listen(0, '127.0.0.1', r)); const n = s.address().port; await new Promise(r => s.close(r)); return n}
;(async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'km-browser-')), tokenFile = path.join(root, 'token')
  fs.writeFileSync(tokenFile, 'b'.repeat(64), {mode: 0o600})
  const apiPort = await port(), uiPort = await port(), origin = `http://127.0.0.1:${uiPort}`
  const children = [], errors = []
  const start = (cmd, args, opts = {}) => {const c = spawn(cmd, args, {stdio: ['ignore', 'ignore', 'pipe'], ...opts}); c.stderr.on('data', d => errors.push(d.toString())); children.push(c); return c}
  let browser
  try {
    start('/home/afrangry/miniconda3/envs/desheng/bin/python', [path.join(__dirname, 'assistant_server.py'), '--port', String(apiPort), '--token-file', tokenFile])
    start(process.execPath, [path.join(repo, 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', String(uiPort), '--strictPort'], {cwd: path.join(repo, 'frontend'), env: {...process.env, KM_API_TARGET: `http://127.0.0.1:${apiPort}`}})
    let ready = false
    for (let i = 0; i < 100; i++) {try {if ((await fetch(`${origin}/api/dashboard/pending/`)).ok) {ready = true; break}} catch {} await new Promise(r => setTimeout(r, 100))}
    assert.ok(ready, 'test servers failed: ' + errors.join('').slice(-1000))
    const api = async (route, method = 'GET', body) => {
      const r = await fetch(`${origin}/api/${route}`, {method, headers: {'Content-Type': 'application/json'}, ...(body ? {body: JSON.stringify(body)} : {})})
      assert.ok(r.ok, `API ${route}: ${r.status}`); return r.status === 204 ? null : r.json()
    }
    const marker = '[桥接UI验收]无日期事项'
    const item = await api('calendar-events/', 'POST', {title: marker, event_date: null, detail: '保留正文', note: '活动结束后，越快越好'})
    browser = await chromium.launch({executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox']})
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}}), pageErrors = []
    page.on('pageerror', e => pageErrors.push(e.message)); page.setDefaultTimeout(10000)
    await page.goto(origin); await page.keyboard.press('Control+k')
    let row = page.locator('.drawer-item').filter({hasText: marker})
    await row.getByText('无 DDL', {exact: true}).waitFor()
    assert.match(await row.innerText(), /活动结束后，越快越好/)
    await row.getByRole('button', {name: `修改「${marker}」`, exact: true}).click()
    await page.getByLabel('事项备注', {exact: true}).fill('无DDL，仍须跟进')
    await page.getByRole('button', {name: '保存', exact: true}).click()
    await page.getByText('备注：无DDL，仍须跟进', {exact: true}).waitFor()
    const saved = (await api('calendar-events/')).find(r => r.id === item.id)
    assert.equal(saved.event_date, null); assert.equal(saved.note, '无DDL，仍须跟进'); assert.equal(saved.detail, '保留正文')
    // Keep the edit's original version while another entry changes the same item.
    await row.getByRole('button', {name: `修改「${marker}」`, exact: true}).click()
    await api(`calendar-events/${item.id}`, 'PATCH', {note: '另一入口修改', expected_version: saved.version})
    await page.getByLabel('事项备注', {exact: true}).fill('过时编辑')
    await page.getByRole('button', {name: '保存', exact: true}).click()
    await page.locator('.drawer-edit .drawer-error').filter({hasText: '刷新'}).waitFor()
    assert.equal((await api('calendar-events/')).find(r => r.id === item.id).note, '另一入口修改')
    await page.getByRole('button', {name: '取消', exact: true}).click()
    // Quick capture is genuinely undated, rather than silently due today.
    await page.getByLabel('快速添加待做事项').fill('[桥接UI验收]极速录入')
    await page.getByLabel('快速添加待做事项').press('Enter')
    await page.locator('.drawer-item').filter({hasText: '[桥接UI验收]极速录入'}).getByText('无 DDL', {exact: true}).waitFor()
    assert.equal((await api('calendar-events/')).find(r => r.title.endsWith('极速录入')).event_date, null)
    // A bill form keeps the version that was actually shown to the user.
    const billMarker = '[桥接UI验收]账单版本'
    let bill = await api('bills/', 'POST', {amount: '36.80', expense_date: new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Shanghai'}).format(new Date()), note: billMarker})
    await page.goto(origin + '/bills')
    await page.getByRole('button', {name: `编辑记录 ${billMarker}`, exact: true}).filter({visible: true}).click()
    bill = await api(`bills/${bill.id}`, 'PATCH', {amount: '35.50', expected_version: bill.version})
    await page.getByLabel('金额', {exact: true}).fill('99.00')
    await page.getByRole('button', {name: '保存修改', exact: true}).click()
    await page.getByRole('dialog').getByRole('alert').filter({hasText: /刷新|查询/}).waitFor()
    assert.equal((await api(`bills/${bill.id}`)).amount, '35.50')
    await page.getByRole('button', {name: '关闭编辑窗口', exact: true}).click()
    await page.reload()
    await page.getByRole('button', {name: `删除记录 ${billMarker}`, exact: true}).filter({visible: true}).click()
    bill = await api(`bills/${bill.id}`, 'PATCH', {amount: '32.10', expected_version: bill.version})
    await page.getByRole('dialog').getByRole('button', {name: '确认删除', exact: true}).click()
    await page.getByRole('dialog').getByRole('alert').filter({hasText: /刷新|查询/}).waitFor()
    assert.equal((await api(`bills/${bill.id}`)).amount, '32.10')
    await page.getByRole('dialog').getByRole('button', {name: '取消', exact: true}).click()
    await page.reload()
    await page.getByRole('button', {name: `删除记录 ${billMarker}`, exact: true}).filter({visible: true}).click()
    await page.getByRole('dialog').getByRole('button', {name: '确认删除', exact: true}).click()
    await page.getByRole('dialog').waitFor({state: 'hidden'})
    assert.ok(!(await api('bills/?limit=200')).items.some(r => r.id === bill.id))
    assert.deepEqual(pageErrors, [])
    console.log(JSON.stringify({ok: true, checks: ['noDDL visible', 'separate detail/note preserved', 'UI update shares row', 'stale task form rejects lost update', 'quick capture null date', 'stale bill edit rejected', 'stale bill delete rejected', 'fresh bill delete succeeds', 'no browser exceptions'], boundary: 'real browser; isolated SQLite/HTTP and separate Vite; no production/model/QQ'}))
  } finally {
    if (browser) await browser.close()
    for (const c of children) {c.kill('SIGTERM'); await new Promise(r => c.exitCode !== null ? r() : c.once('exit', r))}
    fs.rmSync(root, {recursive: true, force: true})
  }
})().catch(e => {console.error(e.message); process.exitCode = 1})

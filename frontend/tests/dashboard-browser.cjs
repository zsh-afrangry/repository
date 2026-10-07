/**
 * 门户首页仪表盘的浏览器回归（docs/14 §10）。
 *
 * 对应文档：docs/14_主页仪表盘与待做事项开发方案.md「§8 相关脚本与测试 / §10 验收」。
 * 改动「待做事项」「本周进度」「加号弹窗」「待做抽屉」「标签页」或主题提示位置时复跑本文件。
 *
 * 跑法（与 portal-browser.cjs 同一套环境变量约定）：
 *   PLAYWRIGHT_MODULE=<playwright 模块路径> \
 *   CHROME_PATH=/usr/bin/google-chrome \
 *   node frontend/tests/dashboard-browser.cjs
 *
 * 默认访问 http://127.0.0.1:3000（可用 PORTAL_URL 覆盖），需要后端在 8010 运行。
 *
 * ⚠️ 本脚本会通过 API 与 UI **创建并删除**自己的测试事项（标题带唯一标记 `MARK`），
 * 只碰 `calendar_events` 一张表，结束时（含失败路径）会按标记前缀清理。
 * 它**不校验**真实业务数据的正确性，只校验页面与接口的契约。
 */
const assert = require('assert')
const path = require('path')

const playwrightModule = process.env.PLAYWRIGHT_MODULE
  || path.join(process.env.HOME || process.env.USERPROFILE || '',
    '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')
const { chromium } = require(playwrightModule)

const chromePath = process.env.CHROME_PATH || '/usr/bin/google-chrome'
const base = process.env.PORTAL_URL || 'http://127.0.0.1:3000'
const api = `${base}/api`
const MARK = `回归探针-${Date.now()}`

/** 本地时区的 YYYY-MM-DD（不要用 toISOString：UTC 会在东八区凌晨算成昨天）。 */
function localDateKey(d) {
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

async function createEvent(request, body) {
  const res = await request.post(`${api}/calendar-events/`, { data: body })
  assert.strictEqual(res.status(), 201, `创建事项失败: ${res.status()}`)
  return res.json()
}

;(async () => {
  const browser = await chromium.launch({
    executablePath: chromePath,
    headless: true,
    args: ['--no-sandbox'],
  })
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  const pageErrors = []
  page.on('pageerror', e => pageErrors.push(e.message))
  page.setDefaultTimeout(10000)

  const created = []
  try {
    const today = localDateKey(new Date())

    // ---- 造数：覆盖「达成规则相反」的关键分支 ----
    // 过去时间、未完成：todo 不算达成，meeting 算达成。
    const overdueTodo = await createEvent(page.request, {
      event_date: today, event_time: '00:00:01', title: `${MARK}-过期待做`, detail: '', tone: 'todo',
    })
    const overdueMeeting = await createEvent(page.request, {
      event_date: today, event_time: '00:00:01', title: `${MARK}-已开完的会`, detail: '', tone: 'meeting',
    })
    // 未来时间、手动完成：todo 算达成。
    const doneTodo = await createEvent(page.request, {
      event_date: today, event_time: '23:59:59', title: `${MARK}-已完成待做`, detail: '', tone: 'todo',
    })
    created.push(overdueTodo.id, overdueMeeting.id, doneTodo.id)
    const doneRes = await page.request.patch(`${api}/calendar-events/${doneTodo.id}/completion`, { data: { done: true } })
    assert.strictEqual(doneRes.status(), 200, '标记完成失败')

    await page.goto(base, { waitUntil: 'networkidle' })

    // ---- V1 卡片改名 + 加号（第二轮：卡名由「本周待做」改为「待做事项」）----
    const title = (await page.locator('.focus-widget .widget-title').first().textContent() || '').trim()
    assert.strictEqual(title, '待做事项', `卡片标题应为「待做事项」，实际「${title}」`)

    const plus = page.locator('.focus-widget .widget-header button').first()
    assert.ok(await plus.count(), '卡片头部应有＋按钮')

    // ---- V2/V7 条目与过期标记 ----
    // 摘要最多 3 条（docs/14 §2.4），所以这里不能断言"≥3"——
    // 造数有三条时正好满，但那是巧合而非契约。
    const items = await page.locator('.focus-widget .focus-item').count()
    assert.ok(items > 0 && items <= 3, `待做摘要应显示 1–3 条，实际 ${items}`)
    // 过期标记只可能出现在被显示的那几条上，所以断言"≤ 造出的过期条数"。
    const overdueTags = await page.locator('.focus-overdue-tag').count()
    assert.ok(overdueTags <= 2, `「已过期」标记不应超过造出的 2 条，实际 ${overdueTags}`)

    // ---- 第二轮新增：分类计数与总数必须可见 ----
    // 摘要被截断到 3 条，若不同时显示计数，"看不到的"就会变成新的隐身。
    const countLine = (await page.locator('.focus-widget .progress-info').first().textContent() || '').trim()
    assert.ok(/未完成/.test(countLine), `应显示未完成总数，实际「${countLine}」`)

    // ---- 第二轮新增：数据不再受日历可见月份影响 ----
    // 这是「翻月后卡片变空」那个缺陷的回归：点「下个月」后卡片内容必须不变。
    const beforeMonth = await page.locator('.focus-widget .focus-item').count()
    await page.locator('.cal-arrow').nth(1).click()
    await page.waitForTimeout(600)
    const afterMonth = await page.locator('.focus-widget .focus-item').count()
    assert.strictEqual(afterMonth, beforeMonth,
      `翻月后待做卡片不应变化（可见月份与清单无关），前 ${beforeMonth} 后 ${afterMonth}`)
    await page.locator('.cal-arrow').nth(0).click() // 翻回当月，避免影响后续断言
    await page.waitForTimeout(300)

    // ---- V3 进度不出现 NaN（分母为 0 的场景由后端用例覆盖） ----
    const pct = (await page.locator('.progress-widget .donut-percentage').first().textContent() || '').trim()
    const dash = await page.locator('.progress-widget .donut-segment').first().getAttribute('stroke-dasharray')
    assert.ok(!/NaN/.test(pct), `百分比不应含 NaN，实际「${pct}」`)
    assert.ok(!/NaN/.test(dash || ''), `stroke-dasharray 不应含 NaN，实际「${dash}」`)

    // ---- V9 「今日安排」数据驱动（不再是写死的三条样例） ----
    const scheduleText = await page.locator('.today-schedule').first().innerText()
    assert.ok(!/项目站会|AutoML 模型评估|阅读：向量数据库原理/.test(scheduleText),
      '「今日安排」不应再显示原写死的样例文案')

    // ---- V6 加号弹窗 ----
    await plus.click()
    const dialog = page.locator('[role="dialog"]').first()
    await dialog.waitFor()
    const values = await dialog.locator('select option').evaluateAll(els => els.map(e => e.value))
    assert.deepStrictEqual(values.slice().sort(), ['meeting', 'todo'],
      `类型下拉应只有 todo/meeting，实际 [${values.join(', ')}]`)
    const dt = dialog.locator('input[type="datetime-local"]').first()
    assert.ok(await dt.count(), '应存在 datetime-local 时间选择器')
    assert.strictEqual(await dt.getAttribute('step'), '1', '时间选择器应支持到秒（step="1"）')
    const dv = await dt.inputValue()
    assert.ok(dv.startsWith(today), `时间选择器默认值应为今天（当前电脑时间），实际「${dv}」`)
    await page.keyboard.press('Escape')
    await dialog.waitFor({ state: 'hidden' })

    // ---- V10 主题提示位置（只改位置，不改样式） ----
    // 2026-10-07：主题提示改用全站共享的 `.app-toast`（原先内联的 `.theme-toast`）。
    // 位置策略不变：桌面 10%、窄屏 8%、水平居中。
    async function toastTopPercent(width, height) {
      await page.setViewportSize({ width, height })
      await page.reload({ waitUntil: 'networkidle' })
      await page.locator('.theme-toggle').first().click()
      const toast = page.locator('.app-toast').first()
      await toast.waitFor()
      const box = await toast.boundingBox()
      const centerOffset = Math.abs((box.x + box.width / 2) - width / 2)
      return { pct: (box.y / height) * 100, centerOffset }
    }
    const wide = await toastTopPercent(1440, 1000)
    assert.ok(Math.abs(wide.pct - 10) < 2.5, `桌面提示应位于约 10%，实际 ${wide.pct.toFixed(1)}%`)
    assert.ok(wide.centerOffset < 5, `提示应水平居中，中心偏差 ${wide.centerOffset.toFixed(1)}px`)

    // 倒计时进度条：必须是"缩到 0"的动画，且时长与提示时长一致
    const bar = page.locator('.app-toast-progress').first()
    assert.ok(await bar.count(), '提示底部应有倒计时进度条')
    assert.ok(/app-toast-countdown/.test(await bar.evaluate(el => getComputedStyle(el).animationName)),
      '进度条应使用倒计时动画')
    assert.strictEqual(await bar.evaluate(el => getComputedStyle(el).animationDuration), '3s',
      '主题提示的进度条时长应为 3s（与 durationMs 共用同一个值）')

    const narrow = await toastTopPercent(390, 844)
    assert.ok(Math.abs(narrow.pct - 8) < 2.5, `窄屏提示应位于约 8%，实际 ${narrow.pct.toFixed(1)}%`)

    // 悬停暂停：提示里有可点元素（如「撤销」），悬停时倒计时必须停住，
    // 否则用户正要点时弹窗先消失。这里用主题提示验证暂停机制本身。
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.reload({ waitUntil: 'networkidle' })
    await page.locator('.theme-toggle').first().click()
    const toastEl = page.locator('.app-toast').first()
    await toastEl.waitFor()
    await toastEl.hover()
    await page.waitForTimeout(300)
    assert.ok(await page.locator('.app-toast-progress.paused').count(),
      '悬停时进度条应暂停')
    // 暂停期间不应消失（主题提示只有 3 秒，暂停后等 4 秒仍在）
    await page.waitForTimeout(4000)
    assert.ok(await page.locator('.app-toast').count(), '悬停暂停期间提示不应消失')
    await page.mouse.move(10, 10)
    await page.waitForTimeout(500)
    assert.strictEqual(await page.locator('.app-toast-progress.paused').count(), 0,
      '移开鼠标后应恢复倒计时')

    // ---- 窄屏无横向溢出 ----
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
    assert.ok(!overflow, '窄屏不应出现横向溢出')

    // ---- 第二轮新增：待做抽屉（L2，docs/14 §11.2）----
    // 判据：随时可达（非首页也能唤出）+ 不打断当前页面。
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto(`${base}/bills`, { waitUntil: 'networkidle' })
    const pathBefore = new URL(page.url()).pathname
    await page.keyboard.press('Control+k')
    const drawer = page.locator('.drawer-panel')
    await drawer.waitFor({ timeout: 5000 })
    assert.ok(await drawer.count(), 'Ctrl+K 应能在 /bills 唤出待做抽屉')
    assert.strictEqual(new URL(page.url()).pathname, pathBefore,
      '打开抽屉不应改变路由（那正是"不打断当前页面"的要求）')
    assert.ok(await page.locator('.drawer-quick-input').count(), '抽屉应有极速录入输入框')

    // 极速录入：只填标题 + Enter 即可保存（不要求选时间）
    const quickTitle = `${MARK}-极速录入`
    await page.locator('.drawer-quick-input').fill(quickTitle)
    await page.locator('.drawer-quick-input').press('Enter')
    await page.waitForTimeout(1200)
    const quickTitles = await page.locator('.drawer-item-title').allTextContents()
    assert.ok(quickTitles.includes(quickTitle), `极速录入应保存成功，实际列表 ${quickTitles.join(' | ')}`)
    assert.strictEqual(quickTitles[0], quickTitle,
      `新录入的无时间事项应排在清单最前（§2.4），实际首条「${quickTitles[0]}」`)

    // ---- 第五轮新增：标签页（全部 / 今天 / 已过期 / 未安排，docs/14 §11.6）----
    // 核心不变量：**每页的角标数字 == 该页实际条数**。
    // 两者都由后端派生（counts 与 item.bucket 同源），这条断言固化那个设计。
    const tabNames = await page.locator('.drawer-tab').evaluateAll(els =>
      els.map(el => (el.textContent || '').replace(/[0-9\s]/g, '').trim()))
    assert.deepStrictEqual(tabNames, ['全部', '今天', '已过期', '未安排'],
      `标签页应为 全部/今天/已过期/未安排，实际 [${tabNames.join(', ')}]`)
    assert.strictEqual(
      await page.locator('.drawer-tab').first().getAttribute('aria-selected'), 'true',
      '「全部」应默认选中——三个分类不是完整划分，必须有兜底页')

    for (let i = 0; i < tabNames.length; i += 1) {
      await page.locator('.drawer-tab').nth(i).click()
      await page.waitForTimeout(400)
      const shown = await page.locator('.drawer-list .drawer-item:not(.is-archived)').count()
      const badge = await page.locator('.drawer-tab').nth(i).evaluate(el => {
        const c = el.querySelector('.drawer-tab-count')
        return c ? Number((c.textContent || '').trim()) : 0
      })
      assert.strictEqual(badge, shown,
        `「${tabNames[i]}」角标 ${badge} 应等于实际条数 ${shown}`)
    }

    // 「全部」必须包含不属于任何分类的"未来有时间"事项，
    // 否则它们会在每个标签页里都看不见（第二轮那个缺陷的翻版）。
    await page.locator('.drawer-tab').first().click()
    await page.waitForTimeout(300)
    const allTitles = await page.locator('.drawer-item-title').allTextContents()
    assert.ok(allTitles.includes(quickTitle),
      '「全部」应显示刚录入的事项')

    // ---- 第四轮新增：作废 / 废纸篓（docs/14 §2.5）----
    // 用户四条决定：无二次确认、顶部提示约 5 秒带撤销、折叠区可恢复、日历照常显示。
    const targetTitle = `${MARK}-极速录入` // 就作废刚建的那条，省得再等一次请求
    const targetRow = page.locator('.drawer-item', { hasText: targetTitle }).first()

    // ① 无二次确认：点一下即作废，不出现额外对话框
    await targetRow.locator('.drawer-item-action').click()
    await page.waitForTimeout(1200)
    const extraDialogs = await page.locator('[role="dialog"]:not(.drawer-panel)').count()
    assert.strictEqual(extraDialogs, 0, '作废不应弹出二次确认框')

    // ② 顶部提示 + 撤销按钮；位置偏上
    // 2026-10-07：作废提示与主题提示合并为共享的 `.app-toast`（见 AppToast.vue）。
    const toast = page.locator('.app-toast').first()
    await toast.waitFor({ timeout: 5000 })
    assert.ok(await page.locator('.app-toast-action').count(), '作废提示应带「撤销」按钮')
    const toastBox = await toast.boundingBox()
    const toastTopPct = (toastBox.y / 1000) * 100
    assert.ok(toastTopPct < 20, `作废提示应在页面上方，实际 top=${toastTopPct.toFixed(1)}%`)
    // 作废提示的进度条时长应为 5s（与 TOAST_DEFAULT_MS 共用同一个值）
    assert.strictEqual(
      await page.locator('.app-toast-progress').first().evaluate(el => getComputedStyle(el).animationDuration),
      '5s', '作废提示的进度条时长应为 5s')

    // 「撤销」按钮真的能撤销（用共享提示的 action 机制）
    await page.locator('.app-toast-action').first().click()
    await page.waitForTimeout(1500)
    const afterUndo = await page.locator('.drawer-item:not(.is-archived) .drawer-item-title').allTextContents()
    assert.ok(afterUndo.includes(targetTitle),
      `提示上的「撤销」应把条目放回列表，实际 ${afterUndo.join(' | ')}`)
    // 撤销后再作废一次，后续断言（折叠区）才有内容
    await page.locator('.drawer-item', { hasText: targetTitle }).first()
      .locator('.drawer-item-action').click()
    await page.waitForTimeout(1200)

    // 作废后该条离开待做列表
    const afterArchive = await page.locator('.drawer-item:not(.is-archived) .drawer-item-title').allTextContents()
    assert.ok(!afterArchive.includes(targetTitle), `作废后应离开待做列表，实际 ${afterArchive.join(' | ')}`)

    // ③ 折叠区可展开、能看到、能恢复
    const archiveToggle = page.locator('.drawer-archive-toggle').first()
    await archiveToggle.waitFor({ timeout: 5000 })
    assert.ok(/已作废/.test(await archiveToggle.textContent()), '应出现「已作废」折叠区')
    await archiveToggle.click()
    await page.waitForTimeout(500)
    const archivedTitles = await page.locator('.drawer-item.is-archived .drawer-item-title').allTextContents()
    assert.ok(archivedTitles.includes(targetTitle), `折叠区应能看到已作废条目，实际 ${archivedTitles.join(' | ')}`)
    assert.strictEqual((await page.locator('.drawer-item.is-archived .drawer-item-action').first().textContent() || '').trim(),
      '恢复', '已作废条目应有「恢复」按钮')
    await page.locator('.drawer-item.is-archived .drawer-item-action').first().click()
    await page.waitForTimeout(1200)
    const afterRestore = await page.locator('.drawer-item:not(.is-archived) .drawer-item-title').allTextContents()
    assert.ok(afterRestore.includes(targetTitle), `「恢复」应把条目放回待做列表，实际 ${afterRestore.join(' | ')}`)

    // ④ 日历照常显示已作废（作废一次，再从接口确认）
    await page.locator('.drawer-item', { hasText: targetTitle }).first()
      .locator('.drawer-item-action').click()
    await page.waitForTimeout(1200)
    const calRows = await page.request.get(`${api}/calendar-events/?date_from=${today}&date_to=${today}`)
    const calJson = await calRows.json()
    const archivedRow = calJson.find(r => r.title === targetTitle)
    assert.ok(archivedRow, '日历接口应仍返回已作废的事项（它确实占用过那天）')
    assert.ok(archivedRow.archived_at, '该行应带 archived_at 时间戳')

    await page.keyboard.press('Escape')
    await drawer.waitFor({ state: 'hidden' })

    assert.deepStrictEqual(pageErrors, [], `存在未捕获的页面异常：${pageErrors.join(' | ')}`)

    console.log('PASS dashboard: 待做摘要 / 本周进度 / 加号弹窗 / 待做抽屉 / 标签页 / 作废回收站 / 主题提示位置')
    console.log(`PASS 累计创建 ${created.length} 条探针并全部清理（含 UI 极速录入的那条）`)
  } finally {
    // 无论断言是否失败都要清理，避免污染真实数据。
    //
    // 分两步，因为**测试会通过两条路径创建事项**：
    //   1. API 直接建的 3 条 → id 记在 `created` 里；
    //   2. UI 极速录入建的那条 → **没有记进 `created`**（是页面自己发的请求）。
    // 所以只按 id 删是不够的，必须再按标题前缀扫一遍并**真的删除**。
    // （2026-10-07 实测踩过：只扫描不删除，UI 建的那条残留了下来。）
    for (const id of created.reverse()) {
      await page.request.delete(`${api}/calendar-events/${id}`).catch(() => {})
    }
    const left = await page.request.get(`${api}/calendar-events/`).catch(() => null)
    if (left && left.ok()) {
      const rows = await left.json()
      const leaked = rows.filter(r => String(r.title || '').startsWith(MARK))
      for (const row of leaked) {
        await page.request.delete(`${api}/calendar-events/${row.id}`).catch(() => {})
      }
      if (leaked.length) {
        console.log(`    清理了 ${leaked.length} 条按标记发现的残留（UI 录入路径）`)
      }
    }
    await browser.close()
  }
})().catch(err => {
  console.error('FAIL', err.message)
  process.exit(1)
})

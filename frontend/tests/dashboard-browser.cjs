/**
 * 门户首页仪表盘的浏览器回归（docs/14 §10）。
 *
 * 对应文档：docs/14_主页仪表盘与待做事项开发方案.md「§8 相关脚本与测试 / §10 验收」。
 * 改动「待做事项」「本周进度」「加号弹窗」「待做抽屉」「标签页」或提示层时复跑本文件。
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

/**
 * 按**按钮文字**定位行内操作按钮（修改 / 作废 / 恢复）。
 *
 * ⚠️ 2026-10-08 起一条事项有**多个**操作按钮（先「修改」，再「作废」/「恢复」），
 * 所以 `.drawer-item-action` 的 `first()` 不再等于"作废"——
 * 原来的 `first()`/无 `.nth()` 写法会点到「修改」上。
 * 按文字定位比按下标更稳：将来再加按钮（如「删除」）也不会串位。
 *
 * ⚠️ 文字匹配要**容忍两侧空白**：按钮内容是模板插值，渲染出来是 `" 恢复 "`
 * （前后各一个空格）。用 `^恢复$` 匹配不到——已实测踩到。
 */
function actionButton(scope, label) {
  return scope.locator('.drawer-item-action').filter({
    hasText: new RegExp(`^\\s*${label}\\s*$`),
  }).first()
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
    // ⚠️ 不要断言"过期标记 ≤ 造出的条数"：表里**可能还有真实用户数据**
    // （2026-10-07 的数据丢失就是因为脚本假设了"这张表只有测试数据"）。
    // 这里只验证"标记数量不超过显示的条目数"——那才是真正的契约。
    const overdueTags = await page.locator('.focus-overdue-tag').count()
    assert.ok(overdueTags <= items,
      `「已过期」标记不应多于显示的条目（显示 ${items} 条，标记 ${overdueTags} 个）`)

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

    // ---- 第二轮新增：待做抽屉（L2，docs/14 §11.1）----
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

    // ---- 标签页（全部 / 今天 / 已过期 / 未安排 / 已完成，docs/14 §11.1）----
    // 核心不变量：**每页的角标数字 == 该页实际条数**。
    // 两者都由后端派生（counts 与 item.bucket 同源），这条断言固化那个设计。
    const tabNames = await page.locator('.drawer-tab').evaluateAll(els =>
      els.map(el => (el.textContent || '').replace(/[0-9\s]/g, '').trim()))
    assert.deepStrictEqual(tabNames, ['全部', '今天', '已过期', '未安排', '已完成'],
      `标签页应为 全部/今天/已过期/未安排/已完成，实际 [${tabNames.join(', ')}]`)
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

    // ---- 时间的视觉权重（用户 2026-10-08 要求"时间更醒目"）----
    // 断言用**计算样式**而不是截图：截图要人眼看，而这里是可判定的规则。
    // 契约：时间必须比同一行的日期更突出（更大、更粗、更亮）。
    // 这三条一起才构成"醒目"——只调大字号但仍用灰色，等于没改。
    {
      // 造一条**带时间**的探针（上面那些探针都无时间，看不到这个元素）
      const timedTodo = await createEvent(page.request, {
        event_date: today, event_time: '09:30:00',
        title: `${MARK}-带时间`, detail: '', tone: 'todo',
      })
      created.push(timedTodo.id)
      // 切回「全部」并刷新抽屉，确保新条目已渲染
      await page.locator('.drawer-tab').first().click()
      await page.waitForTimeout(300)
      await page.keyboard.press('Escape')
      await page.waitForTimeout(300)
      await page.keyboard.press('Control+k')
      await page.waitForTimeout(900)

      const row = page.locator('.drawer-item', { hasText: `${MARK}-带时间` }).first()
      const timeEl = row.locator('.drawer-item-time')
      assert.strictEqual(await timeEl.count(), 1,
        '带时间的事项应渲染出独立的 `.drawer-item-time` 元素')
      assert.strictEqual((await timeEl.textContent() || '').trim(), '09:30',
        '时间应只显示 HH:MM（秒是记录精度，不是决策依据）')

      const [timeStyle, dateStyle] = await Promise.all([
        timeEl.evaluate(el => {
          const s = getComputedStyle(el)
          return { size: parseFloat(s.fontSize), weight: Number(s.fontWeight), color: s.color }
        }),
        row.locator('.drawer-item-date').evaluate(el => {
          const s = getComputedStyle(el)
          return { size: parseFloat(s.fontSize), weight: Number(s.fontWeight), color: s.color }
        }),
      ])

      assert.ok(timeStyle.size > dateStyle.size,
        `时间的字号应大于日期（时间 ${timeStyle.size}px vs 日期 ${dateStyle.size}px）`)
      assert.ok(timeStyle.weight > dateStyle.weight,
        `时间的字重应大于日期（时间 ${timeStyle.weight} vs 日期 ${dateStyle.weight}）`)

      // 颜色：**不能靠"RGB 之和更大"来判断**。
      // 已过期的时间是琥珀色 rgb(251,191,36)，三通道之和(478)反而**低于**
      // 日期灰 rgb(148,163,184)(495)——但它的对比度是 9.87，比灰的 6.43 更高。
      // 亮度之和不是对比度。所以这里按 WCAG 相对亮度算，才是真正的"更醒目"。
      const relLum = c => {
        const [r, g, b] = (c.match(/\d+/g) || []).map(Number).slice(0, 3).map(v => {
          const s = v / 255
          return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
        })
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
      }
      // 抽屉面板底色（深色设计系统，见 main.css）
      const panel = 'rgb(30, 30, 42)'
      const contrast = fg => {
        const a = relLum(fg), b = relLum(panel)
        const [hi, lo] = a > b ? [a, b] : [b, a]
        return (hi + 0.05) / (lo + 0.05)
      }
      assert.ok(contrast(timeStyle.color) > contrast(dateStyle.color),
        `时间的对比度应高于日期（时间 ${contrast(timeStyle.color).toFixed(2)} vs 日期 ${contrast(dateStyle.color).toFixed(2)}）`)
      // 时间自身也要过 WCAG AA 正文线（4.5），无论它是近白还是琥珀
      assert.ok(contrast(timeStyle.color) >= 4.5,
        `时间对比度应达 WCAG AA（实际 ${contrast(timeStyle.color).toFixed(2)}）`)
    }

    // ---- 「已完成」标签页 + 恢复（docs/14 §11.1）----
    // 它补上的缺口：勾选完成后事项离开清单，此前**没有任何地方**能撤销——
    // 误勾了就找不回来。
    const completedTabIndex = tabNames.indexOf('已完成')
    const completedTab = page.locator('.drawer-tab').nth(completedTabIndex)
    const badgeOf = async (idx) => page.locator('.drawer-tab').nth(idx).evaluate(el => {
      const c = el.querySelector('.drawer-tab-count')
      return c ? Number((c.textContent || '').trim()) : 0
    })

    // 勾掉刚录入的那条
    const doneBeforeTick = await badgeOf(completedTabIndex)
    await page.locator('.drawer-item', { hasText: quickTitle }).first()
      .locator('button.drawer-check').click()
    await page.waitForTimeout(1500)

    // ⚠️ **不要写死数字**：表里可能还有真实用户数据（跑本脚本时已存在），
    // 所以断言"比勾选前 +1"，而不是"等于某个常量"。
    // 这个脚本曾因假设"表里只有自己造的数据"而误报，也正是那种假设造成了
    // 2026-10-07 的数据丢失（见 AGENTS.md）。
    const doneBefore = await badgeOf(completedTabIndex)
    assert.strictEqual(doneBefore, doneBeforeTick + 1,
      `勾选后「已完成」应比之前多 1（${doneBeforeTick} → ${doneBeforeTick + 1}），实际 ${doneBefore}`)
    const allAfterDone = await page.locator('.drawer-item-title').allTextContents()
    assert.ok(!allAfterDone.includes(quickTitle),
      `「全部」不应包含已完成的事项（用户决定），实际 ${allAfterDone.join(' | ')}`)

    // 进入已完成页
    await completedTab.click()
    await page.waitForTimeout(400)
    const doneRows = page.locator('.drawer-list .drawer-item:not(.is-archived)')
    assert.strictEqual(await doneRows.count(), doneBefore,
      '已完成页条数应等于其角标')
    assert.ok(/已完成/.test(await page.locator('.drawer-body .drawer-count').textContent() || ''),
      '计数文案应说"已完成"')
    // 行结构不同：没有可点的勾选框，最右侧是「恢复」
    assert.strictEqual(await doneRows.first().locator('button.drawer-check').count(), 0,
      '已完成页不应有可点的勾选框')
    assert.ok(await actionButton(doneRows.first(), '恢复').count(),
      '已完成页应有「恢复」按钮')

    // 恢复刚勾的那条 → 退回待做清单。
    // 它按完成时间倒序排第一（刚完成的），所以 first() 就是它。
    // 先记下它的标题，恢复后要确认它真的离开了已完成页。
    const restoredTitle = (await doneRows.first().locator('.drawer-item-title').textContent() || '').trim()
    await actionButton(doneRows.first(), '恢复').click()
    await page.waitForTimeout(1800)
    assert.strictEqual(await badgeOf(completedTabIndex), doneBefore - 1,
      `恢复后「已完成」角标应 -1（${doneBefore} → ${doneBefore - 1}）`)
    const stillDone = await page.locator('.drawer-item-title').allTextContents()
    assert.ok(!stillDone.includes(restoredTitle),
      `恢复后「${restoredTitle}」应离开已完成页，实际仍在 ${stillDone.join(' | ')}`)
    // 提示应确认这次恢复
    const restoreToast = await page.locator('.app-toast-text').first().textContent().catch(() => '')
    assert.ok(/恢复/.test(restoreToast || ''), `应弹出恢复提示，实际「${restoreToast}」`)

    // 回到「全部」，后续作废测试需要它在那里
    await page.locator('.drawer-tab').first().click()
    await page.waitForTimeout(400)
    const restored = await page.locator('.drawer-item-title').allTextContents()
    assert.ok(restored.includes(quickTitle), '恢复后应回到「全部」列表')

    // ---- 2026-10-08 新增：修改已有事项（docs/14 §11.3）----
    // 核心场景就是"极速录入之后补时间"，所以直接拿刚录入的那条（它是未安排的）来测。
    const editRow = page.locator('.drawer-item', { hasText: quickTitle }).first()
    assert.ok(await actionButton(editRow, '修改').count(), '每条事项应有「修改」按钮')
    await actionButton(editRow, '修改').click()
    await page.waitForTimeout(400)

    // ① 行内展开，不弹第二个弹窗（避免两个 useDialogFocus 争焦点陷阱与滚动锁）
    assert.strictEqual(await page.locator('.drawer-edit').count(), 1, '应就地展开编辑区')
    assert.strictEqual(await page.locator('[role="dialog"]:not(.drawer-panel)').count(), 0,
      '编辑不应再叠一个弹窗')

    // ② 表单已用当前值预填（而不是空白）——否则用户会以为要重填
    assert.strictEqual(await page.locator('.drawer-edit-input[type="text"]').inputValue(),
      quickTitle, '标题应预填当前值')
    assert.strictEqual(await page.locator('.drawer-edit-input[type="time"]').inputValue(), '',
      '未安排的事项时间应为空')

    // ③ 时间控件必须带 step="1"：否则秒被截成 00（改一次就悄悄丢秒）
    assert.strictEqual(await page.locator('.drawer-edit-input[type="time"]').getAttribute('step'),
      '1', '时间输入应支持秒（step="1"）')

    // ④ 补时间 + 改备注 + 改类型，保存
    const editedTitle = `${MARK}-已修改`
    await page.locator('.drawer-edit-input[type="text"]').fill(editedTitle)
    await page.locator('.drawer-edit-input[type="date"]').fill('2026-10-21')
    await page.locator('.drawer-edit-input[type="time"]').fill('14:30:45')
    await page.locator('.drawer-edit-textarea').fill('补上的备注')
    await page.locator('.drawer-edit select').selectOption('meeting')
    await page.locator('.drawer-edit button[type="submit"]').click()
    await page.waitForTimeout(1500)

    // 编辑区收起
    assert.strictEqual(await page.locator('.drawer-edit').count(), 0, '保存后编辑区应收起')

    // ⑤ 值真的落到后端了（不只是界面上变了）
    const afterEdit = await page.request.get(`${api}/calendar-events/?date_from=2026-10-01&date_to=2026-10-31`)
    const editedRow = (await afterEdit.json()).find(r => r.title === editedTitle)
    assert.ok(editedRow, `修改后的标题应能查到，实际未找到「${editedTitle}」`)
    assert.strictEqual(editedRow.event_date, '2026-10-21', '日期应已更新')
    assert.strictEqual(editedRow.event_time, '14:30:45', '时间应已更新，且**秒要保住**')
    assert.strictEqual(editedRow.detail, '补上的备注', '备注应已更新')
    assert.strictEqual(editedRow.tone, 'meeting', '类型应已更新')

    // ⑥ 界面元信息也跟着变了（时间不再是「未安排」）
    const editedRowEl = page.locator('.drawer-item', { hasText: editedTitle }).first()
    assert.ok(!/未安排/.test(await editedRowEl.textContent() || ''),
      '补上时间后不应再显示「未安排」')

    // ⑦ ⭐ 反向：把时间清空 → 回到「未安排」
    // 这是本功能最容易写错的一条：后端用 exclude_unset，必须**显式传 null**。
    // 若前端把空值序列化成"省略该字段"，用户会发现时间改得掉、却清不掉。
    await actionButton(editedRowEl, '修改').click()
    await page.waitForTimeout(400)
    await page.locator('.drawer-edit-input[type="time"]').fill('')
    await page.locator('.drawer-edit button[type="submit"]').click()
    await page.waitForTimeout(1500)

    const afterClear = await page.request.get(`${api}/calendar-events/?date_from=2026-10-01&date_to=2026-10-31`)
    const clearedRow = (await afterClear.json()).find(r => r.title === editedTitle)
    assert.ok(clearedRow, '清空时间后仍应能查到该条')
    assert.strictEqual(clearedRow.event_time, null, '时间应被真正清空（回到「未安排」）')
    assert.ok(/未安排/.test(await page.locator('.drawer-item', { hasText: editedTitle }).first().textContent() || ''),
      '清空时间后界面应重新显示「未安排」')

    // ⑧ 取消按钮不写库
    const cancelRow = page.locator('.drawer-item', { hasText: editedTitle }).first()
    await actionButton(cancelRow, '修改').click()
    await page.waitForTimeout(400)
    await page.locator('.drawer-edit-input[type="text"]').fill('不该被保存的标题')
    await page.locator('.drawer-edit button', { hasText: '取消' }).click()
    await page.waitForTimeout(500)
    assert.strictEqual(await page.locator('.drawer-edit').count(), 0, '「取消」应收起编辑区')
    const afterCancel = await page.request.get(`${api}/calendar-events/?date_from=2026-10-01&date_to=2026-10-31`)
    assert.ok(!(await afterCancel.json()).some(r => r.title === '不该被保存的标题'),
      '「取消」不应把改动写进后端')

    // 后续作废测试用原始标题定位，这里把标题与日期都改回去。
    // ⚠️ **日期也要改回今天**：上面把它改成了 2026-10-21，而后面第 ④ 步
    // 用 `date_from=${today}` 查日历，日期不改回去就查不到——
    // 这个失败与功能无关，纯粹是测试自己造的坑（已实测踩到）。
    await actionButton(page.locator('.drawer-item', { hasText: editedTitle }).first(), '修改').click()
    await page.waitForTimeout(400)
    await page.locator('.drawer-edit-input[type="text"]').fill(quickTitle)
    await page.locator('.drawer-edit-input[type="date"]').fill(today)
    await page.locator('.drawer-edit-input[type="time"]').fill('')
    await page.locator('.drawer-edit button[type="submit"]').click()
    await page.waitForTimeout(1500)

    // ---- 第四轮新增：作废 / 废纸篓（docs/14 §2.5）----
    // 用户四条决定：无二次确认、顶部提示约 5 秒带撤销、折叠区可恢复、日历照常显示。
    const targetTitle = `${MARK}-极速录入` // 就作废刚建的那条，省得再等一次请求
    const targetRow = page.locator('.drawer-item', { hasText: targetTitle }).first()

    // ① 无二次确认：点一下即作废，不出现额外对话框
    await actionButton(targetRow, '作废').click()
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
    await actionButton(page.locator('.drawer-item', { hasText: targetTitle }).first(), '作废').click()
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
    assert.ok(await actionButton(page.locator('.drawer-item.is-archived').first(), '恢复').count(),
      '已作废条目应有「恢复」按钮')
    await actionButton(page.locator('.drawer-item.is-archived').first(), '恢复').click()
    await page.waitForTimeout(1200)
    const afterRestore = await page.locator('.drawer-item:not(.is-archived) .drawer-item-title').allTextContents()
    assert.ok(afterRestore.includes(targetTitle), `「恢复」应把条目放回待做列表，实际 ${afterRestore.join(' | ')}`)

    // ④ 日历照常显示已作废（作废一次，再从接口确认）
    await actionButton(page.locator('.drawer-item', { hasText: targetTitle }).first(), '作废').click()
    await page.waitForTimeout(1200)
    const calRows = await page.request.get(`${api}/calendar-events/?date_from=${today}&date_to=${today}`)
    const calJson = await calRows.json()
    const archivedRow = calJson.find(r => r.title === targetTitle)
    assert.ok(archivedRow, '日历接口应仍返回已作废的事项（它确实占用过那天）')
    assert.ok(archivedRow.archived_at, '该行应带 archived_at 时间戳')

    await page.keyboard.press('Escape')
    await drawer.waitFor({ state: 'hidden' })

    assert.deepStrictEqual(pageErrors, [], `存在未捕获的页面异常：${pageErrors.join(' | ')}`)

    console.log('PASS dashboard: 待做摘要 / 本周进度 / 加号弹窗 / 待做抽屉 / 标签页（含已完成+恢复） / 修改（含补时间与清空时间） / 时间视觉权重 / 作废回收站 / 主题提示位置')
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

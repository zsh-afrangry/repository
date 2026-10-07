/** Portal UI regressions. All API requests are intercepted; no local database is changed.
 * 对应文档：docs/12_首页与账单收尾验收.md「相关测试与脚本」。
 * Start Vite, then run with PLAYWRIGHT_MODULE (if not installed locally),
 * CHROME_PATH and optionally PORTAL_URL / SCREENSHOT_DIR. See docs/12.
 */
const assert = require('node:assert/strict');
const { mkdirSync } = require('node:fs');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.PORTAL_URL || 'http://127.0.0.1:3000';
const output = process.env.SCREENSHOT_DIR;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const category = {id:1,name:'餐饮',type:'category',parent_id:null,sort_order:0,children:[]};
const child = {id:2,name:'午饭',type:'subcategory',parent_id:1,sort_order:0,children:[]};
category.children = [child];
const other = {id:3,name:'工资',type:'category',parent_id:null,sort_order:1,children:[]};
const initialBill = {id:1,record_type:'支出',expense_date:'2026-09-20',expense_time:'12:00:00',amount:'12.50',category_id:1,subcategory_id:2,payment_platform_id:null,payment_channel_id:null,fund_type_id:null,category,subcategory:child,payment_platform:null,payment_channel:null,fund_type:null,reimbursement_status:'无需报销',reimbursement_amount:null,transaction_id:null,note:'午餐测试',created_at:'2026-09-20T12:00:00',updated_at:'2026-09-20T12:00:00'};

(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROME_PATH || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
  try {
    const context = await browser.newContext({viewport:{width:1440,height:1000},timezoneId:'Asia/Shanghai'});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    let bills = [structuredClone(initialBill)], events = [], nextId = 2, failBills = false, slowAugust = false, failTags = false, rejectWrite = false;
    const writes = [];
    await context.route('**/api/**', async route => {
      const req = route.request(), u = new URL(req.url()), path = u.pathname;
      if (!path.startsWith('/api/')) return route.continue();
      const json = (data,status=200) => route.fulfill({status,json:data});
      if (path.includes('weather')) return json({detail:'测试天气不可用'},503);
      if (path.includes('git-stats')) return json({month_commits:2,total_commits:100});
      if (path.includes('/tags')) return failTags ? json({detail:'测试标签不可用'},503) : json(path.endsWith('/all')?[category,child,other]:[category,other]);
      if (path.includes('/calendar-events')) {
        if (req.method()==='POST') { const event={id:nextId++,...req.postDataJSON()};events.push(event); return json(event,201); }
        if (req.method()==='DELETE') { events=events.filter(e=>e.id!==Number(path.split('/').at(-1)));return route.fulfill({status:204}); }
        return json(events);
      }
      if (path.includes('/bills')) {
        if (req.method()==='POST' || req.method()==='PATCH') {
          if (rejectWrite) return json({detail:[{loc:['body','amount'],msg:'金额校验测试失败'}]},422);
          const body=req.postDataJSON(); writes.push(body);
          const bill={...initialBill,...body,id:req.method()==='POST'?nextId++:Number(path.split('/').at(-1)),amount:Number(body.amount).toFixed(2),category:[category,other].find(t=>t.id===body.category_id)||null,subcategory:body.subcategory_id===2?child:null};
          bills=bills.filter(b=>b.id!==bill.id).concat(bill);return json(bill,req.method()==='POST'?201:200);
        }
        if (req.method()==='DELETE') {bills=bills.filter(b=>b.id!==Number(path.split('/').at(-1)));return route.fulfill({status:204});}
        if (failBills) return json({detail:'测试读取失败'},503);
        const month=u.searchParams.get('date_from')?.slice(0,7) || `${u.searchParams.get('year')}-${String(u.searchParams.get('month')).padStart(2,'0')}`;
        const records=bills.filter(b=>b.expense_date.startsWith(month));
        if (slowAugust && month==='2026-08') await delay(450);
        if (path.includes('/summary/')) {
          const income=records.filter(b=>b.record_type==='收入').reduce((s,b)=>s+Number(b.amount),0);
          const expense=records.filter(b=>b.record_type==='支出').reduce((s,b)=>s+Number(b.amount),0);
          return json({income,expense,net:income-expense,year:2026,month:Number(u.searchParams.get('month'))});
        }
        const all=u.searchParams.has('date_from')?records:[...bills].sort((a,b)=>b.expense_date.localeCompare(a.expense_date));
        const skip=Number(u.searchParams.get('skip')||0), limit=Number(u.searchParams.get('limit')||50);
        return json({total:all.length,items:all.slice(skip,skip+limit)});
      }
      return json({detail:'Unexpected API request in portal test'},500);
    });
    const shot = async name => {if(output){mkdirSync(output,{recursive:true});await page.screenshot({path:`${output}/${name}.png`,fullPage:true});}};
    const visibleCards = page.locator('.project-card-v2:visible');
    async function cardsReadable() {
      const count=await visibleCards.count();assert(count>0);
      for(let i=0;i<count;i++) {await visibleCards.nth(i).scrollIntoViewIfNeeded(); await page.waitForFunction(el=>getComputedStyle(el).opacity==='1',await visibleCards.nth(i).elementHandle());}
    }
    await page.goto(base);
    await page.locator('.project-grid-v2').waitFor();
    for(let i=0;i<2;i++) {
      await page.getByPlaceholder('搜索项目名称或关键词...').fill('不存在的项目');
      await page.getByText('没有匹配的项目，请调整搜索或筛选条件。').waitFor();
      await page.getByPlaceholder('搜索项目名称或关键词...').fill('');
      await cardsReadable();
      await page.getByLabel('筛选项目状态').selectOption('等待接入');await cardsReadable();
      await page.getByLabel('筛选项目状态').selectOption('all');await cardsReadable();
    }
    await page.getByLabel('切换视图方式').selectOption('list');
    assert.equal(await page.locator('.project-grid-v2').evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(' ').length),1);
    await page.getByLabel('切换视图方式').selectOption('grid');
    await page.locator('.theme-toggle').click();
    // 2026-10-07：主题提示改用全站共享的 `.app-toast`（原先内联的 `.theme-toast`）。
    await page.locator('.app-toast').waitFor();await delay(350);
    const toast=await page.locator('.app-toast').boundingBox();assert(Math.abs(toast.x+toast.width/2-720)<3);
    const widgetBounds = await page.locator('.widget-card').evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect();return r.left>=0 && r.right<=innerWidth}));
    assert(widgetBounds.every(Boolean), 'desktop widgets must not be clipped');
    await shot('home-desktop');
    console.log('PASS home repeated search/filter, list view, centered toast');
    await page.getByRole('link',{name:'查看全部',exact:true}).click();
    await page.getByRole('dialog').waitFor();
    assert((await page.locator('#calendar-modal-title').innerText()).includes('年'));
    await page.getByLabel('事项标题').fill('隔离日程测试');await page.getByRole('button',{name:'增加',exact:true}).click();
    await page.getByRole('heading',{name:'隔离日程测试',exact:true}).waitFor();
    await page.getByRole('button',{name:'删除 隔离日程测试',exact:true}).click();
    await page.getByRole('heading',{name:'隔离日程测试',exact:true}).waitFor({state:'hidden'});
    await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'hidden'});
    console.log('PASS calendar open today, create/delete, keyboard dismissal');
    await page.getByRole('link',{name:'进入记账',exact:true}).focus();await page.keyboard.press('Enter');
    await page.getByText('午餐测试',{exact:true}).waitFor();
    const day=page.getByRole('button',{name:/09\/20/});
    await day.click();await page.getByText('午餐测试',{exact:true}).waitFor({state:'hidden'});await day.click();await page.getByText('午餐测试',{exact:true}).waitFor();
    await page.getByRole('button',{name:'编辑记录 午餐测试',exact:true}).click();
    assert.equal(await page.getByLabel('小类（选填）').inputValue(),'2');
    await page.getByLabel('备注（选填）').fill('修改后的午餐');await page.getByRole('button',{name:'保存修改',exact:true}).click();
    await page.getByRole('dialog').waitFor({state:'hidden'});assert.equal(writes.at(-1).subcategory_id,2);
    await page.getByRole('button',{name:'编辑记录 修改后的午餐',exact:true}).click();
    await page.getByLabel('大类',{exact:true}).selectOption('3');assert.equal(await page.getByLabel('小类（选填）').evaluate(el=>el.selectedIndex),0);
    await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'hidden'});
    assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('aria-label')),'编辑记录 修改后的午餐');
    await page.getByRole('button',{name:'新增记录',exact:true}).click();
    await page.getByRole('button',{name:'添加记录',exact:true}).focus();await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('aria-label')),'关闭编辑窗口');
    await page.keyboard.press('Shift+Tab');assert.equal(await page.evaluate(()=>document.activeElement.textContent.trim()),'添加记录');
    await page.getByRole('button',{name:'收入',exact:true}).click();await page.getByLabel('日期',{exact:true}).fill('2026-09-21');await page.getByLabel('金额',{exact:true}).fill('100');await page.getByLabel('备注（选填）').fill('收入测试');
    rejectWrite=true;await page.getByRole('button',{name:'添加记录',exact:true}).click();await page.getByRole('alert').filter({hasText:'amount：金额校验测试失败'}).waitFor();
    rejectWrite=false;await page.getByRole('button',{name:'添加记录',exact:true}).click();await page.getByRole('dialog').waitFor({state:'hidden'});
    await page.waitForFunction(()=>document.querySelector('[data-testid="monthly-summary"]')?.textContent.includes('+87.50'));
    await page.getByRole('button',{name:'删除记录 收入测试',exact:true}).click();await page.getByRole('button',{name:'取消',exact:true}).click();assert(bills.some(b=>b.note==='收入测试'));
    await page.getByRole('button',{name:'删除记录 收入测试',exact:true}).click();await page.getByRole('button',{name:'确认删除',exact:true}).click();await page.getByRole('dialog').waitFor({state:'hidden'});assert(!bills.some(b=>b.note==='收入测试'));
    console.log('PASS bills expand/collapse, category preservation, create/edit/delete, summary, Escape/focus');
    slowAugust=true;await page.getByRole('button',{name:'上个月',exact:true}).click();await page.getByRole('button',{name:'上个月',exact:true}).click();await delay(650);
    assert((await page.locator('body').innerText()).includes('2026 · 七月'));assert(await page.getByText('本月暂无记录',{exact:true}).isVisible());
    failBills=true;await page.getByRole('button',{name:'下个月',exact:true}).click();await page.getByRole('button',{name:'重试',exact:true}).waitFor();assert.equal(await page.locator('[data-testid="monthly-summary"]').count(),0);assert.equal(await page.getByText('本月暂无记录',{exact:true}).count(),0);
    failBills=false;await page.getByRole('button',{name:'重试',exact:true}).click();await page.getByText('本月暂无记录',{exact:true}).waitFor();
    bills=Array.from({length:205},(_,i)=>({...initialBill,id:i+10,note:`分页测试${i}`}));
    await page.reload();await page.getByText('分页测试204',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:/^编辑记录 分页测试/}).count(),205);
    console.log('PASS stale month responses, error/retry, full month over 200 records');
    bills=[structuredClone(initialBill)];failTags=true;await page.reload();await page.getByText(/标签读取失败/).waitFor();await page.getByText('午餐测试',{exact:true}).waitFor();failTags=false;
    for(const width of [390,320]) {
      await page.setViewportSize({width,height:844});await page.emulateMedia({reducedMotion:'reduce'});await page.goto(base+'/bills');await page.getByText('午餐测试',{exact:true}).waitFor();
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      await page.getByRole('button',{name:'新增记录',exact:true}).click();await page.getByRole('dialog').waitFor();
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await shot(`bills-modal-${width}`);await page.keyboard.press('Escape');
      await page.goto(base);await page.locator('.project-grid-v2').waitFor();await cardsReadable();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      assert(await page.locator('.filter-controls').evaluate(el=>el.getBoundingClientRect().right<=innerWidth));
      await shot(`home-${width}`);
      await page.emulateMedia({reducedMotion:'no-preference'});await page.emulateMedia({reducedMotion:'reduce'});
    }
    for (const width of [1280,1024,768]) {
      await page.setViewportSize({width,height:900});await page.goto(base);await page.locator('.project-grid-v2').waitFor();
      assert(await page.locator('.widget-card').evaluateAll(es=>es.every(e=>e.getBoundingClientRect().right<=innerWidth)));
    }
    await page.goto(base+'/bills');await page.getByText('午餐测试',{exact:true}).waitFor();await page.goBack();await page.locator('.project-grid-v2').waitFor();await page.goForward();await page.getByText('午餐测试',{exact:true}).waitFor();
    assert.deepEqual(errors,[]);console.log('PASS narrow layouts, reduced motion switches, deep link/reload/back/forward; no uncaught browser errors');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});

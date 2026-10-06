/** Start backend/tests/notes_browser_server.py and a Vite instance proxying to :8011.
 * NOTES_URL defaults to http://127.0.0.1:3001. Only disposable notes data is used.
 */
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const base=process.env.NOTES_URL||'http://127.0.0.1:3001';
const screenshot=process.env.SCREENSHOT_DIR;
const fs=require('node:fs');
(async()=>{const browser=await chromium.launch({executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});try{
const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'reduce'});page.setDefaultTimeout(8000);const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
const wait=()=>page.waitForTimeout(200);
const button=name=>page.getByRole('button',{name,exact:true});
const fill=(name,value)=>page.getByRole('textbox',{name,exact:true}).fill(value);
await page.goto(base+'/notes');await page.getByRole('link',{name:'Transformer',exact:true}).waitFor();
const parserChecks=await page.evaluate(async()=>{const {renderNoteMarkdown,importNoteMarkdown}=await import('/src/features/notes/utils/markdown.ts');const html=renderNoteMarkdown('* A\n* B\n\n```js\n* code\n```\n\n<script>alert(1)</script><img src="x" onerror="alert(1)">\n\n[bad](javascript:alert(1))');return {html,plain:importNoteMarkdown('# unchanged','plain.md'),unsupported:(()=>{try{importNoteMarkdown('---\nunknown: a\n---\nbody','x.md');return false}catch{return true}})()}});
assert.ok(parserChecks.html.includes('<ul>'));assert.ok(!parserChecks.html.includes('<script'));assert.ok(!parserChecks.html.includes('onerror'));assert.ok(!parserChecks.html.includes('href="javascript:'));assert.equal(parserChecks.plain.content,'# unchanged');assert.ok(parserChecks.unsupported);

await button('新建主题').click();await fill('主题名称','验收学习主题');await fill('简介','临时主题用于隔离验收');await button('保存设置').click();await page.waitForURL(/\/notes\/[a-f\d-]+$/);await button('主题设置').waitFor();
const topicUrl=page.url(),id=new URL(topicUrl).pathname.split('/').at(-1),api=base+'/api/notes/topics/'+id;
const read=async()=>{const r=await page.request.get(api);assert.equal(r.status(),200);return r.json()};
for(let i=0;i<6;i++){await button('新增').click();await fill('目录名称','目录'+i);await button('保存设置').click();await page.getByRole('dialog').waitFor({state:'hidden'})}
assert.equal((await read()).sections.length,6);
async function createUnit(title,previous){await button('新建单元').click();await fill('笔记标题',title);await fill('Markdown 正文','# '+title+'\n\n* 项目一\n* 项目二\n\n**重点** 和 `inline`\n\n```js\nconst a = "'+ 'long'.repeat(60)+'";\n```\n\n| 一 | 二 | 三 | 四 |\n| --- | --- | --- | --- |\n| A | B | C | D |');if(previous)await page.getByRole('group',{name:'前节点 · 它依赖的单元'}).getByRole('checkbox',{name:previous,exact:true}).check();await button('保存笔记').click();await button('编辑').waitFor();assert.equal(await page.locator('.notes-prose li').count(),2);assert.equal(await page.locator('.notes-prose pre code').count(),1);const url=page.url();await button('关闭窗口').click();await page.getByRole('dialog').waitFor({state:'hidden'});return url}
const aUrl=await createUnit('单元 A'),bUrl=await createUnit('单元 B','单元 A'),cUrl=await createUnit('单元 C','单元 B');
let data=await read();assert.equal(data.edges.length,2);const a=data.units.find(u=>u.title==='单元 A'),b=data.units.find(u=>u.title==='单元 B');
await page.goto(aUrl);await button('编辑').click();await page.getByRole('group',{name:'前节点 · 它依赖的单元'}).getByRole('checkbox',{name:'单元 C',exact:true}).check();await button('保存笔记').click();await page.getByRole('alert').filter({hasText:'循环'}).first().waitFor();assert.equal(await page.getByRole('textbox',{name:'笔记标题',exact:true}).inputValue(),'单元 A');assert.equal((await read()).edges.length,2);await button('取消').click();await button('编辑').waitFor();
// A stale window cannot replace a newer server version.
await button('编辑').click();await fill('笔记标题','单元 A 草稿');data=await read();const {id:_,...payload}=data;payload.description='由其他窗口更新';assert.equal((await page.request.put(api,{data:payload})).status(),200);await button('保存笔记').click();await page.getByRole('alert').filter({hasText:'其他窗口'}).first().waitFor();assert.equal(await page.getByRole('textbox',{name:'笔记标题',exact:true}).inputValue(),'单元 A 草稿');await button('取消').click();await page.reload();await button('编辑').waitFor();
// Membership edits don't infer new dependencies.
await page.goto(bUrl);await button('编辑').click();await page.getByRole('combobox',{name:'目录归属'}).selectOption(data.sections[1].id);await button('保存笔记').click();await button('编辑').waitFor();data=await read();assert.equal(data.units.find(u=>u.id===b.id).sectionId,data.sections[1].id);assert.equal(data.edges.length,2);
await page.reload();await button('编辑').waitFor();assert.equal(await page.locator('.notes-prose li').count(),2);await button('关闭窗口').click();await button('学习路线').click();assert.equal(await page.locator('.graph-heading span').count(),6);await page.locator('.graph-node').filter({hasText:'单元 B'}).click();await button('打开笔记').click();await button('编辑').waitFor();await page.goBack();await page.getByRole('dialog').waitFor({state:'hidden'});await page.goForward();await button('编辑').waitFor();
// Escape closes reader and traps keyboard inside while it is open.
await page.keyboard.press('Shift+Tab');assert.equal(await page.evaluate(()=>!!document.activeElement.closest('[role="dialog"]')),true);await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'hidden'});
// Import preserves Markdown body and separates supported Frontmatter.
await page.locator('input[type=file]').setInputFiles({name:'import.md',mimeType:'text/markdown',buffer:Buffer.from('---\ntitle: 导入单元\ntags: [导入, 测试]\n---\n# 正文\n\n内容')});assert.equal(await page.getByRole('textbox',{name:'笔记标题',exact:true}).inputValue(),'导入单元');assert.equal(await page.getByRole('textbox',{name:'Markdown 正文',exact:true}).inputValue(),'# 正文\n\n内容');await button('保存笔记').click();await button('编辑').waitFor();await button('关闭窗口').click();
// Nonempty directories and topic are protected.
await page.getByRole('button',{name:'设置目录 目录0',exact:true}).click();await button('删除目录').click();await page.getByRole('alert').filter({hasText:'目录非空'}).first().waitFor();await button('关闭窗口').click();await button('主题设置').click();await button('删除主题').click();await page.getByRole('alert').filter({hasText:'主题非空'}).first().waitFor();await button('关闭窗口').click();
for(const width of [1440,768,390,320]){
 await page.setViewportSize({width,height:1000});await page.goto(topicUrl);await button('学习路线').click();await page.locator('.graph').waitFor();assert.equal(await page.locator('.graph-heading span').count(),6);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);await page.emulateMedia({reducedMotion:'no-preference'});await page.emulateMedia({reducedMotion:'reduce'});
 if(screenshot){fs.mkdirSync(screenshot,{recursive:true});await wait();await page.screenshot({path:`${screenshot}/notes-${width}-workspace.png`})}
 await page.goto(aUrl);await button('编辑').waitFor();assert.equal(await page.locator('.notes-dialog').evaluate(e=>e.scrollWidth>e.clientWidth),false);if(screenshot)await page.screenshot({path:`${screenshot}/notes-${width}-reader.png`});
}
// Unknown topic/unit, API failures, recovery, and old URL compatibility.
await page.goto(topicUrl+'/units/missing');await page.getByText('知识单元不存在或已删除。',{exact:false}).waitFor();await button('关闭窗口').click();
await page.route('**/api/notes/topics/*',r=>r.fulfill({status:503,json:{detail:'验收读取失败'}}));await page.goto(topicUrl);await page.getByRole('alert').filter({hasText:'验收读取失败'}).waitFor();await page.unroute('**/api/notes/topics/*');await button('重新载入').click();await button('主题设置').waitFor();
await page.goto(base+'/Transformer');await page.waitForURL('**/notes/transformer');await button('主题设置').waitFor();
// Delete B clears its two incident edges, preserving A and C.
await page.goto(bUrl);await button('删除单元').click();await page.getByRole('dialog').waitFor({state:'hidden'});data=await read();assert.equal(data.edges.length,0);assert.ok(data.units.some(u=>u.id===a.id));
assert.deepEqual(errors,[]);console.log('PASS Notes UI/API: management, DAG validation, conflicts, migration/refresh, route history, keyboard, import, delete protection, six-column/mobile layouts, errors and legacy redirects');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});

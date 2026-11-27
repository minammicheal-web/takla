import os
APP = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
SHOTS = os.environ.get('SHOTS', '/tmp/shots'); os.makedirs(SHOTS, exist_ok=True)
# Two-step purchase with smart codes and barcode PDF, returns tab with exchange, damaged pieces,
# supplier tab (account, return to supplier), offers, reports, stock count.
import asyncio
from playwright.async_api import async_playwright

async def run(lang, dark):
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, has_touch=True, accept_downloads=True, color_scheme='dark' if dark else 'light')
    if lang == 'en': await ctx.add_init_script("localStorage.setItem('store-lang','en')")
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(APP); await pg.wait_for_timeout(500)
    E = pg.evaluate; sfx = f'{lang}-{"d" if dark else "l"}'; W = pg.wait_for_timeout
    await E("S.settings.autoReceipt=false; S.settings.retDays=15")
    # ---- purchase in two steps
    await E("go('buy')"); await W(300)
    await pg.fill('#bSup', 'مصنع النور'); await pg.fill('#bSupPh', '01000000001'); await pg.fill('#bSupInv', 'F-77')
    await E("bPay='آجل'; renderBuyPay()")
    await pg.screenshot(path=f'{SHOTS}/x0-supplier-{sfx}.png')
    await pg.click('#bNext'); await W(300)
    async def line(name, typ, mat, color, size, qty, cost, price, more=False):
      if not more: await pg.click('#bAddIt'); await W(350)
      await pg.fill('#aName', name); await pg.fill('#aType', typ); (await pg.fill('#aMat', mat)) if await pg.query_selector('#aMat') else None; await pg.fill('#aBrand', 'Levi')
      await pg.fill('#aColor', color); await pg.fill('#aSize', size); await pg.fill('#aQty', str(qty)); await pg.fill('#aCost', str(cost)); await pg.fill('#aPrice', str(price))
    await line('بنطلون جينز', 'بنطلون', 'جينز', 'أزرق', '32', 5, 200, 400)
    await pg.screenshot(path=f'{SHOTS}/x1-additem-{sfx}.png')
    await pg.click('.bal [data-more]'); await W(450)
    await pg.fill('#aColor', 'أزرق'); await pg.fill('#aSize', '34'); await pg.fill('#aQty', '5'); await pg.fill('#aCost', '200'); await pg.fill('#aPrice', '400')
    await pg.click('.bal [data-ok]'); await W(350)
    await line('بلوزة', 'بلوزة', 'قطن', 'أبيض', 'm', 4, 100, 250); await pg.click('.bal [data-ok]'); await W(350)
    await pg.screenshot(path=f'{SHOTS}/x2-lines-{sfx}.png')
    await pg.click('#bSave'); await W(700)
    print('codes', await E("S.items.flatMap(i=>i.variants.map(v=>v.serial)).join(' ')"))
    print('buy', await E("rno(S.txns.find(t=>t.type==='buy'))"))
    await pg.screenshot(path=f'{SHOTS}/x3-labels-{sfx}.png')
    async with pg.expect_download() as dl: await pg.click('.lbd [data-pdf]')
    d = await dl.value; await d.save_as(f'/tmp/labels-{sfx}.pdf'); print('pdf', d.suggested_filename)
    await E("MK.back()"); await W(300)
    # ---- a sale: jeans 32 at a 10% discount + blouse
    await E("""(()=>{const j=S.items.find(i=>i.name==='بنطلون جينز'), v32=j.variants.find(v=>v.size==='32'), bl=S.items.find(i=>i.name==='بلوزة');
      S.txns.push({id:uid(),type:'sell',ts:Date.now()-3*864e5,pay:'كاش',by:'x',lines:[{itemId:j.id,vid:v32.id,qty:1,list:400,price:360,disc:10},{itemId:bl.id,vid:bl.variants[0].id,qty:1,list:250,price:250,disc:0}],cname:'منى',cphone:'01234567890'});
      persist(); C=calc();})()""")
    sale = await E("rno(S.txns.find(t=>t.type==='sell'))"); print('sale', sale)
    # ---- returns tab: exchange jeans 32 (wrong size) for jeans 34, blouse stays
    await E("go('ret')"); await W(300)
    await pg.fill('#rQ', sale.replace('-', '')); await W(400)
    print('loaded', await E("RT && rno(RT.t)"))
    await pg.click('#rBody .rtc >> nth=0 >> [data-ck]'); await W(250)
    await pg.click('#rBody .rtc >> nth=0 >> [data-why=mind]'); await W(250)
    print('discount note', await E("$$('#rBody .rtc')[0].textContent.includes('360')"), 'supplier shown', await E("$('#rBody').textContent.includes('مصنع النور')"))
    await E("(()=>{const j=S.items.find(i=>i.name==='بنطلون جينز'); retPickItem(j, j.variants.find(v=>v.size==='34'));})()"); await W(300)
    print('diff', await E("JSON.stringify(retTotals().D)"))
    await pg.screenshot(path=f'{SHOTS}/x4-exchange-{sfx}.png', full_page=True)
    await pg.click('#rSave'); await W(700)
    nt = await E("JSON.stringify((t=>({no:rno(t),lines:t.lines.length,carry:t.carry.length,ex:t.exchAmt,pay:t.pay}))(S.txns.find(t=>t.exchFrom)))"); print('new invoice', nt)
    print('stock 32/34', await E("(()=>{const j=S.items.find(i=>i.name==='بنطلون جينز'); return j.variants.map(v=>v.size+':'+C.V[v.id].stock).join(' ')})()"))
    await pg.screenshot(path=f'{SHOTS}/x5-newreceipt-{sfx}.png')
    await E("MK.back()"); await W(300)
    # ---- blouse comes back damaged through the new invoice (carried line)
    await E("openReturn(S.txns.find(t=>t.exchFrom))"); await W(400)
    print('rows on new invoice', await E("$$('#rBody .rtc').length"))
    await E("(()=>{const r=retRows(RT.t).find(x=>x.carried); RT.q[r.key]=1; RT.why[r.key]='dmg'; renderRet();})()"); await W(200)
    print('dmg note', await E("$('#rBody').textContent.includes('مرتجعات المورد') || $('#rBody').textContent.includes('supplier returns')"))
    await pg.click('#rSave'); await W(700); await E("MK.back()"); await W(300)
    print('blouse stock/dmg', await E("(()=>{const b=S.items.find(i=>i.name==='بلوزة'), r=C.V[b.variants[0].id]; return r.stock+'/'+r.dmg})()"))
    # ---- suppliers tab
    await E("go('sup')"); await W(300)
    await pg.screenshot(path=f'{SHOTS}/x6-suppliers-{sfx}.png')
    await pg.click('#supBody .ivb'); await W(300)
    print('owed', await E("supAcct(SUP).owed"), 'reasons', await E("JSON.stringify(supReasons(SUP))"))
    # mark a jeans piece from stock as damaged
    await E("(()=>{window._askN=askNum; askNum=()=>Promise.resolve(1);})()")
    await pg.click('#supBody [data-v] [data-mk] >> nth=0'); await W(400)
    await pg.click('#supAllD'); await W(300)
    await pg.screenshot(path=f'{SHOTS}/x7-supplier-{sfx}.png', full_page=True)
    await pg.click('#supRet'); await W(400)
    await pg.click('.srd [data-ok]'); await W(800)
    print('sret', await E("JSON.stringify((t=>({no:rno(t),n:t.lines.reduce((s,l)=>s+l.qty,0),pay:t.pay}))(S.txns.find(t=>t.type==='sret')))"), 'owed after', await E("supAcct(supKey('مصنع النور')).owed"))
    print('dmg left', await E("Object.values(C.V).reduce((s,r)=>s+r.dmg,0)"), await E("JSON.stringify(S.txns.find(t=>t.type==='sret').lines.map(l=>[l.qty,l.dmgQ,l.cost]))"), await E("JSON.stringify(supAcct(supKey('مصنع النور')))"))
    await pg.screenshot(path=f'{SHOTS}/x8-sret-{sfx}.png')
    await E("MK.back()"); await W(300)
    # ---- offers, reports, count
    await E("S.settings.promos=[{id:'p1',name:'عرض الجينز',sc:'type',key:norm('بنطلون'),pct:20,on:true}]; persist()")
    await E("go('sell')"); await W(200)
    await E("(()=>{const j=S.items.find(i=>i.name==='بنطلون جينز'); sSel=j; sVar=j.variants.find(v=>v.size==='34'); renderPick();})()"); await W(200)
    print('offer applied', await E("$('#sNet').value"))
    await E("go('stock')"); await W(300); await pg.click('#stRep'); await W(400)
    await pg.screenshot(path=f'{SHOTS}/x9-reports-{sfx}.png'); await E("MK.back()"); await W(300)
    await pg.click('#stCnt'); await W(400)
    code = await E("S.items[0].variants[0].serial")
    await pg.fill('#ctIn', code); await pg.press('#ctIn', 'Enter'); await W(200)
    print('count', await E("$('#ctR').textContent.slice(0,80)"))
    await pg.screenshot(path=f'{SHOTS}/x10-count-{sfx}.png'); await E("MK.back()"); await W(300)
    await pg.click('#stPro'); await W(300); await pg.screenshot(path=f'{SHOTS}/x11-offers-{sfx}.png'); await E("MK.back()"); await W(300)
    # history renders every type
    await E("go('hist')"); await W(300); print('hist rows', await E("$$('#hList .tx').length"))
    await pg.screenshot(path=f'{SHOTS}/x12-hist-{sfx}.png')
    print('month', await E("JSON.stringify((f=>({sales:f.sales,cogs:Math.round(f.cogs),byPay:f.byPay}))(monthFig(new Date().getFullYear(), new Date().getMonth())))"))
    print('ERR', errs)
    await b.close()

async def main():
  for lang, dark in [('ar', False), ('en', True)]:
    print('====', lang, dark); await run(lang, dark)
asyncio.run(main())

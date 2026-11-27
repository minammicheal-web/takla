import os
APP = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
SHOTS = os.environ.get('SHOTS', '/tmp/shots'); os.makedirs(SHOTS, exist_ok=True)
# Pharmacy tools: active ingredient + alternatives, shelf, Rx/schedule, printed public price, shortages,
# expiry report with return to supplier, prescription photo + doctor, insurance share and dues, chronic meds.
import asyncio
from playwright.async_api import async_playwright

async def run(lang, dark):
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, has_touch=True, color_scheme='dark' if dark else 'light')
    if lang == 'en': await ctx.add_init_script("localStorage.setItem('store-lang','en')")
    await ctx.add_init_script("window.__APP_ACT='pharmacy'")
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(APP); await pg.wait_for_timeout(500)
    E = pg.evaluate; W = pg.wait_for_timeout; sfx = f'{lang}-{"d" if dark else "l"}'
    X = lambda: E("document.querySelectorAll('.mdd-scrim').forEach(x=>x.remove()); closeModal()")
    await E("S.settings.autoReceipt=false; S.settings.margin=20")
    async def buy(name, sci, pub, exp, qty='1', cost='60', loc='', rx=False, tbl=False, sup='فارما'):
      await E("go('buy')"); await W(150); await pg.fill('#bSup', sup); await pg.click('#bNext'); await W(150)
      await pg.click('#bAddIt'); await W(300)
      await pg.fill('#aName', name); await pg.fill('#aSci', sci); await pg.fill('#aQty', qty); await pg.fill('#aCost', cost)
      if pub: await pg.fill('#aPub', pub)
      await pg.fill('#aExp', exp); await pg.fill('#aLoc', loc)
      if rx: await pg.check('#aRx')
      if tbl: await pg.check('#aTbl')
      await pg.screenshot(path=f'{SHOTS}/t1-add-{sfx}.png')
      await pg.click('.bal [data-ok]'); await W(250); await pg.click('#bSave'); await W(500); await X()
    await buy('بنادول إكسترا', 'Paracetamol', '75', '2027-05-01', loc='رف 3', rx=False)
    await buy('أبيمول', 'Paracetamol', '45', '2026-12-15', qty='2', cost='36', loc='رف 3')
    await buy('ترامادول', 'Tramadol', '90', '2027-02-01', cost='70', loc='الدرج المقفول', rx=True, tbl=True, sup='المتحدة')
    print('prices', await E("S.items.map(i=>i.name+':'+itemPriceText(i)+' rx'+(i.rx?1:0)+(i.tbl?1:0)+' '+itLoc(i)).join(' | ')"))
    # public price changes on the next purchase
    await E("go('buy')"); await W(150); await pg.click('#bNext'); await W(150); await pg.click('#bAddIt'); await W(300)
    await pg.fill('#aName', 'بنادول'); await W(200); await pg.click('#aSug [data-s]'); await W(300)
    print('pub prefill', await pg.input_value('#aPub'))
    await pg.fill('#aPub', '80'); await pg.fill('#aPrice', ''); await pg.fill('#aQty', '1'); await pg.fill('#aExp', '2027-06-01'); await W(100)
    print('pub hint', await pg.inner_text('#aPubH'))
    await pg.click('.bal [data-ok]'); await W(250); await pg.click('#bSave'); await W(1200)
    print('alert', await E("(document.querySelector('.mdd .mdd-body')||{}).innerText||''"))
    await X()
    print('panadol price', await E("itemPriceText(S.items[0])"))
    # search by active ingredient, alternatives when out of stock
    await E("go('sell')"); await W(150)
    print('search paracetamol', await E("findItems('paracet').map(i=>i.name).join(',')"))
    await E("(()=>{const it=S.items.find(i=>i.name==='أبيمول'); const v=it.variants[0]; S.txns.push({id:uid(),type:'sell',ts:Date.now()-1000,pay:'كاش',lines:[{itemId:it.id,vid:v.id,qty:C.V[v.id].stock,price:1,list:1}]}); persist(); $('#sItem').value=it.name; pickSell(it);})()"); await W(300)
    await pg.screenshot(path=f'{SHOTS}/t2-alt-{sfx}.png')
    print('alts', await E("$$('#sAlt [data-alt]').map(b=>b.innerText.replace(/\\n/g,' ')).join(' / ')"))
    await pg.click('#sShort'); await W(200)
    await pg.click('#sAlt [data-alt]'); await W(300)
    print('picked', await E("sSel && sSel.name"))
    # unknown name → shortage from the search box
    await pg.fill('#sItem', 'فيتامين سي فوار'); await W(300)
    await pg.click('.acbox [data-act="short"] >> visible=true'); await W(200)
    print('short', await E("S.settings.short.map(x=>x.name+'×'+x.n).join(', ')"))
    # insurance company
    await E("S.settings.ins=[{id:'i1',name:'مصر للتأمين',pct:70}]; persist()")
    # sale: tramadol (schedule) + panadol, insurance, doctor, credit
    await E("(()=>{const it=S.items.find(i=>i.name==='ترامادول'); $('#sItem').value=it.name; pickSell(it);})()"); await W(200); await pg.click('#sAdd'); await W(200)
    await E("(()=>{const it=S.items.find(i=>i.name==='بنادول إكسترا'); $('#sItem').value=it.name; pickSell(it);})()"); await W(200)
    await pg.click('#sUn [data-u="1"]'); await W(100); await pg.click('#sAdd'); await W(200)
    await pg.click('#sInsC [data-ins="i1"]'); await W(200)
    await pg.fill('#sDoc', 'د. أحمد'); await pg.fill('#sCust', 'أم علي'); await pg.fill('#sPhone', '01001234567')
    await pg.click('#sPayC [data-pay="آجل"]'); await W(150)
    print('ins info', await pg.inner_text('#sInsI'), '| rest', await pg.inner_text('#sRest'))
    await pg.screenshot(path=f'{SHOTS}/t3-cart-{sfx}.png', full_page=True)
    await pg.click('#sSave'); await W(400)
    print('confirm', await E("(document.querySelector('.mdd .mdd-body')||{}).innerText||''"))
    await pg.click('.mdd [data-a="1"]'); await W(500)
    t = await E("(()=>{const t=S.txns.filter(t=>t.type==='sell').slice(-1)[0]; return JSON.stringify({ins:t.ins,insAmt:t.insAmt,doc:t.doc,tot:saleTotal(t)})})()")
    print('sale', t, 'bal', await E("JSON.stringify(custBals())"))
    await E("openReceipt(S.txns.filter(t=>t.type==='sell').slice(-1)[0])"); await W(400)
    await pg.screenshot(path=f'{SHOTS}/t4-receipt-{sfx}.png', full_page=True); await X()
    print('wa', (await E("receiptText(S.txns.filter(t=>t.type==='sell').slice(-1)[0])")).replace('\n',' / ')[-260:])
    # insurance dues + payment
    await E("go('cust')"); await W(200); await pg.click('#cIns'); await W(300)
    await pg.screenshot(path=f'{SHOTS}/t5-ins-{sfx}.png', full_page=True)
    await pg.click('#sheet [data-inpay]'); await W(200); await pg.fill('#ipA', '50'); await pg.click('.mdd [data-ok]'); await W(300)
    print('ins due', await E("JSON.stringify(insDue())")); await X()
    # chronic medicine
    await E("openCustomer(S.customers.find(c=>c.name==='أم علي'))"); await W(300)
    await pg.fill('#mdN', 'بنادول إكسترا'); await pg.fill('#mdD', '1'); await pg.click('#mdAdd'); await W(300)
    await E("(()=>{const c=S.customers.find(c=>c.name==='أم علي'); c.meds[0].from=Date.now()-5*86400000; const s=S.txns.filter(t=>t.type==='sell').slice(-1)[0]; s.ts=Date.now()-5*86400000; persist(); openCustomer(c);})()"); await W(300)
    await pg.screenshot(path=f'{SHOTS}/t6-cust-{sfx}.png', full_page=True); await X()
    await E("go('cust')"); await W(200)
    print('due', await pg.inner_text('#cDue'))
    # expiry report + return to supplier
    await E("go('stock')"); await W(200); await pg.click('#stExp'); await W(300)
    await pg.click('#exM [data-m="6"]'); await W(300)
    await pg.screenshot(path=f'{SHOTS}/t7-exp-{sfx}.png', full_page=True)
    print('exp rows', await E("expRows(6).map(x=>x.r.it.name+' '+x.lot.exp+' '+x.sup+' '+x.lot.qty).join(' | ')"))
    await pg.click('#sheet [data-exret] >> nth=0'); await W(400)
    await pg.screenshot(path=f'{SHOTS}/t8-sret-{sfx}.png')
    await pg.click('.srd [data-ok]'); await W(500); await X()
    print('after return', await E("expRows(6).map(x=>x.r.it.name+' '+x.lot.qty).join(' | ')"))
    # shortages in planned orders
    await E("go('plan')"); await W(300)
    await pg.screenshot(path=f'{SHOTS}/t9-short-{sfx}.png', full_page=True)
    print('plan short', (await pg.inner_text('#plShort')).replace('\n',' / ')[:200])
    print('ERR', errs)
    await b.close()

async def main():
  for lang, dark in (('ar', False), ('en', True)):
    print('====', lang, dark); await run(lang, dark)
asyncio.run(main())

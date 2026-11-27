import os
APP = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
SHOTS = os.environ.get('SHOTS', '/tmp/shots'); os.makedirs(SHOTS, exist_ok=True)
import asyncio, json
from playwright.async_api import async_playwright
from helpers import buy_lines
STUB = """window.Android={scan:id=>setTimeout(()=>onScan(id,window.__scan||null,null),50),print:()=>{},openUrl:u=>{window.__url=u},shareText:()=>{},setIcon:k=>{window.__icon=k},setAlerts:j=>{window.__alerts=j}};"""
async def run(lang, dark):
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, has_touch=True, color_scheme='dark' if dark else 'light')
    await ctx.add_init_script(STUB + "window.__APP_ACT='';" + ("localStorage.setItem('store-lang','en');" if lang == 'en' else ''))
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
    await pg.goto(APP); await pg.wait_for_timeout(500)
    sfx = f'{lang}-{"d" if dark else "l"}'
    E = pg.evaluate
    print('icon at start', await E('window.__icon'), 'act', await E('S.settings.act'))
    await pg.screenshot(path=f'{SHOTS}/a0-empty-{sfx}.png')
    # open picker via settings
    await pg.click('#bSet'); await pg.wait_for_timeout(300); await pg.screenshot(path=f'{SHOTS}/a1-set-{sfx}.png')
    await pg.click('#tAct'); await pg.wait_for_timeout(500); await pg.screenshot(path=f'{SHOTS}/a2-pick-{sfx}.png')
    await pg.fill('#aQ', 'صيد' if lang == 'ar' else 'pharm'); await pg.wait_for_timeout(200); await pg.screenshot(path=f'{SHOTS}/a3-search-{sfx}.png')
    await pg.click('[data-aid=pharmacy]'); await pg.wait_for_timeout(500)
    print('act', await E('S.settings.act'), 'icon', await E('window.__icon'), 'title', await E("$('#ttl').textContent"))
    # buy a medicine with two batches
    await E("go('buy')"); await pg.wait_for_timeout(300)
    await E("buyStep(2)"); await pg.click('#bAddIt'); await pg.wait_for_timeout(350)
    print('expiry field', await E("!!$('#aExp')"), 'serial field', await E("!!$('#aSn')"))
    await pg.screenshot(path=f'{SHOTS}/a4-buy-{sfx}.png')
    await E("MK.back()"); await pg.wait_for_timeout(300)
    await buy_lines(pg, [{'name': 'Panadol', 'color': '500mg', 'size': 'أقراص' if lang == 'ar' else 'Tablets', 'qty': 10, 'cost': 40, 'exp': await E('ymd(Date.now()+20*DAY)'), 'batch': 'B1'}])
    print('lot1', await E("JSON.stringify(C.V[S.items[0].variants[0].id].lots.map(l=>[l.batch,l.qty]))"))
    # second batch later expiry (direct)
    await E("""(()=>{const it=S.items[0],v=it.variants[0]; S.txns.push({id:uid(),type:'buy',ts:Date.now()-1000,pay:'كاش',lines:[{itemId:it.id,vid:v.id,qty:5,cost:40,exp:ymd(Date.now()+400*DAY),batch:'B2'}]});
       S.txns.push({id:uid(),type:'buy',ts:Date.now()-900,pay:'كاش',lines:[{itemId:it.id,vid:v.id,qty:3,cost:40,exp:ymd(Date.now()-5*DAY),batch:'B0'}]}); persist();})()""")
    print('lots', await E("JSON.stringify(C.V[S.items[0].variants[0].id].lots.map(l=>[l.batch,l.qty]))"), 'EXP', await E('C.EXP.length'))
    # sell 5 -> should consume expired B0 (3) then B1 (2)
    await E("""(()=>{const it=S.items[0],v=it.variants[0]; S.txns.push({id:'s1',type:'sell',ts:Date.now(),tax:0,pay:'كاش',lines:[{itemId:it.id,vid:v.id,qty:5,price:52,list:52,disc:0}]}); persist();})()""")
    print('after sale', await E("JSON.stringify(C.V[S.items[0].variants[0].id].lots.map(l=>[l.batch,l.qty]))"))
    await E("""(()=>{const t=S.txns.find(x=>x.id==='s1'); S.txns.push({id:uid(),type:'ret',ref:'s1',ts:Date.now()+1000,tax:0,pay:'كاش',restock:true,lines:[{itemId:t.lines[0].itemId,vid:t.lines[0].vid,qty:1,price:52,list:52,li:0}]}); persist();})()""")
    print('after return', await E("JSON.stringify(C.V[S.items[0].variants[0].id].lots.map(l=>[l.batch,l.qty]))"))
    print('alerts', await E("window.__alerts"))
    await E("go('stock')"); await pg.wait_for_timeout(300); await pg.click('#stList .ihead'); await pg.wait_for_timeout(300)
    await pg.screenshot(path=f'{SHOTS}/a6-stock-{sfx}.png', full_page=True)
    await E("go('sell')"); await pg.fill('#sItem', 'Panad'); await pg.wait_for_timeout(300); await pg.click('#pg-sell .aci >> nth=0'); await pg.wait_for_timeout(300)
    await pg.screenshot(path=f'{SHOTS}/a7-sell-{sfx}.png', full_page=True)

    # ---- mobiles: serials ----
    await E("S.settings.act='mobiles'; S.settings.actCfg={}; persist()"); await pg.wait_for_timeout(200)
    print('icon', await E('window.__icon'))
    await E("go('buy')"); await pg.wait_for_timeout(200)
    await buy_lines(pg, [{'name': 'Galaxy A55', 'color': 'أسود' if lang == 'ar' else 'Black', 'size': '256GB', 'qty': 3, 'cost': 15000, 'sn': '3567001\n3567002\n3567003'}])
    print('sns', await E("JSON.stringify(Object.values(C.V).filter(r=>r.sns.length).map(r=>r.sns))"))
    # sell by scanning a serial
    await E("go('sell')"); await E("window.__scan='3567002'"); await E("""(()=>{const i=$('#sItem'); i.value='3567002'; i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter'}))})()""")
    await pg.wait_for_timeout(300)
    print('picked sn', await E("JSON.stringify([...pickSn])"), 'qty', await E("$('#sQty')&&$('#sQty').value"))
    await pg.screenshot(path=f'{SHOTS}/a9-sellsn-{sfx}.png', full_page=True)
    await pg.click('#sAdd'); await pg.wait_for_timeout(200)
    await E("sCust='Ali'"); await pg.click('#sSave'); await pg.wait_for_timeout(600)
    t = await E("JSON.stringify(S.txns[S.txns.length-1].lines)")
    print('sale lines', t)
    await pg.screenshot(path=f'{SHOTS}/a10-receipt-{sfx}.png')
    print(await E("receiptText(S.txns[S.txns.length-1])"))
    await E("$$('.mdd [data-x]').forEach(b=>b.click())"); await pg.wait_for_timeout(300)
    # search by serial
    await pg.click('#bSearch'); await pg.wait_for_timeout(300); await pg.fill('#qIn', '3567002'); await pg.wait_for_timeout(300)
    await pg.screenshot(path=f'{SHOTS}/a11-snsearch-{sfx}.png')
    await E("closeModal()")
    # return the phone
    await E("openReturn(S.txns.filter(t=>t.type==='sell').pop())"); await pg.wait_for_timeout(300)
    await E("(()=>{const r=retRows(RT.t)[0]; RT.q[r.key]=1; RT.why[r.key]='mind'; renderRet();})()"); await pg.click('#rSave'); await pg.wait_for_timeout(500)
    await E("$$('.mdd [data-x]').forEach(b=>b.click())"); await pg.wait_for_timeout(300)
    print('ret lines', await E("JSON.stringify(S.txns[S.txns.length-1].lines)"), 'sns now', await E("JSON.stringify(Object.values(C.V).filter(r=>r.sns.length).map(r=>r.sns))"))
    # fields editor + groceries decimals
    await pg.click('#bSet'); await pg.wait_for_timeout(200); await pg.click('#tActF'); await pg.wait_for_timeout(400)
    await pg.screenshot(path=f'{SHOTS}/a12-fields-{sfx}.png', full_page=True)
    await E("closeModal(); S.settings.act='vegetables'; S.settings.actCfg={}; persist()")
    await buy_lines(pg, [{'name': 'Tomato', 'color': 'Local', 'qty': '12.5', 'cost': 8}])
    print('veg stock', await E("itemStock(S.items.find(i=>i.name==='Tomato'))"), 'unit', await E("unitOf(S.items.find(i=>i.name==='Tomato'))"))
    await E("go('stock')"); await pg.wait_for_timeout(300); await pg.screenshot(path=f'{SHOTS}/a13-veg-{sfx}.png', full_page=True)
    print('ERR', errs)
    await b.close()
async def main():
  await run('ar', False)
  await run('en', True)
asyncio.run(main())

import os
APP = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
SHOTS = os.environ.get('SHOTS', '/tmp/shots'); os.makedirs(SHOTS, exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    ctx=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True)
    pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m: m.type=='error' and errs.append(m.text))
    await pg.goto(APP)
    await pg.evaluate("""()=>{S.settings.autoReceipt=false;const it=newItem('بنطلون جينز'); S.items.push(it); const v=newVariant(it,'كحلي','32');
      S.txns.push({id:uid(),type:'buy',ts:Date.now()-86400000,lines:[{itemId:it.id,vid:v.id,qty:10,cost:200}],pay:'كاش'});
      const c=custFor('أم أحمد','01001234567'); S.txns.push({id:uid(),type:'sell',ts:Date.now(),tax:0,pay:CREDIT,paid:100,cid:c.id,cname:c.name,lines:[{itemId:it.id,vid:v.id,qty:2,price:300,list:300,disc:0}]}); persist();}""")
    await pg.wait_for_timeout(400); await pg.screenshot(path=SHOTS+'/l1-ar.png')
    # settings: Arabic store name -> header stays right
    await pg.click('#bSet'); await pg.wait_for_timeout(300); await pg.screenshot(path=SHOTS+'/l2-set.png')
    await pg.fill('#tShop','داي فيت'); await pg.click('#tSave'); await pg.wait_for_timeout(300)
    print('ar name dir', await pg.evaluate("$('#top header').getAttribute('dir')"), await pg.evaluate("$('#ttl').textContent"))
    await pg.screenshot(path=SHOTS+'/l3-arname.png')
    await pg.click('#bSet'); await pg.fill('#tShop','DayFit'); await pg.click('#tSave'); await pg.wait_for_timeout(300)
    await pg.screenshot(path=SHOTS+'/l4-enname.png')
    # switch to English
    await pg.click('#bSet'); await pg.wait_for_timeout(200)
    await pg.click('#tLang [data-l=en]'); await pg.wait_for_load_state('load'); await pg.wait_for_timeout(800)
    print('lang', await pg.evaluate("document.documentElement.dir+' '+LANG"))
    for t in ['stock','sell','buy','plan','cust','exp','hist']:
      await pg.evaluate(f"go('{t}')"); await pg.wait_for_timeout(450)
      if t=='hist': await pg.click('#hList .tx >> nth=0')
      await pg.screenshot(path=f'{SHOTS}/e-{t}.png', full_page=True)
    left = await pg.evaluate("""(()=>{const out=new Set();const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;while(n=w.nextNode()){if(/[\\u0600-\\u06FF]/.test(n.data)&&n.parentElement.offsetParent!==null)out.add(n.data.trim())}return [...out]})()""")
    print('arabic left visible:', left[:40])
    await pg.click('#bSet'); await pg.wait_for_timeout(300); await pg.screenshot(path=SHOTS+'/e-set.png', full_page=True)
    await pg.evaluate("closeModal(); openReceipt(S.txns.find(t=>t.type==='sell'))"); await pg.wait_for_timeout(300); await pg.screenshot(path=SHOTS+'/e-rc.png')
    print(await pg.evaluate("receiptText(S.txns.find(t=>t.type==='sell'))"))
    await pg.evaluate("$$('.mdd [data-x]').forEach(b=>b.click())"); await pg.wait_for_timeout(300)
    await pg.evaluate("go('exp')"); await pg.click('[data-dt=xDate]'); await pg.wait_for_timeout(400); await pg.screenshot(path=SHOTS+'/e-date.png')
    await pg.keyboard.press('Escape')
    print('ERR', errs)
    await b.close()
asyncio.run(main())

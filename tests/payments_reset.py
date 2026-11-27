import os
APP = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
SHOTS = os.environ.get('SHOTS', '/tmp/shots'); os.makedirs(SHOTS, exist_ok=True)
import asyncio, json
from playwright.async_api import async_playwright
SWIPE = """(dx)=>{const el=document.querySelector('#pg-'+page+' .card, #pg-'+page+' .stat, #pg-'+page+' .empty, #pg-'+page+' .item')||document.querySelector('#pg-'+page);
 const mk=(x,y)=>new Touch({identifier:1,target:el,clientX:x,clientY:y});
 el.dispatchEvent(new TouchEvent('touchstart',{bubbles:true,touches:[mk(200,400)],changedTouches:[mk(200,400)]}));
 el.dispatchEvent(new TouchEvent('touchmove',{bubbles:true,touches:[mk(200+dx/2,402)],changedTouches:[mk(200+dx/2,402)]}));
 el.dispatchEvent(new TouchEvent('touchmove',{bubbles:true,touches:[mk(200+dx,403)],changedTouches:[mk(200+dx,403)]}));
 el.dispatchEvent(new TouchEvent('touchend',{bubbles:true,touches:[],changedTouches:[mk(200+dx,403)]})); return page;}"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    ctx=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True)
    pg=await ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m: m.type=='error' and errs.append(m.text))
    await pg.goto(APP); await pg.evaluate('S.settings.autoReceipt=false')
    # seed: items, buys on two days, sales
    await pg.evaluate("""()=>{const it=newItem('قميص'); S.items.push(it); const v=newVariant(it,'أحمر','M');
      const y=Date.now()-86400000;
      S.txns.push({id:uid(),type:'buy',ts:y,lines:[{itemId:it.id,vid:v.id,qty:10,cost:100}],pay:'كاش'});
      S.txns.push({id:uid(),type:'buy',ts:Date.now()-1000,lines:[{itemId:it.id,vid:v.id,qty:5,cost:100}],pay:'فيزا'});
      S.expenses.push({id:uid(),ts:y,cat:'إيجار',amount:3000}); S.expenses.push({id:uid(),ts:Date.now(),cat:'مواصلات',amount:50}); persist();}""")
    # sell with instapay
    await pg.click('nav button[data-p=sell]')
    await pg.type('#sItem','قميص'); await pg.wait_for_timeout(150); await pg.click('#pg-sell .aci'); await pg.fill('#sQty','3'); await pg.click('#sAdd')
    await pg.click('#sPayC [data-pay="إنستاباي"]'); await pg.wait_for_timeout(100)
    await pg.screenshot(path=SHOTS+'/40-sellpay.png', full_page=True)
    await pg.click('#sSave')
    print('pay saved', await pg.evaluate("S.txns.filter(t=>t.type==='sell').map(t=>t.pay)"), await pg.evaluate("S.settings.sellPay"))
    # swipe tests: from sell, swipe right -> buy ; swipe left -> sell; from stock swipe left (edge) stays
    print('swipe right ->', await pg.evaluate(SWIPE, 150)); print('swipe left ->', await pg.evaluate(SWIPE, -150))
    await pg.click('nav button[data-p=stock]'); print('edge swipe left ->', await pg.evaluate(SWIPE, -150))
    await pg.click('nav button[data-p=buy]'); await pg.wait_for_timeout(400)
    await pg.mouse.move(195,800)
    await pg.screenshot(path=SHOTS+'/41-buy.png')
    # report
    await pg.click('nav button[data-p=exp]'); print('report', (await pg.inner_text('#xReport')).replace('\n',' | ')[:260])
    # reset: sell records only today
    await pg.click('#bSet'); await pg.click('#tReset'); await pg.wait_for_timeout(200)
    await pg.click('.mdd [data-sc=day]'); await pg.click('.mdd label.radio:has(input[value=exp])')
    await pg.wait_for_timeout(100); await pg.screenshot(path=SHOTS+'/42-reset.png')
    print('reset preview', await pg.inner_text('.mdd .warn, .mdd .note'))
    await pg.click('.mdd [data-go]'); await pg.wait_for_timeout(250); await pg.screenshot(path=SHOTS+'/43-confirm.png')
    await pg.click('.mdd [data-a="1"]'); await pg.wait_for_timeout(300)
    print('after exp-day reset', await pg.evaluate("S.expenses.map(e=>e.cat)"))
    # reset buys all -> negative warning
    await pg.click('#bSet'); await pg.click('#tReset'); await pg.wait_for_timeout(200)
    await pg.click('.mdd label.radio:has(input[value=buy])'); await pg.click('.mdd [data-go]'); await pg.wait_for_timeout(250)
    print('neg warn shown', 'بالسالب' in await pg.inner_text('.mdd-scrim:last-of-type .mdd'))
    await pg.click('.mdd-scrim:last-of-type [data-a="0"]'); await pg.wait_for_timeout(250)
    # everything
    await pg.click('.mdd label.radio:has(input[value=everything])'); await pg.click('.mdd [data-go]'); await pg.wait_for_timeout(250)
    await pg.click('.mdd-scrim:last-of-type [data-a="1"]'); await pg.wait_for_timeout(300)
    print('after everything', await pg.evaluate("[S.items.length,S.txns.length,S.expenses.length]"), await pg.inner_text('#toast'))
    print('errors', errs)
    # tablet
    for w,h,n in ((1280,800,'44-tab-land'),(800,1280,'45-tab-port')):
      t=await b.new_page(viewport={'width':w,'height':h})
      await t.goto(APP)
      await t.evaluate("""()=>{for(const [n,c] of [['قميص كاروه','أحمر'],['بنطلون جينز','أزرق'],['جاكيت','أسود'],['بلوزة','أبيض']]){const it=newItem(n);S.items.push(it);const v=newVariant(it,c,'M');v.safety=5;
        S.txns.push({id:uid(),type:'buy',ts:Date.now()-5*86400000,lines:[{itemId:it.id,vid:v.id,qty:12,cost:150}],pay:'كاش'});
        S.txns.push({id:uid(),type:'sell',ts:Date.now()-3600000,lines:[{itemId:it.id,vid:v.id,qty:8,price:200}],pay:'فيزا'});} persist();}""")
      await t.wait_for_timeout(300); await t.screenshot(path=f'{SHOTS}/{n}.png')
      await t.click('nav button[data-p=sell]'); await t.wait_for_timeout(300); await t.screenshot(path=f'{SHOTS}/{n}-sell.png')
      await t.close()
    await b.close()
asyncio.run(main())

import os
APP = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
SHOTS = os.environ.get('SHOTS', '/tmp/shots'); os.makedirs(SHOTS, exist_ok=True)
import asyncio, json
from playwright.async_api import async_playwright
from helpers import buy_lines
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    pg=await b.new_page(viewport={'width':390,'height':844},device_scale_factor=2)
    errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m: m.type=='error' and errs.append(m.text))
    pg.on('dialog',lambda d: asyncio.ensure_future(d.accept()))
    # old-format data to check migration
    await pg.goto(APP); await pg.evaluate('S.settings.autoReceipt=false')
    await pg.evaluate("localStorage.setItem('store-v1', JSON.stringify({v:1,items:[],txns:[],seq:0,ordered:{},settings:{margin:30,round:5,forecastDays:30,coverDays:30,lead:7,soonDays:7,autoReceipt:false}}))")
    await pg.reload()
    print('migrated rnd', await pg.evaluate("JSON.stringify(S.settings.rnd)"), await pg.evaluate("'expenses' in S"))
    # settings: rounding up to 0.5
    await pg.click('#bSet'); await pg.evaluate("$('#tRound').value='up0.5'"); await pg.fill('#tMargin','25'); await pg.click('#tSave')
    print('roundP', await pg.evaluate("[roundP(400.25),roundP(400.6),roundP(400.5),roundP(401)]"))
    # buy with 14% tax: 10 pcs at 300 -> unit 342 -> *1.25 = 427.5
    await buy_lines(pg, [{'name': 'بلوزة', 'color': 'أبيض', 'qty': 10, 'cost': 300}], tax=14, close_labels=False)
    print('buycalc', await pg.evaluate("C.V[S.items[0].variants[0].id].avg"))
    await pg.evaluate("$$('.lbd [data-x]').forEach(b=>b.click())"); await pg.wait_for_timeout(300)
    print('bTax kept', await pg.input_value('#bTax'))
    # sell: discount 10% -> 427.5*0.9 = 384.75 -> 385 ; then second line by net price 400
    await pg.click('nav button[data-p=sell]')
    await pg.type('#sItem','بلوز'); await pg.wait_for_timeout(150); await pg.click('#pg-sell .aci')
    print('price', await pg.input_value('#sPrice'))
    await pg.fill('#sQty','2'); await pg.fill('#sDisc','10'); await pg.dispatch_event('#sDisc','input')
    print('net', await pg.input_value('#sNet'))
    await pg.click('#sAdd')
    await pg.type('#sItem','بلوز'); await pg.wait_for_timeout(150); await pg.click('#pg-sell .aci')
    await pg.fill('#sNet','400'); await pg.dispatch_event('#sNet','input')
    print('disc', await pg.input_value('#sDisc'))
    await pg.click('#sAdd')
    await pg.fill('#sTax','14'); await pg.dispatch_event('#sTax','input'); await pg.fill('#sNote','عميل')
    await pg.screenshot(path=SHOTS+'/20-cart.png',full_page=True)
    print('cart', (await pg.inner_text('#sTot')).replace('\n',' | '))
    await pg.click('#sSave')
    # expenses
    await pg.click('nav button[data-p=exp]')
    for cat,amt in [('إيجار','3000'),('مواصلات','50'),('مواصلات','70')]:
      await pg.click(f'#xCats [data-c="{cat}"]'); await pg.fill('#xAmt',amt); await pg.click('#xSave')
    await pg.click('#xCats [data-c="أخرى"]'); await pg.fill('#xOther','صيانة'); await pg.fill('#xAmt','100'); await pg.click('#xSave')
    print('report', (await pg.inner_text('#xReport')).replace('\n',' | '))
    await pg.screenshot(path=SHOTS+'/21-exp.png',full_page=True)
    await pg.click('nav button[data-p=hist]'); await pg.click('#hList .tx'); await pg.screenshot(path=SHOTS+'/22-hist.png',full_page=True)
    await pg.click('nav button[data-p=stock]'); await pg.screenshot(path=SHOTS+'/23-stock.png')
    await pg.click('#bSet'); await pg.screenshot(path=SHOTS+'/24-set.png',full_page=True)
    print('errors',errs)
    await b.close()
asyncio.run(main())

import os
APP = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
SHOTS = os.environ.get('SHOTS', '/tmp/shots'); os.makedirs(SHOTS, exist_ok=True)
import asyncio, json
from playwright.async_api import async_playwright
from helpers import buy_lines
INIT = "window.SYNC_HOSTS={id:'http://127.0.0.1:8765',tok:'http://127.0.0.1:8765',fs:'http://127.0.0.1:8765'};"
async def phone(b, errs, name):
    ctx = await b.new_context(viewport={'width':390,'height':844}, device_scale_factor=2)
    await ctx.add_init_script(INIT)
    pg = await ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(name+': '+str(e)))
    pg.on('console', lambda m: m.type=='error' and errs.append(name+': '+m.text))
    await pg.goto(APP); await pg.evaluate('S.settings.autoReceipt=false')
    return pg
async def buy(pg, name, color, qty, price):
    await buy_lines(pg, [{'name': name, 'color': color, 'qty': qty, 'cost': price}])
async def sell(pg, q, qty):
    await pg.click('nav button[data-p=sell]')
    await pg.type('#sItem', q); await pg.wait_for_timeout(150); await pg.click('#pg-sell .aci')
    await pg.fill('#sQty', str(qty)); await pg.click('#sAdd'); await pg.click('#sSave')
async def state(pg):
    return await pg.evaluate("JSON.stringify({items:S.items.map(i=>i.serial+' '+i.name), stock:Object.values(C.V).map(r=>r.v.serial+':'+r.stock), txns:S.txns.length, by:S.txns.map(t=>t.by), exp:S.expenses.length, err:syState.err})")
async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    errs = []
    A = await phone(b, errs, 'A'); B = await phone(b, errs, 'B')
    # A creates shop
    await A.click('#bSet'); await A.click('#tSync'); await A.wait_for_timeout(200)
    await A.fill('#yUser', 'مينا'); await A.click('#ySeg [data-m=new]')
    await A.fill('#yShop', 'محل مينا'); await A.fill('#yP', 'P'); await A.fill('#yK', 'KEY'); await A.click('#yGo')
    await A.wait_for_timeout(800); await A.screenshot(path=SHOTS+'/30-synced.png')
    code = await A.evaluate('syCode()')
    await A.click('[data-close]')
    await buy(A, 'قميص', 'أحمر', 10, 100)
    await sell(A, 'قميص', 2)
    await A.wait_for_timeout(2500)
    print('A', await state(A))
    # B joins
    await B.click('#bSet'); await B.click('#tSync'); await B.wait_for_timeout(200)
    await B.fill('#yUser', 'الموظف'); await B.fill('#yCode', code); await B.click('#yGo'); await B.wait_for_timeout(1200)
    print('B joined', await state(B), await B.evaluate('SY.shopName'))
    await sell(B, 'قميص', 3)
    await B.evaluate("S.expenses.push({id:uid(),ts:Date.now(),cat:'مواصلات',amount:40,by:SY.user}); persist()")
    await B.wait_for_timeout(2500)
    await A.evaluate('syncNow()'); await A.wait_for_timeout(800)
    print('A after B', await state(A))
    # offline conflict: both add new item -> same serial
    await A.evaluate("SY._k=SY.k; window._h=HOSTS.fs; HOSTS.fs='http://127.0.0.1:1'"); await B.evaluate("HOSTS.fs='http://127.0.0.1:1'")
    await buy(A, 'بنطلون', 'أزرق', 5, 200); await buy(B, 'جاكيت', 'أسود', 4, 500)
    await A.wait_for_timeout(2500)
    print('A offline err:', await A.evaluate('syState.err'))
    await A.evaluate("HOSTS.fs=window._h"); await B.evaluate("HOSTS.fs='http://127.0.0.1:8765'")
    await A.evaluate('syncNow()'); await A.wait_for_timeout(800); await B.evaluate('syncNow()'); await B.wait_for_timeout(800); await A.evaluate('syncNow()'); await A.wait_for_timeout(800)
    sa, sb = await state(A), await state(B)
    print('A', sa); print('B', sb); print('same:', json.loads(sa)['items'] == json.loads(sb)['items'] or sorted(json.loads(sa)['items'])==sorted(json.loads(sb)['items']), sorted(json.loads(sa)['stock'])==sorted(json.loads(sb)['stock']))
    # delete txn on A propagates
    await A.evaluate("S.txns = S.txns.filter(t=>!(t.type==='sell' && t.by==='الموظف')); persist()"); await A.wait_for_timeout(2500)
    await B.evaluate('syncNow()'); await B.wait_for_timeout(800)
    print('B after delete', await state(B))
    print('errors', errs)
    await b.close()
if __name__ == "__main__": asyncio.run(main())

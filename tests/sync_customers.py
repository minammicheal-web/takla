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
async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    errs = []
    A = await phone(b, errs, 'A'); B = await phone(b, errs, 'B')
    await A.click('#bSet'); await A.click('#tSync'); await A.wait_for_timeout(200)
    await A.fill('#yUser', 'مينا'); await A.click('#ySeg [data-m=new]')
    await A.fill('#yShop', 'DayFit'); await A.fill('#yP', 'P'); await A.fill('#yK', 'KEY'); await A.click('#yGo'); await A.wait_for_timeout(800)
    code = await A.evaluate('syCode()'); await A.click('[data-close]')
    await buy(A, 'بنطلون', 'أسود', 10, 200)
    await A.evaluate("""()=>{const it=S.items[0],v=it.variants[0]; const c=custFor('أم أحمد','01001234567');
      const t={id:uid(),type:'sell',ts:Date.now(),tax:0,pay:CREDIT,paid:100,cid:c.id,cname:c.name,by:who(),lines:[{itemId:it.id,vid:v.id,qty:2,price:300,list:300,disc:0}]};
      S.txns.push(t); S.txns.push({id:uid(),type:'ret',ts:Date.now()+1000,ref:t.id,tax:0,pay:CREDIT,restock:true,cid:c.id,cname:c.name,by:who(),lines:[{itemId:it.id,vid:v.id,qty:1,price:300,list:300,li:0}]});
      S.cpay.push({id:uid(),cid:c.id,ts:Date.now(),amount:50,pay:'كاش'}); persist();}""")
    await A.wait_for_timeout(2500)
    await B.click('#bSet'); await B.click('#tSync'); await B.wait_for_timeout(200)
    await B.fill('#yUser', 'سارة'); await B.fill('#yCode', code); await B.click('#yGo'); await B.wait_for_timeout(1500)
    q = "JSON.stringify({bal:custBals(), stock:Object.values(C.V).map(r=>r.stock), cp:S.cpay.length, users:S.users.length, login:$('#login').style.display, err:syState.err})"
    print('B', await B.evaluate(q))
    # A adds an owner user -> B must show the PIN screen
    await A.evaluate("()=>{const u={id:uid(),name:'مينا',role:'owner',perms:{}}; u.pin=pinH(u,'1234'); S.users.push(u); curUid=u.id; persist();}")
    await A.wait_for_timeout(2500); await B.evaluate('syncNow()'); await B.wait_for_timeout(1000)
    print('B after users', await B.evaluate(q))
    print('errors', errs)
    await b.close()
asyncio.run(main())

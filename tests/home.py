import os
APP = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
SHOTS = os.environ.get('SHOTS', '/tmp/shots'); os.makedirs(SHOTS, exist_ok=True)
# Home tab (logo, name, date, time, new-transaction button), Stock as the last tab, hold an item to delete it.
import asyncio
from playwright.async_api import async_playwright

async def run(lang, dark):
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, has_touch=True, color_scheme='dark' if dark else 'light')
    if lang == 'en': await ctx.add_init_script("localStorage.setItem('store-lang','en')")
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(APP); await pg.wait_for_timeout(500)
    E = pg.evaluate; sfx = f'{lang}-{"d" if dark else "l"}'
    print('page', await E('page'), 'tabs', await E('TABS.join()'), 'time', await E("$('#hmTime').textContent"), 'name', await E("$('#hmName').textContent"))
    await pg.screenshot(path=f'{SHOTS}/h0-home-{sfx}.png')
    await pg.click('#hmAdd'); await pg.wait_for_timeout(450); await pg.screenshot(path=f'{SHOTS}/h1-pick-{sfx}.png')
    await pg.click('.hm-op[data-op=buy]'); await pg.wait_for_timeout(300); print('after pick', await E('page'))
    # two items, one with a purchase
    await E("""(()=>{const a=newItem('بلوزة'); S.items.push(a); newVariant(a,'أحمر',''); const c=newItem('بنطلون جينز'); S.items.push(c); const v=newVariant(c,'كحلي','');
      S.txns.push({id:uid(),type:'buy',ts:Date.now(),pay:'كاش',lines:[{itemId:c.id,vid:v.id,qty:2,cost:100}]}); persist(); go('stock');})()""")
    await pg.wait_for_timeout(300); print('stock is last', await E("[...$$('#nav button')].filter(b=>b.style.display!=='none').pop().dataset.p"))
    # hold the first card
    card = pg.locator('#stList .item').filter(has_text='بلوزة').locator('.ihead')
    bb = await card.bounding_box(); x, y = bb['x'] + 40, bb['y'] + 20
    await pg.mouse.move(x, y); await pg.mouse.down(); await pg.wait_for_timeout(650); await pg.mouse.up(); await pg.wait_for_timeout(400)
    print('menu open', await E("!!document.querySelector('.lpm')"), 'card toggled', await E("$$('#stList .item.open').length"))
    await pg.screenshot(path=f'{SHOTS}/h2-menu-{sfx}.png')
    await pg.click('.lpm [data-m=del]'); await pg.wait_for_timeout(400); await pg.screenshot(path=f'{SHOTS}/h3-confirm-{sfx}.png')
    await pg.click('.mdd .dan'); await pg.wait_for_timeout(400)
    print('items', await E("S.items.map(i=>i.name).join()"))
    # used item: refuses with a toast
    card = pg.locator('#stList .item').first.locator('.ihead'); bb = await card.bounding_box()
    await pg.mouse.move(bb['x'] + 40, bb['y'] + 20); await pg.mouse.down(); await pg.wait_for_timeout(650); await pg.mouse.up(); await pg.wait_for_timeout(400)
    await pg.click('.lpm [data-m=del]'); await pg.wait_for_timeout(300)
    print('items after used delete', await E("S.items.map(i=>i.name).join()"), 'toast', await E("(document.querySelector('.toast,#toast')||{}).textContent"))
    # a plain tap still opens the card
    await pg.wait_for_timeout(500); await pg.click('#stList .item .ihead'); await pg.wait_for_timeout(300); print('tap opens', await E("$$('#stList .item.open').length"))
    await E("MK.home()"); await pg.wait_for_timeout(300); print('home after MK.home', await E('page'))
    print('ERR', errs)
    await b.close()

async def main():
  await run('ar', False)
  await run('en', True)
asyncio.run(main())

import os
APP = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
SHOTS = os.environ.get('SHOTS', '/tmp/shots'); os.makedirs(SHOTS, exist_ok=True)
# Pharmacy pack units: buy by box, price per strip, sell box/strip/tablet and sachets, stock in units, receipt, returns by strip,
# scan a new box code to register it, then buy and sell it by scanning.
import asyncio
from playwright.async_api import async_playwright

async def run(lang, dark):
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, has_touch=True, color_scheme='dark' if dark else 'light')
    if lang == 'en': await ctx.add_init_script("localStorage.setItem('store-lang','en')")
    await ctx.add_init_script("window.__APP_ACT='pharmacy'; window.__scanQ=[]; window.Android={scan:id=>setTimeout(()=>onScan(id, window.__scanQ.shift()),20)}")
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(APP); await pg.wait_for_timeout(500)
    E = pg.evaluate; W = pg.wait_for_timeout; sfx = f'{lang}-{"d" if dark else "l"}'
    await E("S.settings.autoReceipt=false; S.settings.margin=25")
    # ---- purchase: scan a new box code
    await E("go('buy')"); await W(200); await pg.fill('#bSup', 'الشركة المصرية'); await pg.click('#bNext'); await W(200)
    await E("__scanQ.push('6221234567890')"); await pg.click('#bScanIt'); await W(500)
    print('code prefilled', await pg.input_value('#aCode'))
    await pg.fill('#aName', 'بنادول إكسترا'); await pg.fill('#aType', 'مسكن'); await pg.fill('#aColor', '500mg'); await pg.fill('#aSize', 'أقراص')
    await pg.fill('#aQty', '2'); await pg.fill('#aCost', '60')
    await pg.click('#aPU [data-pu="1"]'); await W(100); await pg.fill('#aPrice', '25')
    await pg.fill('#aExp', '2027-03-01'); await pg.fill('#aBatch', 'B1')
    print('hint', await pg.inner_text('#aPkH'))
    await pg.screenshot(path=f'{SHOTS}/u1-add-{sfx}.png')
    await pg.click('.bal [data-ok]'); await W(300)
    # sachets: box of 10
    await pg.click('#bAddIt'); await W(300)
    await pg.fill('#aName', 'فوار ملح فواكه'); await E("(()=>{const s=document.querySelector('#aPack'); s.value='4'; s.dispatchEvent(new Event('change'))})()"); await W(100)
    await pg.fill('[data-pn="0"]', '12'); await pg.fill('#aQty', '1'); await pg.fill('#aCost', '48'); await pg.fill('#aPrice', '60')
    print('hint2', await pg.inner_text('#aPkH'))
    await pg.click('.bal [data-ok]'); await W(300)
    await pg.screenshot(path=f'{SHOTS}/u2-lines-{sfx}.png')
    await pg.click('#bSave'); await W(600)
    await E("document.querySelectorAll('.mdd-scrim').forEach(x=>x.remove()); closeModal()")
    # second purchase of the same box by scanning, older expiry
    await E("go('buy')"); await W(200); await pg.click('#bNext'); await W(200)
    await E("__scanQ.push('6221234567890')"); await pg.click('#bScanIt'); await W(500)
    print('existing', await pg.inner_text('#aEx'), '| cost', await pg.input_value('#aCost'), '| price', await pg.input_value('#aPrice'))
    await pg.fill('#aQty', '1'); await pg.fill('#aExp', '2026-12-20'); await pg.fill('#aBatch', 'B0')
    await pg.click('.bal [data-ok]'); await W(300); await pg.click('#bSave'); await W(600)
    await E("document.querySelectorAll('.mdd-scrim').forEach(x=>x.remove()); closeModal()")
    print('stock', await E("S.items.map(i=>i.name+': '+pkTxt(i,i.variants[0],C.V[i.variants[0].id].stock)+' / '+C.V[i.variants[0].id].stock+' '+baseU(i,i.variants[0])+' / '+itemPriceText(i)).join(' | ')"))
    # ---- sell by scanning: 1 strip + 3 tablets + 1 box, and 2 sachets
    await E("go('sell')"); await W(200)
    await E("__scanQ.push('6221234567890')"); await pg.click('#sItem ~ .scanb'); await W(400)
    await pg.screenshot(path=f'{SHOTS}/u3-sell-{sfx}.png')
    await pg.click('#sUn [data-u="1"]'); await W(100); await pg.fill('#sQty', '1'); await pg.click('#sAdd'); await W(200)
    await E("__scanQ.push('6221234567890')"); await pg.click('#sItem ~ .scanb'); await W(400)
    await pg.click('#sUn [data-u="2"]'); await W(100); await pg.fill('#sQty', '3'); await pg.click('#sAdd'); await W(200)
    await E("__scanQ.push('6221234567890')"); await pg.click('#sItem ~ .scanb'); await W(400)
    await pg.click('#sUn [data-u="0"]'); await W(100); await pg.click('#sAdd'); await W(200)
    await pg.fill('#sItem', 'فوار'); await W(300); await pg.click('.acbox .aci >> visible=true'); await W(300)
    await pg.click('#sUn [data-u="1"]'); await W(100); await pg.fill('#sQty', '2'); await pg.click('#sAdd'); await W(200)
    await pg.screenshot(path=f'{SHOTS}/u4-cart-{sfx}.png', full_page=True)
    print('cart', await E("cart.map(l=>l.qty+'@'+l.price.toFixed(3)+' '+(l.pu||'')).join(', ')"), 'total', await E("cart.reduce((s,l)=>s+l.qty*l.price,0)"))
    await pg.click('#sSave'); await W(500)
    t = await E("S.txns.filter(t=>t.type==='sell').slice(-1)[0].id")
    print('lots after sale', await E("C.V[S.items[0].variants[0].id].lots.map(l=>l.batch+':'+l.qty).join(' ')"))
    print('stock', await E("S.items.map(i=>pkTxt(i,i.variants[0],C.V[i.variants[0].id].stock)).join(' | ')"))
    await E(f"openReceipt(S.txns.find(x=>x.id==='{t}'))"); await W(400)
    await pg.screenshot(path=f'{SHOTS}/u5-receipt-{sfx}.png', full_page=True)
    print('wa', (await E(f"receiptText(S.txns.find(x=>x.id==='{t}'))"))[:400].replace('\n',' / '))
    await E("closeModal(); document.querySelectorAll('.mdd-scrim').forEach(x=>x.remove())")
    # ---- return one strip
    await E(f"openReturn(S.txns.find(x=>x.id==='{t}'))"); await W(400)
    await E("document.querySelector('#rBody [data-ck]').click()"); await W(200)
    print('ret q', await E("JSON.stringify(RT.q)"))
    await pg.screenshot(path=f'{SHOTS}/u6-return-{sfx}.png', full_page=True)
    # ---- stock page
    await E("go('stock')"); await W(300); await E("document.querySelector('#stList .ihead').click()"); await W(200)
    await pg.screenshot(path=f'{SHOTS}/u7-stock-{sfx}.png', full_page=True)
    # ---- unknown code in sell → register
    await E("go('sell')"); await W(200)
    await E("__scanQ.push('6229999999999')"); await pg.click('#sItem ~ .scanb'); await W(400)
    await pg.screenshot(path=f'{SHOTS}/u8-newcode-{sfx}.png')
    await pg.click('.mdd [data-a="1"]'); await W(600)
    print('page', await E("page"), 'code', await pg.input_value('#aCode'))
    # ---- edit item dialog
    await E("closeModal(); document.querySelectorAll('.mdd-scrim').forEach(x=>x.remove()); editItem(S.items[0])"); await W(300)
    await pg.screenshot(path=f'{SHOTS}/u9-edit-{sfx}.png')
    await pg.click('#eSave'); await W(200)
    print('price after edit', await E("S.items[0].variants[0].price"), 'safety', await E("S.items[0].variants[0].safety"))
    print('ERR', errs)
    await b.close()

async def main():
  for lang, dark in (('ar', False), ('en', True)):
    print('====', lang, dark); await run(lang, dark)
asyncio.run(main())

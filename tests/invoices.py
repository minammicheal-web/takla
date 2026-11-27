import os
APP = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
SHOTS = os.environ.get('SHOTS', '/tmp/shots'); os.makedirs(SHOTS, exist_ok=True)
# Invoice numbers, sales/purchase invoice tabs, search by number / name / phone / time window,
# return-period labels, invoice picture preview, supplier invoice photo.
import asyncio, base64
from playwright.async_api import async_playwright

PNG = '/tmp/inv_photo.png'
open(PNG, 'wb').write(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAIAAAAmkwkpAAAAEklEQVR4nGP4z8DAwMDAwMAAAAwAAf9hJzMAAAAASUVORK5CYII='))

async def run(lang, dark):
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    ctx = await b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, has_touch=True, color_scheme='dark' if dark else 'light')
    # an old invoice saved before numbers existed must get a number
    await ctx.add_init_script("""if(!localStorage.getItem('store-v1-seeded')){localStorage.setItem('store-v1-seeded','1');}""")
    if lang == 'en': await ctx.add_init_script("localStorage.setItem('store-lang','en')")
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(APP); await pg.wait_for_timeout(500)
    E = pg.evaluate; sfx = f'{lang}-{"d" if dark else "l"}'
    await E("""(()=>{const DAY=864e5, now=Date.now();
      const a=newItem('قميص'); S.items.push(a); const v=newVariant(a,'أبيض','L'); v.price=300;
      S.txns.push({id:uid(),type:'buy',ts:now-40*DAY,pay:'كاش',lines:[{itemId:a.id,vid:v.id,qty:50,cost:150}],supplier:'مصنع النور'});
      const d10=new Date(now-10*DAY); d10.setHours(19,10,0,0);
      const d10b=new Date(now-10*DAY); d10b.setHours(13,0,0,0);
      const d30=new Date(now-30*DAY); d30.setHours(12,0,0,0);
      S.txns.push({id:uid(),type:'sell',ts:d30.getTime(),pay:'كاش',lines:[{itemId:a.id,vid:v.id,qty:1,price:300,cost:150}],cname:'أحمد علي',cphone:'01011112222'});
      S.txns.push({id:uid(),type:'sell',ts:d10.getTime(),pay:'كاش',lines:[{itemId:a.id,vid:v.id,qty:2,price:300,cost:150}],cname:'منى سمير',cphone:'01299998888'});
      S.txns.push({id:uid(),type:'sell',ts:d10b.getTime(),pay:'كاش',lines:[{itemId:a.id,vid:v.id,qty:1,price:300,cost:150}]});
      fixNos(S); S.settings.retDays=15; persist(); C=calc(); renderAll();})()""")
    print('numbers', await E("S.txns.map(t=>t.type+':'+rno(t)).join(' ')"))
    await E("go('sinv')"); await pg.wait_for_timeout(400)
    print('tab sinv buttons', await E("$$('#pg-sinv .ivb').length"), 'labels', await E("$$('#pg-sinv .ivb .pill').map(x=>x.textContent).join(' | ')"))
    await pg.screenshot(path=f'{SHOTS}/i0-sales-{sfx}.png')
    # search by number, name, phone
    for q in ['2', '00003', 'منى', '9988', 'zzz']:
      await pg.fill('#pg-sinv .iq', q); await pg.wait_for_timeout(150)
      print('q', q, '->', await E("$$('#pg-sinv .ivb b.ltr').map(x=>x.textContent).join()"))
    await pg.fill('#pg-sinv .iq', '')
    # time window: 10 days ago 6 PM → 8 PM
    await pg.click('#pg-sinv [data-qk=range]'); await pg.wait_for_timeout(200)
    await E("""(()=>{const d=new Date(Date.now()-10*864e5); d.setHours(18,0,0,0); IF.sell.from=d.getTime(); d.setHours(20,0,0,0); IF.sell.to=d.getTime(); renderInv('sell');})()""")
    await pg.wait_for_timeout(200)
    print('window 6-8 PM ->', await E("$$('#pg-sinv .ivb b.ltr').map(x=>x.textContent).join()"), await E("$('#pg-sinv .isum').textContent"))
    await pg.screenshot(path=f'{SHOTS}/i1-window-{sfx}.png')
    # the date button opens the Material date picker
    await pg.click('#pg-sinv [data-iv=from]'); await pg.wait_for_timeout(400)
    print('date picker open', await E("!!document.querySelector('.mk-pkd,.mk-pkh,.mdd')"))
    await E("MK.back()"); await pg.wait_for_timeout(400)
    # open the invoice picture
    await pg.click('#pg-sinv .ivb'); await pg.wait_for_timeout(700)
    print('preview img', await E("(()=>{const i=$('.ivd .rcimg'); return i && i.naturalWidth+'x'+i.naturalHeight})()"), 'label', await E("$('.ivd .pill') && $('.ivd .pill').textContent"))
    await pg.screenshot(path=f'{SHOTS}/i2-preview-{sfx}.png')
    await pg.click('.ivd [data-x]'); await pg.wait_for_timeout(400)
    # old invoice → return asks first
    old = await E("S.txns.find(t=>t.type==='sell'&&t.cname==='أحمد علي').id")
    await E(f"openReturn(S.txns.find(t=>t.id==='{old}'))"); await pg.wait_for_timeout(400)
    print('late confirm', await E("($('.mdd h4')||{}).textContent"))
    await pg.screenshot(path=f'{SHOTS}/i3-late-{sfx}.png')
    await E("MK.back()"); await pg.wait_for_timeout(400)
    # new sale gets the next number and the phone
    print('receipt line', await E("receiptText(S.txns.find(t=>t.cname==='منى سمير')).split('\\n').filter(l=>l.includes('15')).join(' / ')"))
    # purchase with a photo
    await E("go('buy')"); await pg.wait_for_timeout(300)
    async with pg.expect_file_chooser() as fc: await pg.click('#bPhAdd')
    await (await fc.value).set_files(PNG); await pg.wait_for_timeout(600)
    print('buy thumbs', await E("$$('#bPhs .pht').length"))
    await E("""(()=>{ $('#bSup').value='مصنع النور'; $('#bSup').dispatchEvent(new Event('change')); })()""")
    print('supplier phone autofill (none yet)', repr(await E("$('#bSupPh').value")))
    await E("$('#bSupPh').value='0225551234'")
    # make the purchase through the data layer (form item entry is covered by other tests)
    await E("""(()=>{const it=S.items[0], v=it.variants[0]; S.txns.push({id:uid(),type:'buy',no:nextNo('buy'),ts:Date.now(),pay:'كاش',lines:[{itemId:it.id,vid:v.id,qty:5,cost:150}],supplier:$('#bSup').value,sphone:$('#bSupPh').value,photos:bPhotos.slice()}); persist(); C=calc();})()""")
    await E("go('pinv')"); await pg.wait_for_timeout(400)
    print('pinv', await E("$$('#pg-pinv .ivb b.ltr').map(x=>x.textContent).join()"))
    await pg.fill('#pg-pinv .iq', '5551'); await pg.wait_for_timeout(150); print('pinv phone', await E("$$('#pg-pinv .ivb').length"))
    await pg.fill('#pg-pinv .iq', ''); await pg.wait_for_timeout(150)
    await pg.screenshot(path=f'{SHOTS}/i4-purchases-{sfx}.png')
    await pg.click('#pg-pinv .ivb'); await pg.wait_for_timeout(800)
    print('buy preview', await E("(()=>{const i=$('.ivd .rcimg'); return i && i.naturalWidth+'x'+i.naturalHeight})()"), 'photo thumbs', await E("$$('.ivd .pht img').filter(i=>i.src).length"))
    await pg.screenshot(path=f'{SHOTS}/i5-buy-preview-{sfx}.png')
    await pg.click('.ivd .pht'); await pg.wait_for_timeout(500); print('viewer', await E("!!$('.phv img')"))
    await pg.screenshot(path=f'{SHOTS}/i6-photo-{sfx}.png')
    await E("MK.back()"); await E("MK.back()"); await pg.wait_for_timeout(400)
    # settings field
    print('retDays', await E("S.settings.retDays"))
    print('ERR', errs)
    await b.close()

async def main():
  for lang, dark in [('ar', False), ('en', True)]:
    print('====', lang, dark); await run(lang, dark)
asyncio.run(main())

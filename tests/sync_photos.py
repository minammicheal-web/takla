import os
APP = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
SHOTS = os.environ.get('SHOTS', '/tmp/shots'); os.makedirs(SHOTS, exist_ok=True)
# A purchase photo taken on phone A is uploaded once and opens on phone B on demand.
import asyncio
from playwright.async_api import async_playwright
from sync_basic import phone, buy
async def main():
  async with async_playwright() as p:
    b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    errs = []
    A = await phone(b, errs, 'A'); B = await phone(b, errs, 'B')
    await A.click('#bSet'); await A.click('#tSync'); await A.wait_for_timeout(200)
    await A.fill('#yUser', 'مينا'); await A.click('#ySeg [data-m=new]')
    await A.fill('#yShop', 'محل صور'); await A.fill('#yP', 'P'); await A.fill('#yK', 'KEY'); await A.click('#yGo')
    await A.wait_for_timeout(800); code = await A.evaluate('syCode()'); await A.click('[data-close]')
    await A.evaluate("(()=>{const id=uid(); PH.save(id,'data:image/jpeg;base64,/9j/AAAA'); bPhotos.push(id); drawBuyPhotos();})()")
    await buy(A, 'جاكيت', 'أسود', 3, 200)
    await A.wait_for_timeout(2500)
    print('A buy', await A.evaluate("JSON.stringify(S.txns.map(t=>[rno(t),(t.photos||[]).length]))"), 'snap', await A.evaluate("Object.keys(SNAPM).filter(k=>k.startsWith('f_')).length"))
    await B.click('#bSet'); await B.click('#tSync'); await B.wait_for_timeout(200)
    await B.click('#ySeg [data-m=join]') if await B.locator('#ySeg [data-m=join]').count() else None
    await B.fill('#yUser', 'الموظف'); await B.fill('#yCode', code); await B.click('#yGo'); await B.wait_for_timeout(1500)
    pid = await B.evaluate("(S.txns.find(t=>t.photos)||{photos:[]}).photos[0]||''")
    print('B has txn photo id', bool(pid), 'local before', await B.evaluate(f"PH.has('{pid}')"))
    print('B loaded', (await B.evaluate(f"PH.load('{pid}')"))[:30])
    await A.evaluate("syPush && syPush()"); await A.wait_for_timeout(800)
    print('A photo not deleted from cloud', await A.evaluate("Object.keys(SNAPM).filter(k=>k.startsWith('f_')).length"))
    print('errors', [e for e in errs if 'UNSAFE_PORT' not in e])
    await b.close()
asyncio.run(main())

import os
APP = 'file://' + os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'index.html'))
SHOTS = os.environ.get('SHOTS', '/tmp/shots'); os.makedirs(SHOTS, exist_ok=True)
import asyncio
from playwright.async_api import async_playwright
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    for vw,vh,name in [(390,844,'ph'),(1100,800,'tab')]:
      ctx=await b.new_context(viewport={'width':vw,'height':vh},device_scale_factor=1)
      pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
      await pg.goto(APP)
      await pg.evaluate("""()=>{S.customers.push({id:'c1',name:'أم أحمد',phone:'01001234567'}); persist(); go('cust'); $$('#cSeg button')[1].click();}""")
      await pg.wait_for_timeout(500); await pg.screenshot(path=f'{SHOTS}/c-{name}.png'); print(name, errs)
    await b.close()
asyncio.run(main())

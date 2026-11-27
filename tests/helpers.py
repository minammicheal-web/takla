# Purchase through the two-step form: supplier page -> Next -> add each line -> save.
async def buy_lines(pg, lines, sup='', tax=None, close_labels=True):
    await pg.click('nav button[data-p=buy]'); await pg.wait_for_timeout(150)
    if await pg.evaluate("BD.step") != 1: await pg.evaluate("buyStep(1)")
    if sup: await pg.fill('#bSup', sup)
    if tax is not None: await pg.fill('#bTax', str(tax))
    await pg.click('#bNext'); await pg.wait_for_timeout(150)
    for l in lines:
        await pg.click('#bAddIt'); await pg.wait_for_timeout(350)
        for k, sel in [('name', '#aName'), ('type', '#aType'), ('color', '#aColor'), ('size', '#aSize'), ('qty', '#aQty'), ('cost', '#aCost'), ('price', '#aPrice'), ('code', '#aCode')]:
            if k in l: await pg.fill(sel, str(l[k]))
        if 'exp' in l: await pg.evaluate(f"(()=>{{const i=$('#aExp'); i.value='{l['exp']}';}})()")
        if 'batch' in l: await pg.fill('#aBatch', l['batch'])
        if 'sn' in l: await pg.fill('#aSn', l['sn'])
        await pg.click('.bal [data-ok]'); await pg.wait_for_timeout(300)
    await pg.click('#bSave'); await pg.wait_for_timeout(500)
    if close_labels: await pg.evaluate("$$('.lbd [data-x]').forEach(b=>b.click())"); await pg.wait_for_timeout(300)

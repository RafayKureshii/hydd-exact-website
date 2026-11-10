#!/usr/bin/env python3
"""Optional: run after build, with playwright+pillow installed and network access."""
import asyncio, argparse
from pathlib import Path

async def main():
    p=argparse.ArgumentParser()
    p.add_argument('--local',default='http://127.0.0.1:8000')
    args=p.parse_args()
    from playwright.async_api import async_playwright
    from PIL import Image,ImageChops
    out=Path('visual_qa');out.mkdir(exist_ok=True)
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True)
        for width,height in [(1440,900),(390,844)]:
            page=await browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
            for path in ('/','/services/','/mise-disposition/','/notre-fl/','/contact/'):
                slug=path.strip('/').replace('/','-') or 'home'
                shots=[]
                for label,base in [('original','https://www.hydd.fr'),('clone',args.local.rstrip('/'))]:
                    try:
                        await page.goto(base+path,wait_until='domcontentloaded',timeout=45000)
                        await page.wait_for_timeout(1700)
                        name=out/f'{slug}_{width}_{label}.png'
                        await page.screenshot(path=str(name),full_page=True)
                        shots.append(name)
                    except Exception as e:print(f'FAILED {label}: {path} {e}')
                if len(shots)==2:
                    a,b=[Image.open(x).convert('RGB') for x in shots]
                    if a.size==b.size:
                        mismatch=ImageChops.difference(a,b).getbbox() is not None
                        print(f'{slug} {width}: same dimensions, pixel differences={mismatch}')
                    else:
                        print(f'{slug} {width}: page dimensions differ: {a.size} vs {b.size}')
            await page.close()
        await browser.close()

if __name__=='__main__':asyncio.run(main())

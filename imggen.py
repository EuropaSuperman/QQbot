import asyncio

import markdown
from pyppeteer import launch
from botpy import logging
from pyppeteer import __chromium_revision__,__pyppeteer_home__
_log = logging.get_logger()
_log.info(f"浏览器路径：{__pyppeteer_home__}/local-chromium/{__chromium_revision__}/chrome-linux/chrome")
async def convert_md_to_image(browser,text,path):
    html_content = markdown.markdown(text)
    page = await browser.newPage()
    # 加载 HTML 并渲染
    await page.setContent(f"""
        <html>
            <head>
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        line-height: 1.6; 
                        padding: 20px;
                        max-width: 800px;
                        margin: 0 auto;
                    }}
                </style>
            </head>
            <body>{html_content}</body>
        </html>
    """)

    # 截图保存为图片
    await page.screenshot({"path": path, "fullPage": True})
    await page.close()
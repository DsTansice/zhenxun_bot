from nonebot import on_command, Driver
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Bot, MessageEvent, Message
from utils.message_builder import image
from utils.image_utils import CreateImg
from utils.browser import get_browser
from configs.path_config import IMAGE_PATH
import nonebot
from services.log import logger
from utils.utils import scheduler
from nonebot.permission import SUPERUSER
from typing import List
import os
import asyncio
import time


__zx_plugin_name__ = "原神今日素材"
__plugin_usage__ = """
usage：
    看看原神今天要刷什么
    指令：
        今日素材/今天素材
""".strip()
__plugin_superuser_usage__ = """
usage：
    更新原神今日素材
    指令：
        更新原神今日素材
""".strip()
__plugin_des__ = "看看原神今天要刷什么"
__plugin_cmd__ = ["今日素材/今天素材", "更新原神今日素材 [_superuser]"]
__plugin_type__ = ("原神相关",)
__plugin_version__ = 0.1
__plugin_author__ = "HibiKier"
__plugin_settings__ = {
    "level": 5,
    "default_status": True,
    "limit_superuser": False,
    "cmd": ["今日素材", "今天素材"],
}

driver: Driver = nonebot.get_driver()

material = on_command("今日素材", aliases={"今日材料", "今天素材", "今天材料"}, priority=5, block=True)

super_cmd = on_command("更新原神今日素材", permission=SUPERUSER, priority=1, block=True)


@material.handle()
async def _(bot: Bot, event: MessageEvent, state: T_State):
    if time.strftime("%w") == "0":
        await material.send("今天是周日，所有材料副本都开放了。")
        return
    await material.send(
        Message(
            image("daily_material.png", "genshin/material")
            + "\n※ 每日素材数据来源于 genshin.pub"
        )
    )
    logger.info(
        f"(USER {event.user_id}, GROUP {event.group_id if event.message_type != 'private' else 'private'})"
        f" 发送查看今日素材"
    )


@super_cmd.handle()
async def _(bot: Bot, event: MessageEvent, state: T_State):
    if await update_image():
        await super_cmd.send("更新成功...")
        logger.info(f"更新每日天赋素材成功...")
    else:
        await super_cmd.send(f"更新失败...")


@driver.on_startup
async def update_image():
    page = None
    try:
        if not os.path.exists(f"{IMAGE_PATH}/genshin/material"):
            os.mkdir(f"{IMAGE_PATH}/genshin/material")
        for file in os.listdir(f"{IMAGE_PATH}/genshin/material"):
            os.remove(f"{IMAGE_PATH}/genshin/material/{file}")
        browser = await get_browser()
        if not browser:
            logger.warning("获取 browser 失败，请部署至 linux 环境....")
            return False
        url = "https://genshin.pub/daily"
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=10000)
        await page.set_viewport_size({"width": 2560, "height": 1080})
        await page.evaluate(
            """
            document.getElementsByClassName('GSTitleBar_gs_titlebar__2IJqy')[0].remove();
            e = document.getElementsByClassName('GSContainer_gs_container__2FbUz')[0];
            e.setAttribute("style", "height:880px");
        """
        )
        await page.click("button")
        div = await page.query_selector(".GSContainer_content_box__1sIXz")
        for i, card in enumerate(
            await page.query_selector_all(".GSTraitCotainer_trait_section__1f3bc")
        ):
            index = 0
            type_ = "char" if not i else "weapons"
            for x in await card.query_selector_all("xpath=child::*"):
                await x.screenshot(
                    path=f"{IMAGE_PATH}/genshin/material/{type_}_{index}.png",
                    timeout=100000,
                )
                # 下滑两次
                for _ in range(3):
                    await div.press("PageDown")
                index += 1
            # 结束后上滑至顶
            for _ in range(index * 3):
                await div.press("PageUp")
        file_list = os.listdir(f"{IMAGE_PATH}/genshin/material")
        char_imgs = [
            f"{IMAGE_PATH}/genshin/material/{x}"
            for x in file_list
            if x.startswith("char")
        ]
        weapons_imgs = [
            f"{IMAGE_PATH}/genshin/material/{x}"
            for x in file_list
            if x.startswith("weapons")
        ]
        char_imgs.sort()
        weapons_imgs.sort()
        height = await asyncio.get_event_loop().run_in_executor(
            None, get_background_height, weapons_imgs
        )
        background_img = CreateImg(1200, height + 100, color="#f6f2ee")
        current_width = 50
        for imgs in [char_imgs, weapons_imgs]:
            current_height = 20
            for img in imgs:
                x = CreateImg(0, 0, background=img)
                background_img.paste(x, (current_width, current_height))
                current_height += x.size[1]
            current_width += 600
        background_img.save(f"{IMAGE_PATH}/genshin/material/daily_material.png")
        await page.close()
        return True
    except Exception as e:
        logger.error(f"原神每日素材更新出错... {type(e)}: {e}")
        if page:
            await page.close()
        return False


# 获取背景高度以及修改最后一张图片的黑边
def get_background_height(weapons_imgs: List[str]) -> int:
    height = 0
    for weapons in weapons_imgs:
        height += CreateImg(0, 0, background=weapons).size[1]
    last_weapon = CreateImg(0, 0, background=weapons_imgs[-1])
    w, h = last_weapon.size
    last_weapon.crop((0, 0, w, h - 10))
    last_weapon.save(weapons_imgs[-1])

    return height


@scheduler.scheduled_job(
    "cron",
    hour=4,
    minute=1,
)
async def _():
    for _ in range(5):
        try:
            await update_image()
            logger.info(f"更新每日天赋素材成功...")
            break
        except Exception as e:
            logger.error(f"更新每日天赋素材出错 e：{e}")

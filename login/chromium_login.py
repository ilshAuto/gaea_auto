import os
import random
import sys
import time
from datetime import datetime

import cv2
import httpx
import pyautogui
from DrissionPage._base.chromium import Chromium
from DrissionPage._configs.chromium_options import ChromiumOptions
from DrissionPage._units.actions import Actions
from fake_useragent import UserAgent
from loguru import logger

logger.remove()
logger.add(sys.stdout, format="<g>{time:YYYY-MM-DD HH:mm:ss:SSS}</g> | <c>{level}</c> | <level>{message}</level>")


def find_image_in_screenshot(screenshot_path, template_path, threshold=0.8):
    """在截图中查找模板图片"""
    try:
        # 读取图片
        screenshot = cv2.imread(screenshot_path)
        template = cv2.imread(template_path)

        # 模板匹配
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            logger.info(f"Image found with confidence: {max_val}")
            return max_loc
        logger.warning(f"Image not found (confidence: {max_val})")
        return None

    except Exception as e:
        logger.error(f"Error in image recognition: {e}")
        return None


def click_location(page, screenshot_path, template_path):
    for i in range(3):
        # 添加时间戳到文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename, ext = os.path.splitext(screenshot_path)
        current_screenshot = f"{filename}_{timestamp}{ext}"

        try:
            page.get_screenshot(current_screenshot)
            logger.info(f"Screenshot saved to {current_screenshot}")

            # 查找图像
            location = find_image_in_screenshot(current_screenshot, template_path)
            print(location)

            # 删除截图文件
            if os.path.exists(current_screenshot):
                os.remove(current_screenshot)
                logger.info(f"Deleted screenshot: {current_screenshot}")

            if location is None:
                time.sleep(5)
                continue

            if location:
                x, y = location
                print(x, y)
                click_x = x

                logger.info(f"Clicking at position ({click_x}, {y})")

                actions = Actions(page)
                actions.move_to((click_x, y), duration=random.uniform(1, 3))
                actions.click().click()
                time.sleep(5)

            break

        except Exception as e:
            logger.error(f"Error in click_location: {e}")
            # 确保即使发生异常也删除截图
            if os.path.exists(current_screenshot):
                os.remove(current_screenshot)

def start_login():
    account_list = []
    with open('./account_login', 'r', encoding='utf-8') as f:
        for line in f:
            email, password, proxy = line.strip().split('----')
            account_list.append(
                {'email': email, 'password': password, 'proxy': proxy})
    for acc in account_list:
        co = ChromiumOptions()
        co.set_proxy(proxy)
        # chromium = Chromium(addr_or_opts=co)
        chromium = Chromium(co)
        page = chromium.new_tab()
        try:
            # page.listen.start("https://app.aigaea.net/login/")
            page.get('https://app.aigaea.net/login/')
            page.ele('@placeholder=Enter your email or username').input(acc['email'])
            page.ele('@placeholder=Enter your password').input(acc['password'])
            page.ele('@class=el-checkbox__inner').click()
            time.sleep(8)
            click_location(page, './page_screen.png', './checkBox.png')
            page.ele('@class=el-button is-round w-full z-[999]').click()
            time.sleep(15)
            page.refresh()
            browser_id = page.local_storage('browser_id')
            gaea_token = page.local_storage('gaea_token')
            print(browser_id)
            if browser_id is not None:
                req_json = {
                    'proxy': acc['proxy'],
                    'email': acc['email'],
                    'password': acc['password'],
                    'browser_id': browser_id,

                    'token': gaea_token,
                }
                print(req_json)
                # 写入文件（account）格式： email----password----browser_id----proxy----token
                with open('./account', 'a', encoding='utf-8') as f:
                    f.write(f'{acc["email"]}----{acc["password"]}----{browser_id}----{acc["proxy"]}----{gaea_token}\n')
            chromium.quit()
        except Exception as e:
            print(e)
            chromium.quit()

if __name__ == '__main__':
    logger.info('🚀 [ILSH] DAWN v1.0 | Airdrop Campaign Live')
    logger.info('🌐 ILSH Community: t.me/ilsh_auto')
    logger.info('🐦 X(Twitter): https://x.com/hashlmBrian')
    logger.info('☕ Pay meCoffe：USDT（TRC20）:TAiGnbo2isJYvPmNuJ4t5kAyvZPvAmBLch')
    start_login()



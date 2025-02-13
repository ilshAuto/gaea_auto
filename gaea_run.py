import asyncio
import sys
import time
import cloudscraper

PING_URL = 'https://api.aigaea.net/api/network/ping'
IP_URL = 'https://api.aigaea.net/api/network/ip'
SCORE_URL = 'https://api.aigaea.net/api/earn/info'
DAILY_CHECK_URL = 'https://api.aigaea.net/api/mission/complete-mission'
from loguru import logger

logger.remove()
logger.add(sys.stdout, format="<g>{time:YYYY-MM-DD HH:mm:ss:SSS}</g> | <c>{level}</c> | <level>{message}</level>")
# logger.add(
#     "logs/file_{time}.log",  # 文件路径，会自动创建目录
#     rotation="500 MB",  # 日志文件大小达到500MB时会自动新建文件
#     encoding="utf-8",  # 设置编码
#     enqueue=True,  # 异步写入
#     retention="10 days",  # 保留10天的日志
#     format="{time:YYYY-MM-DD HH:mm:ss:SSS} | {level} | {message}",  # 文件中的日志格式
#     level="DEBUG"  # 日志级别
# )


class ScraperReq:
    def __init__(self, proxy: dict, header: dict):
        self.scraper = cloudscraper.create_scraper(browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False,
        })
        self.proxy: dict = proxy
        self.header: dict = header

    def post_req(self, url, req_json, req_param=None):
        # logger.info(self.header)
        # logger.info(req_json)
        return self.scraper.post(url=url, headers=self.header, json=req_json, proxies=self.proxy, params=req_param)

    async def post_async(self, url, req_param=None, req_json=None):
        return await asyncio.to_thread(self.post_req, url, req_json, req_param)

    def get_req(self, url, req_param):
        return self.scraper.get(url=url, headers=self.header, params=req_param, proxies=self.proxy)

    async def get_async(self, url, req_param=None, req_json=None):
        return await asyncio.to_thread(self.get_req, url, req_param)


class Geae:
    def __init__(self, account: dict, scraper: ScraperReq, check_score_scraper: ScraperReq):
        self.account: dict = account
        self.scraper = scraper
        self.country = ''
        self.proxy_res = ''
        self.check_score_scraper = check_score_scraper
        self.time_ = time.time()

    async def get_proxy_res(self):
        res = await self.scraper.get_async(url='http://ip-api.com/json', req_param=None)
        self.proxy_res = res.json()['query']
        self.country = res.json()['country']

    async def ping(self):
        req_json = {"uid": self.account['uid'], "browser_id": self.account['browser_id'], "timestamp": int(time.time()),
                    "version": "1.0.1"}
        res = await self.scraper.post_async(PING_URL, req_json=req_json)
        return res

    async def ip(self):
        res = await self.scraper.get_async(IP_URL)
        print(res.text)

    async def check_score(self):
        """
        {
            "code": 200,
            "success": true,
            "msg": "Success",
            "data": {
                "total_total": 1569.51,
                "today_total": 477.08
            }
        }
        """
        res = await self.check_score_scraper.get_async(SCORE_URL)
        # print(res.text)
        if res.json()['code'] == 200:
            logger.info(
                f'SCORE: 账号：{self.account["email"]}, socks信息：{self.account["proxy"]} 代理ip：{self.proxy_res}, 代理国家：{self.country}, 分数：{res.json()["data"]["total_total"]}')
        else:
            logger.error(
                f'SCORE: 账号：{self.account["email"]}, socks信息：{self.account["proxy"]} 代理ip：{self.proxy_res}, 代理国家：{self.country}, 错误：{res.json()["msg"]}')

    async def check_daily_statistic(self):
        """检查每日统计信息判断是否需要签到"""
        try:
            res = await self.check_score_scraper.get_async('https://api.aigaea.net/api/earn/daily-statistic')
            data = res.json().get('data', [])
            
            # 修改1：使用UTC时间
            today = time.strftime("%d/%m/%Y", time.gmtime())  # UTC时间
            
            if not data:
                logger.info(f'账号：{self.account["email"]}每日统计数据为空，需要签到')
                return True
                
            first_entry = data[0]
            # 修改2：添加network_points日志
            if first_entry['date'] == today and first_entry['checkin_points'] == 0:
                logger.info(f'账号：{self.account["email"]} 今日{first_entry["date"]}尚未签到，当前network_points：{first_entry.get("network_points", 0)}')
                return True
                
            return False
        except Exception as e:
            logger.error(f'账号：{self.account["email"]}检查每日统计失败: {e}')
            return False

    async def loop_task(self):
        try:
            await self.get_proxy_res()
        except Exception as e:
            return
            
        while True:
            try:
                await self.get_uid()
                
                # 修改后的签到触发条件
                if await self.check_daily_statistic():
                    await self.daily_check_in()
                    self.time_ = time.time()  # 重置计时
                    
                res = await self.ping()
                logger.info(
                    f'PING: ip分数：{res.json()["data"]["score"]},账号：{self.account["email"]}, socks信息：{self.account["proxy"]} 代理ip：{self.proxy_res}, 代理国家：{self.country}')
            except Exception as e:
                logger.error(f'PING错误: {e}')
            try:
                await self.check_score()
            except Exception as e:
                logger.error(
                    f'IP: 账号：{self.account["email"]}, socks信息：{self.account["proxy"]} 代理ip：{self.proxy_res}, 代理国家：{self.country}, 错误：{e}')
            await asyncio.sleep(10 * 60)

    async def daily_check_in(self):
        req_json = {"mission_id": "1"}
        res = await self.scraper.post_async(url=DAILY_CHECK_URL, req_param=None, req_json=req_json)
        if res.json()['code'] == 200:
            # 修改3：签到成功日志添加network_points
            logger.info(
                f'DAILY-CHECK: 完成，账号：{self.account["email"]}, network_points：{res.json().get("data", {}).get("network_points", "N/A")}')
        else:
            logger.info(
                f'DAILY-CHECK: 失败，账号：{self.account["email"]}')

    async def get_uid(self):
        try:
            session_url = 'https://api.aigaea.net/api/auth/session'

            res = await self.check_score_scraper.post_async(session_url)
            uid = res.json()['data']['uid']
            self.account.update({'uid': uid})
            logger.info(f'获取uid成功:账号：{self.account["email"]}, socks信息：{self.account["proxy"]}, uid: {uid}')
        except Exception as e:
            logger.error(
                f'获取uid失败:账号：{self.account["email"]}, socks信息：{self.account["proxy"]} , {e}')
            raise Exception("获取uid失败", e)
        pass


async def run_gaea(account: dict):
    header = {
        'Authorization': f'Bearer {account["token"]}',
        'Content-Type': 'application/json',
        'Origin': 'chrome-extension://cpjicfogbgognnifjgmenmaldnmeeeib',
        'Priority': 'u=1, i',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'none'
    }

    proxy_dict = {
        'http': account['proxy'],
        'https': account['proxy'],
    }

    scraper = ScraperReq(proxy_dict, header)

    check_score_header = {
        'Authorization': f'Bearer {account["token"]}',
        'Content-Type': 'application/json',
        'Origin': 'https://app.aigaea.net',
        'Priority': 'u=1, i',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site'
    }

    check_score_scraper = ScraperReq(proxy_dict, check_score_header)
    gaea = Geae(account, scraper, check_score_scraper)
    await gaea.loop_task()


async def main():
    """
    account 文件格式：email----password----browser_id----proxy----token
    """
    accounts = []
    with open('./account', 'r') as f:
        for l in f.readlines():
            email, password, browser_id, proxy, token = l.strip().split('----')
            accounts.append({
                'email': email,
                'password': password,
                'browser_id': browser_id,
                'proxy': proxy,
                'token': token
            })
    tasks = [run_gaea(account) for account in accounts]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    logger.info('🚀 [ILSH] DAWN v1.0 | Airdrop Campaign Live')
    logger.info('🌐 ILSH Community: t.me/ilsh_auto')
    logger.info('🐦 X(Twitter): https://x.com/hashlmBrian')
    logger.info('☕ Pay meCoffe：USDT（TRC20）:TAiGnbo2isJYvPmNuJ4t5kAyvZPvAmBLch')
    asyncio.run(main())

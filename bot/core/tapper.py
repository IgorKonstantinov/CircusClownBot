import heapq
import asyncio
import pprint
import random
from urllib.parse import unquote, quote
from time import time
from datetime import datetime, timezone

import requests

import aiohttp
import json
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestWebView
from bot.config import settings

from bot.utils import logger
from bot.utils.bot import calculate_price

from bot.exceptions import InvalidSession
from .headers import headers, headers_options

class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.peer_name = 'circus_clicker_bot'
        self.peer_url = 'https://circus-clown.com/'
        self.user_id = 0
        self.headers = headers

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer(self.peer_name)
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"{self.session_name} | FloodWait {fl}")
                    logger.info(f"{self.session_name} | FloodWait Sleep {fls}s")
                    fls += 5
                    await asyncio.sleep(fls)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=peer,
                bot=peer,
                platform='android',
                from_bot_menu=False,
                url=self.peer_url
            ))

            auth_url = web_view.url

            tg_web_data = unquote(
                string=unquote(string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0]))

            self.user_id = (await self.tg_client.get_me()).id

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Telegram Authorization: {error}")
            await asyncio.sleep(delay=30)

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")
            await asyncio.sleep(delay=30)

    async def auth(self, http_client: aiohttp.ClientSession, initData: str = ''):
        try:
            auth_url = f"https://api.circus-clown.com/api/user/info?telegramId={self.user_id}&initData={initData}"

            response = await http_client.get(url=auth_url)
            response.raise_for_status()

            response_json = await response.json()
            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Auth Error: {error}")
            await asyncio.sleep(delay=30)

    async def tap(self, http_client: aiohttp.ClientSession, taps: int = 0):
        try:
            tap_url = "https://api.circus-clown.com/api/user/click"
            params = {'amount': taps}

            response = requests.post(url=tap_url, params=params, headers=self.headers)
            response.raise_for_status()

            response_json = response.json()
            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Tap Error: {error}")
            await asyncio.sleep(delay=30)

    async def tap_options(self, http_client: aiohttp.ClientSession, taps: int = 0):
        try:
            tap_url = "https://api.circus-clown.com/api/user/click"
            params = {'amount': taps}
            response = await http_client.options(url=tap_url, params=params)
            response.raise_for_status()

            response_text = await response.text()
            return response_text

        except Exception as error:
            logger.error(f"{self.session_name} | Tap Options Error: {error}")
            await asyncio.sleep(delay=30)

    async def businesses(self, http_client: aiohttp.ClientSession, action='', id: int = 0):
        try:
            match action:
                case 'get':
                    businesses_url = "https://api.circus-clown.com/api/businesses"
                    response = await http_client.get(url=businesses_url)
                case 'set':
                    businesses_url = "https://api.circus-clown.com/api/user/upgradeBusiness"
                    params = {'userId': {self.user_id}, 'businesId': id}
                    print(params)
                    response = requests.post(url=businesses_url, params=params, headers=self.headers)
                case _:
                    raise ValueError("There is no passive_action.")

            response.raise_for_status()

            response_json = await response.json()
            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when get businesses data: {error}")
            await asyncio.sleep(delay=30)

    async def referrals(self, http_client: aiohttp.ClientSession, action=''):
        try:
            match action:
                case 'get':
                    referrals_url = f"https://api.circus-clown.com/api/serverFunctions/getReferrals"
                    response = await http_client.get(url=referrals_url)
                case 'post':
                    raw_data = {'timestamp': int(time())}
                    referrals_url = "https://api-v1-production.pixie-game.com/api/v3/referrals/get/coins"
                    response = await http_client.post(url=referrals_url, json=raw_data)
                case _:
                    raise ValueError("There is no passive_action.")

            response.raise_for_status()

            response_json = await response.json()
            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when get referrals data: {error}")
            await asyncio.sleep(delay=30)

    async def daily(self, http_client: aiohttp.ClientSession):
        try:
            daily_url = "https://api.circus-clown.com/api/user/collectDaily"
            params = {'userId': self.user_id}

            #response = await http_client.post(url=daily_url, params=params)
            response = requests.post(url=daily_url, params=params, headers=self.headers)
            response.raise_for_status()

            response_json = response.json()
            return response_json

        except Exception as error:
            logger.error(f"{self.session_name} | Daily | Unknown error: {error}")
            await asyncio.sleep(delay=30)

    async def run(self, proxy: str | None) -> None:
        referrals_created_time = 0
        while True:
            error_sleep = random.randint(*settings.SLEEP_BETWEEN_MINING)
            try:
                #Randomize variables
                random_sleep = random.randint(*settings.SLEEP_RANDOM)
                long_sleep = random.randint(*settings.SLEEP_BETWEEN_MINING)

                tg_web_data = await self.get_tg_web_data(proxy=proxy)
                http_client = aiohttp.ClientSession(headers=headers)

                initData = settings.API_INITDATA
                auth_data = await self.auth(http_client=http_client, initData=initData)

                logger.info(f"Generate new access_token: {auth_data['token']}")
                http_client.headers["authorization"] = auth_data['token']
                self.headers.update({'authorization': auth_data['token']})

                auth_data_balance = auth_data['mtkBalance']
                auth_data_balance_old = auth_data['mtkBalanceBeforeUpdate']
                auth_data_current_energy = auth_data['currentEnergy']

                auth_data_click_level = auth_data['clickLevel']
                auth_data_click_power = auth_data['totalClickPower']

                logger.success(f"{self.session_name} | Auth | "
                               f"Balance: <c>{auth_data_balance} (+{auth_data_balance-auth_data_balance_old} passive)</c> | "
                               f"Energy: <c>{auth_data_current_energy}</c> | "
                               f"Click: level: <c>{auth_data_click_level}</c>, power: <c>{auth_data_click_power}</c>")
                await asyncio.sleep(delay=random_sleep)

                if settings.AUTO_UPGRADE:

                    businesses_action = 'get'
                    businesses_data = await self.businesses(http_client=http_client, action=businesses_action)
                    if businesses_data:
                        logger.success(f"{self.session_name} | Bot action: <red>[businesses/{businesses_action}]:</red> <c>{businesses_data}</c>")
                        await asyncio.sleep(delay=random_sleep)
                    else:
                        logger.info(f"{self.session_name} | Cannot [businesses/{businesses_action}]")

                    exit()

                    prices_data = businesses_data['businesses']
                    levels_data = auth_data['user']['businesses_data']
                    levels_data = json.loads(levels_data)

                    # Создаем словарь для уровней
                    levels = {card_id: info['level'] for card_id, info in levels_data['data'].items()}
                    queue = []

                    for card in prices_data:
                        card_id = str(card['id'])

                        if card_id in levels:
                            level = levels[card_id]
                            name = card['name_en']
                            price = card['price']
                            coef = card['price_coef']
                            calculated_price = calculate_price(price, coef, level)

                            if calculated_price <= auth_data_balance:
                                print(name, card_id, level, calculated_price)
                                heapq.heappush(queue, (calculated_price, card_id, level, name))
                        else:
                            level = 1
                            name = card['name_en']
                            price = card['price']
                            coef = card['price_coef']
                            calculated_price = calculate_price(price, coef, level)

                            if calculated_price <= auth_data_balance:
                                print(name, card_id, level, calculated_price)
                                heapq.heappush(queue, (calculated_price, card_id, level, name))

                    if len(queue) > 1:
                        card_upgrade = heapq.nsmallest(1, queue)[0]
                        print(card_upgrade)

                        card_upgrade_price = card_upgrade[0]
                        card_upgrade_id = card_upgrade[1]
                        card_upgrade_level = int(card_upgrade[2])
                        card_upgrade_name = card_upgrade[3]

                        logger.info(f"{self.session_name} | Sleep {random_sleep:,}s before upgrade card: <e>[{card_upgrade_id}/{card_upgrade_name}]</e> to level: <e>[{card_upgrade_level}]</e> with price: <e>[{card_upgrade_price}]</e>")
                        await asyncio.sleep(delay=random_sleep)

                        businesses_action = 'set'
                        businesses_data = await self.businesses(http_client=http_client, action=businesses_action, id=card_upgrade_id)
                        if businesses_data:
                            logger.success(
                                f"{self.session_name} | Bot action: <red>[businesses/{businesses_action}]</red> : <c>{businesses_data}</c>")
                            await asyncio.sleep(delay=random_sleep)
                        else:
                            logger.info(f"{self.session_name} | Cannot [businesses/{businesses_action}]")

                    else:
                        logger.info(f"{self.session_name} | Cannot [businesses], balance is too small: <g>{auth_data_balance}</g>")

                if settings.AUTO_REFERRALS and (time() - referrals_created_time >= 3600):

                    referrals_created_time = time()
                    logger.info(f"{self.session_name} | Sleep {random_sleep:,}s before refarrals claim")
                    await asyncio.sleep(delay=random_sleep)

                    referrals_action = 'get'
                    referrals_data = await self.referrals(http_client=http_client, action=referrals_action)
                    print(referrals_data)

                    if referrals_data['total'] > 0:
                        logger.success(f"{self.session_name} | Bot action: <red>[refarrals/{referrals_action}]</red>")
                        await asyncio.sleep(delay=random_sleep)

                        referrals_action = 'post'
                        referrals_data = await self.referrals(http_client=http_client, action=referrals_action)
                        logger.success(f"{self.session_name} | Bot action: <red>[refarrals/{referrals_action}]:</red> {referrals_data}")
                        await asyncio.sleep(delay=random_sleep)

                    else:
                        logger.info(f"{self.session_name} | Cannot [refarrals/{referrals_action}]: no referrals")

                # daily
                if auth_data['dailyPrizeCollectAvailable']:
                    logger.info(f"{self.session_name} | sleep {random_sleep:,}s before bot action: <e>[daily]</e>")
                    await asyncio.sleep(delay=random_sleep)
                    daily_data = await self.daily(http_client=http_client)
                    logger.success(
                        f"{self.session_name} | <red>[action/daily]</red> "
                        f"data: <c>{daily_data}</c>")

                # taps
                logger.info(f"{self.session_name} | sleep {random_sleep:,}s before bot action: <e>[tap]</e>")
                await asyncio.sleep(delay=random_sleep)

                while auth_data_current_energy > 100:
                    taps = random.randint(*settings.TAP_RANDOM)

                    if taps*auth_data_click_power >= auth_data_current_energy:
                        taps = abs(auth_data_current_energy // auth_data_click_power -1)

                    taps_data = await self.tap(http_client=http_client, taps=taps)
                    if taps_data:
                        auth_data_current_energy = auth_data_current_energy - taps * auth_data_click_power
                        logger.success(f"{self.session_name} | Bot action: <red>[tap/{taps}/{taps*auth_data_click_power}]</red> Energy: <c>{auth_data_current_energy}</c>")
                        await asyncio.sleep(delay=random_sleep)
                    else:
                        logger.error(f"{self.session_name} | Bot action:[tap] error")

                logger.info(f"{self.session_name} | Sleep {long_sleep:,}s")
                await http_client.close()
                await asyncio.sleep(delay=long_sleep)

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error} | sleep {error_sleep}")
                await http_client.close()
                await asyncio.sleep(delay=error_sleep)


async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")

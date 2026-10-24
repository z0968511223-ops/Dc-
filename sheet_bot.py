import discord
from discord.ext import tasks
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import requests
import hashlib

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
SHEET_ID = "1Xu56GR58a3eIi-LvJ-gEPZgvfWRUww38NMhPH95bOrg"
GID = "0"  # announcement 分頁
TZ = ZoneInfo("Asia/Taipei")

intents = discord.Intents.default()
bot = discord.Client(intents=intents)

last_content = ""
last_hash = ""

def now_tw():
    return datetime.now(TZ)

def fetch_sheet():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return r.text.strip()
    except Exception as e:
        print(f"抓取失敗：{e}", flush=True)
    return None

@tasks.loop(minutes=5)
async def check_sheet():
    global last_content, last_hash
    content = fetch_sheet()
    if not content:
        return

    current_hash = hashlib.md5(content.encode()).hexdigest()
    if current_hash == last_hash:
        return

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("找不到頻道", flush=True)
        return

    now = now_tw().strftime("%m/%d")
    if not last_content:
        # 第一次啟動，只記錄不通知
        last_content = content
        last_hash = current_hash
        print("首次載入完成", flush=True)
        return

    # 簡單比對（可依實際需求再優化）
    old_lines = set(last_content.splitlines())
    new_lines = set(content.splitlines())

    added = new_lines - old_lines
    removed = old_lines - new_lines

    if added and not removed:
        msg = f"**公告新增 {now}**\n" + "\n".join(sorted(added))
    elif removed and not added:
        msg = f"**公告更新 {now}**\n（內容有修改）"
    else:
        msg = f"**公告更新 {now}**\n" + "\n".join(sorted(added))

    await channel.send(msg)
    last_content = content
    last_hash = current_hash
    print(f"已發送公告變動 {now}", flush=True)

@bot.event
async def on_ready():
    print(f"公告機器人已上線：{bot.user}", flush=True)
    if not check_sheet.is_running():
        check_sheet.start()

bot.run(TOKEN)

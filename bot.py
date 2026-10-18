import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta

# ==================== 設定區 ====================
TOKEN = "MTU2MTAzOTIyMDkwMDg4ODY2Nw.G90kHN.x6UX1otak3yQyts3rkfjX_f66gFTJTkpzTTdAo"
CHANNEL_ID = 123456789012345678  # 1561090723833716887

ADVANCE_MINUTES = 5

# ==================== 時間表 ====================
SCHEDULE = [
    {"name": "野外 Boss 群組1", "times": ["00:15", "09:15", "12:15", "21:15"], "days": None},
    {"name": "野外 Boss 群組2", "times": ["01:59"], "days": None},
    {"name": "野外 Boss 群組3", "times": ["11:57"], "days": None},
    {"name": "世界 Boss 亞加拉旭", "times": ["21:00"], "days": None},
    {"name": "世界 Boss 沙赫加", "times": ["21:00"], "days": None},
    {"name": "巨人塔 1F", "times": ["21:00"], "days": [0, 3]},
    {"name": "巨人塔 2F", "times": ["21:00"], "days": [1, 4]},
    {"name": "巨人塔 3F", "times": ["21:00"], "days": [2, 5]},
    {"name": "巨人塔 4F", "times": ["21:00"], "days": [0, 3]},
    {"name": "大氾濫", "times": ["20:00"], "days": None},
    {"name": "神石戰", "times": ["19:30"], "days": [6], "every_n_days": 14},
    {"name": "激戰", "times": ["21:00"], "days": [1, 4, 6]},
]

# ==================== 機器人核心 ====================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

notified = set()

def is_event_today(event, now):
    weekday = now.weekday()
    if event["days"] is not None and weekday not in event["days"]:
        return False
    if "every_n_days" in event:
        base_date = datetime(2026, 9, 16)
        days_diff = (now.date() - base_date.date()).days
        if days_diff % event["every_n_days"] != 0:
            return False
    return True

def should_notify(event, now):
    if not is_event_today(event, now):
        return False
    current_time = now.strftime("%H:%M")
    for t in event["times"]:
        target = datetime.strptime(t, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        notify_time = target - timedelta(minutes=ADVANCE_MINUTES)
        if notify_time.strftime("%H:%M") == current_time:
            key = f"{event['name']}_{current_time}_{now.date()}"
            if key not in notified:
                notified.add(key)
                return True
    return False

@tasks.loop(minutes=1)
async def check_schedule():
    now = datetime.now()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return
    for event in SCHEDULE:
        if should_notify(event, now):
            await channel.send(f"@everyone **{event['name']}** 即將開始！（{ADVANCE_MINUTES} 分鐘後）")

@bot.tree.command(name="今日", description="查看今天有哪些活動")
async def today(interaction: discord.Interaction):
    now = datetime.now()
    today_events = []

    for event in SCHEDULE:
        if is_event_today(event, now):
            times = "、".join(event["times"])
            today_events.append(f"**{event['name']}**：{times}")

    if today_events:
        msg = "**今天的活動時間表：**\n" + "\n".join(today_events)
    else:
        msg = "今天沒有安排的活動。"

    await interaction.response.send_message(msg)

@bot.event
async def on_ready():
    print(f"機器人已上線：{bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"已同步 {len(synced)} 個斜線指令")
    except Exception as e:
        print(f"同步指令失敗：{e}")

    if not check_schedule.is_running():
        check_schedule.start()

bot.run(TOKEN)
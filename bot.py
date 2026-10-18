import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta
import os

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

SCHEDULE = [
    {"name": "野外 Boss 群組1", "times": ["00:15", "09:15", "12:15", "21:15"], "days": None, "category": "大世界"},
    {"name": "世界 Boss 亞加拉旭", "times": ["21:00"], "days": None, "category": "大世界"},
    {"name": "世界 Boss 沙赫加", "times": ["21:00"], "days": None, "category": "大世界"},
    {"name": "世界 Boss 貝西摩斯", "times": ["21:00"], "days": None, "category": "大世界"},
    {"name": "世界 Boss 達里恩特", "times": ["21:00"], "days": [2], "category": "大世界"},
    {"name": "巨人塔 1F", "times": ["21:00"], "days": [0, 3], "category": "大世界"},
    {"name": "巨人塔 2F", "times": ["21:00"], "days": [1, 4], "category": "大世界"},
    {"name": "巨人塔 3F", "times": ["21:00"], "days": [2, 5], "category": "大世界"},
    {"name": "巨人塔 4F", "times": ["21:00"], "days": [0, 3], "category": "大世界"},
    {"name": "大氾濫", "times": ["20:00"], "days": None, "category": "大世界"},
    {"name": "激戰", "times": ["21:00"], "days": [1, 4, 6], "category": "大世界"},
    {"name": "次元BOSS", "times": ["21:30"], "days": None, "category": "大世界"},
    {"name": "神石戰", "times": ["19:30"], "days": [6], "base_date": datetime(2026, 11, 1), "every_n_days": 14, "category": "公會"},
    {"name": "公會活動集合（複製體/遠征/競技場/證明）", "times": ["22:20"], "days": [6], "category": "公會"},
]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
notified = set()
dynamic_timers = {}

def is_event_on_date(event, target_date):
    weekday = target_date.weekday()
    days = event.get("days")
    if days is not None and weekday not in days:
        return False
    if "every_n_days" in event:
        base = event.get("base_date", datetime(2026, 9, 16))
        days_diff = (target_date.date() - base.date()).days
        if days_diff < 0 or (days_diff % event["every_n_days"]) != 0:
            return False
    return True

def should_notify(event, now, minutes_before):
    if not is_event_on_date(event, now):
        return False
    current_time = now.strftime("%H:%M")
    for t in event["times"]:
        target = datetime.strptime(t, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
        notify_time = target - timedelta(minutes=minutes_before)
        if notify_time.strftime("%H:%M") == current_time:
            key = f"{event['name']}_{minutes_before}_{current_time}_{now.date()}"
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
        # 倒數 10 分鐘
        if should_notify(event, now, 10):
            await channel.send(f"@everyone **{event['name']}** 即將開始！（還有 10 分鐘）")
        # 倒數 5 分鐘
        if should_notify(event, now, 5):
            await channel.send(f"@everyone **{event['name']}** 即將開始！（還有 5 分鐘）")

    to_remove = []
    for name, next_time in list(dynamic_timers.items()):
        for minutes in [10, 5]:
            if now >= next_time - timedelta(minutes=minutes) and now < next_time - timedelta(minutes=minutes-1):
                key = f"dynamic_{name}_{minutes}_{next_time}"
                if key not in notified:
                    notified.add(key)
                    await channel.send(f"@everyone **{name}** 即將刷新！（還有 {minutes} 分鐘）")
                    if minutes == 5:
                        to_remove.append(name)
    for name in to_remove:
        dynamic_timers.pop(name, None)

def build_day_message(target_date, title_prefix):
    world_events = []
    guild_events = []
    for event in SCHEDULE:
        if is_event_on_date(event, target_date):
            times = "、".join(event["times"])
            line = f"{event['name']}：{times}"
            if event.get("category") == "公會":
                guild_events.append(line)
            else:
                world_events.append(line)

    msg = f"**{title_prefix}大世界活動：**\n"
    msg += "\n".join(world_events) if world_events else f"{title_prefix}無大世界活動"
    msg += f"\n\n**{title_prefix}公會活動：**\n"
    msg += "\n".join(guild_events) if guild_events else f"{title_prefix}無公會活動"
    return msg

@bot.tree.command(name="今日", description="查看今天有哪些活動")
async def today(interaction: discord.Interaction):
    msg = build_day_message(datetime.now(), "今日")
    await interaction.response.send_message(msg)

@bot.tree.command(name="明日", description="查看明天有哪些活動")
async def tomorrow(interaction: discord.Interaction):
    tomorrow_date = datetime.now() + timedelta(days=1)
    msg = build_day_message(tomorrow_date, "明日")
    await interaction.response.send_message(msg)

@bot.tree.command(name="擊殺", description="記錄擊殺並開始倒數（分鐘）")
async def kill(interaction: discord.Interaction, 名稱: str, 分鐘: int):
    if 分鐘 <= 0:
        await interaction.response.send_message("分鐘數必須大於 0", ephemeral=True)
        return
    next_time = datetime.now() + timedelta(minutes=分鐘)
    dynamic_timers[名稱.strip()] = next_time
    hours, mins = divmod(分鐘, 60)
    time_str = f"{hours}小時{mins}分鐘" if hours else f"{mins}分鐘"
    await interaction.response.send_message(f"已記錄 **{名稱}** 擊殺！\n刷新間隔：{time_str}\n下次時間：{next_time.strftime('%m/%d %H:%M')}")

@bot.tree.command(name="狀態", description="查看目前動態倒數")
async def status(interaction: discord.Interaction):
    if not dynamic_timers:
        await interaction.response.send_message("目前沒有進行中的動態倒數。")
        return
    lines = []
    now = datetime.now()
    for name, next_time in dynamic_timers.items():
        remaining = next_time - now
        total_mins = int(remaining.total_seconds() // 60)
        hours, mins = divmod(total_mins, 60)
        lines.append(f"**{name}**：還剩 {hours}小時{mins}分鐘（{next_time.strftime('%H:%M')}）")
    await interaction.response.send_message("**目前動態倒數：**\n" + "\n".join(lines))

@bot.tree.command(name="取消", description="取消某個動態倒數")
async def cancel(interaction: discord.Interaction, 名稱: str):
    name = 名稱.strip()
    if name in dynamic_timers:
        dynamic_timers.pop(name)
        await interaction.response.send_message(f"已取消 **{name}** 的倒數。")
    else:
        await interaction.response.send_message(f"找不到 **{name}** 的倒數。", ephemeral=True)

@bot.event
async def on_ready():
    print(f"機器人已上線：{bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"已同步 {len(synced)} 個斜線指令")
    except Exception as e:
        print(e)
    if not check_schedule.is_running():
        check_schedule.start()

bot.run(TOKEN)

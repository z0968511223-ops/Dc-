import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta
import os

# ==================== 設定區 ====================
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

ADVANCE_MINUTES = 5

# ==================== 固定時間表 ====================
SCHEDULE = [
    # 野外 Boss
    {"name": "野外 Boss 群組1", "times": ["00:15", "09:15", "12:15", "21:15"], "days": None},

    # 世界 Boss
    {"name": "世界 Boss 亞加拉旭", "times": ["21:00"], "days": None},
    {"name": "世界 Boss 沙赫加", "times": ["21:00"], "days": None},
    {"name": "世界 Boss 貝西摩斯", "times": ["21:00"], "days": None},  # 擊殺後隔天再刷，目前先當每天
    {"name": "世界 Boss 達里恩特", "times": ["21:00"], "days": [2]},  # 週三

    # 巨人塔
    {"name": "巨人塔 1F", "times": ["21:00"], "days": [0, 3]},
    {"name": "巨人塔 2F", "times": ["21:00"], "days": [1, 4]},
    {"name": "巨人塔 3F", "times": ["21:00"], "days": [2, 5]},
    {"name": "巨人塔 4F", "times": ["21:00"], "days": [0, 3]},

    # 其他
    {"name": "大氾濫", "times": ["20:00"], "days": None},
    {"name": "神石戰", "times": ["19:30"], "days": [6], "base_date": datetime(2026, 11, 1), "every_n_days": 14},
    {"name": "激戰", "times": ["21:00"], "days": [1, 4, 6]},

    # 公會活動
    {"name": "公會活動集合（複製體/遠征/競技場/證明）", "times": ["22:20"], "days": [6]},
]

# ==================== 機器人核心 ====================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

notified = set()
dynamic_timers = {}

def is_event_today(event, now):
    weekday = now.weekday()
    if event["days"] is not None and weekday not in event["days"]:
        return False

    if "every_n_days" in event:
        base = event.get("base_date", datetime(2026, 9, 16))
        days_diff = (now.date() - base.date()).days
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

    to_remove = []
    for name, next_time in list(dynamic_timers.items()):
        if now >= next_time - timedelta(minutes=ADVANCE_MINUTES) and now < next_time:
            key = f"dynamic_{name}_{next_time}"
            if key not in notified:
                notified.add(key)
                await channel.send(f"@everyone **{name}** 即將刷新！（約 {ADVANCE_MINUTES} 分鐘後）")
                to_remove.append(name)
    for name in to_remove:
        dynamic_timers.pop(name, None)

@bot.tree.command(name="今日", description="查看今天有哪些固定活動")
async def today(interaction: discord.Interaction):
    now = datetime.now()
    today_events = []
    for event in SCHEDULE:
        if is_event_today(event, now):
            times = "、".join(event["times"])
            today_events.append(f"**{event['name']}**：{times}")
    msg = "**今天的固定活動：**\n" + "\n".join(today_events) if today_events else "今天沒有固定活動。"
    await interaction.response.send_message(msg)

@bot.tree.command(name="擊殺", description="記錄擊殺並開始倒數（分鐘）")
async def kill(interaction: discord.Interaction, 名稱: str, 分鐘: int):
    name = 名稱.strip()
    if 分鐘 <= 0:
        await interaction.response.send_message("分鐘數必須大於 0", ephemeral=True)
        return
    next_time = datetime.now() + timedelta(minutes=分鐘)
    dynamic_timers[name] = next_time
    hours = 分鐘 // 60
    mins = 分鐘 % 60
    time_str = f"{hours}小時{mins}分鐘" if hours else f"{mins}分鐘"
    await interaction.response.send_message(
        f"已記錄 **{name}** 擊殺！\n刷新間隔：{time_str}\n下次時間：{next_time.strftime('%m/%d %H:%M')}"
    )

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
        hours = total_mins // 60
        mins = total_mins % 60
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

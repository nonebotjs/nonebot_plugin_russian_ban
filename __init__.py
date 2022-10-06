from nonebot.plugin.on import on_command
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    Message,
    GroupMessageEvent,
    GROUP_ADMIN,
    GROUP_OWNER
    )
from nonebot.permission import SUPERUSER

from nonebot.typing import T_State
from nonebot.params import Depends, CommandArg, Arg, State

import asyncio
import time
import random

try:
    import ujson as json
except ModuleNotFoundError:
    import json

from pathlib import Path

def get_message_at(data: str) -> list:
    '''
    获取at对象
    '''
    qq_list = []
    data = json.loads(data)
    try:
        for msg in data['message']:
            if msg['type'] == 'at':
                qq_list.append(int(msg['data']['qq']))
        return qq_list
    except Exception:
        return []

# 快捷禁言/解禁

path = Path() / "data" / "Focus_namelist.json"
if path.exists():
    with open(path, "r", encoding="utf8") as f:
        namelist = json.load(f)
else:
    namelist = {}

add_namelist = on_command("添加名单", rule = to_me(), permission = SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority = 5)

@add_namelist.handle()
async def _(event: GroupMessageEvent,arg: Message = CommandArg()):
    group_id = str(event.group_id)
    at = get_message_at(event.json())
    msg = arg.extract_plain_text().strip().split()
    n = len(at)
    if n == len(msg):
        namelist.setdefault(group_id,{})
        for i in range(n):
            namelist[group_id].update({msg[i]:at[i]})
        with open(path, "w", encoding="utf8") as f:
            json.dump(namelist, f, ensure_ascii=False, indent=4)
        await add_namelist.finish("已添加")

ban = on_command("禁言", permission = SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority = 5)

@ban.handle()
async def _(bot:Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    group_id = str(event.group_id)
    msg = arg.extract_plain_text().strip()
    namelist.setdefault(group_id,{})
    if msg in namelist[group_id].keys():
        user_id = namelist[group_id][msg]
        await bot.set_group_ban(group_id = event.group_id, user_id = user_id, duration = 86400)
    else:
        at = get_message_at(event.json())
        if at:
            for i in at:
                await bot.set_group_ban(group_id = event.group_id, user_id = i, duration = 86400)
        else:
            pass

global ban_list

amnesty = on_command("解封", aliases = {"解禁", "解除禁言"}, permission = SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority = 5)

@amnesty.handle()
async def _(bot:Bot, event: GroupMessageEvent, arg: Message = CommandArg(), state: T_State = State()):
    global ban_list
    ban_list = []
    member_list = await bot.get_group_member_list(group_id = event.group_id, no_cache = True)
    msg = ""
    for member in member_list:
        if member['shut_up_timestamp'] > 0:
            ban_list.append(member['user_id'])
            nickname = member['card'] or member['nickname']
            t = int((member['shut_up_timestamp'] - time.time()))
            td = int(t/86400)
            t -= td * 86400
            th = int(t/3600)
            t -= th * 3600
            tm = int(t/60)
            Time = ""
            Time += f" {td} 天" if td > 0 else ""
            Time += f" {th} 小时" if th > 0 or td > 0 else ""
            Time += f" {tm} 分钟"
            msg += f"{nickname} {member['user_id']}\n    -- {Time}\n"
    else:
        if ban_list:
            name = arg.extract_plain_text().strip()
            group_id = str(event.group_id)
            namelist.setdefault(group_id,{})
            if name in namelist[group_id].keys():
                state['user_id'] = namelist[group_id][name]
            else:
                await amnesty.send("以下成员正在禁言：\n" + msg[:-1])
                await asyncio.sleep(2)
        else:
            await amnesty.finish()

@amnesty.got("user_id", prompt = "请输入要解除禁言的成员，如输入多个群成员用空格隔开。")
async def _(bot:Bot, event: GroupMessageEvent, user_id: Message = Arg()):
    global ban_list
    user_id = str(user_id).strip().split()
    if user_id:
        for i in user_id:
            if int(i) in ban_list:
                await bot.set_group_ban(group_id = event.group_id, user_id = int(i), duration = 0)

    await amnesty.finish()

global star, st
star = 0
st = 0

ban_game = on_command("无赌注轮盘", aliases = {"自由轮盘", "拨动滚轮"}, priority = 5)

@ban_game.handle()
async def _(bot:Bot, event: GroupMessageEvent, state: T_State = State()):
    global star, st
    if star:
        star = random.randint(1,6)
        st = 0
        await ban_game.finish("重新装弹！")
    else:
        star = random.randint(1,6)
        msg = [
            "这个游戏非常简单，只需要几种道具：一把左轮，一颗子弹，以及愿意跟你一起玩的人。",
            "拿起这把左轮，对着自己的脑袋扣动扳机。如果安然无恙，继续游戏。",
            "如果你是六分之一的“幸运儿”，那么恭喜你，游戏结束。",
            "等等......好像有点不对劲？不过好在“幸运儿”永远没有机会开口说话并诉说游戏的邪恶了",
            "这个游戏非常公平，因为左轮最大的优点就是——不会卡壳",
            "小提示：每次开枪之前可以重新拨动滚轮哦"
            ]
        await ban_game.finish("游戏开始！\n"+ random.choice(msg))

async def Ready(bot: Bot, event: Event) -> bool:
    global star
    return star > 0

shot = on_command("开枪", permission = Ready ,priority = 4, block=True)

@shot.handle()
async def _(bot:Bot, event: GroupMessageEvent):
    global star, st
    st += 1
    if st == star:
        star = 0
        st = 0
        try:
            await bot.set_group_ban(group_id = event.group_id, user_id = event.user_id, duration = random.randint(1,10)*60)
        except:
            pass
        await shot.finish("中弹！游戏结束。",at_sender = True)
    else:
        msg = [
            "——传来一声清脆的金属碰撞声。\n没有人知道子弹的位置。可是不论它转到了哪里，总是要响的。",
            "恭喜你，安然无恙......但是下一次还会这么幸运吗？",
            "显然你不是这六分之一的“幸运儿”。但是好消息是，游戏还在继续。",
            "咔的一声，撞针敲击到空仓上。——你还安全地活着。",
            "你的运气不错。祝你好运。",
            f"偷偷告诉你，如果没有拨动滚轮的话，接下来第{star - st}发是子弹的位置。",
            f"偷偷告诉你，如果没有拨动滚轮的话，{'下回合将游戏结束。' if star - st == 1 else '下一发是空的。'}",
            "小提示：其实你可以不参加这个游戏",
            "小提示：每次开枪之前可以重新拨动滚轮哦"
            ]
        await shot.finish("继续！\n" + random.choice(msg))

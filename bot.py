import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

API_TOKEN = "8754097637:AAGSyoW-LHjwJ3j87Krnh1eue0bnKkBb3X4"

GROUP_NEW = -1003735668749
GROUP_DESIGN = -1003867470006
GROUP_READY = -1003312397488
GROUP_SENT = -1003671523271
GROUP_ISSUES = -1003747379674

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

order_id = 0

def new_buttons():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🎨 تم التصميم", callback_data="to_design"),
        InlineKeyboardButton("⚠️ مشاكل", callback_data="to_issues")
    )
    return kb

@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer("اكتب /new لإضافة طلب")

@dp.message_handler(commands=['new'])
async def new_order(msg: types.Message):
    global order_id
    order_id += 1

    text = f"📦 طلب جديد #{order_id}\n\nالحالة: جديد"

    await bot.send_message(GROUP_NEW, text, reply_markup=new_buttons())

@dp.callback_query_handler(lambda c: c.data == "to_design")
async def to_design(call: types.CallbackQuery):
    text = call.message.text.replace("جديد", "تم التصميم")

    await bot.send_message(GROUP_DESIGN, text)
    await call.message.delete()

@dp.callback_query_handler(lambda c: c.data == "to_issues")
async def to_issues(call: types.CallbackQuery):
    text = call.message.text + "\n⚠️ مشكلة"

    await bot.send_message(GROUP_ISSUES, text)
    await call.message.delete()

if __name__ == "__main__":
    executor.start_polling(dp)
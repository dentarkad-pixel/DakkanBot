import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

API_TOKEN = os.getenv("8754097637:AAGSyoW-LHjwJ3j87Krnh1eue0bnKkBb3X4")

GROUP_NEW = -1003735668749
GROUP_DESIGN = -1003867470006
GROUP_READY = -1003312397488
GROUP_SENT = -1003671523271
GROUP_ISSUES = -1003747379674

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

order_id = 0

# ================= STATES =================
class OrderState(StatesGroup):
    name = State()
    phone = State()
    city = State()
    area = State()

# ================= START =================
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer("اكتب /new لإنشاء طلب جديد")

# ================= NEW ORDER =================
@dp.message_handler(commands=['new'])
async def new_order(msg: types.Message):
    await msg.answer("👤 اسم الزبون:")
    await OrderState.name.set()

@dp.message_handler(state=OrderState.name)
async def get_name(msg: types.Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await msg.answer("📞 رقم الهاتف:")
    await OrderState.phone.set()

@dp.message_handler(state=OrderState.phone)
async def get_phone(msg: types.Message, state: FSMContext):
    await state.update_data(phone=msg.text)
    await msg.answer("📍 المدينة:")
    await OrderState.city.set()

@dp.message_handler(state=OrderState.city)
async def get_city(msg: types.Message, state: FSMContext):
    await state.update_data(city=msg.text)
    await msg.answer("🏘 المنطقة:")
    await OrderState.area.set()

@dp.message_handler(state=OrderState.area)
async def finish_order(msg: types.Message, state: FSMContext):
    global order_id
    order_id += 1

    data = await state.get_data()

    text = f"""
📦 طلب جديد #{order_id}

👤 الاسم: {data['name']}
📞 الرقم: {data['phone']}
📍 المدينة: {data['city']}
🏘 المنطقة: {msg.text}

الحالة: ⏳ جديد
"""

    await bot.send_message(GROUP_NEW, text, reply_markup=new_buttons())
    await msg.answer("✅ تم إرسال الطلب")
    await state.finish()

# ================= BUTTONS =================

def new_buttons():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🎨 تم التصميم", callback_data="design"),
        InlineKeyboardButton("⚠️ مشاكل", callback_data="issues")
    )
    return kb

def design_buttons():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📦 جاهز", callback_data="ready"),
        InlineKeyboardButton("⚠️ مشاكل", callback_data="issues")
    )
    return kb

def ready_buttons():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🚚 تم الإرسال", callback_data="sent"),
        InlineKeyboardButton("⚠️ مشاكل", callback_data="issues")
    )
    return kb

def issues_buttons():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🆕 رجوع جديد", callback_data="back_new"),
        InlineKeyboardButton("🎨 رجوع تصميم", callback_data="back_design"),
        InlineKeyboardButton("📦 رجوع جاهز", callback_data="back_ready"),
        InlineKeyboardButton("🚚 رجوع إرسال", callback_data="back_sent"),
    )
    return kb

# ================= MOVEMENT =================

@dp.callback_query_handler(lambda c: c.data == "design")
async def move_design(call: types.CallbackQuery):
    text = call.message.text.replace("جديد", "🎨 تم التصميم")
    await bot.send_message(GROUP_DESIGN, text, reply_markup=design_buttons())
    await call.message.delete()

@dp.callback_query_handler(lambda c: c.data == "ready")
async def move_ready(call: types.CallbackQuery):
    text = call.message.text.replace("تم التصميم", "📦 جاهز")
    await bot.send_message(GROUP_READY, text, reply_markup=ready_buttons())
    await call.message.delete()

@dp.callback_query_handler(lambda c: c.data == "sent")
async def move_sent(call: types.CallbackQuery):
    text = call.message.text.replace("جاهز", "🚚 تم الإرسال")
    await bot.send_message(GROUP_SENT, text)
    await call.message.delete()

@dp.callback_query_handler(lambda c: c.data == "issues")
async def move_issues(call: types.CallbackQuery):
    text = call.message.text + "\n⚠️ مشكلة"
    await bot.send_message(GROUP_ISSUES, text, reply_markup=issues_buttons())
    await call.message.delete()

# ================= RETURN FROM ISSUES =================

@dp.callback_query_handler(lambda c: c.data.startswith("back"))
async def back_handler(call: types.CallbackQuery):
    text = call.message.text.replace("⚠️ مشكلة", "")

    if call.data == "back_new":
        await bot.send_message(GROUP_NEW, text, reply_markup=new_buttons())

    elif call.data == "back_design":
        await bot.send_message(GROUP_DESIGN, text, reply_markup=design_buttons())

    elif call.data == "back_ready":
        await bot.send_message(GROUP_READY, text, reply_markup=ready_buttons())

    elif call.data == "back_sent":
        await bot.send_message(GROUP_SENT, text)

    await call.message.delete()

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

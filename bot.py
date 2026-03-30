import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

API_TOKEN = os.getenv("BOT_TOKEN")

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
    order_type = State()
    pieces = State()
    over_type = State()
    hand_type = State()
    size = State()
    notes = State()
    images = State()

# ================= START =================
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.answer("اكتب /new لإنشاء طلب جديد")

# ================= NEW =================
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

# ================= TYPE =================
def order_type_kb():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("طباعة", callback_data="type_print"),
        InlineKeyboardButton("تطريز", callback_data="type_emb")
    )
    return kb

@dp.message_handler(state=OrderState.area)
async def get_area(msg: types.Message, state: FSMContext):
    await state.update_data(area=msg.text)
    await msg.answer("اختر نوع الطلب:", reply_markup=order_type_kb())
    await OrderState.order_type.set()

@dp.callback_query_handler(lambda c: c.data.startswith("type"), state=OrderState.order_type)
async def choose_type(call: types.CallbackQuery, state: FSMContext):
    t = "طباعة" if call.data == "type_print" else "تطريز"
    await state.update_data(order_type=t)
    await call.message.answer("اختر القطع:", reply_markup=pieces_kb([]))
    await state.update_data(pieces=[])
    await OrderState.pieces.set()

# ================= PIECES =================
pieces_list = ["سيت 3","سيت 6","أوفر","كلو","صدرية","حضينة وكماط","ملحف"]

def pieces_kb(selected):
    kb = InlineKeyboardMarkup(row_width=2)
    for p in pieces_list:
        mark = "✅ " if p in selected else ""
        kb.insert(InlineKeyboardButton(mark+p, callback_data=f"piece_{p}"))
    kb.add(InlineKeyboardButton("✔️ تم", callback_data="done_pieces"))
    return kb

@dp.callback_query_handler(lambda c: c.data.startswith("piece"), state=OrderState.pieces)
async def choose_pieces(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("pieces", [])
    piece = call.data.split("_")[1]

    if piece in selected:
        selected.remove(piece)
    else:
        selected.append(piece)

    await state.update_data(pieces=selected)
    await call.message.edit_reply_markup(reply_markup=pieces_kb(selected))

# ================= OVER + HAND =================
@dp.callback_query_handler(lambda c: c.data == "done_pieces", state=OrderState.pieces)
async def done_pieces(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pieces = data.get("pieces", [])

    need_over = any(p in pieces for p in ["أوفر","سيت 3","سيت 6"])
    need_hand = any(p in pieces for p in ["ملحف","سيت 3","سيت 6"])

    await state.update_data(need_over=need_over, need_hand=need_hand)

    if need_over:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("دانتيل", callback_data="over_دانتيل"),
            InlineKeyboardButton("طباكات", callback_data="over_طباكات"),
            InlineKeyboardButton("صفح", callback_data="over_صفح"),
            InlineKeyboardButton("دانتيل طباكات", callback_data="over_دانتيل طباكات")
        )
        await call.message.answer("نوع الأوفر:", reply_markup=kb)
        await OrderState.over_type.set()
    elif need_hand:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("كشكش", callback_data="hand_كشكش"),
            InlineKeyboardButton("حب الرمان", callback_data="hand_حب")
        )
        await call.message.answer("نوع الملحف:", reply_markup=kb)
        await OrderState.hand_type.set()
    else:
        await ask_size(call.message)
        await OrderState.size.set()

@dp.callback_query_handler(lambda c: c.data.startswith("over"), state=OrderState.over_type)
async def choose_over(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(over_type=call.data.split("_")[1])

    data = await state.get_data()
    if data.get("need_hand"):
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("كشكش", callback_data="hand_كشكش"),
            InlineKeyboardButton("حب الرمان", callback_data="hand_حب")
        )
        await call.message.answer("نوع الملحف:", reply_markup=kb)
        await OrderState.hand_type.set()
    else:
        await ask_size(call.message)
        await OrderState.size.set()

@dp.callback_query_handler(lambda c: c.data.startswith("hand"), state=OrderState.hand_type)
async def choose_hand(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(hand_type=call.data.split("_")[1])
    await ask_size(call.message)
    await OrderState.size.set()

# ================= SIZE =================
sizes = ["حديثي ولادة","1","2","3","4","5","6","7","8","9","10","11","12"]

def size_kb():
    kb = InlineKeyboardMarkup(row_width=4)
    for s in sizes:
        kb.insert(InlineKeyboardButton(s, callback_data=f"size_{s}"))
    return kb

async def ask_size(msg):
    await msg.answer("اختر القياس:", reply_markup=size_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("size"), state=OrderState.size)
async def get_size(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(size=call.data.split("_")[1])
    await call.message.answer("📝 ملاحظات؟ (اكتب لا إذا ماكو)")
    await OrderState.notes.set()

# ================= NOTES =================
@dp.message_handler(state=OrderState.notes)
async def get_notes(msg: types.Message, state: FSMContext):
    notes = "لا يوجد" if msg.text == "لا" else msg.text
    await state.update_data(notes=notes)
    await msg.answer("📸 ارسل الصور (1-4) ثم اكتب تم")
    await state.update_data(images=[])
    await OrderState.images.set()

# ================= IMAGES =================
@dp.message_handler(content_types=['photo'], state=OrderState.images)
async def get_images(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    images = data.get("images", [])

    if len(images) >= 4:
        await msg.answer("❌ الحد الأقصى 4 صور")
        return

    images.append(msg.photo[-1].file_id)
    await state.update_data(images=images)
    await msg.answer(f"تم حفظ الصورة ({len(images)}/4)")

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
        InlineKeyboardButton("🆕 جديد", callback_data="back_new"),
        InlineKeyboardButton("🎨 تصميم", callback_data="back_design"),
        InlineKeyboardButton("📦 جاهز", callback_data="back_ready"),
    )
    return kb

# ================= FINISH =================
@dp.message_handler(lambda m: m.text == "تم", state=OrderState.images)
async def finish(msg: types.Message, state: FSMContext):
    global order_id
    order_id += 1

    data = await state.get_data()

    over = data.get("over_type", "لا يوجد")
    hand = data.get("hand_type", "لا يوجد")

    text = f"""
📦 طلب #{order_id}

👤 {data['name']}
📞 {data['phone']}
📍 {data['city']} - {data['area']}

🧵 النوع: {data['order_type']}
👕 القطع: {", ".join(data['pieces'])}

👗 الأوفر: {over}
🛏 الملحف: {hand}

📏 القياس: {data['size']}

📝 {data['notes']}

الحالة: ⏳ جديد
"""

    sent = await bot.send_message(GROUP_NEW, text, reply_markup=new_buttons())

    for img in data.get("images", []):
        await bot.send_photo(GROUP_NEW, img, reply_to_message_id=sent.message_id)

    await msg.answer("✅ تم إرسال الطلب")
    await state.finish()

# ================= MOVEMENT =================
@dp.callback_query_handler(lambda c: c.data == "design")
async def move_design(call: types.CallbackQuery):
    text = call.message.text.replace("⏳ جديد", "🎨 تم التصميم")
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

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

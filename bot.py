import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from openpyxl import Workbook, load_workbook

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
    box_color = State()
    dist_count = State()
    size = State()
    price = State()
    notes = State()
    images = State()

# ================= EXCEL =================
def save_to_excel(data):
    file = "orders.xlsx"
    if not os.path.exists(file):
        wb = Workbook()
        ws = wb.active
        ws.append([
            "رقم الطلب","الاسم","الهاتف","المدينة","المنطقة",
            "النوع","القطع","الأوفر","الملحف",
            "لون البوكس","عدد التوزيعات",
            "القياس","السعر","ملاحظات"
        ])
        wb.save(file)

    wb = load_workbook(file)
    ws = wb.active

    ws.append([
        data["id"], data["name"], data["phone"],
        data["city"], data["area"], data["type"],
        data["pieces"], data["over"], data["hand"],
        data["box"], data["dist"],
        data["size"], data["price"], data["notes"]
    ])
    wb.save(file)

# ================= HELP =================
def extract_images(text):
    if "📸" in text:
        imgs = text.split("📸")[1].strip()
        return imgs.split("|") if imgs else []
    return []

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
pieces_list = ["سيت 3","سيت 6","أوفر","كلو","صدرية","حضينة وكماط","ملحف","بوكس ككو","توزيعات"]

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

# ================= SMART =================
@dp.callback_query_handler(lambda c: c.data == "done_pieces", state=OrderState.pieces)
async def done_pieces(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pieces = data.get("pieces", [])

    need_over = any(p in pieces for p in ["أوفر","سيت 3","سيت 6"])
    need_hand = any(p in pieces for p in ["ملحف","سيت 3","سيت 6"])
    need_box = "بوكس ككو" in pieces
    need_dist = "توزيعات" in pieces

    await state.update_data(need_over=need_over, need_hand=need_hand, need_box=need_box, need_dist=need_dist)

    # 🔹 إذا يحتاج الأوفر
    if need_over:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("دانتيل", callback_data="over_دانتيل"),
            InlineKeyboardButton("طباكات", callback_data="over_طباكات"),
            InlineKeyboardButton("صفح", callback_data="over_صفح"),
            InlineKeyboardButton("دانتيل طباكات", callback_data="over_دانتيل طباكات")
        )
        await call.message.answer("نوع الأوفر:", reply_markup=kb)
        await OrderState.over_type.set()
        return

    # 🔹 إذا يحتاج الملحف
    if need_hand:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("كشكش", callback_data="hand_كشكش"),
            InlineKeyboardButton("حب الرمان", callback_data="hand_حب")
        )
        await call.message.answer("نوع الملحف:", reply_markup=kb)
        await OrderState.hand_type.set()
        return

    # 🔹 إذا يحتاج البوكس
    if need_box:
        await ask_box(call.message)
        await OrderState.box_color.set()
        return

    # 🔹 إذا يحتاج التوزيعات
    if need_dist:
        await call.message.answer("اكتب عدد التوزيعات:")
        await OrderState.dist_count.set()
        return

    await ask_size(call.message)
    await OrderState.size.set()

# ================= OVER =================
@dp.callback_query_handler(lambda c: c.data.startswith("over"), state=OrderState.over_type)
async def choose_over(call: types.CallbackQuery, state: FSMContext):
    over_choice = call.data.split("_")[1]
    await state.update_data(over_type=over_choice)

    data = await state.get_data()
    if data.get("need_hand"):
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("كشكش", callback_data="hand_كشكش"),
            InlineKeyboardButton("حب الرمان", callback_data="hand_حب")
        )
        await call.message.answer("🛏 نوع الملحف:", reply_markup=kb)
        await OrderState.hand_type.set()
        return
    if data.get("need_box"):
        await ask_box(call.message)
        await OrderState.box_color.set()
        return
    if data.get("need_dist"):
        await call.message.answer("🎉 اكتب عدد التوزيعات:")
        await OrderState.dist_count.set()
        return
    await ask_size(call.message)
    await OrderState.size.set()

# ================= HAND =================
@dp.callback_query_handler(lambda c: c.data.startswith("hand"), state=OrderState.hand_type)
async def choose_hand(call: types.CallbackQuery, state: FSMContext):
    hand_choice = call.data.split("_")[1]
    await state.update_data(hand_type=hand_choice)

    data = await state.get_data()
    if data.get("need_box"):
        await ask_box(call.message)
        await OrderState.box_color.set()
        return
    if data.get("need_dist"):
        await call.message.answer("🎉 اكتب عدد التوزيعات:")
        await OrderState.dist_count.set()
        return
    await ask_size(call.message)
    await OrderState.size.set()

# ================= BOX =================
def ask_box(msg):
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("أبيض", callback_data="box_ابيض"),
        InlineKeyboardButton("رصاصي", callback_data="box_رصاصي"),
        InlineKeyboardButton("وردي", callback_data="box_وردي"),
        InlineKeyboardButton("سماوي", callback_data="box_سماوي")
    )
    return msg.answer("🎁 اختر لون البوكس:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("box"), state=OrderState.box_color)
async def choose_box(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(box_color=call.data.split("_")[1])
    data = await state.get_data()
    if data.get("need_dist"):
        await call.message.answer("🎉 اكتب عدد التوزيعات:")
        await OrderState.dist_count.set()
        return
    await ask_size(call.message)
    await OrderState.size.set()

# ================= DIST =================
@dp.message_handler(state=OrderState.dist_count)
async def get_dist(msg: types.Message, state: FSMContext):
    await state.update_data(dist_count=msg.text)
    await ask_size(msg)
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
    await call.message.answer("💰 اكتب سعر الطلب:")
    await OrderState.price.set()

# ================= PRICE =================
@dp.message_handler(state=OrderState.price)
async def get_price(msg: types.Message, state: FSMContext):
    await state.update_data(price=msg.text)
    await msg.answer("📝 ملاحظات؟ (اكتب لا إذا ماكو)")
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

@dp.message_handler(lambda m: m.text == "تم", state=OrderState.images)
async def finish(msg: types.Message, state: FSMContext):
    global order_id
    order_id += 1

    data = await state.get_data()
    over = data.get("over_type", "لا يوجد")
    hand = data.get("hand_type", "لا يوجد")
    box = data.get("box_color", "لا يوجد")
    dist = data.get("dist_count", "لا يوجد")
    images_text = "|".join(data.get("images", []))

    text = f"""
📦 طلب #{order_id}

👤 {data['name']}
📞 {data['phone']}
📍 {data['city']} - {data['area']}

🧵 النوع: {data['order_type']}
👕 القطع: {", ".join(data['pieces'])}

👗 الأوفر: {over}
🛏 الملحف: {hand}
🎁 لون البوكس: {box}
🎉 عدد التوزيعات: {dist}

📏 القياس: {data['size']}
💰 السعر: {data['price']}

📝 {data['notes']}

📸 {images_text}

الحالة: ⏳ جديد
"""
    await bot.send_message(GROUP_NEW, text)
    if data.get("images"):
        media = [InputMediaPhoto(media=i) for i in data["images"]]
        await bot.send_media_group(GROUP_NEW, media)

    await msg.answer("✅ تم إرسال الطلب")
    await state.finish()

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

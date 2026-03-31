import os
import re
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from openpyxl import Workbook, load_workbook

# ================= TOKEN & GROUPS =================
API_TOKEN = os.getenv("BOT_TOKEN")

if not API_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable not set!")

GROUP_NEW = -1003735668749
GROUP_DESIGN = -1003867470006
GROUP_READY = -1003312397488
GROUP_SENT = -1003671523271
GROUP_ISSUES = -1003747379674

GROUPS_MAP = {
    "new": GROUP_NEW,
    "design": GROUP_DESIGN,
    "ready": GROUP_READY,
    "sent": GROUP_SENT,
    "issues": GROUP_ISSUES
}

GROUPS_NAMES = {
    GROUP_NEW: "طلبات جديدة",
    GROUP_DESIGN: "تم التصميم",
    GROUP_READY: "مجهز",
    GROUP_SENT: "تم الإرسال",
    GROUP_ISSUES: "مشاكل"
}

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

orders_data = {}

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
def get_next_order_id():
    file = "orders.xlsx"
    if not os.path.exists(file):
        return 1
    
    try:
        wb = load_workbook(file)
        ws = wb.active
        ids = [row[0].value for row in ws.iter_rows(min_row=2, max_col=1) 
               if isinstance(row[0].value, int)]
        return max(ids) + 1 if ids else 1
    except Exception as e:
        print(f"❌ خطأ في قراءة الإكسل: {e}")
        return 1

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
        data["id"], 
        data["name"], 
        data["phone"],
        data["city"], 
        data["area"], 
        data["order_type"],
        ",".join(data["pieces"]), 
        data.get("over_type", "لا يوجد"), 
        data.get("hand_type", "لا يوجد"),
        data.get("box_color", "لا يوجد"), 
        data.get("dist_count", "لا يوجد"),
        data["size"], 
        data["price"], 
        data["notes"]
    ])
    wb.save(file)

# ================= VALIDATION =================
def validate_phone(phone: str) -> bool:
    phone = phone.strip()
    return bool(re.match(r'^[0-9\+\-\s\(\)]{7,15}$', phone))

def validate_price(price: str) -> bool:
    price = price.strip()
    try:
        float(price)
        return True
    except ValueError:
        return False

def validate_dist_count(count: str) -> bool:
    count = count.strip()
    try:
        num = int(count)
        return num > 0
    except ValueError:
        return False

# ================= HELPER FUNCTIONS =================
def get_status_buttons(order_id: int, current_group: str = "new"):
    kb = InlineKeyboardMarkup(row_width=2)
    
    if current_group != "new":
        kb.insert(InlineKeyboardButton("⬅️ طلبات جديدة", callback_data=f"move_{order_id}_new"))
    
    if current_group != "design":
        kb.insert(InlineKeyboardButton("✏️ تم التصميم", callback_data=f"move_{order_id}_design"))
    
    if current_group != "ready":
        kb.insert(InlineKeyboardButton("📦 مجهز", callback_data=f"move_{order_id}_ready"))
    
    if current_group != "sent":
        kb.insert(InlineKeyboardButton("✈️ تم الإرسال", callback_data=f"move_{order_id}_sent"))
    
    if current_group != "issues":
        kb.insert(InlineKeyboardButton("⚠️ مشاكل", callback_data=f"move_{order_id}_issues"))
    
    return kb

def format_order_text(data: dict, order_id: int, current_group: str = "new") -> str:
    over = data.get("over_type", "لا يوجد")
    hand = data.get("hand_type", "لا يوجد")
    box = data.get("box_color", "لا يوجد")
    dist = data.get("dist_count", "لا يوجد")
    group_display = GROUPS_NAMES.get(GROUPS_MAP.get(current_group), "غير معروف")

    text = f"""📦 *طلب #{order_id}*

👤 *الاسم:* {data['name']}
📞 *الهاتف:* {data['phone']}
📍 *المدينة - المنطقة:* {data['city']} - {data['area']}

🧵 *النوع:* {data['order_type']}
👕 *القطع:* {', '.join(data['pieces'])}

👗 *الأوفر:* {over}
🛏 *الملحف:* {hand}
🎁 *لون البوكس:* {box}
🎉 *عدد التوزيعات:* {dist}

📏 *القياس:* {data['size']}
💰 *السعر:* {data['price']} ر.س

📝 *الملاحظات:*
{data['notes']}

━━━━━━━━━━━━━━━━━━
📍 *الحالة الحالية:* {group_display}"""
    return text

# ================= KEYBOARDS =================
def order_type_kb():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🖨 طباعة", callback_data="type_print"),
        InlineKeyboardButton("🧵 تطريز", callback_data="type_emb")
    )
    return kb

pieces_list = [
    "سيت 3", "سيت 6", "أوفر", "كلو", "صدرية", 
    "حضينة وكماط", "ملحف", "بوكس ككو", "توزيعات"
]

def pieces_kb(selected):
    kb = InlineKeyboardMarkup(row_width=2)
    for p in pieces_list:
        mark = "✅" if p in selected else "☐"
        kb.insert(InlineKeyboardButton(f"{mark} {p}", callback_data=f"piece_{p}"))
    kb.add(InlineKeyboardButton("✔️ تم", callback_data="done_pieces"))
    return kb

def over_type_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🎀 دانتيل", callback_data="over_دانتيل"),
        InlineKeyboardButton("🧵 طباكات", callback_data="over_طباكات"),
        InlineKeyboardButton("📄 صفح", callback_data="over_صفح"),
        InlineKeyboardButton("🎀🧵 دانتيل طباكات", callback_data="over_دانتيل+طباكات")
    )
    return kb

def hand_type_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🎀 كشكش", callback_data="hand_كشكش"),
        InlineKeyboardButton("🌸 حب الرمان", callback_data="hand_حب الرمان")
    )
    return kb

def box_color_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("⚪ أبيض", callback_data="box_أبيض"),
        InlineKeyboardButton("⚫ رصاصي", callback_data="box_رصاصي"),
        InlineKeyboardButton("🩷 وردي", callback_data="box_وردي"),
        InlineKeyboardButton("🩵 سماوي", callback_data="box_سماوي")
    )
    return kb

sizes = ["حديثي ولادة", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]

def size_kb():
    kb = InlineKeyboardMarkup(row_width=4)
    for s in sizes:
        kb.insert(InlineKeyboardButton(s, callback_data=f"size_{s}"))
    return kb

# ================= START =================
@dp.message_handler(commands=['start'])
async def start(msg: types.Message, state: FSMContext):
    await state.finish()
    await msg.answer("👋 مرحباً! اكتب /new لإنشاء طلب جديد")

# ================= NEW ORDER =================
@dp.message_handler(commands=['new'])
async def new_order(msg: types.Message, state: FSMContext):
    await state.finish()
    await msg.answer("👤 اسم الزبون:")
    await OrderState.name.set()

# ================= COLLECT INFO =================
@dp.message_handler(state=OrderState.name)
async def get_name(msg: types.Message, state: FSMContext):
    name = msg.text.strip()
    if len(name) < 2:
        await msg.answer("❌ الاسم قصير جداً، حاول مرة أخرى:")
        return
    
    await state.update_data(name=name)
    await msg.answer("📞 رقم الهاتف:")
    await OrderState.phone.set()

@dp.message_handler(state=OrderState.phone)
async def get_phone(msg: types.Message, state: FSMContext):
    phone = msg.text.strip()
    if not validate_phone(phone):
        await msg.answer("❌ صيغة الهاتف غير صحيحة. حاول مرة أخرى:")
        return
    
    await state.update_data(phone=phone)
    await msg.answer("📍 المدينة:")
    await OrderState.city.set()

@dp.message_handler(state=OrderState.city)
async def get_city(msg: types.Message, state: FSMContext):
    city = msg.text.strip()
    if len(city) < 2:
        await msg.answer("❌ اسم المدينة قصير جداً، حاول مرة أخرى:")
        return
    
    await state.update_data(city=city)
    await msg.answer("🏘 المنطقة:")
    await OrderState.area.set()

@dp.message_handler(state=OrderState.area)
async def get_area(msg: types.Message, state: FSMContext):
    area = msg.text.strip()
    if len(area) < 2:
        await msg.answer("❌ اسم المنطقة قصير جداً، حاول مرة أخرى:")
        return
    
    await state.update_data(area=area)
    await msg.answer("🧵 اختر نوع الطلب:", reply_markup=order_type_kb())
    await OrderState.order_type.set()

# ================= ORDER TYPE =================
@dp.callback_query_handler(lambda c: c.data.startswith("type_"), state=OrderState.order_type)
async def choose_type(call: types.CallbackQuery, state: FSMContext):
    order_type = "طباعة" if call.data == "type_print" else "تطريز"
    await state.update_data(order_type=order_type)
    await call.message.edit_text("👕 اختر القطع:", reply_markup=pieces_kb([]))
    await state.update_data(pieces=[])
    await OrderState.pieces.set()

# ================= PIECES =================
@dp.callback_query_handler(lambda c: c.data.startswith("piece_"), state=OrderState.pieces)
async def choose_pieces(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("pieces", [])
    piece = call.data.split("piece_", 1)[1]

    if piece in selected:
        selected.remove(piece)
    else:
        selected.append(piece)

    await state.update_data(pieces=selected)
    await call.message.edit_reply_markup(reply_markup=pieces_kb(selected))

# ================= DONE PIECES =================
@dp.callback_query_handler(lambda c: c.data == "done_pieces", state=OrderState.pieces)
async def done_pieces(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pieces = data.get("pieces", [])

    if not pieces:
        await call.answer("❌ اختر قطعة واحدة على الأقل!", show_alert=True)
        return

    need_over = any(p in pieces for p in ["أوفر", "سيت 3", "سيت 6"])
    need_hand = any(p in pieces for p in ["ملحف", "سيت 3", "سيت 6"])
    need_box = "بوكس ككو" in pieces
    need_dist = "توزيعات" in pieces

    await state.update_data(need_over=need_over, need_hand=need_hand, need_box=need_box, need_dist=need_dist)

    if need_over:
        await call.message.answer("✨ نوع الأوفر:", reply_markup=over_type_kb())
        await OrderState.over_type.set()
        return

    if need_hand:
        await call.message.answer("🛏 نوع الملحف:", reply_markup=hand_type_kb())
        await OrderState.hand_type.set()
        return

    if need_box:
        await call.message.answer("🎁 اختر لون البوكس:", reply_markup=box_color_kb())
        await OrderState.box_color.set()
        return

    if need_dist:
        await call.message.answer("🎉 اكتب عدد التوزيعات:")
        await OrderState.dist_count.set()
        return

    await call.message.answer("📏 اختر القياس:", reply_markup=size_kb())
    await OrderState.size.set()

# ================= OVER TYPE =================
@dp.callback_query_handler(lambda c: c.data.startswith("over_"), state=OrderState.over_type)
async def choose_over(call: types.CallbackQuery, state: FSMContext):
    over_choice = call.data.split("over_", 1)[1]
    await state.update_data(over_type=over_choice)

    data = await state.get_data()
    
    if data.get("need_hand"):
        await call.message.answer("🛏 ��وع الملحف:", reply_markup=hand_type_kb())
        await OrderState.hand_type.set()
        return
    
    if data.get("need_box"):
        await call.message.answer("🎁 اختر لون البوكس:", reply_markup=box_color_kb())
        await OrderState.box_color.set()
        return
    
    if data.get("need_dist"):
        await call.message.answer("🎉 اكتب عدد التوزيعات:")
        await OrderState.dist_count.set()
        return
    
    await call.message.answer("📏 اختر القياس:", reply_markup=size_kb())
    await OrderState.size.set()

# ================= HAND TYPE =================
@dp.callback_query_handler(lambda c: c.data.startswith("hand_"), state=OrderState.hand_type)
async def choose_hand(call: types.CallbackQuery, state: FSMContext):
    hand_choice = call.data.split("hand_", 1)[1]
    await state.update_data(hand_type=hand_choice)

    data = await state.get_data()
    
    if data.get("need_box"):
        await call.message.answer("🎁 اختر لون البوكس:", reply_markup=box_color_kb())
        await OrderState.box_color.set()
        return
    
    if data.get("need_dist"):
        await call.message.answer("🎉 اكتب عدد التوزيعات:")
        await OrderState.dist_count.set()
        return
    
    await call.message.answer("📏 اختر القياس:", reply_markup=size_kb())
    await OrderState.size.set()

# ================= BOX COLOR =================
@dp.callback_query_handler(lambda c: c.data.startswith("box_"), state=OrderState.box_color)
async def choose_box(call: types.CallbackQuery, state: FSMContext):
    box_color = call.data.split("box_", 1)[1]
    await state.update_data(box_color=box_color)

    data = await state.get_data()
    
    if data.get("need_dist"):
        await call.message.answer("🎉 اكتب عدد التوزيعات:")
        await OrderState.dist_count.set()
        return
    
    await call.message.answer("📏 اختر القياس:", reply_markup=size_kb())
    await OrderState.size.set()

# ================= DISTRIBUTION COUNT =================
@dp.message_handler(state=OrderState.dist_count)
async def get_dist(msg: types.Message, state: FSMContext):
    count = msg.text.strip()
    
    if not validate_dist_count(count):
        await msg.answer("❌ أدخل رقماً صحيحاً أكبر من 0:")
        return
    
    await state.update_data(dist_count=count)
    await msg.answer("📏 اختر القياس:", reply_markup=size_kb())
    await OrderState.size.set()

# ================= SIZE =================
@dp.callback_query_handler(lambda c: c.data.startswith("size_"), state=OrderState.size)
async def get_size(call: types.CallbackQuery, state: FSMContext):
    size = call.data.split("size_", 1)[1]
    await state.update_data(size=size)
    await call.message.answer("💰 اكتب سعر الطلب (مثال: 150.50):")
    await OrderState.price.set()

# ================= PRICE =================
@dp.message_handler(state=OrderState.price)
async def get_price(msg: types.Message, state: FSMContext):
    price = msg.text.strip()
    
    if not validate_price(price):
        await msg.answer("❌ أدخل سعراً صحيحاً (مثال: 150 أو 150.50):")
        return
    
    await state.update_data(price=price)
    await msg.answer("📝 ملاحظات؟ (اكتب 'لا' إذا لم تكن هناك ملاحظات):")
    await OrderState.notes.set()

# ================= NOTES =================
@dp.message_handler(state=OrderState.notes)
async def get_notes(msg: types.Message, state: FSMContext):
    notes = "لا يوجد" if msg.text.strip().lower() in ["لا", "لايوجد", "ليس"] else msg.text.strip()
    await state.update_data(notes=notes)
    await msg.answer("📸 ارسل الصور (1-4 صور) ثم اكتب 'تم'\n\n💡 أو اكتب 'تم' مباشرة بدون صور")
    await state.update_data(images=[])
    await OrderState.images.set()

# ================= IMAGES =================
@dp.message_handler(content_types=['photo'], state=OrderState.images)
async def get_images(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    images = data.get("images", [])
    
    if len(images) >= 4:
        await msg.answer("❌ الحد الأقصى هو 4 صور!")
        return
    
    images.append(msg.photo[-1].file_id)
    await state.update_data(images=images)
    await msg.answer(f"✅ تم حفظ الصورة ({len(images)}/4)\n\n💡 اكتب 'تم' لإنهاء الطلب")

@dp.message_handler(state=OrderState.images)
async def finish_order(msg: types.Message, state: FSMContext):
    text_input = msg.text.strip().lower()
    
    if "تم" not in text_input and text_input != "done":
        await msg.answer("❌ اكتب 'تم' لإنهاء الطلب أو أرسل صورة (1-4)")
        return
    
    try:
        order_id = get_next_order_id()
        data = await state.get_data()
        images_list = data.get("images", [])

        orders_data[order_id] = {
            "data": data,
            "images": images_list,
            "current_group": "new"
        }

        await save_to_excel({**data, "id": order_id})

        text = format_order_text(data, order_id, "new")
        status_kb = get_status_buttons(order_id, "new")

        if images_list:
            media = [InputMediaPhoto(media=i) for i in images_list]
            print(f"📸 إرسال {len(images_list)} صور للكروب {GROUP_NEW}")
            await bot.send_media_group(chat_id=GROUP_NEW, media=media)
        
        print(f"📝 إرسال نص الطلب #{order_id} للكروب {GROUP_NEW}")
        msg_result = await bot.send_message(
            chat_id=GROUP_NEW, 
            text=text, 
            reply_markup=status_kb, 
            parse_mode='Markdown'
        )
        
        print(f"✅ تم إرسال الطلب #{order_id} بنجاح")
        await msg.answer(f"✅ تم إنشاء الطلب بنجاح!\n\n📌 رقم الطلب: {order_id}")
    
    except Exception as e:
        print(f"❌ خطأ في الإرسال: {type(e).__name__}: {e}")
        await msg.answer(f"❌ خطأ: {str(e)}")

    await state.finish()

# ================= MOVE ORDER =================
@dp.callback_query_handler(lambda c: c.data.startswith("move_"))
async def move_order(call: types.CallbackQuery):
    try:
        parts = call.data.split("_")
        order_id = int(parts[1])
        target_group_name = parts[2]

        if order_id not in orders_data:
            await call.answer("❌ لم أستطع العثور على الطلب!", show_alert=True)
            return

        order_info = orders_data[order_id]
        data = order_info["data"]
        images_list = order_info["images"]
        current_group = order_info["current_group"]

        if current_group == target_group_name:
            await call.answer("🔔 الطلب موجود بالفعل هنا!", show_alert=True)
            return

        target_group_id = GROUPS_MAP.get(target_group_name)
        if not target_group_id:
            await call.answer("❌ خطأ في الكروب!", show_alert=True)
            return

        text = format_order_text(data, order_id, target_group_name)
        status_kb = get_status_buttons(order_id, target_group_name)

        if images_list:
            media = [InputMediaPhoto(media=i) for i in images_list]
            await bot.send_media_group(chat_id=target_group_id, media=media)
        
        await bot.send_message(
            chat_id=target_group_id, 
            text=text, 
            reply_markup=status_kb, 
            parse_mode='Markdown'
        )

        await call.message.delete()
        orders_data[order_id]["current_group"] = target_group_name

        target_group_display = GROUPS_NAMES.get(target_group_id, "غير معروف")
        await call.answer(f"✅ تم النقل إلى {target_group_display}", show_alert=False)

    except Exception as e:
        print(f"❌ خطأ: {type(e).__name__}: {e}")
        await call.answer(f"❌ خطأ: {str(e)}", show_alert=True)

# ================= RUN =================
if __name__ == "__main__":
    print("🚀 البوت يعمل الآن...")
    executor.start_polling(dp, skip_updates=True)

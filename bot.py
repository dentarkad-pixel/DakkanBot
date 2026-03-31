import os
import re
import json
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

# خريطة الكروبات
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

# قاموس لتخزين معلومات الطلبات (تخزين مؤقت في الذاكرة)
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
    """احصل على رقم الطلب التالي من الإكسل"""
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
    """احفظ بيانات الطلب في الإكسل"""
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
    """تحقق من صيغة رقم الهاتف"""
    phone = phone.strip()
    return bool(re.match(r'^[0-9\+\-\s\(\)]{7,15}$', phone))

def validate_price(price: str) -> bool:
    """تحقق من صيغة السعر"""
    price = price.strip()
    try:
        float(price)
        return True
    except ValueError:
        return False

def validate_dist_count(count: str) -> bool:
    """تحقق من عدد التوزيعات"""
    count = count.strip()
    try:
        num = int(count)
        return num > 0
    except ValueError:
        return False

# ================= GENERATE STATUS BUTTONS =================
def get_status_buttons(order_id: int, current_group: str = "new"):
    """احصل على أزرار الحالة بناءً على الكروب الحالي"""
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

# ================= FORMAT ORDER TEXT =================
def format_order_text(data: dict, order_id: int, current_group: str = "new") -> str:
    """نسق نص الطلب"""
    over = data.get("over_type", "لا يوجد")
    hand = data.get("hand_type", "لا يوجد")
    box = data.get("box_color", "لا يوجد")
    dist = data.get("dist_count", "لا يوجد")

    group_display = GROUPS_NAMES.get(GROUPS_MAP.get(current_group), "غير معروف")

    text = f"""
📦 *طلب #{order_id}*

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
📍 *الحالة الحالية:* {group_display}
"""
    return text

# ================= START =================
@dp.message_handler(commands=['start'])
async def start(msg: types.Message, state: FSMContext):
    """بدء البوت وتصفير أي حالة معلقة"""
    await state.finish()
    await msg.answer("👋 مرحباً! اكتب /new لإنشاء طلب جديد")

# ================= NEW ORDER =================
@dp.message_handler(commands=['new'])
async def new_order(msg: types.Message, state: FSMContext):
    """ابدأ طلب جديد"""
    await state.finish()
    await msg.answer("👤 اسم الزبون:")
    await OrderState.name.set()

# ================= COLLECT INFO =================
@dp.message_handler(state=OrderState.name)
async def get_name(msg: types.Message, state: FSMContext):
    """احصل على اسم الزبون"""
    name = msg.text.strip()
    if len(name) < 2:
        await msg.answer("❌ الاسم قصير جداً، حاول مرة أخرى:")
        return
    
    await state.update_data(name=name)
    await msg.answer("📞 رقم الهاتف:")
    await OrderState.phone.set()

@dp.message_handler(state=OrderState.phone)
async def get_phone(msg: types.Message, state: FSMContext):
    """احصل على رقم الهاتف مع التحقق"""
    phone = msg.text.strip()
    if not validate_phone(phone):
        await msg.answer("❌ صيغة الهاتف غير صحيحة. حاول مرة أخرى (مثال: 966501234567):")
        return
    
    await state.update_data(phone=phone)
    await msg.answer("📍 المدينة:")
    await OrderState.city.set()

@dp.message_handler(state=OrderState.city)
async def get_city(msg: types.Message, state: FSMContext):
    """احصل على المدينة"""
    city = msg.text.strip()
    if len(city) < 2:
        await msg.answer("❌ اسم المدينة قصير جداً، حاول مرة أخرى:")
        return
    
    await state.update_data(city=city)
    await msg.answer("🏘 المنطقة:")
    await OrderState.area.set()

@dp.message_handler(state=OrderState.area)
async def get_area(msg: types.Message, state: FSMContext):
    """احصل على المنطقة واعرض أنواع الطلب"""
    area = msg.text.strip()
    if len(area) < 2:
        await msg.answer("❌ اسم المنطقة قصير جداً، حاول مرة أخرى:")
        return
    
    await state.update_data(area=area)
    await msg.answer("🧵 اختر نوع الطلب:", reply_markup=order_type_kb())
    await OrderState.order_type.set()

# ================= ORDER TYPE =================
def order_type_kb():
    """لوحة مفاتيح نوع الطلب"""
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🖨 طباعة", callback_data="type_print"),
        InlineKeyboardButton("🧵 تطريز", callback_data="type_emb")
    )
    return kb

@dp.callback_query_handler(lambda c: c.data.startswith("type_"), state=OrderState.order_type)
async def choose_type(call: types.CallbackQuery, state: FSMContext):
    """اختر نوع الطلب"""
    order_type = "طباعة" if call.data == "type_print" else "تطريز"
    await state.update_data(order_type=order_type)
    await call.message.edit_text("👕 اختر القطع (يمكنك اختيار أكثر من واحد):", reply_markup=pieces_kb([]))
    await state.update_data(pieces=[])
    await OrderState.pieces.set()

# ================= PIECES =================
pieces_list = [
    "سيت 3", "سيت 6", "أوفر", "كلو", "صدرية", 
    "حضينة وكماط", "ملحف", "بوكس ككو", "توزيعات"
]

def pieces_kb(selected):
    """لوحة مفاتيح القطع"""
    kb = InlineKeyboardMarkup(row_width=2)
    for p in pieces_list:
        mark = "✅" if p in selected else "☐"
        kb.insert(InlineKeyboardButton(f"{mark} {p}", callback_data=f"piece_{p}"))
    kb.add(InlineKeyboardButton("✔️ تم", callback_data="done_pieces"))
    return kb

@dp.callback_query_handler(lambda c: c.data.startswith("piece_"), state=OrderState.pieces)
async def choose_pieces(call: types.CallbackQuery, state: FSMContext):
    """اختر/ألغ القطع"""
    data = await state.get_data()
    selected = data.get("pieces", [])
    piece = call.data.split("piece_", 1)[1]

    if piece in selected:
        selected.remove(piece)
    else:
        selected.append(piece)

    await state.update_data(pieces=selected)
    await call.message.edit_reply_markup(reply_markup=pieces_kb(selected))

# ================= SMART CONDITIONAL LOGIC =================
@dp.callback_query_handler(lambda c: c.data == "done_pieces", state=OrderState.pieces)
async def done_pieces(call: types.CallbackQuery, state: FSMContext):
    """تحقق من الأسئلة المشروطة"""
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
        kb = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("🎀 دانتيل", callback_data="over_دانتيل"),
            InlineKeyboardButton("🧵 طباكات", callback_data="over_طباكات"),
            InlineKeyboardButton("📄 صفح", callback_data="over_صفح"),
            InlineKeyboardButton("🎀🧵 دانتيل طباكات", callback_data="over_دانتيل+طباكات")
        )
        await call.message.answer("✨ نوع الأوفر:", reply_markup=kb)
        await OrderState.over_type.set()
        return

    if need_hand:
        kb = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("🎀 كشكش", callback_data="hand_كشكش"),
            InlineKeyboardButton("🌸 حب الرمان", callback_data="hand_حب الرمان")
        )
        await call.message.answer("🛏 نوع الملحف:", reply_markup=kb)
        await OrderState.hand_type.set()
        return

    if need_box:
        await ask_box(call.message)
        await OrderState.box_color.set()
        return

    if need_dist:
        await call.message.answer("🎉 اكتب عدد التوزيعات:")
        await OrderState.dist_count.set()
        return

    await ask_size(call.message)
    await OrderState.size.set()

# ================= OVER TYPE =================
@dp.callback_query_handler(lambda c: c.data.startswith("over_"), state=OrderState.over_type)
async def choose_over(call: types.CallbackQuery, state: FSMContext):
    """اختر نوع الأوفر"""
    over_choice = call.data.split("over_", 1)[1]
    await state.update_data(over_type=over_choice)

    data = await state.get_data()
    
    if data.get("need_hand"):
        kb = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("🎀 كشكش", callback_data="hand_كشكش"),
            InlineKeyboardButton("🌸 حب الرمان", callback_data="hand_حب الرمان")
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

# ================= HAND TYPE =================
@dp.callback_query_handler(lambda c: c.data.startswith("hand_"), state=OrderState.hand_type)
async def choose_hand(call: types.CallbackQuery, state: FSMContext):
    """اختر نوع الملحف"""
    hand_choice = call.data.split("hand_", 1)[1]
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

# ================= BOX COLOR =================
def ask_box(msg):
    """اسأل عن لون البوكس"""
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("⚪ أبيض", callback_data="box_أبيض"),
        InlineKeyboardButton("⚫ رصاصي", callback_data="box_رصاصي"),
        InlineKeyboardButton("🩷 وردي", callback_data="box_وردي"),
        InlineKeyboardButton("🩵 سماوي", callback_data="box_سماوي")
    )
    return msg.answer("🎁 اختر لون البوكس:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("box_"), state=OrderState.box_color)
async def choose_box(call: types.CallbackQuery, state: FSMContext):
    """اختر لون البوكس"""
    box_color = call.data.split("box_", 1)[1]
    await state.update_data(box_color=box_color)

    data = await state.get_data()
    
    if data.get("need_dist"):
        await call.message.answer("🎉 اكتب عدد التوزيعات:")
        await OrderState.dist_count.set()
        return
    
    await ask_size(call.message)
    await OrderState.size.set()

# ================= DISTRIBUTION COUNT =================
@dp.message_handler(state=OrderState.dist_count)
async def get_dist(msg: types.Message, state: FSMContext):
    """احصل على عدد التوزيعات مع التحقق"""
    count = msg.text.strip()
    
    if not validate_dist_count(count):
        await msg.answer("❌ أدخل رقماً صحيحاً أكبر من 0:")
        return
    
    await state.update_data(dist_count=count)
    await ask_size(msg)
    await OrderState.size.set()

# ================= SIZE =================
sizes = ["حديثي ولادة", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]

def size_kb():
    """لوحة مفاتيح القياسات"""
    kb = InlineKeyboardMarkup(row_width=4)
    for s in sizes:
        kb.insert(InlineKeyboardButton(s, callback_data=f"size_{s}"))
    return kb

async def ask_size(msg):
    """اسأل عن القياس"""
    await msg.answer("📏 اختر القياس:", reply_markup=size_kb())

@dp.callback_query_handler(lambda c: c.data.startswith("size_"), state=OrderState.size)
async def get_size(call: types.CallbackQuery, state: FSMContext):
    """اختر القياس"""
    size = call.data.split("size_", 1)[1]
    await state.update_data(size=size)
    await call.message.answer("💰 اكتب سعر الطلب (مثال: 150.50):")
    await OrderState.price.set()

# ================= PRICE =================
@dp.message_handler(state=OrderState.price)
async def get_price(msg: types.Message, state: FSMContext):
    """احصل على السعر مع التحقق"""
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
    """احصل على الملاحظات"""
    notes = "لا يوجد" if msg.text.strip().lower() in ["لا", "لايوجد", "ليس"] else msg.text.strip()
    await state.update_data(notes=notes)
    await msg.answer("📸 ارسل الصور (1-4 صور) ثم اكتب 'تم'")
    await state.update_data(images=[])
    await OrderState.images.set()

# ================= IMAGES =================
@dp.message_handler(content_types=['photo'], state=OrderState.images)
async def get_images(msg: types.Message, state: FSMContext):
    """احصل على الصور"""
    data = await state.get_data()
    images = data.get("images", [])
    
    if len(images) >= 4:
        await msg.answer("❌ الحد الأقصى هو 4 صور!")
        return
    
    images.append(msg.photo[-1].file_id)
    await state.update_data(images=images)
    await msg.answer(f"✅ تم حفظ الصورة ({len(images)}/4)")

@dp.message_handler(lambda m: m.text.strip().lower() in ["تم", "done"], state=OrderState.images)
async def finish_order(msg: types.Message, state: FSMContext):
    """إنهاء الطلب وإرساله"""
    order_id = get_next_order_id()
    data = await state.get_data()
    images_list = data.get("images", [])

    # احفظ بيانات الطلب في الذاكرة
    orders_data[order_id] = {
        "data": data,
        "images": images_list,
        "current_group": "new"
    }

    # احفظ في الإكسل
    await save_to_excel({**data, "id": order_id})

    # نسق نص الطلب
    text = format_order_text(data, order_id, "new")
    
    # أزرار الحالة
    status_kb = get_status_buttons(order_id, "new")

    # إرسال الصور أولاً إذا كانت موجودة
    try:
        if images_list:
            media = [InputMediaPhoto(media=i) for i in images_list]
            await bot.send_media_group(GROUP_NEW, media)
        
        # إرسال نص الطلب مع الأزرار
        await bot.send_message(GROUP_NEW, text, reply_markup=status_kb, parse_mode='Markdown')
        await msg.answer("✅ تم إنشاء الطلب بنجاح!")
    
    except Exception as e:
        await msg.answer(f"❌ خطأ: {str(e)}")
        print(f"❌ خطأ في إرسال الطلب: {e}")

    await state.finish()

# ================= CHANGE STATUS / MOVE ORDER =================
@dp.callback_query_handler(lambda c: c.data.startswith("move_"))
async def move_order(call: types.CallbackQuery):
    """انقل الطلب إلى كروب آخر"""
    try:
        parts = call.data.split("_")
        order_id = int(parts[1])
        target_group_name = parts[2]

        # تحقق من وجود الطلب
        if order_id not in orders_data:
            await call.answer("❌ لم أستطع العثور على بيانات الطلب!", show_alert=True)
            return

        order_info = orders_data[order_id]
        data = order_info["data"]
        images_list = order_info["images"]
        current_group = order_info["current_group"]

        # تحقق من أن الكروب الجديد مختلف عن الحالي
        if current_group == target_group_name:
            await call.answer("🔔 الطلب موجود بالفعل هنا!", show_alert=True)
            return

        # احصل على معرف الكروب الجديد
        target_group_id = GROUPS_MAP.get(target_group_name)
        if not target_group_id:
            await call.answer("❌ خطأ في الكروب المستهدف!", show_alert=True)
            return

        # نسق نص الطلب
        text = format_order_text(data, order_id, target_group_name)
        status_kb = get_status_buttons(order_id, target_group_name)

        # أرسل الصور والنص في الكروب الجديد
        if images_list:
            media = [InputMediaPhoto(media=i) for i in images_list]
            await bot.send_media_group(target_group_id, media)
        
        await bot.send_message(target_group_id, text, reply_markup=status_kb, parse_mode='Markdown')

        # احذف الرسالة من الكروب السابق
        await call.message.delete()

        # حدّث معلومات الطلب
        orders_data[order_id]["current_group"] = target_group_name

        target_group_display = GROUPS_NAMES.get(target_group_id, "غير معروف")
        await call.answer(f"✅ تم نقل الطلب إلى {target_group_display}", show_alert=False)

    except ValueError:
        await call.answer("❌ خطأ في معالجة الطلب!", show_alert=True)
    except Exception as e:
        print(f"❌ خطأ في نقل الطلب: {e}")
        await call.answer(f"❌ خطأ: {str(e)}", show_alert=True)

# ================= RUN =================
if __name__ == "__main__":
    print("🚀 البوت يعمل الآن...")
    executor.start_polling(dp, skip_updates=True)

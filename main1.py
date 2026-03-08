import telebot
from telebot import types
import requests
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import random
import string
TOKEN = "8413470357:AAF9kCNNP1MsUzxBBiVyu2tXR7GQ_Pg5nKs"
FIREBASE_URL = "https://asthmar-8b9a6-default-rtdb.firebaseio.com"
DATABASE_SECRET = "FqqoLMBh6gbbXhmvvcC1KQ0rJOIkbPUwnfaoESOj"
CH_USER = "@my00002"
ADMIN_USER = "@altaee_z"
BOT_NAME = "البوت الالكتروني المحترف "
POINT_NAME = "نقطة"
ADMIN_ID = 6454550864
bot = telebot.TeleBot(TOKEN)
def fb_get(path):
    return requests.get(f"{FIREBASE_URL}/{path}.json?auth={DATABASE_SECRET}").json()

def fb_patch(path, data):
    requests.patch(f"{FIREBASE_URL}/{path}.json?auth={DATABASE_SECRET}", json.dumps(data))

default_counters = {
    "c1": {"name": "عداد المبتدئ", "value": 100, "price": 1000, "duration": 365, "desc": "يعطيك 100 نقطة يومياً لمدة سنة"},
    "c2": {"name": "عداد المحترف", "value": 500, "price": 4000, "duration": 365, "desc": "يعطيك 500 نقطة يومياً لمدة سنة"},
    "c3": {"name": "عداد الملكي", "value": 1200, "price": 8000, "duration": 365, "desc": "يعطيك 1200 نقطة يومياً لمدة سنة"}
}
if not fb_get("counters"):
    fb_patch("counters", default_counters)

def auto_reward_task():
    users = fb_get("users")
    if not users: return
    
    now = datetime.now()
    for uid, data in users.items():
        if "last_claim" in data and "active_counter_val" in data:
            last_c = datetime.strptime(data['last_claim'], '%Y-%m-%d %H:%M:%S')
            if now >= last_c + timedelta(hours=24):
                new_pts = data['points'] + data['active_counter_val']
                fb_patch(f"users/{uid}", {
                    "points": new_pts,
                    "last_claim": now.strftime('%Y-%m-%d %H:%M:%S')
                })
                bot.send_message(uid, f"💰 <b>تم إضافة {data['active_counter_val']} {POINT_NAME} إلى حسابك تلقائياً!</b>\nنقاطك الحالية: {new_pts}\nتحديثك القادم بعد 24 ساعة.", parse_mode="HTML")

        if "expiry_date" in data:
            exp = datetime.strptime(data['expiry_date'], '%Y-%m-%d %H:%M:%S')
            if now >= exp: # انتهى الوقت
                fb_patch(f"users/{uid}", {"active_counter_val": 0, "expiry_date": None, "counter": 0})
                bot.send_message(uid, "⚠️ <b>تنبيه: انتهت مدة العداد الخاص بك وتم حذفه.</b>", parse_mode="HTML")
            elif now >= exp - timedelta(days=2): # قبل يومين
                if not data.get("expiry_notified"):
                    bot.send_message(uid, f"⚠️ <b>تنبيه: عدادك سينتهي بعد يومين بتاريخ {data['expiry_date']}!</b>", parse_mode="HTML")
                    fb_patch(f"users/{uid}", {"expiry_notified": True})

sched = BackgroundScheduler()
sched.add_job(auto_reward_task, 'interval', minutes=1)
sched.start()
@bot.callback_query_handler(func=lambda call: call.data == "contact_admin")
def contact_admin_start(call):
    msg = bot.send_message(call.message.chat.id, "📥 **أرسل مشكلتك الآن (نص، صورة، أو فيديو):**\nيمكنك شرح المشكلة بالتفصيل وسأقوم بإيصالها للمطور فوراً.", parse_mode="Markdown")
    bot.register_next_step_handler(msg, forward_to_admin)

def forward_to_admin(message):
    uid = str(message.from_user.id)
    name = message.from_user.first_name
    user_username = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"
    
    user_data = fb_get(f"users/{uid}") or {}
    points = user_data.get('points', 0)
    counter = user_data.get('counter', 0)

    info_text = f"""
📩 رسالة جديدة من مستخدم:
━━━━━━━━━━━━━━
👤 الاسم: {name}
🆔 الآيدي: <code>{uid}</code>
🔗 اليوزر: {user_username}
💰 النقاط: {points} | 📊 العداد: {counter}
━━━━━━━━━━━━━━
👇 الرسالة أدناه:
    """
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 رد على المستخدم", callback_data=f"reply_to_{uid}"))

    bot.send_message(ADMIN_ID, info_text, parse_mode="HTML")
    
    if message.content_type == 'text':
        bot.send_message(ADMIN_ID, f"📝 النص:\n{message.text}", reply_markup=markup)
    elif message.content_type == 'photo':
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🖼 صورة من المستخدم\n{message.caption or ''}", reply_markup=markup)
    elif message.content_type == 'video':
        bot.send_video(ADMIN_ID, message.video.file_id, caption=f"📹 فيديو من المستخدم\n{message.caption or ''}", reply_markup=markup)
    
    log_data = {
        "from": uid,
        "type": message.content_type,
        "content": message.text if message.content_type == 'text' else "Media File",
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    fb_patch("support_logs", log_data)

    bot.send_message(uid, "✅ تم إرسال رسالتك للإدارة بنجاح، انتظر الرد قريباً.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_to_"))
def admin_reply_start(call):
    target_uid = call.data.replace("reply_to_", "")
    msg = bot.send_message(ADMIN_ID, f"✍️ **أكتب ردك الآن للمستخدم ({target_uid}):**\n(يمكنك إرسال نص، صورة، أو فيديو)")
    bot.register_next_step_handler(msg, send_reply_to_user, target_uid)

def send_reply_to_user(message, target_uid):
    try:
        header = "🔔 رد من الإدارة:\n━━━━━━━━━━━━━━\n"
        
        if message.content_type == 'text':
            bot.send_message(target_uid, header + message.text, parse_mode="Markdown")
        elif message.content_type == 'photo':
            bot.send_photo(target_uid, message.photo[-1].file_id, caption=header + (message.caption or ""))
        elif message.content_type == 'video':
            bot.send_video(target_uid, message.video.file_id, caption=header + (message.caption or ""))
        
        bot.send_message(ADMIN_ID, "✅ تم إرسال الرد للمستخدم بنجاح.")
        
        fb_patch("support_replies", {"to": target_uid, "reply": "Media/Text", "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ فشل إرسال الرد. قد يكون المستخدم حظر البوت.\n{e}")        

def main_markup():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("📊 قسم العدادات", callback_data="list_c"),
        types.InlineKeyboardButton("💰 قسم السحب", callback_data="withdraw_home"),
        types.InlineKeyboardButton("🔗 رابط الدعوة", callback_data="ref_link"),
        types.InlineKeyboardButton("👤 منو دعاني؟", callback_data="who_invited_me"),
        types.InlineKeyboardButton("🎫 استخدام كوبون", callback_data="use_coupon"),
        types.InlineKeyboardButton("💳 قسم الوكلاء", callback_data="agents"),
        types.InlineKeyboardButton("🔄 تحويل النقاط", callback_data="transfer"),
        types.InlineKeyboardButton("🎁 إهداء العداد", callback_data="gift_c"),
        types.InlineKeyboardButton("🎁 الهدية اليومية", callback_data="daily_gift"),
        types.InlineKeyboardButton("🛠 الدعم الفني", url="t.me/altaee_z"),
        types.InlineKeyboardButton("💼 لوحة الوكلاء", callback_data="agent_panel"),
        types.InlineKeyboardButton("👨‍💻 تواصل مع الإدارة", callback_data="contact_admin")
    )
    return m
def save_withdraw_info(message, data_raw):
    uid = str(message.from_user.id)
    info = message.text
    parts = data_raw.split("_")
    item_type = parts[1]
    price = int(parts[2])
    
    order_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("✅ نعم، متأكد", callback_data=f"final_{order_id}_{price}_{item_type}"))
    m.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="withdraw_home"))
    
    bot.send_message(uid, f"هل أنت متأكد من إرسال الطلب؟\n\nالمعلومات: {info}\nالكمية: {item_type}\nالكود: {order_id}", reply_markup=m)
    
    fb_patch(f"pending_orders/{order_id}", {"uid": uid, "info": info, "type": item_type, "price": price})
def send_proof_to_user(message, order_data):
    user_id = order_data['uid']
    if message.content_type == 'photo':
        bot.send_photo(user_id, message.photo[-1].file_id, caption=f"✅ تم قبول طلبك {order_data['type']}!\nتم الخصم بنجاح.")
    else:
        bot.send_message(user_id, f"✅ تم قبول طلبك {order_data['type']}!\n\nالإثبات: {message.text}")
    
    channel_text = f"""
✅ إثبات سحب جديد!
👤 المستخدم: {user_id}
🏷 الفئة: {order_data['type']}
💰 المبلغ: {order_data['price']}
⏰ الحالة: تم الدفع بنجاح
__________________
حقوق البوت: @altaee_z
    """
    bot.send_message(CH_USER, channel_text)
    bot.send_message(ADMIN_ID, "✅ تم إرسال الإثبات ونشر الحالة في القناة.")   
def get_receiver_id(message):
    uid = str(message.from_user.id)
    receiver_id = message.text
    
    if not receiver_id.isdigit():
        return bot.send_message(uid, "❌ يرجى إرسال آيدي صحيح (أرقام فقط).")
    
    if receiver_id == uid:
        return bot.send_message(uid, "❌ لا يمكنك التحويل لنفسك!")
        
    receiver_data = fb_get(f"users/{receiver_id}")
    if not receiver_data:
        return bot.send_message(uid, "❌ هذا الآيدي غير موجود في قاعدة بيانات البوت.")
    
    try:
        chat = bot.get_chat(receiver_id)
        receiver_name = chat.first_name # يجيب اسمه الأول من تليجرام
        receiver_user = f"@{chat.username}" if chat.username else "لا يوجد يوزر"
    except:
        receiver_name = "مستخدم غير معروف"
        receiver_user = "غير متوفر"

    text = f"""
🔍 معلومات المستلم :
👤 اسمه: <b>{receiver_name}</b>
🆔 ايديه: <code>{receiver_id}</code>
🔗 يوزره: {receiver_user}
💰 نقاطه الحالية: {receiver_data.get('points', 0)}

💵 كم عدد النقاط التي تريد تحويلها؟
(سيتم خصم 200 نقطة إضافية كعمولة)
    """
    msg = bot.send_message(uid, text, parse_mode="HTML")
    bot.register_next_step_handler(msg, get_transfer_amount, receiver_id)

def get_transfer_amount(message, receiver_id):
    uid = str(message.from_user.id)
    try:
        amount = int(message.text)
    except:
        return bot.send_message(uid, "❌ يرجى إرسال أرقام فقط.")
        
    if amount <= 0:
        return bot.send_message(uid, "❌ يجب أن يكون المبلغ أكبر من 0.")
        
    u_sender = fb_get(f"users/{uid}")
    total_needed = amount + 200 # المبلغ + العمولة
    
    if u_sender.get('points', 0) < total_needed:
        return bot.send_message(uid, f"❌ نقاطك لا تكفي! تحتاج إلى {total_needed} نقطة (شاملة العمولة).")
        
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("✅ موافق، حول الآن", callback_data=f"confirmtr_{receiver_id}_{amount}"))
    m.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="back_main"))
    
    bot.send_message(uid, f"⚠️ **تأكيد التحويل:**\n\nستقوم بتحويل {amount} نقطة إلى {receiver_id}.\nسيتم خصم {total_needed} من رصيدك.\n\nهل أنت متأكد؟", reply_markup=m)
def get_gift_receiver_id(message):
    uid = str(message.from_user.id)
    receiver_id = message.text
    
    if not receiver_id.isdigit() or receiver_id == uid:
        return bot.send_message(uid, "❌ آيدي غير صالح!")
        
    receiver_data = fb_get(f"users/{receiver_id}")
    if not receiver_data:
        return bot.send_message(uid, "❌ هذا المستخدم غير مسجل في البوت.")
    
    try:
        chat = bot.get_chat(receiver_id)
        receiver_name = chat.first_name
    except:
        receiver_name = "مستخدم البوت"

    text = f"🔍 **المستلم:** {receiver_name}\n🆔 **الآيدي:** <code>{receiver_id}</code>\n📊 **عداد المستلم الحالي:** {receiver_data.get('counter', 0)}\n\n⚡️ **كم تريد إهداء من قيمة عدادك؟**"
    msg = bot.send_message(uid, text, parse_mode="HTML")
    bot.register_next_step_handler(msg, get_gift_amount, receiver_id)

def get_gift_amount(message, receiver_id):
    uid = str(message.from_user.id)
    try:
        gift_val = int(message.text)
    except:
        return bot.send_message(uid, "❌ أرقام فقط!")
        
    u_sender = fb_get(f"users/{uid}")
    if gift_val <= 0 or gift_val > u_sender.get('counter', 0):
        return bot.send_message(uid, "❌ القيمة غير صالحة أو أكبر من قيمة عدادك!")
        
    commission = int(gift_val * 0.02) # عمولة 2%
    total_deduct = gift_val + commission # الخصم من المحول (القيمة + العمولة)
    
    if u_sender.get('counter', 0) < total_deduct:
         return bot.send_message(uid, f"❌ عدادك لا يكفي! تحتاج {total_deduct} (القيمة + 2% عمولة).")

    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("✅ تأكيد الإهداء", callback_data=f"conf_gift_{receiver_id}_{gift_val}"))
    m.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="back_main"))
    
    bot.send_message(uid, f"⚠️ **تأكيد عملية الإهداء:**\n\nستقوم بإرسال {gift_val} من قيمة عدادك إلى {receiver_id}.\nسيتم خصم {total_deduct} من عدادك (شاملة العمولة).\n\nهل أنت متأكد؟", reply_markup=m)  
def update_daily_button(chat_id, message_id, time_left):
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton(f"🕒 الهدية القادمة بعد: {time_left}", callback_data="daily_gift"))
    m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
    try:
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=m)
    except:
        pass
@bot.message_handler(commands=['start'])
def start(message):
    if hasattr(message, 'message'): # يعني جاي من زر (CallbackQuery)
        uid = str(message.from_user.id)
        msg_text = "" # لا يوجد نص للفحص
        is_callback = True
    else: # يعني جاي من أمر /start حقيقي
        uid = str(message.from_user.id)
        msg_text = message.text if message.text else ""
        is_callback = False

    user_data = fb_get(f"users/{uid}")

    if not user_data:
        text_args = msg_text.split()
        inviter_id = None
        if len(text_args) > 1:
            potential_inviter = text_args[1]
            if potential_inviter != uid:
                inviter_id = potential_inviter

        new_user = {
            "points": 0,
            "counter": 0,
            "invited_by": inviter_id,
            "join_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "referrals": 0,
            "last_daily_gift": None,
            "expiry_date": None,
            "purchased": 0,
            "daily_gifts": 0
        }
        fb_patch(f"users/{uid}", new_user)

        if inviter_id:
            inviter_data = fb_get(f"users/{inviter_id}")
            if inviter_data:
                new_points = inviter_data.get('points', 0) + 1000
                new_refs = inviter_data.get('referrals', 0) + 1
                fb_patch(f"users/{inviter_id}", {"points": new_points, "referrals": new_refs})
                try:
                    bot.send_message(inviter_id, f"✅ مستخدم جديد انضم عبر رابطك!\n🎁 حصلت على <b>1000</b> نقطة.\n📊 إجمالي دعواتك الآن: {new_refs}", parse_mode="HTML")
                except: pass

    try:
        status = bot.get_chat_member(CH_USER, uid).status
        if status in ['left', 'kicked']:
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("اشترك هنا", url=f"t.me/{CH_USER[1:]}"))
            return bot.send_message(uid, f"❌ يجب الاشتراك في {CH_USER} أولاً!", reply_markup=btn)
    except: pass

    user = fb_get(f"users/{uid}")
    if not user: user = {}

    welcome_msg = f"""
اهلا بك عزيزي <b>{message.from_user.first_name}</b> في هذا البوت <b>({BOT_NAME})</b> 

🆔 ايديك: <code>{uid}</code>
💰 عدد نقاطك: <b>{user.get('points', 0)}</b>
📊 عدادك: <b>{user.get('counter', 0)}</b>
🛒 السلع المشتراة: <b>{user.get('purchased', 0)}</b>
🎁 الهدايا اليومية: <b>{user.get('daily_gifts', 0)}</b>
👥 مشاركات الرابط: <b>{user.get('referrals', 0)}</b>

🔗 رابط الدعوة الخاص بك: 
https://t.me/{bot.get_me().username}?start={uid}

__________________
🤍 تلجرام : <a href="https://t.me/altaee_z">@altaee_z</a> 
🌐 موقعي : <a href="http://www.ali-Altaee.free.nf">www.ali-Altaee.free.nf</a>
    """

    if is_callback:
        try:
            bot.edit_message_text(welcome_msg, uid, message.message.message_id, reply_markup=main_markup(), parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            # إذا فشل التعديل لأي سبب (رسالة مفقودة أو قديمة)، نرسل رسالة جديدة
            bot.send_message(uid, welcome_msg, reply_markup=main_markup(), parse_mode="HTML", disable_web_page_preview=True)
    else:
        bot.send_message(uid, welcome_msg, reply_markup=main_markup(), parse_mode="HTML", disable_web_page_preview=True)
CH_LOGS = "@my00002" # يوزر قناتك للتوثيق

@bot.callback_query_handler(func=lambda call: call.data == "agent_panel")
def agent_panel(call):
    uid = str(call.from_user.id)
    agent_data = fb_get(f"agents/{uid}")
    
    if not agent_data:
        return bot.answer_callback_query(call.id, "❌ نعتذر، أنت لست مسجلاً كوكيل معتمد. لشراء النفاط وتفعيل العدادت اذهب الى قسم الوكلاء.", show_alert=True)
    
    balance = agent_data.get('balance', 0)
    name = agent_data.get('name', call.from_user.first_name)
    
    text = f"""
💼 لوحة الوكلاء المعتمدين
━━━━━━━━━━━━━━
👤 الاسم: <b>{name}</b>
🆔 الآيدي: <code>{uid}</code>
🔗 اليوزر: @{call.from_user.username or 'لا يوجد'}
💰 رصيدك الافتراضي: <b>{balance:,}</b> نقطة
━━━━━━━━━━━━━━
    """
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ إضافة نقاط لمستخدم", callback_data="agent_add_points"),
        types.InlineKeyboardButton("💰 مطالبة برصيد", callback_data="agent_request_bal")
    )
    bot.edit_message_text(text, uid, call.message.message_id, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "agent_request_bal")
def agent_req(call):
    uid = str(call.from_user.id)
    agent_data = fb_get(f"agents/{uid}")
    balance = agent_data.get('balance', 0)
    
    admin_msg = f"🚨 طلب شحن رصيد وكيل\n\n👤 الوكيل: {call.from_user.first_name}\n🆔 الآيدي: {uid}\n💰 رصيده الحالي: {balance:,}"
    bot.send_message(ADMIN_ID, admin_msg)
    bot.answer_callback_query(call.id, "✅ تم إرسال طلبك للمطور بنجاح.", show_alert=True)

# --- عملية إضافة النقاط ---
@bot.callback_query_handler(func=lambda call: call.data == "agent_add_points")
def agent_add_start(call):
    msg = bot.send_message(call.from_user.id, "🆔 أرسل آيدي المستخدم الذي تريد تحويل النقاط له:")
    bot.register_next_step_handler(msg, agent_check_user)

def agent_check_user(message):
    target_id = message.text.strip()
    user_data = fb_get(f"users/{target_id}")
    name = message.from_user.first_name
    user_username = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"
    
    if not user_data:
        return bot.send_message(message.chat.id, "❌ هذا الآيدي غير مسجل في البوت!")
    
    info = f"""
معلومات هذا المستخدم:
━━━━━━━━━━━━━━
👤 الاسم: {name}
🔗 اليوزر: {user_username}
🆔 الآيدي: <code>{target_id}</code>
💰 نقاطه الحالية: {user_data.get('points', 0)}
━━━━━━━━━━━━━━
✅ أرسل الآن عدد النقاط التي تريد تحويلها:
    """
    msg = bot.send_message(message.chat.id, info, parse_mode="HTML")
    bot.register_next_step_handler(msg, agent_final_transfer, target_id, user_data)

def agent_final_transfer(message, target_id, user_data):
    agent_id = str(message.from_user.id)
    try:
        amount = int(message.text)
        agent_data = fb_get(f"agents/{agent_id}")
        
        if amount <= 0: return bot.send_message(agent_id, "❌ أدخل كمية صالحة!")
        if agent_data['balance'] < amount:
            return bot.send_message(agent_id, "❌ عذراً، رصيدك الافتراضي غير كافٍ!")

        new_agent_bal = agent_data['balance'] - amount
        new_user_points = user_data.get('points', 0) + amount
        
        fb_patch(f"agents/{agent_id}", {"balance": new_agent_bal})
        fb_patch(f"users/{target_id}", {"points": new_user_points})
        
        agent_link = f"https://t.me/{message.from_user.username}" if message.from_user.username else "https://t.me/altaee_z"
        msg_user = f"✅ تم تحويل <b>{amount:,}</b> نقطة لك من قبل الوكيل المعتمد!\n💰 رصيدك الآن: <b>{new_user_points:,}</b>"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👤 حساب الوكيل", url=agent_link))
        
        try: bot.send_message(target_id, msg_user, reply_markup=markup, parse_mode="HTML")
        except: pass

        log = f"""
🔄 عملية تحويل نقاط معتمدة
━━━━━━━━━━━━━━
👨‍💼 الوكيل: {message.from_user.first_name}
👤 إلى المستخدم: {target_id}
💵 الكمية: {amount:,} نقطة
📈 المجموع الجديد: {new_user_points:,}
📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}
━━━━━━━━━━━━━━
        """
        bot.send_message(CH_LOGS, log)
        bot.send_message(agent_id, f"✅ تم التحويل بنجاح!\nرصيدك الحالي: {new_agent_bal:,}")

    except:
        bot.send_message(agent_id, "❌ خطأ! يرجى إرسال أرقام فقط.")
@bot.message_handler(commands=['add_agent'])
def add_agent_cmd(message):
    uid = message.from_user.id
    if int(uid) != ADMIN_ID: # آيديك هنا
        return bot.reply_to(message, "❌ هذا الأمر للمطور فقط!")

    msg = bot.send_message(message.chat.id, 
        "➕ **إضافة وكيل جديد:**\n\n"
        "أرسل بيانات الوكيل بالشكل التالي:\n"
        "`الآيدي-الاسم-الرصيد`\n\n"
        "💡 مثال: `12345678-وكيل بغداد-50000`", 
        parse_mode="Markdown")
    
    bot.register_next_step_handler(msg, save_new_agent)

def save_new_agent(message):
    try:
        # تقسيم النص (آيدي-اسم-رصيد)
        data = message.text.split('-')
        if len(data) != 3:
            return bot.send_message(message.chat.id, "❌ خطأ في التنسيق! اتبع المثال: `آيدي-اسم-رصيد`")

        agent_id = data[0].strip()
        agent_name = data[1].strip()
        initial_balance = int(data[2].strip())

        # تجهيز بيانات الوكيل
        agent_obj = {
            "name": agent_name,
            "balance": initial_balance,
            "username": "مضاف يدوياً",
            "date_added": datetime.now().strftime('%Y-%m-%d')
        }

        # حفظ في الفايربيس بمسار agents/agent_id
        fb_patch(f"agents/{agent_id}", agent_obj)

        # رسالة نجاح
        success_text = f"""
✅ تم تعيين الوكيل بنجاح!
━━━━━━━━━━━━━━
👤 الاسم: {agent_name}
🆔 الآيدي: <code>{agent_id}</code>
💰 الرصيد الممنوح: {initial_balance:,}
━━━━━━━━━━━━━━
📢 الآن يمكن للوكيل الدخول للوحة التحكم من البوت.
        """
        bot.send_message(message.chat.id, success_text, parse_mode="HTML")
        
        try:
            bot.send_message(agent_id, f"🎉 مبروك! تم تعيينك كوكيل معتمد برصيد: {initial_balance:,} نقطة.")
        except:
            pass

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ أثناء الحفظ!\nالتفاصيل: {e}")

@bot.message_handler(commands=['del_agent'])
def del_agent_cmd(message):
    if int(message.from_user.id) != ADMIN_ID:
        return
    
    msg = bot.send_message(message.chat.id, "🗑 حذف وكيل:\nأرسل آيدي الوكيل المراد حذفه نهائياً:")
    bot.register_next_step_handler(msg, remove_agent_from_db)

def remove_agent_from_db(message):
    agent_id = message.text.strip()
    requests.delete(f"{DB_URL}agents/{agent_id}.json")
    bot.send_message(message.chat.id, f"✅ تم حذف الوكيل {agent_id} من النظام.")        
@bot.callback_query_handler(func=lambda call: True)
def handle_calls(call):
    uid = str(call.from_user.id)
    if call.data == "list_c":
        cs = fb_get("counters")
        m = types.InlineKeyboardMarkup()
        for k, v in cs.items():
            m.add(types.InlineKeyboardButton(f"{v['name']} | {v['price']} {POINT_NAME}", callback_data=f"info_{k}"))
        m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
        bot.edit_message_text("اختر العداد المناسب لك:", uid, call.message.id, reply_markup=m)

    elif call.data.startswith("info_"):
        cid = call.data.split("_")[1]
        c = fb_get(f"counters/{cid}")
        u = fb_get(f"users/{uid}")
        can_buy = u['points'] >= c['price']
        status = "✅ يمكنك الشراء" if can_buy else f"❌ نقاطك لا تكفي، تحتاج {c['price'] - u['points']} نقطة"
        
        text = f"📦 اسم العداد: {c['name']}\n💎 قيمته: {c['value']}\n💰 سعره: {c['price']}\n⏳ مدته: {c['duration']} يوم\n📝 وصفه: {c['desc']}\n\nحالة الشراء: {status}"
        m = types.InlineKeyboardMarkup()
        if can_buy: m.add(types.InlineKeyboardButton("🛒 شراء الآن", callback_data=f"buy_{cid}"))
        m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="list_c"))
        bot.edit_message_text(text, uid, call.message.id, reply_markup=m)

    elif call.data.startswith("buy_"):
        cid = call.data.split("_")[1]
        c = fb_get(f"counters/{cid}")
        u = fb_get(f"users/{uid}")
        
        if u['points'] >= c['price']:
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            exp_str = (datetime.now() + timedelta(days=c['duration'])).strftime('%Y-%m-%d %H:%M:%S')
            old_purchased_count = u.get('purchased', 0)
            new_purchased_count = old_purchased_count + 1
            old_counter = u.get('counter', 0) # نجيب القيمة القديمة (إذا ماكو نعتبرها 0)
            new_counter = old_counter + c['value'] # نجمع القديم ويه قيمة العداد الجديد
            fb_patch(f"users/{uid}", {
                "points": u['points'] - c['price'],
                "counter": new_counter, # هسة صار يجمع (مثلاً 50 + 150 = 200)
                "active_counter_val": new_counter, # هم نحدث القيمة البرمجية للاضافة
                "last_claim": now_str,
                "purchased": new_purchased_count,
                "expiry_date": exp_str,
                "expiry_notified": False
            })
            bot.answer_callback_query(call.id, "مبروك! تم تفعيل العداد")
            bot.send_message(CH_USER, f"📢 مستخدم جديد اشترى {c['name']}\nبقيت نقاطه: {u['points'] - c['price']}\nالتعدين يبدأ الآن لمدة {c['duration']} يوم.")
            bot.edit_message_text("✅ تم الشراء! ستبدأ باستلام النقاط كل 24 ساعة.", uid, call.message.id)

    elif call.data == "back_main":
        bot.delete_message(uid, call.message.id)
        start(call)
    elif call.data == "withdraw_home":
        u = fb_get(f"users/{uid}")
        text = f"اهلا بك في قسم السحب\n💰 عدد نقاطك: {u.get('points', 0)}\n📊 عدادك: {u.get('counter', 0)}\n🆔 ايديك: {uid}"
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(
            types.InlineKeyboardButton("💳 ماستر كارد", callback_data="draw_master"),
            types.InlineKeyboardButton("📱 زين كاش", callback_data="draw_zain"),
            types.InlineKeyboardButton("🏦 FIB", callback_data="draw_fib"),
            types.InlineKeyboardButton("📞 رصيد", callback_data="draw_balance"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        )
        bot.edit_message_text(text, uid, call.message.id, reply_markup=m)

    elif call.data == "draw_master":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(
            types.InlineKeyboardButton("10$ | 1000 نقطة", callback_data="item_ماستر10_1000"),
            types.InlineKeyboardButton("25$ | 2500 نقطة", callback_data="item_ماستر25_2500"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="withdraw_home")
        )
        bot.edit_message_text("اختر الكمية المطلوبة للماستر كارد:", uid, call.message.id, reply_markup=m)

    elif call.data.startswith("item_"):
        parts = call.data.split("_")
        item_name = parts[1]
        price = int(parts[2])
        u = fb_get(f"users/{uid}")
        
        can_draw = u.get('points', 0) >= price
        status = "✅ يمكنك السحب" if can_draw else f"❌ لا يمكنك، تحتاج {price - u.get('points', 0)} نقطة"
        
        text = f"تفاصيل الطلب:\nالنوع: {item_name}\nالسعر: {price} نقطة\n\n{status}"
        m = types.InlineKeyboardMarkup()
        if can_draw:
            m.add(types.InlineKeyboardButton("🚀 تأكيد السحب", callback_data=f"confirm_{item_name}_{price}"))
        m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="withdraw_home"))
        bot.edit_message_text(text, uid, call.message.id, reply_markup=m)

    elif call.data.startswith("confirm_"):
        bot.delete_message(uid, call.message.id)
        msg = bot.send_message(uid, "📝 يرجى إرسال تفاصيل السحب (رقم البطاقة / رقم الهاتف) واسمك الكامل:")
        bot.register_next_step_handler(msg, save_withdraw_info, call.data) 
    elif call.data.startswith("final_"):
        parts = call.data.split("_")
        order_id = parts[1]
        price = int(parts[2])
        item_type = parts[3]
        
        u = fb_get(f"users/{uid}")
        now_date = datetime.now().strftime('%Y-%m-%d')
        
        if u.get('last_withdraw_date') == now_date:
            return bot.answer_callback_query(call.id, "❌ مسموح لك بطلب سحب واحد فقط في اليوم!", show_alert=True)

        order_data = fb_get(f"pending_orders/{order_id}")
        if not order_data:
            return bot.answer_callback_query(call.id, "❌ خطأ في بيانات الطلب، حاول مجدداً.")

        fb_patch(f"users/{uid}", {"last_withdraw_date": now_date}) # تسجل أنه طلب اليوم
        bot.edit_message_text(f"✅ تم إرسال طلبك <code>{order_id}</code> للمراجعة.\n⚠️ سيتم خصم النقاط عند موافقة الإدارة.", uid, call.message.id, parse_mode="HTML")
        
        admin_m = types.InlineKeyboardMarkup()
        admin_m.add(
            types.InlineKeyboardButton("✅ موافقة وخصم", callback_data=f"approve_{order_id}"),
            types.InlineKeyboardButton("❌ رفض الطلب", callback_data=f"reject_{order_id}")
        )
        
        admin_text = f"🚨 طلب سحب جديد!\n👤 المستخدم: {call.from_user.first_name}\n🆔 آيدي: <code>{uid}</code>\n🏷 النوع: {item_type}\n💰 السعر: {price}\n📝 المعلومات: <code>{order_data.get('info', 'لا يوجد')}</code>\n🔢 الكود: <code>{order_id}</code>"
        bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_m, parse_mode="HTML")

    elif call.data.startswith("approve_"):
        order_id = call.data.split("_")[1]
        order_data = fb_get(f"pending_orders/{order_id}")
        
        if not order_data:
            return bot.send_message(ADMIN_ID, "❌ هذا الطلب لم يعد موجوداً في القاعدة.")
            
        u_id = order_data['uid']
        u_info = fb_get(f"users/{u_id}")
        price = order_data['price']
        
        if u_info.get('points', 0) >= price:
            new_pts = u_info['points'] - price
            fb_patch(f"users/{u_id}", {"points": new_pts})
            
            msg = bot.send_message(ADMIN_ID, f"✅ تم خصم {price} من المستخدم. أرسل الآن صورة الإثبات أو نص التحويل:")
            bot.register_next_step_handler(msg, send_proof_to_user, order_data)
        else:
            bot.send_message(ADMIN_ID, "❌ المستخدم لا يملك نقاط كافية حالياً (ربما صرفها بعد الطلب).")

    elif call.data.startswith("reject_"):
        order_id = call.data.split("_")[1]
        order_data = fb_get(f"pending_orders/{order_id}")
        if order_data:
            fb_patch(f"users/{order_data['uid']}", {"last_withdraw_date": ""}) 
            bot.send_message(order_data['uid'], f"❌ نعتذر، تم رفض طلبك {order_id}.")
            bot.send_message(ADMIN_ID, "✅ تم رفض الطلب بنجاح.") 
    elif call.data == "draw_zain":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(
            types.InlineKeyboardButton("5,000 دينار | 1500 نقطة", callback_data="item_زين5_1500"),
            types.InlineKeyboardButton("10,000 دينار | 3000 نقطة", callback_data="item_زين10_3000"),
            types.InlineKeyboardButton("25,000 دينار | 7000 نقطة", callback_data="item_زين25_7000"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="withdraw_home")
        )
        bot.edit_message_text("اختر الكمية المطلوبة لزين كاش:", uid, call.message.id, reply_markup=m)

    elif call.data == "draw_fib":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(
            types.InlineKeyboardButton("10$ FIB | 1200 نقطة", callback_data="item_FIB10_1200"),
            types.InlineKeyboardButton("50$ FIB | 5500 نقطة", callback_data="item_FIB50_5500"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="withdraw_home")
        )
        bot.edit_message_text("اختر الكمية المطلوبة لمحفظة FIB:", uid, call.message.id, reply_markup=m)

    elif call.data == "draw_balance":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(
            types.InlineKeyboardButton("📱 قسم رصيد آسيا سيل", callback_data="bal_asia"),
            types.InlineKeyboardButton("📱 قسم رصيد زين أثير", callback_data="bal_zain"),
            types.InlineKeyboardButton("📱 قسم رصيد كورك", callback_data="bal_korek"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="withdraw_home")
        )
        bot.edit_message_text("اختر شركة الاتصال الخاصة بك:", uid, call.message.id, reply_markup=m)

    elif call.data == "bal_asia":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(
            types.InlineKeyboardButton("كارت آسيا 5$ | 1500 نقطة", callback_data="item_آسيا5_1500"),
            types.InlineKeyboardButton("كارت آسيا 10$ | 3000 نقطة", callback_data="item_آسيا10_3000"),
            types.InlineKeyboardButton("رصيد تحويل 3000 | 800 نقطة", callback_data="item_آسيا_تحويل_800"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="draw_balance")
        )
        bot.edit_message_text("فئات رصيد آسيا سيل المتوفرة:", uid, call.message.id, reply_markup=m)

    elif call.data == "bal_zain":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(
            types.InlineKeyboardButton("كارت أثير 5$ | 1500 نقطة", callback_data="item_أثير5_1500"),
            types.InlineKeyboardButton("كارت أثير 10$ | 3000 نقطة", callback_data="item_أثير10_3000"),
            types.InlineKeyboardButton("رصيد تحويل 3000 | 800 نقطة", callback_data="item_أثير_تحويل_800"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="draw_balance")
        )
        bot.edit_message_text("فئات رصيد زين أثير المتوفرة:", uid, call.message.id, reply_markup=m)

    elif call.data == "bal_korek":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(
            types.InlineKeyboardButton("كارت كورك 5$ | 1500 نقطة", callback_data="item_كورك5_1500"),
            types.InlineKeyboardButton("كارت كورك 10$ | 3000 نقطة", callback_data="item_كورك10_3000"),
            types.InlineKeyboardButton("رصيد تحويل 3000 | 800 نقطة", callback_data="item_كورك_تحويل_800"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="draw_balance")
        )
        bot.edit_message_text("فئات رصيد كورك المتوفرة:", uid, call.message.id, reply_markup=m)
    elif call.data == "agents":
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(
            types.InlineKeyboardButton("📍 بابل", callback_data="city_babil"),
            types.InlineKeyboardButton("📍 بغداد", callback_data="city_baghdad"),
            types.InlineKeyboardButton("📍 البصرة", callback_data="city_basra"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        )
        bot.edit_message_text("🏢 أهلاً بك في قسم الوكلاء المعتمدين\n\nاختر محافظتك لتظهر لك قائمة الوكلاء:", uid, call.message.id, reply_markup=m, parse_mode="HTML")

    elif call.data == "city_babil":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(
            types.InlineKeyboardButton("👤 الوكيل علي الطائي", callback_data="view_agent_1"),
            types.InlineKeyboardButton("👤 الوكيل أحمد الحلي", callback_data="view_agent_2"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="agents")
        )
        bot.edit_message_text("✨ وكلاء محافظة بابل المعتمدين:", uid, call.message.id, reply_markup=m, parse_mode="HTML")

    elif call.data == "view_agent_1":
        name = "علي الطائي"
        a_id = "6454550864"
        user = "@altaee_z"
        phone1 = "9647800000000" # رقم الوكيل مع مفتاح الدول وبدون + للزر 
        phone = "+9649874935849" #للنص 
        
        text = f"""
🌟 معلومات الوكيل المعتمد
━━━━━━━━━━━━━━
👤 الاسم: {name}
🆔 الآيدي: <code>{a_id}</code>
🔗 اليوزر: {user}
📞 واتساب: <code>{phone}</code>
━━━━━━━━━━━━━━
✅ هذا الوكيل معتمد لشحن النقاط والتعاملات المالية.
        """
        
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(
            types.InlineKeyboardButton("💬 تليجرام", url=f"t.me/{user[1:]}"),
            types.InlineKeyboardButton("🟢 واتساب", url=f"https://wa.me/{phone1}"),
            types.InlineKeyboardButton("📢 القناة", url="https://t.me/my00002")
        )
        m.add(types.InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="city_babil"))
        
        bot.edit_message_text(text, uid, call.message.id, reply_markup=m, parse_mode="HTML")

    elif call.data == "city_baghdad":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(
            types.InlineKeyboardButton("👤 وكيل بغداد الرئيسي", callback_data="view_agent_bg"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="agents")
        )
        bot.edit_message_text("✨ وكلاء محافظة بغداد المعتمدين:", uid, call.message.id, reply_markup=m, parse_mode="HTML")            
    elif call.data == "transfer":
        u = fb_get(f"users/{uid}")
        text = f"""
🔄 قسم تحويل النقاط
━━━━━━━━━━━━━━
👤 اسمك: {call.from_user.first_name}
🆔 ايديك: <code>{uid}</code>
💰 نقاطك الحالية: <b>{u.get('points', 0)}</b>
📊 عدادك: <b>{u.get('counter', 0)}</b>
━━━━━━━━━━━━━━
⚠️ ملاحظات التحويل:
- عمولة التحويل الثابتة هي: <b>200 نقطة</b>.
- مسموح بعملية تحويل <b>واحدة فقط</b> في اليوم.
        """
        m = types.InlineKeyboardMarkup()
        if u.get('points', 0) > 200: # يجب أن يملك أكثر من العمولة ليبدأ
            m.add(types.InlineKeyboardButton("🚀 ابدأ التحويل الآن", callback_data="start_trans"))
        else:
            m.add(types.InlineKeyboardButton("❌ نقاطك لا تكفي (العمولة 200)", callback_data="low_p_trans"))
        m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
        bot.edit_message_text(text, uid, call.message.id, reply_markup=m, parse_mode="HTML")

    elif call.data == "start_trans":
        u = fb_get(f"users/{uid}")
        now_date = datetime.now().strftime('%Y-%m-%d')
        
        if u.get('last_transfer_date') == now_date:
            return bot.answer_callback_query(call.id, "❌ مسموح لك بعملية تحويل واحدة فقط في اليوم!", show_alert=True)
            
        msg = bot.send_message(uid, "🆔 يرجى إرسال (آيدي ID) الشخص الذي تريد التحويل له:")
        bot.register_next_step_handler(msg, get_receiver_id)
    elif call.data.startswith("confirmtr_"):
        parts = call.data.split("_")
        rec_id = parts[1]
        amt = int(parts[2])
        commission = 200
        total_deduct = amt + commission
        
        sender_data = fb_get(f"users/{uid}")
        rec_data = fb_get(f"users/{rec_id}")
        
        if sender_data.get('points', 0) >= total_deduct:
            now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            now_date = datetime.now().strftime('%Y-%m-%d')
            
            new_sender_pts = sender_data['points'] - total_deduct
            fb_patch(f"users/{uid}", {
                "points": new_sender_pts,
                "last_transfer_date": now_date
            })
            
            new_rec_pts = rec_data.get('points', 0) + amt
            fb_patch(f"users/{rec_id}", {"points": new_rec_pts})
            
            bot.edit_message_text(f"✅ تم التحويل بنجاح!\n\nتم خصم: {total_deduct} (شامل العمولة)\nنقاطك الآن: {new_sender_pts}\nنقاط المستلم الآن: {new_rec_pts}", uid, call.message.id)
            
            bot.send_message(rec_id, f"🎁 وصلتك نقاط جديدة!\n\nحول لك المستخدم (<code>{uid}</code>) مبلغ: <b>{amt}</b> نقطة.\nنقاطك الحالية: {new_rec_pts}\nتاريخ العملية: {now_time}", parse_mode="HTML")
            
            channel_msg = f"""
🔄 عملية تحويل ناجحة
━━━━━━━━━━━━━━
👤 من: <code>{uid}</code>
👤 إلى: <code>{rec_id}</code>
💰 المبلغ المحول: {amt}
💎 العمولة: {commission}
✅ النقاط الجديدة للمستقبل: {new_rec_pts}
⏰ التاريخ: {now_time}
━━━━━━━━━━━━━━
حقوق البوت: {CH_USER}
            """
            bot.send_message(CH_USER, channel_msg, parse_mode="HTML")
        else:
            bot.answer_callback_query(call.id, "❌ حدث خطأ، نقاطك غير كافية!")
    elif call.data == "gift_c":
        u = fb_get(f"users/{uid}")
        counter_val = u.get('counter', 0)
        text = f"""
🎁 قسم إهداء العداد
━━━━━━━━━━━━━━
👤 اسمك: {call.from_user.first_name}
📊 قيمة عدادك الحالي: <b>{counter_val}</b>
🆔 ايديك: <code>{uid}</code>
━━━━━━━━━━━━━━
⚠️ ملاحظات الإهداء:
- عمولة الإهداء هي: <b>2%</b> من القيمة المهدات.
- مسموح بعملية إهداء <b>واحدة فقط</b> في اليوم.
- يتم خصم القيمة من عدادك وإضافتها لعداد المستلم.
        """
        m = types.InlineKeyboardMarkup()
        if counter_val > 10: # يجب أن يملك عداد معقول للإهداء
            m.add(types.InlineKeyboardButton("🎁 ابدأ الإهداء الآن", callback_data="start_gift"))
        else:
            m.add(types.InlineKeyboardButton("❌ عدادك ضعيف جداً للإهداء", callback_data="low_c_gift"))
        m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
        bot.edit_message_text(text, uid, call.message.id, reply_markup=m, parse_mode="HTML")

    elif call.data == "start_gift":
        u = fb_get(f"users/{uid}")
        now_date = datetime.now().strftime('%Y-%m-%d')
        
        if u.get('last_gift_date') == now_date:
            return bot.answer_callback_query(call.id, "❌ مسموح لك بعملية إهداء واحدة فقط في اليوم!", show_alert=True)
            
        msg = bot.send_message(uid, "🆔 أرسل آيدي الشخص الذي تريد إهداء العداد له:")
        bot.register_next_step_handler(msg, get_gift_receiver_id)
    elif call.data.startswith("conf_gift_"):
        parts = call.data.split("_")
        rec_id = parts[2]
        gift_val = int(parts[3])
        
        commission = int(gift_val * 0.02)
        total_deduct = gift_val + commission
        
        sender_data = fb_get(f"users/{uid}")
        rec_data = fb_get(f"users/{rec_id}")
        
        if sender_data and sender_data.get('counter', 0) >= total_deduct:
            now = datetime.now()
            expiry_date = (now + timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')
            first_claim = now.strftime('%Y-%m-%d %H:%M:%S')
            new_sender_counter = sender_data['counter'] - total_deduct
            fb_patch(f"users/{uid}", {
                "counter": new_sender_counter,
                "active_counter_val": new_sender_counter,
                "last_gift_date": now.strftime('%Y-%m-%d')
            })
            
            new_rec_counter = rec_data.get('counter', 0) + gift_val
            fb_patch(f"users/{rec_id}", {
                "counter": new_rec_counter,
                "active_counter_val": new_rec_counter,
                "expiry_date": expiry_date, # العداد ينتهي بعد سنة
                "last_claim": first_claim,  # يبدأ التعدين بعد 24 ساعة من الآن
                "expiry_notified": False    # إعادة تفعيل تنبيه الانتهاء
            })
            
            bot.edit_message_text(f"✅ تم الإهداء بنجاح!\nخصم من عدادك: {total_deduct}\nعدادك الحالي: {new_sender_counter}", uid, call.message.id)
            
            gift_msg = f"""
🎁 مبروك! وصلتك هدية عداد جديدة
━━━━━━━━━━━━━━
👤 من المرسل: <code>{uid}</code>
📊 القيمة المضافة: <b>{gift_val}</b>
⏳ مدة العداد: <b>سنة كاملة (365 يوم)</b>
💰 أول دفعة نقاط: <b>بعد 24 ساعة من الآن</b>
━━━━━━━━━━━━━━
✅ تم تحديث عدادك وتمديد الصلاحية.
            """
            bot.send_message(rec_id, gift_msg, parse_mode="HTML")
            
            channel_msg = f"🎁 إهداء وتفعيل عداد لمدة سنة\n━━━━━━━━━━━━━━\n👤 من: <code>{uid}</code>\n👤 إلى: <code>{rec_id}</code>\n📊 القيمة: {gift_val}\n💎 العمولة: {commission}\n⏰ تاريخ البدء: {now.strftime('%Y-%m-%d')}\n⏳ تاريخ الانتهاء: {expiry_date}\n━━━━━━━━━━━━━━\n{CH_USER}"
            bot.send_message(CH_USER, channel_msg, parse_mode="HTML")
        else:
            bot.answer_callback_query(call.id, "❌ فشل الإهداء: رصيد العداد غير كافٍ.", show_alert=True)     
    elif call.data == "daily_gift":
        uid = str(call.from_user.id)
        u = fb_get(f"users/{uid}")
        
        last_gift_time_str = u.get('last_daily_gift', None)
        gift_amount = 250 # مقدار الهدية
        now = datetime.now()
        
        can_claim = False
        if last_gift_time_str:
            last_gift_time = datetime.strptime(last_gift_time_str, '%Y-%m-%d %H:%M:%S')
            wait_until = last_gift_time + timedelta(hours=24)
            
            if now >= wait_until:
                can_claim = True
            else:
                remaining_time = wait_until - now
                seconds = int(remaining_time.total_seconds())
                hours, remainder = divmod(seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                
                bot.answer_callback_query(call.id, f"🕒 متبقي {time_str} لاستلام الهدية القادمة!", show_alert=True)
                update_daily_button(uid, call.message.id, time_str)
                return
        else:
            can_claim = True

        if can_claim:
            current_points = u.get('points', 0)
            new_points = current_points + gift_amount
            old_daily_count = u.get('daily_gifts', 0)
            new_daily_count = old_daily_count + 1
            fb_patch(f"users/{uid}", {
                "points": new_points,
                "last_daily_gift": now.strftime('%Y-%m-%d %H:%M:%S'),
                "daily_gifts": new_daily_count # <--- السطر الجديد
            })
            
            bot.answer_callback_query(call.id, f"🎉 مبروك! حصلت على {gift_amount} نقطة هدية.", show_alert=True)
            text = f"✅ تم إضافة {gift_amount} نقطة إلى حسابك!\n💰 نقاطك الجديدة: {new_points}\n\nعد بعد 24 ساعة للحصول على الهدية التالية."
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton(f"🕒 عداد: 23:59:59", callback_data="daily_gift"))
            m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
            bot.edit_message_text(text, uid, call.message.id, reply_markup=m)
    elif call.data == "ref_link":
        u = fb_get(f"users/{uid}")
        ref_count = u.get('referrals', 0)
        bot_username = bot.get_me().username
        link = f"https://t.me/{bot_username}?start={uid}"
        
        text = f"""
🔗 رابط الإحالة الخاص بك
━━━━━━━━━━━━━━
شارك هذا الرابط مع أصدقائك واحصل على <b>1000</b> نقطة عن كل شخص يسجل في البوت!

👥 عدد الأشخاص الذين دعوتهم: <b>{ref_count}</b>
💰 إجمالي أرباحك من الدعوات: <b>{ref_count * 1000}</b> نقطة

رابطك:
<code>{link}</code>
        """
        m = types.InlineKeyboardMarkup()
        m.add(types.InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={link}&text=سجل في هذا البوت واحصل على نقاط مجانية!"))
        m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
        bot.edit_message_text(text, uid, call.message.id, reply_markup=m, parse_mode="HTML")

    elif call.data == "who_invited_me":
        u = fb_get(f"users/{uid}")
        inviter_id = u.get('invited_by')
        
        if inviter_id:
            try:
                chat = bot.get_chat(inviter_id)
                name = chat.first_name
                user = f"@{chat.username}" if chat.username else "لا يوجد يوزر"
                date = u.get('join_date', 'غير متوفر')
                
                text = f"""
👤 معلومات الشخص الذي دعاك:
━━━━━━━━━━━━━━
👤 الاسم: <b>{name}</b>
🆔 الآيدي: <code>{inviter_id}</code>
🔗 اليوزر: {user}
📅 تاريخ دعوتك: <code>{date}</code>
━━━━━━━━━━━━━━
شكراً لانضمامك إلينا!
                """
            except:
                text = "❌ لم نتمكن من جلب معلومات الداعي، ربما قام بحظر البوت."
        else:
            text = "🧐 يبدو أنك دخلت للبوت مباشرةً ولم يدعُك أحد."
            
        m = types.InlineKeyboardMarkup()
        m.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
        bot.edit_message_text(text, uid, call.message.id, reply_markup=m, parse_mode="HTML")  
    elif call.data == "use_coupon":
        msg = bot.send_message(uid, "🎟️ أرسل رمز الكوبون الآن:")
        bot.register_next_step_handler(msg, process_coupon)
def process_coupon(message):
    uid = str(message.from_user.id)
    code_sent = message.text.strip()
    coupon_data = fb_get("coupons")
    if not coupon_data:
        return bot.send_message(uid, "❌ لا توجد كوبونات فعالة حالياً.")
    if coupon_data.get('code') != code_sent:
        return bot.send_message(uid, "❌ هذا الكوبون غير موجود أو غير صحيح!")
    uses = int(coupon_data.get('uses', 0))
    limit = int(coupon_data.get('limit', 0))
    if uses >= limit:
        return bot.send_message(uid, "🚫 نأسف، وصل هذا الكوبون للحد الأقصى!")

    claimed = coupon_data.get('claimed_by', [])
    if not isinstance(claimed, list): 
        claimed = []
    
    if uid in claimed:
        return bot.send_message(uid, "⚠️ أنت استخدمت هذا الكوبون مسبقاً!")

    try:
        expiry = datetime.strptime(coupon_data['expiry'], '%Y-%m-%d %H:%M')
        if datetime.now() > expiry:
            return bot.send_message(uid, "⌛ انتهت صلاحية الكوبون.")
    except: pass

    reward = int(coupon_data.get('reward', 0))
    user = fb_get(f"users/{uid}")
    if not user: user = {"points": 0}
    
    new_points = user.get('points', 0) + reward
    fb_patch(f"users/{uid}", {"points": new_points})
    
    claimed.append(uid)
    fb_patch("coupons", {
        "uses": uses + 1,
        "claimed_by": claimed
    })
    
    bot.send_message(uid, f"🎉 مبروك! تم تفعيل الكوبون.\n🎁 حصلت على: {reward} نقطة.\n💰 رصيدك الآن: {new_points}")
@bot.message_handler(commands=['add_coupon'])
def add_coupon(message):
    uid = message.from_user.id
    
    if int(uid) != int(ADMIN_ID):
        return bot.reply_to(message, "❌ هذا الأمر مخصص للمطور فقط!")

    msg = bot.send_message(message.chat.id, 
        "🎫 أرسل تفاصيل الكوبون بالشكل التالي:\n\n"
        "`الكود-النقاط-العدد-الدقائق`\n\n"
        "💡 مثال: `VIP100-5000-10-60` \n"
        "*(كود VIP100 يعطي 5000 نقطة لـ 10 أشخاص لمدة ساعة)*", 
        parse_mode="Markdown")
    
    bot.register_next_step_handler(msg, save_new_coupon)

def save_new_coupon(message):
    uid = str(message.from_user.id)
    try:
        data = message.text.split('-')
        if len(data) != 4:
            return bot.send_message(uid, "❌ خطأ! يرجى اتباع المثال: كود-نقاط-عدد-وقت")

        code = data[0].strip()
        reward = int(data[1].strip())
        limit = int(data[2].strip())
        minutes = int(data[3].strip())
        
        expiry_time = (datetime.now() + timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M')
        
        coupon_obj = {
            "code": code,
            "reward": reward,
            "limit": limit,
            "uses": 0,
            "expiry": expiry_time,
            "claimed_by": ["0"] # قائمة وهمية للبداية
        }
        
        fb_patch("coupons", coupon_obj)
        
        response = f"""
✅ تم إنشاء الكوبون بنجاح!
━━━━━━━━━━━━━━
🎫 الكود: `{code}`
💰 النقاط: `{reward}`
👥 العدد: {limit} مستخدم
⌛ ينتهي في: {expiry_time}
━━━━━━━━━━━━━━
📢 يمكنك نشره الآن في قناتك!
        """
        bot.send_message(message.chat.id, response, parse_mode="Markdown")

    except Exception as e:
        bot.send_message(uid, f"❌ حدث خطأ أثناء الحفظ!\nالتفاصيل: {e}")

bot.polling(none_stop=True)

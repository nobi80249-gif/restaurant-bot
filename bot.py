import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import BOT_TOKEN, WORKING_HOURS, MENU
from database import init_db, save_order, get_orders
from datetime import datetime
import json

# تنظیم logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ذخیره سفارش موقت کاربر
user_orders = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ربات"""
    keyboard = [
        [InlineKeyboardButton("📋 مشاهده منو", callback_data='menu')],
        [InlineKeyboardButton("⏰ ساعت کاری", callback_data='working_hours')],
        [InlineKeyboardButton("📞 تماس با ما", callback_data='contact')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '🍽️ خوش آمدید به رستوران ما!\n\nچه کاری می‌تونم برای شما کنم؟',
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دکمه‌های inline"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'menu':
        await show_menu(query, context)
    elif query.data == 'working_hours':
        await show_working_hours(query, context)
    elif query.data == 'contact':
        await show_contact(query, context)
    elif query.data.startswith('add_item_'):
        await add_to_order(query, context)
    elif query.data == 'checkout':
        await checkout(query, context)
    elif query.data == 'cancel_order':
        await cancel_order(query, context)

async def show_menu(query, context):
    """نمایش منو"""
    menu_text = '🍽️ منوی رستوران:\n\n'
    keyboard = []
    
    for idx, (item, price) in enumerate(MENU.items()):
        menu_text += f'{item} - {price:,} تومان\n'
        keyboard.append([InlineKeyboardButton(f'افزودن {item}', callback_data=f'add_item_{idx}')])
    
    keyboard.append([InlineKeyboardButton('✅ تایید سفارش', callback_data='checkout')])
    keyboard.append([InlineKeyboardButton('❌ لغو', callback_data='cancel_order')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=menu_text, reply_markup=reply_markup)

async def show_working_hours(query, context):
    """نمایش ساعت کاری"""
    hours_text = '⏰ ساعت کاری رستوران:\n\n'
    for day, hours in WORKING_HOURS.items():
        hours_text += f'{day}: {hours}\n'
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=hours_text, reply_markup=reply_markup)

async def show_contact(query, context):
    """نمایش اطلاعات تماس"""
    contact_text = '''📞 اطلاعات تماس رستوران:\n
تلفن: 021-12345678
آدرس: تهران، خیابان آزادی\nایمیل: info@restaurant.com
    '''
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=contact_text, reply_markup=reply_markup)

async def add_to_order(query, context):
    """افزودن آیتم به سفارش"""
    user_id = query.from_user.id
    
    if user_id not in user_orders:
        user_orders[user_id] = {'items': [], 'total': 0}
    
    item_idx = int(query.data.split('_')[-1])
    items_list = list(MENU.items())
    item_name, price = items_list[item_idx]
    
    user_orders[user_id]['items'].append({'name': item_name, 'price': price})
    user_orders[user_id]['total'] += price
    
    await query.edit_message_text(
        text=f'✅ {item_name} به سفارش شما اضافه شد!\n\nمجموع: {user_orders[user_id]["total"]:,} تومان',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت به منو', callback_data='menu')]])
    )

async def checkout(query, context):
    """پرداخت و تایید سفارش"""
    user_id = query.from_user.id
    
    if user_id not in user_orders or not user_orders[user_id]['items']:
        await query.edit_message_text(text='❌ سفارشی موجود نیست!')
        return
    
    order_items = user_orders[user_id]['items']
    total = user_orders[user_id]['total']
    
    items_text = ''.join([f"• {item['name']} - {item['price']:,} تومان\n" for item in order_items])
    
    checkout_text = f'''📋 خلاصه سفارش:\n
{items_text}
📊 مجموع: {total:,} تومان

لطفاً شماره تلفن خود را ارسال کنید:'''
    
    await query.edit_message_text(text=checkout_text)
    context.user_data['waiting_for_phone'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت پیام‌های متنی"""
    user_id = update.message.from_user.id
    
    if context.user_data.get('waiting_for_phone'):
        phone = update.message.text
        context.user_data['phone'] = phone
        context.user_data['waiting_for_phone'] = False
        context.user_data['waiting_for_address'] = True
        
        await update.message.reply_text('🏠 آدرس تحویل را وارد کنید:')
    
    elif context.user_data.get('waiting_for_address'):
        address = update.message.text
        phone = context.user_data.get('phone')
        
        if user_id in user_orders:
            order_items = user_orders[user_id]['items']
            total = user_orders[user_id]['total']
            
            order_id = save_order(
                user_id=user_id,
                username=update.message.from_user.username or 'بدون نام',
                items=order_items,
                total_price=total,
                phone=phone,
                address=address
            )
            
            confirmation_text = f'''✅ سفارش شما با موفقیت ثبت شد!\n
🎟️ شماره سفارش: {order_id}
📍 آدرس: {address}
📞 تلفن: {phone}
💰 مجموع: {total:,} تومان

زمان تحویل: 30-45 دقیقه'''
            
            await update.message.reply_text(confirmation_text)
            
            # پاک کردن سفارش موقت
            del user_orders[user_id]
            context.user_data['waiting_for_address'] = False
        else:
            await update.message.reply_text('❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.')

async def cancel_order(query, context):
    """لغو سفارش"""
    user_id = query.from_user.id
    if user_id in user_orders:
        del user_orders[user_id]
    
    await query.edit_message_text(
        text='❌ سفارش لغو شد.',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='menu')]])
    )

def main():
    """شروع ربات"""
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info('🤖 ربات شروع شد...')
    app.run_polling()

if __name__ == '__main__':
    main()

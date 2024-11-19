from telegram import Update, ReplyKeyboardMarkup, ChatMemberMember, ChatMemberRestricted, ChatMemberAdministrator, ChatMemberOwner
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta
from hethong import ActivityTracker
import os
import pytz
from group_config import GroupConfig
from XNK import XuatNhapKhoan
from admin_commands import AdminCommands
from job_scheduler import JobScheduler
from ht2 import ExcelExporter
import re
import traceback
from help import HelpHandler
import telegram
from XNK4 import DetailedTransactionHistory
from XNK3 import ExcelExporter

BOT_TOKEN = "7940264319:AAHELSGRa8VSBTWJfYo_0_axHUtTDRQhldU"

# Thêm danh sách operators
OPERATORS = ["Timotimo666", "XXXXXX"]  # Thay thế bằng username của các operators thực tế

# Theo dõi các nhóm đang hoạt động
active_groups = set()

# Khởi tạo GroupConfig
group_config = GroupConfig()

# Khởi tạo JobScheduler
job_scheduler = JobScheduler()

# Hàm gửi file statistics
async def send_statistics(context: ContextTypes.DEFAULT_TYPE):
    """Callback function cho job tự động gửi thống kê"""
    job = context.job
    chat_id = job.data['chat_id']
    try:
        chat = await context.bot.get_chat(chat_id)
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs('statistics', exist_ok=True)
        
        # Lấy tracker và khởi tạo ExcelExporter
        tracker = ActivityTracker(chat.title)
        excel_exporter = ExcelExporter(tracker)
        
        # Debug log
        print(f"Exporting statistics for group: {chat.title}")
        
        # Xuất file Excel với tất cả thống kê
        result = excel_exporter.export_statistics()
        if not result:
            print(f"No data to export for {chat.title}")
            return
            
        success, excel_file = result
        print(f"Export result: success={success}, file={excel_file}")
        
        if success and os.path.exists(excel_file):
            print(f"Sending file: {excel_file}")
            await context.bot.send_document(
                chat_id=chat_id,
                document=open(excel_file, 'rb'),
                caption=f"考勤统计 - {chat.title}"
            )
        else:
            print(f"File not found: {excel_file}")
            
    except Exception as e:
        print(f"Error in automatic send_statistics: {str(e)}")
        traceback.print_exc()  # In ra stack trace đầy đủ

# Hàm xử lý lệnh set send statistics
async def handle_set_statistics_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh set send statistics"""
    try:
        chat = update.effective_chat
        user = update.effective_user
        
        # Kiểm tra quyền
        admin_cmd = AdminCommands(chat.title)
        if not (admin_cmd.is_operator(user.username) or admin_cmd.is_level1(user.username)):
            await update.message.reply_text("⚠️ 只有系统管理员和一级代理可以设置自动发送时间")
            return

        message_text = update.message.text.lower()
        time_str = message_text.split('set send statistics')[1].strip()
        
        # Kiểm tra format thời gian
        try:
            hour, minute = map(int, time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except ValueError:
            await update.message.reply_text("时间格式错误。请使用 HH:MM 格式 (00:00-23:59)")
            return
            
        # Lấy timezone của nhóm
        settings = group_config.get_group_settings(str(chat.id))
        group_tz = settings.get('timezone', 'UTC')
        
        # Gọi schedule_daily_statistics với timezone
        success, message = job_scheduler.schedule_daily_statistics(
            context,
            chat.id,
            chat.title,
            time_str,
            group_tz
        )
        
        if success:
            # Lưu vào group_config
            settings = group_config.get_group_settings(str(chat.id)) or {}
            settings.update({
                'auto_send_time': time_str,
                'timezone': group_tz
            })
            group_config.set_group_settings(str(chat.id), chat.title, settings)
            
        await update.message.reply_text(message)
        
    except Exception as e:
        print(f"Error setting statistics time: {str(e)}")
        traceback.print_exc()
        await update.message.reply_text("设置自动发送时间失败")

# Thêm hàm xử lý cài đặt timezone
async def handle_set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = str(chat.id)  # Đảm bảo chat_id là string
    group_name = chat.title
    
    print(f"DEBUG: Setting timezone for chat {chat_id} ({group_name})")
    
    try:
        message_text = update.message.text
        country = message_text.split()[-1]
        tracker = ActivityTracker(chat.title)
        success, tz = tracker.set_timezone(country)
        
        if success:
            # Lưu cấu hình vào group_settings.json
            group_config.set_group_timezone(
                str(chat.id),
                chat.title,
                tz,
                country
            )
            
            # Lấy thời gian hiện tại theo múi giờ vừa cài đặt
            current_time = datetime.now(pytz.timezone(tz))
            formatted_time = current_time.strftime('%Y/%m/%d %H:%M')
            
            # Lấy thời gian gửi tự động nếu có
            settings = group_config.get_group_settings(str(chat.id))
            auto_send_time = settings.get('auto_send_time', '')
            
            if auto_send_time:
                await update.message.reply_text(
                    f"🌍 已将时区设置为 {tz}\n"
                    f"⏰ 当前时间: {formatted_time}\n"
                    f"⚡ 自动发送时间: {auto_send_time}"
                )
            else:
                await update.message.reply_text(
                    f"🌍 已将时区设置为 {tz}\n"
                    f"⏰ 当前时间: {formatted_time}"
                )
        else:
            await update.message.reply_text("⚠️ 不支持该国家的时区设置")
    except Exception as e:
        print(f"Error setting timezone: {str(e)}")
        await update.message.reply_text("❌ 设置时区失败")

# Hàm khởi tạo menu chính
def main_menu():
    keyboard = [
        ["💼 上班", "🏠 下班"],
        ["🍚 吃饭", "🚾 上厕所", "🚬 抽烟", "🚶‍♂️ 离开"],
        ['↩️ 回']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Hàm bắt đầu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /start"""
    try:
        chat = update.effective_chat
        
        # Kiểm tra quyền của bot trong nhóm
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        
        # Kiểm tra quyền gửi tin nhắn của bot
        if isinstance(bot_member, ChatMemberMember):
            # Bot là thành viên thường
            await update.message.reply_text("⚠️ Bot需要管理员权限才能最好地工作！")
            return
        elif isinstance(bot_member, ChatMemberRestricted):
            # Bot bị hạn chế quyền
            await update.message.reply_text("⚠️ Bot权限受限，请授予管理员权限！") 
            return
        elif not isinstance(bot_member, (ChatMemberAdministrator, ChatMemberOwner)):
            # Bot không phải là quản trị viên hoặc chủ nhóm
            await update.message.reply_text("⚠️ Bot需要管理员权限才能最好地工作！")
            return
            
        # Luôn hiển thị menu cơ bản
        await update.message.reply_text(
            "🔰 请选择功能:",
            reply_markup=main_menu()
        )
        
    except Exception as e:
        print(f"Error in start: {str(e)}")
        traceback.print_exc()

# Hàm xử lý tin nhắn
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Xử lý tất cả các tin nhắn và lệnh từ người dùng trong group
    """
    try:
        chat = update.effective_chat
        
        # Thêm chat_id vào active_groups khi có tin nhắn mới
        active_groups.add(str(chat.id))
        
        user = update.effective_user
        text = update.message.text.strip()
        text_lower = text.lower()

        # 1. Kiểm tra cơ bản
        if not user.username:
            await update.message.reply_text("👤 您需要设置用户名才能使用此功能")
            return
            
        if not update.effective_chat.type.endswith('group'):
            print("DEBUG: Not a group message")
            return

        # 2. Khởi tạo đối tượng
        admin_cmd = AdminCommands(chat.title)
        tracker = ActivityTracker(chat.title)
        xnk = XuatNhapKhoan(chat.title, str(chat.id))
        user_identifier = user.username or user.first_name

        # 3. Kiểm tra quyền chi tiết và log
        is_operator = admin_cmd.is_operator(user.username)
        is_level1 = admin_cmd.is_level1(user.username)
        is_level2 = admin_cmd.is_level2(user.username, chat.id)
        is_authorized = admin_cmd.is_user_authorized(user.username, chat.id)
        
        print(f"DEBUG: Checking permissions for {user.username}")
        print(f"DEBUG: is_operator: {is_operator}")
        print(f"DEBUG: is_level1: {is_level1}")
        print(f"DEBUG: is_level2: {is_level2}")
        print(f"DEBUG: is_authorized: {is_authorized}")

        # 4. Kiểm tra các lệnh xuất nhập khoản (cần quyền level2 trở lên)
        transaction_commands = ['+', '-', '入款', '下发', 'xf']
        if any(text.startswith(pattern) for pattern in transaction_commands):
            print(f"DEBUG: Transaction command detected: {text}")
            if not (is_operator or is_level1 or is_level2):
                print(f"DEBUG: User {user.username} denied permission for transaction")
                await update.message.reply_text("⚠️ 您没有使用权限或授权已过期，请联系管理员")
                return
            else:
                print(f"DEBUG: User {user.username} has permission for transaction")
                
                # Xử lý số tiền và loại giao dịch
                amount_match = re.match(r'^(\+|-|入款|下发|xf)\s*(\d+\.?\d*)$', text)
                if amount_match:
                    command, amount_str = amount_match.groups()
                    amount = float(amount_str)
                    transaction_type = '入款' if command in ['+', '入款'] else '下发'
                    
                    try:
                        response = await xnk.process_transaction(
                            user_id=user.id,
                            username=user.username,
                            amount=amount,
                            transaction_type=transaction_type,
                            message=update.message
                        )
                        if response:
                            await update.message.reply_text(response, parse_mode='HTML')
                        return
                    except Exception as e:
                        print(f"Error processing transaction: {str(e)}")
                        return

        # 5. Xử lý menu cơ bản (chỉ cần is_authorized)
        basic_commands = ["💼 上班", "🏠 下班", "🍚 吃饭", "🚾 上厕所", "🚬 抽烟", "🚶‍♂️ 离开", "↩️ 回"]
        if text in basic_commands:
            print(f"DEBUG: Basic command detected: {text}")
            if not (is_operator or is_level1 or is_level2 or is_authorized):
                print(f"DEBUG: User {user.username} denied permission for basic command")
                await update.message.reply_text("⚠️ 您没有使用权限或授权已过期，请联系管理员")
                return
            else:
                print(f"DEBUG: User {user.username} has permission for basic command")
                
            command = text.split()[-1]
            response = None
            
            if command == "上班":
                response = tracker.start_work(user.id, user_identifier)
            elif command == "下班":
                response = tracker.end_work(user.id, user_identifier)
            elif command == "回":
                response = tracker.end_break(user.id, user_identifier)
            else:
                response = tracker.start_break(user.id, command)
                
            if response:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=response,
                    parse_mode='HTML',
                    reply_markup=main_menu()
                )
            return

        # 6. Kiểm tra các lệnh khác
        other_commands = [
            r'expiretime', r'查账', r'help', r'帮助', r'otc', r'币价',
            r'set', r'设置', r'auth', r'del', r'list', r'add',
            r'cleartodayrecord', r'清理今日记录',
            r'send statistics', r'set send statistics',
            r'set timezone', r'set time zone', r'按国家设置时间',
            r'发送报告', r'设置报告发送时间', r'授权'
        ]

        if any(re.match(f"^{pattern}", text_lower) for pattern in other_commands):
            print(f"DEBUG: Other command detected: {text}")
            if not (is_operator or is_level1 or is_level2 or is_authorized):
                print(f"DEBUG: User {user.username} denied permission for other command")
                await update.message.reply_text("⚠️ 您没有使用权限或授权已过期，请联系管理员")
                return
            else:
                print(f"DEBUG: User {user.username} has permission for other command")

        # 8. Cập nhật username chỉ khi có quyền
        if is_authorized:
            tracker.update_username(user.id, user_identifier)

        # 9. Kiểm tra các lệnh khác (chỉ cho admin, level1, level2)
        if not (is_operator or is_level1 or is_level2):
    #        await update.message.reply_text("⚠️ Bạn chỉ có quyền sử dụng menu cơ bản\n\n您只能使用基本菜单功能")
            return

        # 10. Kiểm tra quyền cho lệnh nâng cao
        level2_commands = [
            r'\+', r'-', r'入款', r'下发', r'xf',
            r'expiretime', r'查账', r'help', r'帮助', r'otc', r'币价'
        ]
        level1_commands = [
            r'设置', r'auth', r'del', r'list',
            r'cleartodayrecord', r'清理今日记录',
            r'send statistics', r'set send statistics',
            r'set timezone', r'set time zone', r'按国家设置时间',
            r'发送报告', r'设置报告发送时间', r'授权'
        ]

        if any(re.match(f"^{pattern}", text_lower) for pattern in level1_commands):
            if not (is_operator or is_level1):
                await update.message.reply_text("⚠️ 此功能仅限管理员")
                return
        elif any(re.match(f"^{pattern}", text_lower) for pattern in level2_commands):
            if not (is_operator or is_level1 or is_level2):
                await update.message.reply_text("⚠️ 您没有使用权限或授权已过期，请联系管理员")
                return
        # 11. Xử lý các lệnh giao dịch
        amount = None
        transaction_type = None
        specified_currency = None

        if text.startswith('下发'):
            try:
                amount, specified_currency = xnk.parse_withdrawal_command(text)
                if amount is not None:
                    transaction_type = "下发"
            except Exception as e:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="金额格式错误"
                )
                return
        elif text.startswith('+') or text.startswith('入款'):
            try:
                amount = float(text.replace('+', '').replace('入款', '').strip())
                transaction_type = "入款"
            except ValueError:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="金额格式错误"
                )
                return
        elif text.startswith('-') or text.startswith('xf'):
            try:
                amount = float(text.replace('-', '').replace('xf', '').strip())
                transaction_type = "下发"
            except ValueError:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="金额格式错误"
                )
                return

        if amount is not None and transaction_type is not None:
            try:
                # Khởi tạo XuatNhapKhoan với chat_id
                xnk = XuatNhapKhoan(chat.title, chat.id)
                
                response = await xnk.process_transaction(
                    user_id=user.id,
                    username=user.username or user.first_name,
                    amount=amount,
                    transaction_type=transaction_type,
                    specified_currency=specified_currency,
                    message=update.message  # Thêm message object
                )
                if response:
                    await context.bot.send_message(
                        chat_id=chat.id,
                        text=response,
                        parse_mode='HTML'
                    )
            except Exception as e:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=f"处理交易失败:\n{str(e)}",
                    parse_mode='HTML'
                )
                return

        # 12. Xử lý các lệnh cài đặt thời gian
        if text.lower().startswith('set send statistics'):
            try:
                time_str = text.lower().split('set send statistics')[1].strip()
                
                try:
                    hour, minute = map(int, time_str.split(':'))
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError
                except ValueError:
                    await update.message.reply_text("时间格式错误。请使用 HH:MM 格式 (00:00-23:59)")
                    return
                    
                success, message = job_scheduler.schedule_daily_statistics(
                    context,
                    chat.id,
                    chat.title,
                    time_str
                )
                
                if success:
                    group_config.set_group_settings(
                        str(chat.id),
                        chat.title,
                        {'auto_send_time': time_str}
                    )
                    
                await update.message.reply_text(message)
                return
                
            except Exception as e:
                print(f"Error setting statistics time: {str(e)}")
                await update.message.reply_text("设置自动发送时失败")
                return

        # 13. Xử lý các lệnh cài đặt phí và tỷ giá
        if text.startswith('设置费率') and not text.lower().startswith('set send statistics'):
            try:
                rate = float(text.split('费率')[1].strip())
                response = xnk.set_fee_rate(rate)
                await update.message.reply_text(response)
                return
            except Exception as e:
                await update.message.reply_text("设置费率失败，请使用正确格式：设置费率 0.05")
                return

        if text.lower() == 'setusdt' or text == '设置USDT汇率':
            try:
                rate = float(text.split()[-1])
                response = await admin_cmd.set_usdt_rate(rate)
                await update.message.reply_text(response)
                return
            except:
                await update.message.reply_text("设置失败，请使用正确格式：setusdt 6.9")
                return

        if text.startswith('设置') and '汇率' in text:
            try:
                parts = text.split('汇率')
                currency_type = parts[0][2:].strip()
                rate = float(parts[1].strip())
                
                response = xnk.set_exchange_rate(currency_type, rate)
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=response
                )
                return
            except ValueError:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="设置汇率失败，请确保输入的是有效数字"
                )
                return
            except Exception as e:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="设置汇率失败，请使用正确格式：设置USDT汇率 3.95"
                )
                return
                    # 14. Xử lý lệnh timezone
        if text.startswith(('set timezone', 'set time zone', '按国家设置时间')):
            try:
                if text.startswith('set time zone'):
                    country = text.replace('set time zone', '').strip()
                elif text.startswith('set timezone'):
                    country = text.replace('set timezone', '').strip()
                else:
                    country = text.replace('按国家设置时间', '').strip()
                
                success, tz = tracker.set_timezone(country)
                
                if success:
                    group_config.set_group_timezone(
                        str(chat.id),
                        chat.title,
                        tz,
                        country
                    )
                    
                    current_time = datetime.now(pytz.timezone(tz))
                    formatted_time = current_time.strftime('%Y/%m/%d %H:%M')
                    
                    settings = group_config.get_group_settings(str(chat.id))
                    auto_send_time = settings.get('auto_send_time', '')
                    
                    if auto_send_time:
                        await update.message.reply_text(
                            f"🌍 已将时区设置为 {tz}\n"
                            f"⏰ 当前时间: {formatted_time}\n"
                            f"⚡ 自动发送时间: {auto_send_time}"
                        )
                    else:
                        await update.message.reply_text(
                            f"🌍 已将时区设置为 {tz}\n"
                            f"⏰ 当前时间: {formatted_time}"
                        )
                else:
                    await update.message.reply_text("⚠️ 不支持该国家的时区设置")
                return
            except Exception as e:
                print(f"Error setting timezone: {str(e)}")
                await update.message.reply_text("❌ 设置时区失败")
                return

        # 15. Xử lý các lệnh kiểm tra và báo cáo
        if text.lower() in ['查账', 'checkbook']:
            try:
                message = xnk.check_recent_transactions()
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=message,
                    parse_mode='HTML'
                )
                return
            except Exception as e:
                print(f"Error in check transactions: {str(e)}")
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="获取交易记录失败"
                )
                return

        if text.lower() in ['otc', '币价', 'z0', '/otc']:
            try:
                response = await admin_cmd.get_okx_price()
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=response,
                    parse_mode='HTML'
                )
                return
            except Exception as e:
                await context.bot.send_message(
                    chat_id=chat.id, 
                    text=f"获取OTC价格失败: {str(e)}"
                )
                return

        if text.lower() in ['expiretime', '/expiretime']:
            try:
                response = await admin_cmd.check_user_expiry(user.username, chat.id)
                await update.message.reply_text(response)
                return
            except Exception as e:
                print(f"Error checking expiry time: {str(e)}")
                await update.message.reply_text("检查授权失败，请稍后再试")
                return

        if text.lower() in ['list', '/list']:
            try:
                response = await admin_cmd.list_group_auth(chat.title, chat.id)
                await update.message.reply_text(response)
                return
            except Exception as e:
                print(f"Error listing auth: {str(e)}")
                await update.message.reply_text("获取授权列表失败")
                return

        # 16. Xử lý lệnh xóa và báo cáo
        if text in ['清理今日记录', 'cleartodayrecord']:
            try:
                response = xnk.clear_today_records()
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=response
                )
                return
            except Exception as e:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="清理记录失败，请稍后再试"
                )
                return

        # Xử lý lệnh gửi báo cáo
        report_commands = [
            '发送报告', 'sendreport', '发送月报', 'sendmonthlyreport',  # Lệnh báo cáo tháng
            '发送日报', 'senddaily', '发送每日报告', 'senddailyreport'  # Lệnh báo cáo ngày
        ]
        if text_lower in report_commands:
            await handle_send_report_now(update, context)
            return
            
        if text.startswith('设置报告发送时间'):
            await handle_set_monthly_report_time(update, context)
            return

        # Các lệnh cấp quyền
        command = text_lower.split()[0]
        if command in ['authuser', '/authuser', 'add', '/add']:
            args = text.split()[1:]
            if len(args) == 0:
                await update.message.reply_text("请指定用户名，例如: authuser @username")
                return
            # ... phần code xử lý cấp quyền còn lại

        # Xử lý lệnh cấp quyền
        if text.lower().startswith(('add', 'auth')):
            try:
                args = text.split()
                if len(args) < 2:
                    if admin_cmd.is_operator(user.username):
                        await update.message.reply_text("格式错误。正确格式：\nadd @用户账号 天数\nadd admin @用户账号")
                    else:
                        await update.message.reply_text("格式错误。正确格式：\nadd @用户账号\nadd admin @用户账号")
                    return

                target_username = None
                duration_days = None
                is_admin_auth = False

                if args[0].lower() == 'add':
                    if len(args) >= 3 and args[1].lower() == 'admin':
                        # Lệnh add admin @username - cấp quyền level1
                        if not admin_cmd.is_level1(user.username):
                            await update.message.reply_text("只有一级代理可以添加其他一级代理")
                            return
                        target_username = args[2].replace('@', '')
                        is_admin_auth = True
                    else:
                        # Lệnh add @username [days] - cấp quyền level2 hoặc level1 tùy người thực hiện
                        target_username = args[1].replace('@', '')
                        # Chỉ operator mới được chỉ định số ngày
                        if admin_cmd.is_operator(user.username) and len(args) >= 3:
                            try:
                                duration_days = int(args[2])
                            except ValueError:
                                await update.message.reply_text("天数必须是数字")
                                return

                if not target_username:
                    await update.message.reply_text("请指定用户名")
                    return

                # Kiểm tra quyền thực hiện lệnh
                if not (admin_cmd.is_operator(user.username) or admin_cmd.is_level1(user.username)):
                    await update.message.reply_text("您没有权限执行此操作")
                    return

                # Xử lý cấp quyền
                if is_admin_auth:
                    # Cấp quyền level1 (từ level1 cho level1 khác)
                    response = await admin_cmd.authorize_user(
                        user.username,
                        target_username,
                        chat.id,
                        None, 
                        is_level1=True
                    )
                else:
                    # Cấp quyền thông thường
                    if admin_cmd.is_operator(user.username):
                        # Operator có thể chỉ định số ngày
                        if duration_days is None:
                            duration_days = 30  # Mặc định 30 ngày cho operator
                    else:
                        # Level1 cấp quyền, số ngày sẽ bằng số ngày còn lại của level1
                        duration_days = None

                    response = await admin_cmd.authorize_user(
                        user.username,
                        target_username,
                        chat.id,
                        duration_days
                    )

                await update.message.reply_text(response)
                return

            except Exception as e:
                print(f"Error in add command: {str(e)}")
                await update.message.reply_text("添加用户失败")
                return

        # Xử lý lệnh thu hồi quyền
        if text.lower().startswith('del'):
            try:
                args = text.split()
                if len(args) < 2:
                    await update.message.reply_text("格式错误。正确格式：del @用户账号")
                    return

                target_username = args[1].replace('@', '')

                if not target_username:
                    await update.message.reply_text("请指定用户名")
                    return

                # Kiểm tra quyền
                if not (admin_cmd.is_operator(user.username) or admin_cmd.is_level1(user.username)):
                    await update.message.reply_text("您没有权限执行此操作")
                    return

                response = await admin_cmd.revoke_user_auth(
                    admin_username=user.username,
                    target_username=target_username,
                    chat_id=chat.id
                )
                await update.message.reply_text(response)
                return

            except Exception as e:
                print(f"Error in del command: {str(e)}")
                await update.message.reply_text("删除用户失败")
                return

        # Thêm xử lý lệnh help/帮助
        if text.lower() in ['help', '帮助', '/help']:
            try:
                help_text = (
                    "🔹 基本命令:\n"
                    "💼 上班 - 开始工作\n"
                    "🏠 下班 - 结束工作\n"
                    "🍚 吃饭 - 开始休息\n"
                    "🚾 上厕所 - 开始休息\n"
                    "🚬 抽烟 - 开始休息\n"
                    "🚶‍♂️ 离开 - 开始休息\n"
                    "↩️ 回 - 结束休息\n\n"
                    
                    "🔹 交易命令:\n"
                    "+ 或 入款 [金额] - 入款\n"
                    "- 或 下发 或 xf [金额] - 下发\n"
                    "查账 - 查看交易记录\n"
                    "币价/otc - 查看当前币价\n\n"
                    
                    "🔹 管理命令:\n"
                    "expiretime - 查看授权时间\n"
                    "list - 查看授权列表\n"
                    "authuser - 授权用户\n"
                    "del - 删除授权"
                )
                await update.message.reply_text(help_text)
                return
            except Exception as e:
                print(f"Error showing help: {str(e)}")
                await update.message.reply_text("显示帮助信息失败")
                return

        # Thêm kiểm tra text là None
        if not text:
            return

        # Thêm xử lý ký tự đặc biệt
        text = text.replace('\u200b', '').strip()  # Xóa zero-width space

    except telegram.error.ChatMigrated as e:
        new_chat_id = e.new_chat_id
        group_config.update_chat_id(str(chat.id), str(new_chat_id))
        return await handle_message(update, context)
        
    except Exception as e:
        print(f"Error in handle_message: {str(e)}")
        traceback.print_exc()
            
# Thêm handler mới để xem số dư
async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    admin_cmd = AdminCommands(chat.title)
    if not (admin_cmd.is_operator(user.username) or 
            admin_cmd.is_level1(user.username) or 
            admin_cmd.is_user_authorized(user.username, chat.id)):
        await update.message.reply_text("您没有使用权限")
        return
        
    xnk = XuatNhapKhoan(chat.title)
    balance_info = xnk.get_user_balance(user.id)
    if balance_info:
        response = (f"用户: {balance_info['username']}\n"
                   f"余额: {balance_info['balance']}\n"
                   f"总入款: {balance_info['total_in']}\n"
                   f"总下发: {balance_info['total_out']}")
    else:
        response = "没有找到您的交易记录"
    
    await update.message.reply_text(response)

async def handle_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh thêm admin level 1 mới"""
    try:
        chat = update.effective_chat
        user = update.effective_user
        
        print(f"DEBUG: User {user.username} attempting to add admin")
        
        admin_cmd = AdminCommands(chat.title)
        if not (admin_cmd.is_operator(user.username) or admin_cmd.is_level1(user.username)):
            print(f"DEBUG: User {user.username} not authorized")
            await update.message.reply_text("⚠️ 只有系统管理员和一级代理可以添加一级代理")
            return
            
        # Lấy username từ lệnh và xóa @ nếu có
        target_username = update.message.text.split('add admin')[1].strip().replace("@", "")
        if not target_username:
            await update.message.reply_text("请指定用户名")
            return
            
        print(f"DEBUG: Attempting to add {target_username} as admin by {user.username}")
        
        # Lấy timezone của nhóm
        settings = group_config.get_group_settings(str(chat.id))
        group_tz = pytz.timezone(settings.get('timezone', 'UTC'))
        
        success, expiry_time = await admin_cmd.add_admin(user.username, target_username)
        print(f"DEBUG: Add admin result: {success}")
        
        if success:
            # Chuyển đổi thời gian từ UTC sang timezone của nhóm
            expiry_dt = datetime.strptime(expiry_time, '%Y-%m-%d %H:%M:%S %z').astimezone(group_tz)
            
            await update.message.reply_text(
                f"✅ 已将 {target_username} 添加为一级代理\n"
                f"到期时间: {expiry_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            await update.message.reply_text("❌ 添加一级代理失败")
            
    except Exception as e:
        print(f"Error in handle_add_admin: {str(e)}")
        traceback.print_exc()
        await update.message.reply_text("添加一级代理失败")

# Thêm các handler mới
async def handle_auth_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh cấp quyền: /authuser @username số_ngày"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not user.username:
        await update.message.reply_text("👤 您需要设置用户名才能使用此功能")
        return
        
    admin_cmd = AdminCommands(chat.title)
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "使用方法: /authuser @username 天数\n"
            "例如: /authuser @username 30"
        )
        return
        
    try:
        target_username = context.args[0]
        duration_days = int(context.args[1])
        
        if duration_days <= 0:
            await update.message.reply_text("授权天数必须大于0")
            return
            
        response = await admin_cmd.authorize_user(
            user.username,
            target_username,
            duration_days,
            chat.id,
            chat.title
        )
        await update.message.reply_text(response)
    except ValueError:
        await update.message.reply_text("请输入有效的天数")
    except Exception as e:
        await update.message.reply_text(f"授权失败: {str(e)}")

async def handle_revoke_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh thu hồi quyền: revokeuser @username hoặc del @username"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not user.username:
        await update.message.reply_text("👤 您需要设置用户名才能使用此功能")
        return
        
    if len(context.args) < 1:
        await update.message.reply_text("请指定用户名，例如: revokeuser @username")
        return
        
    admin_cmd = AdminCommands(chat.title)
    target_username = context.args[0].replace("@", "")  # Xóa @ nếu có
    response = await admin_cmd.revoke_user_auth(
        admin_username=user.username,
        target_username=target_username,
        chat_id=chat.id  # Thêm chat_id vào đây
    )
    await update.message.reply_text(response)

async def handle_check_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh kiểm tra quyền: /checkauth"""
    chat = update.effective_chat
    user = update.effective_user
    admin_cmd = AdminCommands(chat.title)
    
    user_info = await admin_cmd.get_user_info(user.id)
    if user_info:
        await update.message.reply_text(user_info)
    else:
        await update.message.reply_text("您还未获得授权")

async def handle_list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    admin_cmd = AdminCommands(chat.title)
    
    if not admin_cmd.is_operator(user.username):
        await update.message.reply_text("您没有权限查看授权列表")
        return
    
    response = await admin_cmd.list_all_auth()
    await update.message.reply_text(response)

# Thêm hàm xử lý status và group_status
async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    if not user.username:
        await update.message.reply_text("您需要设置用户名才能用此功能")
        return
        
    admin_cmd = AdminCommands(chat.title)
    if not admin_cmd.is_user_authorized(user.username, chat.id):
        await update.message.reply_text("⚠️ 您没有使用权限或授权已过期，请联系管理员")
        return
        
    tracker = ActivityTracker(chat.title)
    status = tracker.get_status(user.id)
    await update.message.reply_text(status)

async def handle_group_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    
    if not user.username:
        await update.message.reply_text("👤 您需要设置用户名才能使用此功能")
        return
        
    admin_cmd = AdminCommands(chat.title)
    if not admin_cmd.is_user_authorized(user.username, chat.id):
        await update.message.reply_text("⚠️ 您没有使用权限或授权已过期，请联系管理员")
        return
        
    tracker = ActivityTracker(chat.title)
    status = tracker.get_group_status()
    await update.message.reply_text(status)

async def handle_expiretime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat = update.effective_chat
        user = update.effective_user
        
        if not user.username:
            await update.message.reply_text("👤 您需要设置用户名才能使用此功能")
            return
            
        admin_cmd = AdminCommands(chat.title)
        
        # Lấy timezone của nhóm từ group_settings
        group_config = GroupConfig()
        settings = group_config.get_group_settings(str(chat.id))
        timezone = settings.get('timezone', 'UTC')
        tz = pytz.timezone(timezone)
        
        username = user.username.lower().replace("@", "")
        
        if not admin_cmd.is_user_authorized(username, chat.id):
            await update.message.reply_text("⚠️ 您没有使用权限或授权已过期")
            return
            
        if username == admin_cmd.DEFAULT_ADMIN:
            await update.message.reply_text("👑 系统管理员账户无过期时间")
            return
            
        admin_config = admin_cmd._load_admin_config()
        
        # Điều chỉnh emoji cho phù hợp với vai trò
        if username in admin_config.get('level1_users', {}):
            user_data = admin_config['level1_users'][username]

        elif username in admin_config.get('level2_users', {}):
            user_data = admin_config['level2_users'][username]

        else:
            await update.message.reply_text("❌ 未找到您的授权信息")
            return
            
        expiry = datetime.strptime(user_data['expiry_time'], '%Y-%m-%d %H:%M:%S %z').astimezone(tz)
        current_time = datetime.now(tz)
        
        remaining = expiry - current_time
        remaining_days = remaining.days
        remaining_hours = int(remaining.seconds / 3600)
        remaining_minutes = int((remaining.seconds % 3600) / 60)
        
        if remaining.total_seconds() > 0:
            status_emoji = "✅"
            if remaining_days > 30:
                time_emoji = "📅"
            elif remaining_days > 7:
                time_emoji = "📆"
            elif remaining_days > 0:
                time_emoji = "⏰"
            else:
                time_emoji = "⚡"
                
            response = (
                f"👤 用户: @{username}\n"
                f"{status_emoji} 授权状态: 有效\n"
                f"🌐 时区: {timezone}\n"
                f"📌 到期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"{time_emoji} 剩余时间: {remaining_days}天 {remaining_hours}小时 {remaining_minutes}分钟"
            )
        else:
            response = (
                f"👤 用户: @{username}\n"
                f"❌ 授权状态: 已过期\n"
                f"🌐 时区: {timezone}\n"
                f"⏱️ 过期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
        response = "══════════════\n" + response + "\n══════════════"
            
        await update.message.reply_text(response)
        
    except Exception as e:
        print(f"Error in handle_expiretime: {str(e)}")
        traceback.print_exc()
        await update.message.reply_text("❌ 检查授权失败，请稍后再试")

async def handle_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh cấp quyền cho nhóm"""
    chat = update.effective_chat
    user = update.effective_user
    admin_cmd = AdminCommands(chat.title)
    response = await admin_cmd.authorize_group(chat.id)
    await update.message.reply_text(response)

async def handle_recycle_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh thu hồi quyền của nhóm"""
    try:
        chat = update.effective_chat
        user = update.effective_user
        
        if not user.username:
            await update.message.reply_text("👤 您需要设置用户名才能使用此功能")
            return
            
        admin_cmd = AdminCommands(chat.title)
        
        # Kiểm tra quyền
        if not (admin_cmd.is_operator(user.username) or admin_cmd.is_level1(user.username)):
            await update.message.reply_text("⚠️ 只有管理员和一级代理可以执行此操作")
            return

        # 1. Cập nhật group_settings.json
        settings = group_config.get_group_settings(str(chat.id))
        if settings:
            settings['allow_all_members'] = False
            group_config.set_group_settings(str(chat.id), chat.title, settings)

        # 2. Thu hồi quyền trong admin_config
        response = await admin_cmd.revoke_group_auth(user.username, chat.id)
        
        await update.message.reply_text(response)
        
    except Exception as e:
        print(f"Error in handle_recycle_auth: {str(e)}")
        await update.message.reply_text("❌ 取消群组授权失败")

# Thêm hàm xử lý gửi báo cáo ngay lập tức
async def handle_send_report_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh gửi báo cáo: 发送报告/发送日报"""
    try:
        chat = update.effective_chat
        user = update.effective_user
        text = update.message.text.strip()
        
        print(f"Received command: '{text}'")
        
        # Kiểm tra quyền - chỉ cho level 1 và operator
        admin_cmd = AdminCommands(chat.title)
        is_level1 = admin_cmd.is_level1(user.username)
        is_operator = admin_cmd.is_operator(user.username)
        
        if not (is_level1 or is_operator):
            await update.message.reply_text("⚠️ 此功能仅限管理员")
            return
            
        # Lấy timezone từ tracker
        tracker = ActivityTracker(chat.title)
        tz = pytz.timezone(tracker.timezone)
        current_date = datetime.now(tz).strftime('%Y%m%d')
        
        # Xác định loại báo cáo cần xuất
        monthly_report_commands = ['发送报告', 'sendreport', '发送月报', 'sendmonthlyreport']
        daily_report_commands = ['发送日报', 'senddaily', '发送每日报告', 'senddailyreport']
        
        print(f"Checking command type...")
        print(f"Is monthly report: {text.lower() in monthly_report_commands}")
        print(f"Is daily report: {text.lower() in daily_report_commands}")
        
        if text.lower() in monthly_report_commands:
            print("Executing monthly report from XNK3...")
            
            # 1. Lấy dữ liệu từ XNK4
            daily_report = DetailedTransactionHistory(chat.title)
            
            # 2. Load config và data
            config = daily_report._load_config()
            data = daily_report._load_data()
            
            # 3. Tính toán các giá trị cần thiết
            fee_rate = config.get('fee_rate', 0)
            exchange_rate = config.get('exchange_rate', 0)
            currency_type = config.get('currency_type', '')
            
            total_in = sum(t['amount'] for t in data['transactions'] if t['type'] == '入款')
            total_out = sum(t['amount'] for t in data['transactions'] if t['type'] == '下发')
            
            expected_out = total_in * (1 - fee_rate/100)
            remaining = expected_out - total_out
            
            expected_currency = expected_out / exchange_rate if exchange_rate > 0 else 0
            total_currency_out = total_out / exchange_rate if exchange_rate > 0 else 0
            remaining_currency = remaining / exchange_rate if exchange_rate > 0 else 0
            
            # 4. Chuẩn bị dữ liệu cho XNK3
            data_for_xnk3 = {
                'fee_rate': fee_rate,
                'exchange_rate': exchange_rate,
                'currency_type': currency_type,
                'total_in': total_in,
                'total_out': total_out,
                'expected_out': expected_out,
                'expected_currency': expected_currency,
                'total_currency_out': total_currency_out,
                'remaining': remaining,
                'remaining_currency': remaining_currency
            }
            
            # 5. Xuất báo cáo tháng từ XNK3
            excel_exporter = ExcelExporter(chat.title)
            report_file, _ = excel_exporter.export_daily_balance(data_for_xnk3)
            caption = f"月度报告 - {chat.title} - {current_date}"
            no_data_msg = "没有找到本月的出入款记录"
            
        elif text.lower() in daily_report_commands:
            print("Executing daily report from XNK4...")
            daily_report = DetailedTransactionHistory(chat.title)
            report_file = daily_report.create_daily_report(current_date)
            caption = f"每日报告 - {chat.title} - {current_date}"
            no_data_msg = "没有找到今日的交易记录"
        else:
            await update.message.reply_text("无效的命令")
            return
        
        if report_file and os.path.exists(report_file):
            print(f"Sending file: {report_file}")
            await update.message.reply_document(
                document=open(report_file, 'rb'),
                caption=caption
            )
        else:
            print(f"File not found: {report_file}")
            await update.message.reply_text(no_data_msg)
            
    except Exception as e:
        print(f"Error in handle_send_report_now: {str(e)}")
        traceback.print_exc()
        await update.message.reply_text("发送报告失败，请稍后再试")

# Thêm hàm xử lý cài đặt thời gian gửi theo ngày
async def handle_set_monthly_report_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh cài đặt thời gian gửi báo cáo: 设置报告发送时间"""
    try:
        chat = update.effective_chat
        user = update.effective_user
        
        # Kiểm tra quyền
        admin_cmd = AdminCommands(chat.title)
        if not (admin_cmd.is_operator(user.username) or admin_cmd.is_level1(user.username)):
            await update.message.reply_text("⚠️ 只有系统管理员和一级代理可以设置自动发送时间")
            return

        message_parts = update.message.text.split()
        if len(message_parts) != 3:
            await update.message.reply_text("格式错误。请使用: 设置报告发送时间 日期 时间\n例如: 设置报告发送时间 1 08:00")
            return
            
        try:
            day = int(message_parts[1])
            time_str = message_parts[2]
            hour, minute = map(int, time_str.split(':'))
            
            if not (1 <= day <= 31 and 0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except ValueError:
            await update.message.reply_text("格式错误。日期必须为1-31，时间格式为HH:MM (00:00-23:59)")
            return
            
        # Lấy timezone của nhóm
        settings = group_config.get_group_settings(str(chat.id))
        group_tz = settings.get('timezone', 'UTC')
        
        success, message = await job_scheduler.schedule_monthly_report(
            context,
            chat.id,
            chat.title,
            day,
            time_str,
            group_tz
        )
        
        if success:
            # Lưu vào group_config
            settings = group_config.get_group_settings(str(chat.id)) or {}
            settings.update({
                'monthly_report_day': day,
                'monthly_report_time': time_str,
                'timezone': group_tz
            })
            group_config.set_group_settings(str(chat.id), chat.title, settings)
            
        await update.message.reply_text(message)
        
    except Exception as e:
        print(f"Error setting monthly report time: {str(e)}")
        traceback.print_exc()
        await update.message.reply_text("设置自动发送时间失败")

# Thêm hàm xử lý lệnh '授权' để cấp quyền cho toàn bộ nhóm
async def handle_group_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat = update.effective_chat
        user = update.effective_user
        message_text = update.message.text.strip()
        
        if not user.username:
            await update.message.reply_text("👤 您需要设置用户名才能使用此功能")
            return
            
        admin_cmd = AdminCommands(chat.title)
        
        # Kiểm tra quyền
        if not (admin_cmd.is_operator(user.username) or admin_cmd.is_level1(user.username)):
            await update.message.reply_text("👑 只有系统管理员和一级代理可以使用此命令")
            return
            
        # Lấy timezone của nhóm
        settings = group_config.get_group_settings(str(chat.id))
        group_tz = settings.get('timezone', 'UTC')
        tz = pytz.timezone(group_tz)
            
        # Xử lý khác nhau cho operator và level1
        if admin_cmd.is_operator(user.username):
            # Operator phải chỉ định số ngày
            try:
                parts = message_text.split()
                if len(parts) != 2:
                    await update.message.reply_text("❌ 格式错误。请使用: 授权 天数\n例如: 授权 30")
                    return
                    
                days = int(parts[1])
                if days <= 0:
                    await update.message.reply_text("❌ 天数必须大于0")
                    return
                    
                # Sử dụng timezone của nhóm
                expiry_time = (datetime.now(tz) + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S %z')
                
            except ValueError:
                await update.message.reply_text("❌ 格式错误。请使用: 授权 天数\n例如: 授权 30")
                return
        else:
            # Level1 tự động dùng thời hạn còn lại của họ
            admin_config = admin_cmd._load_admin_config()
            if user.username not in admin_config.get('level1_users', {}):
                await update.message.reply_text("❌ 无法获取您的授权信息")
                return
                
            level1_expiry = admin_config['level1_users'][user.username]['expiry_time']
            expiry_time = level1_expiry
            
            # Tính số ngày còn lại của level1 theo timezone của nhóm
            expiry_dt = datetime.strptime(expiry_time, '%Y-%m-%d %H:%M:%S %z').astimezone(tz)
            current_time = datetime.now(tz)
            days = (expiry_dt - current_time).days
            
        # Cập nhật settings
        settings = group_config.get_group_settings(str(chat.id)) or {}
        settings.update({
            'chat_id': str(chat.id),
            'title': chat.title,
            'allow_all_members': True,
            'group_expiry': expiry_time
        })
        
        group_config.set_group_settings(str(chat.id), chat.title, settings)
        
        # Format thời gian hết hạn để hiển thị theo timezone của nhóm
        expiry_dt = datetime.strptime(expiry_time, '%Y-%m-%d %H:%M:%S %z').astimezone(tz)
        formatted_expiry = expiry_dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Hiển thị thông báo khác nhau cho operator và level1
        if admin_cmd.is_operator(user.username):
            await update.message.reply_text(
                f"✅ 已授权本群所有成员使用菜单功能\n"
                f"⏳ 授权期限: {days}天\n"
                f"📅 到期时间: {formatted_expiry}\n"
                f"🌍 时区: {group_tz}"  # Thêm thông tin timezone
            )
        else:
            await update.message.reply_text(
                f"✅ 已授权本群所有成员使用菜单功能\n"
                f"⏳ 授权期限与您的一级代理权限同步\n"
                f"📅 到期时间: {formatted_expiry}\n"
                f"🌍 时区: {group_tz}"  # Thêm thông tin timezone
            )
            
    except Exception as e:
        print(f"Error in handle_group_auth: {str(e)}")
        traceback.print_exc()
        await update.message.reply_text("❌ 群组授权失败")
        return

# Thêm handler cho sự kiện thành viên mới
async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi có thành viên mới vào nhóm"""
    try:
        chat = update.effective_chat
        new_members = update.message.new_chat_members
        
        # Kiểm tra xem nhóm có được cấp quyền không
        group_config = GroupConfig()
        settings = group_config.get_group_settings(str(chat.id))
        
        if settings and settings.get('allow_all_members'):
            # Kiểm tra thời hạn của nhóm
            if 'group_expiry' in settings:
                expiry_time = datetime.strptime(settings['group_expiry'], '%Y-%m-%d %H:%M:%S %z')
                if expiry_time > datetime.now(expiry_time.tzinfo):
                    # Gửi menu cho thành viên mới
                    for member in new_members:
                        if not member.is_bot:  # Bỏ qua các bot
                            try:
                                await context.bot.send_message(
                                    chat_id=chat.id,
                                    text="🔰 请选择功能:",
                                    reply_markup=main_menu()
                                )
                            except Exception as e:
                                print(f"Error sending menu to new member {member.id}: {str(e)}")
                                
    except Exception as e:
        print(f"Error in handle_new_member: {str(e)}")

# Đặt ở ngoài hàm main(), cùng cấp với các hàm handler khác
async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cleanup khi tắt bot - chỉ operator mới có quyền"""
    try:
        user = update.effective_user
        if user.username not in OPERATORS:
            await update.message.reply_text("⚠️ 此命令仅限机器人管理员使用")
            return

        print(f"Operator {user.username} is shutting down bot...")
        for chat_id in active_groups:
            try:
                xnk = XuatNhapKhoan(chat_id)
                xnk.executor.shutdown(wait=True)
                print(f"Cleaned up resources for group {chat_id}")
            except Exception as e:
                print(f"Error cleaning up group {chat_id}: {e}")

        await update.message.reply_text("🔄 Bot正在关闭...")
        
        # Dừng application
        await context.application.stop()
        
    except Exception as e:
        print(f"Error in shutdown: {str(e)}")
        traceback.print_exc()

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Khởi tạo help_handler
    help_handler = HelpHandler()
    
    # Tạo filter cho tin nhắn nhóm
    group_filter = filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP
    
    # Thêm handlers cho help và timezone
    application.add_handler(CommandHandler("help", help_handler.handle_help, filters=group_filter))
    application.add_handler(CommandHandler("timezonelist", help_handler.handle_timezone_list, filters=group_filter))
    
    # Thêm message handlers cho help text
    application.add_handler(MessageHandler(
        (filters.Regex(r'^help$') | filters.Regex(r'^帮助$')) & group_filter & ~filters.COMMAND,
        help_handler.handle_help
    ))
    
    application.add_handler(MessageHandler(
        (filters.Regex(r'^帮助按国家设置时间$') | filters.Regex(r'^help set time zone$')) & group_filter & ~filters.COMMAND,
        help_handler.handle_timezone_list
    ))
    
    # Basic handlers - chỉ trong nhóm
    application.add_handler(CommandHandler("start", start, filters=group_filter))
    application.add_handler(CommandHandler("checkauth", handle_check_auth, filters=group_filter))
    application.add_handler(CommandHandler("expiretime", handle_expiretime, filters=group_filter))
    
    # Admin handlers - chỉ trong nhóm
    application.add_handler(CommandHandler("list", handle_list_all, filters=group_filter))
    application.add_handler(CommandHandler("auth", handle_auth, filters=group_filter))
    application.add_handler(CommandHandler("recycleauth", handle_recycle_auth, filters=group_filter))
    application.add_handler(CommandHandler("authuser", handle_auth_user, filters=group_filter))
    application.add_handler(CommandHandler("revokeuser", handle_revoke_user, filters=group_filter))
    
    # Message handlers cho các lệnh đặc biệt
    special_handlers = [
        (r'^send statistics.*', send_statistics),
        (r'^expiretime$', handle_expiretime),
        (r'^set send statistics.*', handle_set_statistics_time),
    ]
    
    for pattern, handler in special_handlers:
        application.add_handler(MessageHandler(
            filters.Regex(pattern) & group_filter & ~filters.COMMAND,
            handler
        ))
    
    # Khôi phục lịch đã lưu - thêm async/await
    async def post_init(app):
        await job_scheduler.load_all_schedules(app)
    
    # Thêm post_init vào application 
    application.post_init = post_init
    
    # Handler cho thành viên mới
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS & group_filter,
        handle_new_member
    ))
    
    # Sửa lại handler cho lệnh '授权'
    application.add_handler(MessageHandler(
        filters.Regex(r'^授权(\s+\d+)?$') & group_filter & ~filters.COMMAND,
        handle_group_auth
    ))
    
    # Trong hàm main(), thêm handler này
    application.add_handler(MessageHandler(
        filters.Regex(r'^(取消授权|撤销授权)$') & group_filter & ~filters.COMMAND,
        handle_recycle_auth
    ))
    
    # Thêm handler cho lệnh add admin (đặt trước handler tin nhắn chung)
    application.add_handler(MessageHandler(
        filters.Regex(r'^add admin.*') & group_filter & ~filters.COMMAND,
        handle_add_admin
    ))

    # Handler xử lý tin nhắn chung cuối cùng
    application.add_handler(MessageHandler(
        filters.TEXT & group_filter & ~filters.COMMAND,
        handle_message
    ))

    # Thêm handler shutdown để cleanup
    application.add_handler(CommandHandler('stop', shutdown))

    # Chạy bot
    application.run_polling()

if __name__ == '__main__':
    main()

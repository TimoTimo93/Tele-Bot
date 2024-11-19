import json
import os
from datetime import datetime
import pytz
from hethong import ActivityTracker, GroupConfig
import traceback
from xnk2 import TransactionProcessor
from threading import Thread
from XNK3 import ExcelExporter
from XNK4 import DetailedTransactionHistory
from concurrent.futures import ThreadPoolExecutor


class XuatNhapKhoan:
    def __init__(self, group_name, chat_id=None):
        self.group_name = group_name
        self.chat_id = chat_id
        self.data_file = f"data/{group_name}/transactions.json"
        self.config_file = f"data/{group_name}/config.json"
        self.daily_report = DetailedTransactionHistory(group_name)
        self.group_config = GroupConfig()
        self.tracker = ActivityTracker(group_name)
        self.new_day_flag_file = f"data/{group_name}/new_day_flag.json"
        self.processor = TransactionProcessor()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.ensure_files()

    def ensure_files(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if not os.path.exists(self.data_file):
            self._save_data({
                'transactions': [],
                'total_in': 0,
                'total_out': 0,
                'users': {}
            })
        if not os.path.exists(self.config_file):
            self._save_config({
                'fee_rate': 0,  # Tỷ lệ phí nhập khoản
                'exchange_rate': 0,  # Tỷ giá quy đổi
                'currency_type': ''  # Loại tiền tệ
            })
            
        # Tạo admin_config.json trong cùng thư mục
        admin_config_file = f"data/{self.group_name}/admin_config.json"
        if not os.path.exists(admin_config_file):
            with open(admin_config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'operators': [],
                    'authorized_groups': {},
                    'usdt_rate': 0,
                }, f, ensure_ascii=False, indent=2)

    def _save_config(self, config):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def _load_config(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'fee_rate': 0}

    def set_fee_rate(self, rate):
        """Cài đặt tỷ lệ phí nhập khoản"""
        try:
            config = self._load_config()
            config['fee_rate'] = float(rate)
            self._save_config(config)
            return f"费率设置成功：{rate}%"
        except Exception as e:
            print(f"Error setting fee rate: {str(e)}")
            raise Exception("设置费率失败")

    def set_exchange_rate(self, currency_type, rate):
        """Cài đặt tỷ giá quy đổi"""
        try:
            print(f"Setting exchange rate: {currency_type} = {rate}")  # Debug log
            
            config = self._load_config()
            config['exchange_rate'] = float(rate)
            config['currency_type'] = currency_type
            self._save_config(config)
            
            return f"{currency_type}汇率设置成功：{rate}"
        except Exception as e:
            print(f"Error in set_exchange_rate: {str(e)}")  # Debug log
            raise Exception(f"设置{currency_type}汇率失败")

    def check_balance_for_withdrawal(self, amount):
        """Kiểm tra số dư trước khi xuất khoản"""
        try:
            data = self._load_data()
            config = self._load_config()
            
            total_in = data.get('total_in', 0)
            total_out = data.get('total_out', 0)
            fee_rate = float(config.get('fee_rate', 0))
            
            # Tính toán số tiền có thể xuất
            available_amount = total_in * (1 - fee_rate/100) - total_out
            
            if amount > available_amount:
                error_message = (
                    f"❌ 余额不足\n"
                    f"💰 当前可用：<code>{available_amount:.2f}</code>\n"
                    f"📤 请求下发：<code>{amount:.2f}</code>"
                )
                return False, error_message
                
            return True, None
            
        except Exception as e:
            print(f"Error in check_balance_for_withdrawal: {str(e)}")
            return False, "检查余额时出错"

    async def process_transaction(self, user_id, username, amount, transaction_type, specified_currency=None, message=None):
        """Xử lý giao dịch bất đồng bộ"""
        try:
            # Kiểm tra số dư nếu là giao dịch xuất khoản
            if transaction_type == "下发":
                has_sufficient_balance, error_message = self.check_balance_for_withdrawal(amount)
                if not has_sufficient_balance:
                    if message and hasattr(message, 'reply_text'):
                        await message.reply_text(error_message, parse_mode='HTML')
                    return None

            # Tiếp tục xử lý giao dịch nếu số dư đủ
            data = self._load_data()
            config = self._load_config()
            
            # Lấy chat_id từ message object
            if message and hasattr(message, 'chat'):
                self.chat_id = str(message.chat.id)

            # Lấy timezone từ group_settings
            if self.chat_id:
                group_settings = self.group_config.get_group_settings(self.chat_id)
                timezone = group_settings.get('timezone', 'UTC')
            else:
                timezone = 'UTC'

            data['timezone'] = timezone

            # Lấy thông tin người gửi tin nhắn gốc nếu là reply
            original_sender = None
            if message and message.reply_to_message:
                reply_user = message.reply_to_message.from_user
                original_sender = reply_user.username or reply_user.first_name
                if original_sender:
                    original_sender = original_sender.replace('@', '')

            # Xử lý giao dịch
            message_text, updated_data = self.processor.process_transaction(
                data,
                config,
                amount,
                transaction_type,
                user_id,
                username,
                specified_currency,
                original_sender
            )

            # Lưu dữ liệu đã cập nhật
            self._save_data(updated_data)
            return message_text

        except Exception as e:
            print(f"Error in process_transaction: {str(e)}")
            traceback.print_exc()
            return None

    def _async_save_and_export(self, data):
        """Lưu data và xuất Excel trong thread riêng"""
        def save_and_export():
            try:
                self._save_data(data)
                self.export_to_excel()
            except Exception as e:
                print(f"Error in async save: {str(e)}")
                
        Thread(target=save_and_export, daemon=True).start()

    def _add_transaction(self, data, user_id, username, amount, transaction_type, original_sender=None):
        """Thêm giao dịch vào data"""
        current_time = datetime.now(pytz.timezone(self.tracker.timezone))
        transaction = {
            'user_id': user_id,
            'username': username,  # Người thao tác xuất nhập khoản (operator)
            'amount': amount,
            'type': transaction_type,
            'timestamp': current_time.strftime('%H:%M:%S'),
            'original_sender': original_sender  # Người gửi lệnh gốc
        }
        
        if 'transactions' not in data:
            data['transactions'] = []
        data['transactions'].append(transaction)

    def parse_withdrawal_command(self, text):
        """Phân tích lệnh xuất khoản"""
        try:
            # Loại bỏ khoảng trắng thừa và chuyển về chữ thường
            text = text.strip().lower()
            
            # Kiểm tra xem có bắt đầu bằng '下发' không
            if not text.startswith('下发'):
                return None, None
                
            # Lấy phần số tiền (bỏ '下发' ở đầu)
            amount_str = text[2:].strip()
            
            # Nếu chuỗi rỗng sau khi bỏ '下发'
            if not amount_str:
                return None, None
                
            # Kiểm tra ký tự cuối có phải là chữ cái không
            if amount_str[-1].isalpha():
                currency = amount_str[-1]
                try:
                    amount = float(amount_str[:-1])
                    print(f"Parsed amount with currency: {amount}{currency}")  # Debug log
                    return amount, currency
                except ValueError:
                    print(f"Failed to parse amount: {amount_str[:-1]}")  # Debug log
                    return None, None
            else:
                try:
                    amount = float(amount_str)
                    print(f"Parsed amount without currency: {amount}")  # Debug log
                    return amount, None
                except ValueError:
                    print(f"Failed to parse amount: {amount_str}")  # Debug log
                    return None, None
                
        except Exception as e:
            print(f"Error in parse_withdrawal_command: {str(e)}")  # Debug log
            return None, None

    def _load_data(self):
        """Tải dữ liệu giao dịch"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {
                    'transactions': [],
                    'total_in': 0,
                    'total_out': 0,
                    'currency_out': 0,
                    'users': {}
                }
            
            # Lấy timezone từ group_settings.json sử dụng chat_id
            if self.chat_id:
                settings = self.group_config.get_group_settings(self.chat_id)
                print(f"DEBUG: Group settings for chat_id {self.chat_id}: {settings}")
                timezone = settings.get('timezone', 'UTC')
                print(f"DEBUG: Found timezone: {timezone}")
                data['timezone'] = timezone
            else:
                print("DEBUG: No chat_id set, using UTC timezone")
                data['timezone'] = 'UTC'
            
            return data
            
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return {
                'transactions': [],
                'total_in': 0,
                'total_out': 0,
                'currency_out': 0,
                'users': {},
                'timezone': 'UTC'
            }

    def _save_data(self, data):
        """Lưu dữ liệu giao dịch"""
        try:
            # Thêm group_name vào data
            data['group_name'] = self.group_name
            
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving data: {str(e)}")
            raise

    def get_user_balance(self, user_id):
        """Lấy số dư của người dùng"""
        data = self._load_data()
        user_id = str(user_id)
        if user_id in data['users']:
            return data['users'][user_id]
        return None

    def get_group_summary(self):
        """Lấy tổng kết nhóm"""
        data = self._load_data()
        total_balance = 0
        total_in = 0
        total_out = 0
        
        for user in data['users'].values():
            total_balance += user['balance']
            total_in += user['total_in']
            total_out += user['total_out']
            
        return {
            'total_balance': total_balance,
            'total_in': total_in,
            'total_out': total_out
        }

    def _check_new_day(self):
        """Kiểm tra xem có phải đang ở ngày mới không"""
        try:
            if os.path.exists(self.new_day_flag_file):
                with open(self.new_day_flag_file, 'r') as f:
                    data = json.load(f)
                    current_date = datetime.now(pytz.timezone(self.tracker.timezone)).strftime('%Y/%m/%d')
                    if data.get('date') == current_date:
                        return True
                # Xóa file flag sau khi đã kiểm tra
                os.remove(self.new_day_flag_file)
            return False
        except:
            return False

    def clear_today_records(self):
        """Xóa hoàn toàn dữ liệu theo lệnh thủ công"""
        try:
            # Xóa file transactions.json nếu tồn tại
            if os.path.exists(self.data_file):
                os.remove(self.data_file)
            
            # Xóa hoàn toàn dữ liệu
            new_data = {
                'transactions': [],
                'total_in': 0,
                'total_out': 0,
                'currency_out': 0,
                'users': {}
            }
            
            self._save_data(new_data)
            print("All records cleared successfully")
            
            return "✅ 今日记录已清理"
        except Exception as e:
            print(f"Error in clear_today_records: {str(e)}")
            traceback.print_exc()
            return "清理失败"

    def _clear_transactions(self):
        """Xóa dữ liệu giao dịch và tạo data mới"""
        try:
            # Tạo data mới với số dư được giữ lại từ ngày trước
            new_data = {
                'transactions': [],
                'total_in': 0,
                'total_out': 0,
                'currency_out': 0,
                'users': {}
            }
            
            # Lưu data mới
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)
            
            print("Transactions cleared successfully")
            return True
            
        except Exception as e:
            print(f"Error in _clear_transactions: {str(e)}")
            traceback.print_exc()
            return False

    def auto_clear_daily(self):
        """Tự động xóa giao dịch hàng ngày"""
        try:
            print("Auto clearing daily transactions...")
            data = self._load_data()
            config = self._load_config()
            
            # Tính toán số dư còn lại
            total_in = data.get('total_in', 0)
            fee_rate = float(config.get('fee_rate', 0))
            exchange_rate = float(config.get('exchange_rate', 0))
            currency_type = config.get('currency_type', '')
            
            # Tính toán số tiền chưa xuất sau khi tính phí
            expected_out = total_in * (1 - fee_rate/100)
            total_out = data.get('total_out', 0)
            remaining = expected_out - total_out
            
            # Tính ngược lại số tiền gốc từ số tiền còn lại
            original_amount = remaining / (1 - fee_rate/100) if remaining > 0 else 0
            
            # Tính số tiền chưa xuất sau quy đổi
            remaining_currency = remaining / exchange_rate if exchange_rate > 0 else 0
            total_currency_out = data.get('currency_out', 0)

            # Chuẩn bị dữ liệu để chuyển sang XNK3
            data_for_xnk3 = {
                'fee_rate': fee_rate,
                'exchange_rate': exchange_rate,
                'currency_type': currency_type,
                'total_in': original_amount,
                'expected_out': expected_out,
                'total_out': total_out,
                'total_currency_out': total_currency_out,
                'remaining': remaining,
                'remaining_currency': remaining_currency
            }

            # Xuất số dư vào báo cáo t

            # Tạo data mới với số dư được giữ lại
            new_data = {
                'transactions': [],
                'total_in': original_amount,
                'total_out': 0,
                'currency_out': 0,
                'users': {}
            }
            self._save_data(new_data)
            

            message = (
                f"💫 <b>结转余额:</b>\n"
                f"💰 总入款: <code>{original_amount:,.0f}</code>\n"
                f"📊 费率: {fee_rate}%\n"
                f"💱 {currency_type}汇率: {exchange_rate}"
            )
            
            return message, remaining
            
        except Exception as e:
            print(f"Error in auto_clear_daily: {str(e)}")
            traceback.print_exc()
            return "Error clearing transactions", 0

    def process_command(self, command):
        """Xử lý các lệnh"""
        if command in ['清理今日记录', 'cleartodayrecord']:
            return self.clear_today_records()
        # ... existing code ...

    def check_recent_transactions(self):
        """Kiểm tra lịch sử giao dịch gần đây"""
        try:
            data = self._load_data()
            config = self._load_config()
            
            fee_rate = config.get('fee_rate', 0)
            exchange_rate = config.get('exchange_rate', 0)
            currency_type = config.get('currency_type', '')
            currency_symbol = currency_type[0] if currency_type else ''
            
            # Sắp xếp giao dịch theo thời gian mới nhất
            all_transactions = sorted(data.get('transactions', []), 
                                    key=lambda x: x['timestamp'], 
                                    reverse=True)
            
            # Tách và lấy 5 giao dịch gần nhất cho mỗi loại
            in_transactions = []
            out_transactions = []
            
            for trans in all_transactions:
                if trans['type'] == "入款" and len(in_transactions) < 5:
                    in_transactions.append(trans)
                elif trans['type'] == "下发" and len(out_transactions) < 5:
                    out_transactions.append(trans)
            
            # Tạo message với header
            message = ["<b>🔄 交易明细</b>"]
            message.append("━━━━━━━━━━━━━━")
            
            # Phần nhập khoản
            message.append(f"<b>💰 已入款（{len(in_transactions)}）</b>")
            if in_transactions:
                for t in in_transactions:
                    message.append(
                        f"👤 <code>{t['username']}</code> | ⏰ {t['timestamp']} | 💵 <code>{t['amount']}</code>"
                    )
            else:
                message.append("暂无入款记录")
            message.append("")
            
            # Phần xuất khoản
            message.append(f"<b>💸 已下发（{len(out_transactions)}）</b>")
            if out_transactions:
                for t in out_transactions:
                    amount_str = str(t['amount'])
                    if exchange_rate > 0:
                        if '(' in amount_str:
                            base_amount = float(amount_str.split('(')[0].strip())
                            currency_amount = base_amount / exchange_rate
                        else:
                            base_amount = float(amount_str)
                            currency_amount = base_amount / exchange_rate
                        
                        message.append(
                            f"👤 <code>{t['username']}</code> | ⏰ {t['timestamp']} | 💵 <code>{base_amount:.2f}</code> | 💱 <code>{currency_amount:.2f}</code>{currency_symbol}"
                        )
                    else:
                        message.append(
                            f"👤 <code>{t['username']}</code> | ⏰ {t['timestamp']} | 💵 <code>{amount_str}</code>"
                        )
            else:
                message.append("暂无下发记录")
            message.append("")
            
            # Tính toán các số liệu
            total_in = data.get('total_in', 0)
            total_out = data.get('total_out', 0)
            expected_out = total_in * (1 - fee_rate/100)
            remaining = expected_out - total_out
            
            # Thêm thông tin tổng hợp
            message.extend([
                f"💰 总入款：<code>{total_in:.2f}</code>",
                f"📊 费率：{fee_rate}%",
                f"💱 {currency_type}汇率：{exchange_rate}"
            ])
            
            # Thêm thông tin quy đổi
            if exchange_rate > 0:
                expected_currency = expected_out / exchange_rate
                total_currency_out = data.get('currency_out', 0)
                remaining_currency = expected_currency - total_currency_out
                
                message.extend([
                    "",
                    f"📈 应下发：<code>{expected_out:.2f}</code> | <code>{expected_currency:.2f}</code> {currency_symbol}",
                    f"📉 总下发：<code>{total_out:.2f}</code> | <code>{total_currency_out:.2f}</code> {currency_symbol}",
                    f"💎 未下发：<code>{remaining:.2f}</code> | <code>{remaining_currency:.2f}</code> {currency_symbol}"
                ])
            else:
                message.extend([
                    "",
                    f"📈 应下发：<code>{expected_out:.2f}</code>",
                    f"📉 总下发：<code>{total_out:.2f}</code>",
                    f"💎 未下发：<code>{remaining:.2f}</code>"
                ])
            
            return "\n".join(message)
            
        except Exception as e:
            print(f"Error in check_recent_transactions: {str(e)}")
            raise Exception("获取交易记录失败")
  
    def export_to_excel(self, date_str=None, new_day=False):
        try:
            print("Starting export to Excel...")  # Debug log
            data = self._load_data()
            config = self._load_config()
            
            # Chỉ tạo một thư mục reports
            reports_dir = f"data/{self.group_name}/reports"
            os.makedirs(reports_dir, exist_ok=True)
            
            print("Creating detailed report...")  # Debug log
            detailed_report_path = self.daily_report.create_daily_report(date_str)
            print(f"Detailed report created at: {detailed_report_path}")  # Debug log
            
            print("Creating summary report...")  # Debug log
            excel_exporter = ExcelExporter(self.group_name)
            summary_report_path = excel_exporter.export_to_excel(data, config, date_str, new_day)
            print(f"Summary report created at: {summary_report_path}")  # Debug log
            
            return detailed_report_path, summary_report_path
            
        except Exception as e:
            print(f"Error in export_to_excel: {str(e)}")
            traceback.print_exc()
            return None, None

    def generate_summary(self):
        """Chuyển hướng sang check_recent_transactions để đảm bảo format thống nhất"""
        return self.check_recent_transactions()



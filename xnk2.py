from datetime import datetime
import pytz
import json

class TransactionProcessor:
    def process_transaction(self, data, config, amount, transaction_type, user_id=None, username=None, specified_currency=None, original_sender=None):
        """Xử lý giao dịch và trả về message ngay lập tức"""
        try:
            # Lấy timezone từ data
            if 'timezone' not in data:
                print(f"DEBUG: No timezone in data: {data}")  # Thêm debug log
                raise Exception("未设置时区，请先设置时区")
            
            timezone = data['timezone']
            tz = pytz.timezone(timezone)
            print(f"DEBUG: Using timezone: {timezone}")  # Debug log
            
            # Đảm bảo amount là số float
            try:
                amount = float(amount) if amount is not None else 0.0
            except (ValueError, TypeError):
                raise Exception("金额必须是数字")

            # Sử dụng timezone khi lấy thời gian
            current_time = datetime.now(tz).strftime('%H:%M:%S')
            print(f"DEBUG: Current time in {timezone}: {current_time}")  # Debug log
            print(f"DEBUG: UTC time: {datetime.now(pytz.UTC).strftime('%H:%M:%S')}")  # Thêm debug log
            
            if transaction_type == "入款":
                data['total_in'] = data.get('total_in', 0) + amount
                display_amount = amount
            else:
                display_amount = self._process_withdrawal(data, config, amount, specified_currency)
                
            # Cập nhật transactions list
            if 'transactions' not in data:
                data['transactions'] = []
                
            # Đảm bảo username không bị None
            username = username if username else "Unknown"
            
            transaction = {
                'type': transaction_type,
                'amount': display_amount,
                'timestamp': current_time,
                'user_id': user_id,
                'username': username.replace('@', ''),  # Loại bỏ @ nếu có
                'original_sender': original_sender  # Thêm original_sender vào transaction
            }
            data['transactions'].insert(0, transaction)
                
            message = self._generate_message(data, config)
            return message, data
            
        except Exception as e:
            raise Exception(str(e))

    def _process_withdrawal(self, data, config, amount, specified_currency=None):
        """Xử lý giao dịch xuất khoản"""
        try:
            fee_rate = float(config.get('fee_rate', 0))
            exchange_rate = float(config.get('exchange_rate', 0))
            currency_type = config.get('currency_type', '')
            
            expected_out = float(data.get('total_in', 0)) * (1 - fee_rate/100)
            
            # Xử lý xuất khoản với specified_currency
            if specified_currency and currency_type and specified_currency.upper() == currency_type[0].upper():
                available_currency = expected_out / exchange_rate if exchange_rate else 0
                used_currency = float(data.get('currency_out', 0))
                remaining_currency = available_currency - used_currency

                if amount <= remaining_currency:
                    converted_amount = amount * exchange_rate
                    data['currency_out'] = used_currency + amount
                    data['total_out'] = float(data.get('total_out', 0)) + converted_amount
                else:
                    raise Exception(f"{currency_type}余额不足，当前可用：<code>{remaining_currency:.2f}</code> {currency_type}")

            # Xử lý xuất khoản thông thường
            elif exchange_rate > 0:
                remaining = expected_out - float(data.get('total_out', 0))
                if amount <= remaining + 0.01:
                    new_total_out = float(data.get('total_out', 0)) + amount
                    if abs(new_total_out - expected_out) < 0.01:
                        new_total_out = expected_out
                    data['total_out'] = new_total_out
                    data['currency_out'] = float(data.get('currency_out', 0)) + (amount / exchange_rate)
                else:
                    raise Exception(f"余额不足，当前可用：<code>{remaining:.2f}</code>")
            else:
                remaining = expected_out - float(data.get('total_out', 0))
                if amount <= remaining + 0.01:
                    data['total_out'] = float(data.get('total_out', 0)) + amount
                else:
                    raise Exception(f"余额不足，当前可用：<code>{remaining:.2f}</code>")
                
            return amount
        except ValueError as e:
            raise Exception("数据转换错误，请检查配置和金额")

    def _generate_message(self, data, config):
        """Tạo message theo format mới với HTML code"""
        # Định nghĩa các biến cần thiết ngay từ đầu phương thức
        fee_rate = config.get('fee_rate', 0)
        exchange_rate = config.get('exchange_rate', 0)
        currency_type = config.get('currency_type', '')
        currency_symbol = currency_type[0] if currency_type else ''

        # Lấy trực tiếp 5 giao dịch đầu tiên cho mỗi loại
        # vì transactions đã được sắp xếp mới nhất lên đầu
        transactions = data.get('transactions', [])
        deposits = []
        withdrawals = []
        
        for t in transactions:
            if t['type'] == '入款' and len(deposits) < 5:
                deposits.append(t)
            elif t['type'] == '下发' and len(withdrawals) < 5:
                withdrawals.append(t)
                
            # Dừng khi đã đủ 5 giao dịch cho cả 2 loại
            if len(deposits) >= 5 and len(withdrawals) >= 5:
                break
        
        # Tạo message với header
        message = ["<b>🔄 交易明细</b>"]  # Thêm tiêu đề
        message.append("━━━━━━━━━━━━━━")  # Thêm đường phân cách
        
        # Phần nhập khoản - 5 giao dịch gần nhất
        message.append(f"<b>💰 已入款（{len(deposits)}）</b>")  # Thêm icon và in đậm
        if deposits:
            for t in deposits:
                username = t.get('username', 'Unknown')
                message.append(
                    f"👤 <code>{username}</code> | ⏰ {t['timestamp']} | 💵 <code>{t['amount']}</code>"
                )
        else:
            message.append("暂无入款记录")  # Thêm thông báo khi không có giao dịch
        message.append("")
        
        # Phần xuất khoản - 5 giao dịch gần nhất với số tiền quy đổi
        message.append(f"<b>💸 已下发（{len(withdrawals)}）</b>")  # Thêm icon và in đậm
        if withdrawals:
            for t in withdrawals:
                username = t.get('username', 'Unknown')
                amount_str = str(t['amount'])
                if exchange_rate > 0:
                    if '(' in amount_str:
                        base_amount = float(amount_str.split('(')[0].strip())
                        currency_amount = base_amount / exchange_rate
                    else:
                        base_amount = float(amount_str)
                        currency_amount = base_amount / exchange_rate
                    
                    message.append(
                        f"👤 <code>{username}</code> | ⏰ {t['timestamp']} | 💵 <code>{base_amount:.2f}</code> | 💱 <code>{currency_amount:.2f}</code>{currency_symbol}"
                    )
                else:
                    message.append(
                        f"👤 <code>{username}</code> | ⏰ {t['timestamp']} | 💵 <code>{amount_str}</code>"
                    )
        else:
            message.append("暂无下发记录")  # Thêm thông báo khi không có giao dịch
        message.append("")
        
        # Tính toán các số liệu
        total_in = data.get('total_in', 0)
        total_out = data.get('total_out', 0)
        expected_out = total_in * (1 - fee_rate/100)
        remaining = expected_out - total_out
        
        # Thêm thông tin tổng hợp với icon
        message.extend([
            f"💰 总入款：<code>{total_in:.2f}</code>",
            f"📊 费率：{fee_rate}%",
            f"💱 {currency_type}汇率：{exchange_rate}"
        ])
        
        # Thêm thông tin quy đổi nếu có
        if exchange_rate > 0:
            expected_currency = expected_out / exchange_rate
            total_currency_out = data.get('currency_out', 0)
            remaining_currency = expected_currency - total_currency_out
            
            message.extend([
                "",
                f"📈 应下发：<code>{expected_out:.2f}</code> | <code>{expected_currency:.2f}</code>{currency_symbol}",
                f"📉 总下发：<code>{total_out:.2f}</code> | <code>{total_currency_out:.2f}</code>{currency_symbol}",
                f"💎 未下发：<code>{remaining:.2f}</code> | <code>{remaining_currency:.2f}</code>{currency_symbol}"
            ])
        else:
            message.extend([
                "",
                f"📈 应下发：<code>{expected_out:.2f}</code>",
                f"📉 总下发：<code>{total_out:.2f}</code>",
                f"💎 未下发：<code>{remaining:.2f}</code>"
            ])
        
        return "\n".join(message)

import json
import os
from datetime import datetime, timedelta
import aiohttp
import pytz
import hmac
import base64
from group_config import GroupConfig
import traceback
import ssl



class AdminCommands:
    def __init__(self, group_name):
        self.group_name = group_name
        self.WECHAT_KEYWORDS = ['微信', '支付宝', 'wx', 'zfb', 'wechat', 'alipay']
        self.admin_file = "data/admin_config.json"
        self.group_file = f"data/{group_name}/admin_config.json"
        self.group_settings_file = "data/group_settings.json"
        self.DEFAULT_ADMIN = "timotimo666"
        self.ensure_files()

    def ensure_files(self):
        """Khởi tạo các file config"""
        try:
            # Tạo file admin config
            os.makedirs(os.path.dirname(self.admin_file), exist_ok=True)
            if not os.path.exists(self.admin_file):
                admin_config = {
                    'operators': [self.DEFAULT_ADMIN],
                    'level1_users': {},
                    'level2_users': {},
                    'usdt_rate': 0
                }
                with open(self.admin_file, 'w', encoding='utf-8') as f:
                    json.dump(admin_config, f, indent=2, ensure_ascii=False)

            # Tạo file group config
            os.makedirs(os.path.dirname(self.group_file), exist_ok=True)
            if not os.path.exists(self.group_file):
                group_config = {
                    'group_info': {
                        'name': self.group_name,
                        'authorized_by': self.DEFAULT_ADMIN,
                        'expiry_time': None
                    },
                    'level2_users': {}
                }
                with open(self.group_file, 'w', encoding='utf-8') as f:
                    json.dump(group_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error ensuring files: {str(e)}")

    def _load_admin_config(self):
        """Load config từ file admin"""
        try:
            default_config = {
                'operators': [self.DEFAULT_ADMIN],
                'level1_users': {},
                'level2_users': {},
                'usdt_rate': 0
            }
            
            if not os.path.exists(self.admin_file):
                print(f"DEBUG: Admin file not found at {self.admin_file}")
                return default_config
                
            try:
                with open(self.admin_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    config = json.loads(content)

                    
                    # Kiểm tra và giữ lại dữ liệu hiện có
                    if 'operators' not in config:
                        config['operators'] = default_config['operators']
                    if 'level1_users' not in config:
                        config['level1_users'] = default_config['level1_users']
                    if 'level2_users' not in config:
                        config['level2_users'] = default_config['level2_users']
                    if 'usdt_rate' not in config:
                        config['usdt_rate'] = default_config['usdt_rate']
                        
                    return config
                    
            except json.JSONDecodeError as e:

                return default_config
                
        except Exception as e:
            traceback.print_exc()
            return default_config

    def _load_group_config(self):
        """Load config từ file group"""
        try:
            # Đảm bảo đường dẫn đúng đến file config của nhóm
            group_file = f"data/{self.group_name}/admin_config.json"
            
            if os.path.exists(group_file):
                with open(group_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Tạo config mặc định nếu file chưa tồn tại
                default_config = {
                    'group_info': {
                        'name': self.group_name,
                        'authorized_by': self.DEFAULT_ADMIN,
                        'expiry_time': None
                    },
                    'level2_users': {}
                }
                # Đảm bảo thư mục tồn tại
                os.makedirs(os.path.dirname(group_file), exist_ok=True)
                # Lưu config mặc định
                with open(group_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                return default_config
                
        except Exception as e:

            traceback.print_exc()
            return {'group_info': {'name': self.group_name}, 'level2_users': {}}

    async def list_operators(self):
        """Liệt kê danh sách người điều hành"""
        config = self._load_config()
        if not config['operators']:
            return "目前没有操作员"
        return "操作员列表:\n" + "\n".join(config['operators'])

    async def set_usdt_rate(self, rate):
        """Cài đặt tỷ giá USDT"""
        try:
            rate = float(rate)
            config = self._load_config()
            config['usdt_rate'] = rate
            self._save_config(config)
            return f"USDT汇率已设置为: {rate}"
        except:
            return "设置失败，请输入有效数字"

    def _generate_sign(self, timestamp, method, request_path):
        message = timestamp + method + request_path
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        d = mac.digest()
        return base64.b64encode(d).decode()

    async def get_coingecko_price(self):
        """Lấy giá USDT/CNY từ CoinGecko"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=cny"
            
            headers = {
                'accept': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and 'tether' in data:
                            price = data['tether']['cny']
                            message = (
                                "USDT/CNY 当前价格：\n"
                                f"1 USDT = CN¥{price}"
                            )
                            return message
                    print(f"API Response: {await response.text()}")  # Debug log
                    return "获取价格失败，API返回异常"
        except Exception as e:
            print(f"Error getting price: {str(e)}")  # Debug log
            return "获取价格失败，请稍后再试"

    async def authorize_group(self, admin_username, chat_id):
        """Cấp quyền cho nhóm"""
        try:
            admin_username = admin_username.replace("@", "").lower()
            
            # Kiểm tra xem người dùng có phải là admin không
            if not self.is_operator(admin_username):
                return "⚠️ 您没有权限执行此操作"
            
            # Lấy thông tin admin
            admin_config = self._load_admin_config()
            if admin_username not in admin_config.get('level1_users', {}):
                return "⚠️ 您需要先获得授权才能授权群组"
            
            # Cập nhật thông tin nhóm
            group_config = self._load_group_config()
            group_config['group_info']['authorized_by'] = admin_username
            group_config['group_info']['expiry_time'] = admin_config['level1_users'][admin_username]['expiry_time']
            
            # Lưu cấu hình
            with open(self.group_file, 'w', encoding='utf-8') as f:
                json.dump(group_config, f, ensure_ascii=False, indent=2)
            
            return "✅ 群组授权成功"
        
        except Exception as e:
            print(f"Error in authorize_group: {str(e)}")
            raise Exception("❌ 授权失败")

    async def revoke_group_auth(self, admin_username, chat_id):
        """Thu hồi quyền của nhóm"""
        try:
            admin_username = admin_username.replace("@", "").lower()
            
            # Kiểm tra xem người dùng có phải là admin hoặc level 1 không
            if not (self.is_operator(admin_username) or self.is_level1(admin_username)):
                return "⚠️ 您没有权限执行此操作"
            
            # Cập nhật thông tin nhóm
            group_config = self._load_group_config()
            if isinstance(group_config, str):
                print(f"Error loading group config: {group_config}")
                return "❌ 取消授权失败"
            
            group_config['group_info']['expiry_time'] = None
            group_config['level2_users'] = {}  # Xóa tất cả người dùng level 2
            
            try:
                # Đảm bảo thư mục tồn tại
                os.makedirs(os.path.dirname(self.group_file), exist_ok=True)
                
                # Lưu cấu hình
                with open(self.group_file, 'w', encoding='utf-8') as f:
                    json.dump(group_config, f, ensure_ascii=False, indent=2)
                    
                # Kiểm tra xem file đã được lưu đúng chưa
                if os.path.exists(self.group_file):
                    with open(self.group_file, 'r', encoding='utf-8') as f:
                        saved_config = json.load(f)
                    print(f"DEBUG: Saved config: {saved_config}")  # Log config đã lưu
                    
                    if saved_config.get('level2_users', None) != {}:
                        print("DEBUG: level2_users not empty after save!")
                        return "❌ 取消授权失败 - 保存错误"
                
                return "✅ 已取消群组授权"
                
            except Exception as e:
                print(f"Error saving group config: {str(e)}")
                return "❌ 取消授权失败 - 保存错误"
            
        except Exception as e:
            print(f"Error in revoke_group_auth: {str(e)}")
            traceback.print_exc()
            return "❌ 取消授权失败"

    async def check_expiry_time(self, group_id):
        """Kiểm tra thời hạn của nhóm"""
        try:
            admin_config = self._load_admin_config()
            group_config = self._load_group_config()
            expiry_str = admin_config['authorized_groups'].get(str(group_id))
            
            if expiry_str:
                # Lấy tracker khi cần
                tracker = self.get_tracker()
                timezone = tracker.timezone
                tz = pytz.timezone(timezone)
                
                # Parse thời gian hết hạn với timezone của nhóm
                expiry = datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
                expiry = tz.localize(expiry)
                
                # Lấy thời gian hiện tại theo timezone của nhóm
                current_time = datetime.now(tz)
                
                # Tính thời gian còn lại
                remaining = expiry - current_time
                remaining_days = remaining.days
                
                if remaining.total_seconds() > 0:
                    return f"⏳ 授权到期时间: {expiry_str} ({timezone})\n⌛ 剩余天数: {remaining_days}天"
                else:
                    return f"❌ 授权已过期\n⏰ 过期时间: {expiry_str} ({timezone})"
            return "⚠️ 该群组未授权"
        except Exception as e:
            print(f"Error in check_expiry_time: {str(e)}")
            return "❌ 检查授权失败，请稍后再试"

    def is_operator(self, username):
        """Kiểm tra xem user có phải là operator không"""
        try:
            admin_config = self._load_admin_config()
            username = username.replace("@", "").lower()
            return username == self.DEFAULT_ADMIN.lower() or username in [op.lower() for op in admin_config['operators']]
        except Exception as e:
            print(f"Error checking operator: {str(e)}")
            return username == self.DEFAULT_ADMIN.lower()

    def is_group_authorized(self, group_id):
        """Kiểm tra xem nhóm có được phép không"""
        try:
            config = self._load_config()
            expiry_str = config['authorized_groups'].get(str(group_id))
            
            if not expiry_str:
                return False
                
            # Lấy timezone từ ActivityTracker
            timezone = self.get_tracker().timezone
            tz = pytz.timezone(timezone)
            
            # Parse thời gian hết hạn với timezone của nhóm
            expiry = datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
            expiry = tz.localize(expiry)
            
            # Lấy thời gian hiện tại theo timezone của nhóm
            current_time = datetime.now(tz)
            
            return current_time < expiry
        except Exception as e:
            print(f"Error in is_group_authorized: {str(e)}")
            return False

    async def get_okx_price(self):
        """Lấy giá OTC thực tế từ OKX"""
        try:
            url = "https://www.okx.com/v3/c2c/tradingOrders/books"
            
            buy_params = {
                "quoteCurrency": "CNY",
                "baseCurrency": "USDT", 
                "side": "buy",
                "paymentMethod": "all",
                "userType": "merchant",
                "showTrade": "false",
                "showFollow": "false",
                "showAlreadyTraded": "false"
            }
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            # Tạo SSL context không xác minh chứng chỉ
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Thêm SSL context vào ClientSession
            conn = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=conn) as session:
                async with session.get(url, params=buy_params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data and "data" in data and "buy" in data["data"]:
                            merchants = data["data"]["buy"]
                            
                            bank_merchants = []
                            alipay_merchants = []
                            wechat_merchants = []
                            
                            for merchant in merchants:
                                price = float(merchant["price"])
                                name = merchant["nickName"]
                                payment_methods = merchant["paymentMethods"]
                                
                                merchant_info = {
                                    'price': price,
                                    'name': name
                                }
                                
                                for payment in payment_methods:
                                    payment = payment.lower()
                                    if any(term in payment for term in ["银行卡", "银行", "bank"]):
                                        bank_merchants.append(merchant_info)
                                    if any(term in payment for term in ["支付宝", "alipay"]):
                                        alipay_merchants.append(merchant_info)
                                    if any(term in payment for term in self.WECHAT_KEYWORDS):
                                        wechat_merchants.append(merchant_info)
                            
                            bank_merchants = sorted(list({(m['price'], m['name']): m for m in bank_merchants}.values()), 
                                                 key=lambda x: x['price'], reverse=True)
                            alipay_merchants = sorted(list({(m['price'], m['name']): m for m in alipay_merchants}.values()), 
                                                    key=lambda x: x['price'], reverse=True)
                            wechat_merchants = sorted(list({(m['price'], m['name']): m for m in wechat_merchants}.values()), 
                                                    key=lambda x: x['price'], reverse=True)
                            
                            number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
                            
                            message = "🏦OKX OTC商家实时汇率 TOP 5\n\n"
                            
                            message += "💳 银行卡价格\n"
                            for i, m in enumerate(bank_merchants[:5]):
                                message += f"{number_emojis[i]} {m['price']:.2f} {m['name']}\n"
                            
                            message += "\n💸 支付宝价格：\n"
                            for i, m in enumerate(alipay_merchants[:5]):
                                message += f"{number_emojis[i]} {m['price']:.2f} {m['name']}\n"
                            
                            message += "\n📲 微信价格：\n"
                            for i, m in enumerate(wechat_merchants[:5]):
                                message += f"{number_emojis[i]} {m['price']:.2f} {m['name']}\n"
                            
                            return message
                        
                        return "获取OKX价格失败，API返回数据格式错误"
                    
                    return f"获取OKX价格失败，HTTP状态码: {response.status}"
                    
        except aiohttp.ClientError as e:
            print(f"Connection error: {str(e)}")
            return "获取OKX价格失败，连接错误"
        except Exception as e:
            print(f"Error getting OKX price: {str(e)}")
            return f"获取OKX价格失败，错误信息: {str(e)}"

    async def authorize_user(self, admin_username, target_username, chat_id, duration_days=1):
        """Cấp quyền cho user"""
        try:
            # Xóa @ nếu có và chuyển về chữ thường
            admin_username = admin_username.replace("@", "").lower() if admin_username else None
            target_username = target_username.replace("@", "").lower() if target_username else None
            
            # Load configs
            admin_config = self._load_admin_config()
            group_config = self._load_group_config()
            
            # Kiểm tra timezone từ group_settings
            group_config_obj = GroupConfig()
            settings = group_config_obj.get_group_settings(str(chat_id))
            timezone = settings.get('timezone', 'UTC') if settings else 'UTC'
            tz = pytz.timezone(timezone)
            
            # Lấy thời gian hiện tại theo timezone của nhóm
            current_time = datetime.now(tz)
            
            # Nếu là operator cấp quyền level 1
            if admin_username == self.DEFAULT_ADMIN or admin_username in admin_config['operators']:
                expiry = current_time + timedelta(days=duration_days)
                expiry_time_str = expiry.strftime('%Y-%m-%d %H:%M:%S %z')
                current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S %z')
                
                admin_config['level1_users'][target_username] = {
                    'username': target_username,
                    'authorized_by': admin_username,
                    'authorized_date': current_time_str,
                    'expiry_time': expiry_time_str,
                    'group_ids': []
                }
                with open(self.admin_file, 'w', encoding='utf-8') as f:
                    json.dump(admin_config, f, indent=2, ensure_ascii=False)
                
                return (f"已授权用户: @{target_username}\n"
                       f"授权期限: {duration_days} 天\n"
                       f"到期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})")
               
            # Nếu là level 1 cấp quyền level 2
            elif admin_username in admin_config['level1_users']:
                # Lấy thông tin level 1
                level1_data = admin_config['level1_users'][admin_username]
                level1_expiry = datetime.strptime(level1_data['expiry_time'], '%Y-%m-%d %H:%M:%S %z').astimezone(tz)
                
                # Tính thời gian còn lại của level 1
                remaining = level1_expiry - current_time
                
                # Nếu level 1 đã hết hạn
                if remaining.total_seconds() <= 0:
                    return "您的授权已过期，无法授权其他用户"
                
                # Đặt thời hạn level 2 bằng với thời hạn còn lại của level 1
                expiry = level1_expiry
                expiry_time_str = expiry.strftime('%Y-%m-%d %H:%M:%S %z')
                current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S %z')
                
                # Tính số ngày còn lại
                remaining_days = remaining.days
                remaining_hours = int(remaining.seconds / 3600)
                remaining_minutes = int((remaining.seconds % 3600) / 60)
                
                # Lưu vào admin_config thay vì group_config
                admin_config['level2_users'][target_username] = {
                    'username': target_username,
                    'authorized_by': admin_username,
                    'authorized_date': current_time_str,
                    'expiry_time': expiry_time_str
                }
                with open(self.admin_file, 'w', encoding='utf-8') as f:
                    json.dump(admin_config, f, indent=2, ensure_ascii=False)
                
                return (f"已授权用户: @{target_username}\n"
                       f"授权期限: {remaining_days}天 {remaining_hours}小时 {remaining_minutes}分钟\n"
                       f"到期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})")
            else:
                return "您没有权限授权其他用户"
            
        except Exception as e:
            print(f"Error in authorize_user: {str(e)}")
            return f"❌ 授权失败: {str(e)}"

    async def revoke_user_auth(self, admin_username, target_username, chat_id):
        """Thu hồi quyền của user"""
        try:
            # Xóa @ nếu có và chuyển về chữ thường
            admin_username = admin_username.replace("@", "").lower()
            target_username = target_username.replace("@", "").lower()
            
            # Kiểm tra timezone từ group_settings
            group_config = GroupConfig()
            settings = group_config.get_group_settings(str(chat_id))
            timezone = settings.get('timezone', 'UTC') if settings else 'UTC'
            tz = pytz.timezone(timezone)
            
            # Lấy thời gian hiện tại theo timezone của nhóm
            current_time = datetime.now(tz)
            
            admin_config = self._load_admin_config()

            # Kiểm tra quyền của admin
            if not (admin_username == self.DEFAULT_ADMIN or 
                   admin_username in admin_config['operators'] or 
                   admin_username in admin_config['level1_users']):
                return "您没有权限撤销授权"
                
            # Thu hồi quyền level 1
            if target_username in admin_config['level1_users']:
                if not (admin_username == self.DEFAULT_ADMIN or admin_username in admin_config['operators']):
                    return "您没有权限撤销一级用户的授权"
                del admin_config['level1_users'][target_username]
                with open(self.admin_file, 'w', encoding='utf-8') as f:
                    json.dump(admin_config, f, indent=2, ensure_ascii=False)
                return f"已撤销 @{target_username} 的一级授权"
                
            # Thu hồi quyền level 2 (từ admin_config thay vì group_config)
            if target_username in admin_config.get('level2_users', {}):
                del admin_config['level2_users'][target_username]
                with open(self.admin_file, 'w', encoding='utf-8') as f:
                    json.dump(admin_config, f, indent=2, ensure_ascii=False)
                return f"已撤销 @{target_username} 授权"
                
            return f"未找到用户 @{target_username} 的授权信息"
            
        except Exception as e:
            print(f"Error in revoke_user_auth: {str(e)}")
            return f"❌ 撤销授权失败: {str(e)}"

    async def check_user_expiry(self, username, chat_id):
        """Kiểm tra thời hạn của user"""
        try:
            # Xóa @ nếu có và chuyển về chữ thường
            username = username.replace("@", "").lower()
            
            # Kiểm tra timezone từ group_settings
            group_config_obj = GroupConfig()
            settings = group_config_obj.get_group_settings(str(chat_id))
            timezone = settings.get('timezone', 'UTC') if settings else 'UTC'
            tz = pytz.timezone(timezone)
            
            # Lấy thời gian hiện tại theo timezone của nhóm
            current_time = datetime.now(tz)
            
            # Load configs
            admin_config = self._load_admin_config()
            
            # Đảm bảo load đúng file group config
            group_file = f"data/{self.group_name}/admin_config.json"
            if os.path.exists(group_file):
                with open(group_file, 'r', encoding='utf-8') as f:
                    group_config = json.load(f)
            else:
                group_config = {'group_info': {'name': self.group_name}, 'level2_users': {}}
            
            print(f"DEBUG: Group config path: {group_file}")
            print(f"DEBUG: Group config content: {group_config}")
            print(f"DEBUG: Checking username: {username}")
            print(f"DEBUG: Level2 users: {group_config.get('level2_users', {})}")
            
            # Nếu là admin mặc định
            if username == self.DEFAULT_ADMIN:
                return "系统管理员账户无过期时间"
                
            # Kiểm tra level 1
            if username in admin_config.get('level1_users', {}):
                user_data = admin_config['level1_users'][username]
                level = "一级管理"
            # Kiểm tra level 2 trong group_config
            elif username in group_config.get('level2_users', {}):
                user_data = group_config['level2_users'][username]
                level = "二级管理"
            else:
                return "未找到您的授权信息"
                
            # Parse thời gian hết hạn với timezone
            expiry = datetime.strptime(user_data['expiry_time'], '%Y-%m-%d %H:%M:%S %z')
            expiry = expiry.astimezone(tz)
            
            # Tính thời gian còn lại
            remaining = expiry - current_time
            remaining_days = remaining.days
            remaining_hours = int(remaining.seconds / 3600)
            remaining_minutes = int((remaining.seconds % 3600) / 60)
            
            if remaining.total_seconds() > 0:
                response = (
                    f"用户级别: {level}\n"
                    f"到期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})\n"
                    f"剩余时间: {remaining_days}天 {remaining_hours}小时 {remaining_minutes}分钟"
                )
            else:
                response = (
                    f"用户级别: {level}\n"
                    f"授权已过期\n"
                    f"过期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})"
                )
                
            return response
                   
        except Exception as e:
            print(f"Error in check_user_expiry: {str(e)}")
            traceback.print_exc()
            return f"❌ 检查授权失败: {str(e)}"

    def is_user_authorized(self, username, chat_id):
        """Kiểm tra quyền truy cập của user"""
        try:
            # Cập nhật trạng thái nhóm trước khi kiểm tra
            self.update_group_status(chat_id)
            
            if not username:
                print("DEBUG: No username provided") 
                return False
                
            username = username.lower().replace("@", "")
            print(f"DEBUG: Checking authorization for {username}")
        
            # Load configs
            admin_config = self._load_admin_config()
                
            # Load group settings
            group_config = GroupConfig()
            settings = group_config.get_group_settings(str(chat_id))
            timezone = settings.get('timezone', 'UTC')
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz)
            
            # 1. Kiểm tra quyền chủ bot (cao nhất)
            if username == self.DEFAULT_ADMIN:
                print(f"DEBUG: {username} is bot owner")
                return True
                
            # 2. Kiểm tra quyền operator
            if username in admin_config.get('operators', []):
                print(f"DEBUG: {username} is operator")
                return True
                
            # 3. Kiểm tra quyền level 1
            if username in admin_config.get('level1_users', {}):
                user_data = admin_config['level1_users'][username]
                expiry = datetime.strptime(user_data['expiry_time'], '%Y-%m-%d %H:%M:%S %z')
                expiry = expiry.astimezone(tz)
                if current_time < expiry:
                    print(f"DEBUG: Level1 user {username} is valid")
                    return True
                print(f"DEBUG: Level1 user {username} expired")
            
            # 4. Kiểm tra quyền level 2
            if username in admin_config.get('level2_users', {}):
                user_data = admin_config['level2_users'][username]
                expiry = datetime.strptime(user_data['expiry_time'], '%Y-%m-%d %H:%M:%S %z')
                expiry = expiry.astimezone(tz)
                if current_time < expiry:
                    print(f"DEBUG: Level2 user {username} is valid")
                    return True
                print(f"DEBUG: Level2 user {username} expired")
            
            # 5. Kiểm tra quyền nhóm (thấp nhất)
            if settings.get('allow_all_members') and settings.get('group_expiry'):
                group_expiry = datetime.strptime(settings['group_expiry'], '%Y-%m-%d %H:%M:%S %z')
                group_expiry = group_expiry.astimezone(tz)
                if current_time < group_expiry:
                    print(f"DEBUG: Group authorization is valid")
                    return True
                print(f"DEBUG: Group authorization expired")
                    
            print(f"DEBUG: {username} not authorized")
            return False
            
        except Exception as e:
            print(f"Error checking authorization: {str(e)}")
            traceback.print_exc()
            return False

    def get_user_level(self, username, chat_id):
        """Lấy cấp độ quyền của user"""
        try:
            username = username.lower().replace("@", "")
            admin_config = self._load_admin_config()
            
            if username == self.DEFAULT_ADMIN:
                return "owner"
            elif username in admin_config.get('operators', []):
                return "operator"
            elif username in admin_config.get('level1_users', {}):
                return "level1"
            elif username in admin_config.get('level2_users', {}):
                return "level2"
            else:
                group_config = GroupConfig()
                settings = group_config.get_group_settings(str(chat_id))
                if settings.get('allow_all_members'):
                    return "group"
            return None
        except Exception as e:
            print(f"Error getting user level: {str(e)}")
            return None

    async def get_user_info(self, username):
        """Lấy thông tin người dùng"""
        admin_config = self._load_admin_config()
        group_config = self._load_group_config()
        
        # Kiểm tra trong cả 2 config
        if username in admin_config['level1_users']:
            user_data = admin_config['level1_users'][username]
        #    level = "一级"
        elif username in group_config['level2_users']:
            user_data = group_config['level2_users'][username]
         #   level = "二级" 
        else:
            if username == self.DEFAULT_ADMIN:
                return "系统管理员"
            return None
        
        return (f"用户: {user_data['username']}\n"
            #    f"授权级别: {level}\n"
                f"授权人: @{user_data['authorized_by']}\n"
                f"过期时间: {user_data['expiry_time']}")

    async def list_all_auth(self, chat_id):
        """Liệt kê tất cả quyền"""
        try:
            admin_config = self._load_admin_config()
            group_config = self._load_group_config()
            
            # Lấy timezone từ group_settings
            group_settings = GroupConfig()
            settings = group_settings.get_group_settings(str(chat_id))
            timezone = settings.get('timezone', 'UTC') if settings else 'UTC'
            tz = pytz.timezone(timezone)
            
            # Lấy thời gian hiện tại theo timezone của nhóm
            current_time = datetime.now(tz)
            
            response = [f"群组: {self.group_name}"]
            # Level 1 users
            if admin_config['level1_users']:
                response.append("\n管理:")
                for username, data in admin_config['level1_users'].items():
                    # Parse thời gian với timezone
                    expiry = datetime.strptime(data['expiry_time'], '%Y-%m-%d %H:%M:%S %z').astimezone(tz)
                    auth_time = datetime.strptime(data['authorized_date'], '%Y-%m-%d %H:%M:%S %z').astimezone(tz)
                    
                    # Tính thời gian còn lại
                    remaining = expiry - current_time
                    remaining_days = remaining.days
                    remaining_hours = int(remaining.seconds / 3600)
                    remaining_minutes = int((remaining.seconds % 3600) / 60)
                    
                    if remaining.total_seconds() > 0:
                        response.extend([
                            f"用户: @{username}",
                            f"授权人: @{data['authorized_by']}",
                    #        f"授权时间: {auth_time.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})",
                            f"到期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})",
                            f"剩余时间: {remaining_days}天 {remaining_hours}小时 {remaining_minutes}分钟",
                            ""
                        ])
                    else:
                        response.extend([
                            f"用户: @{username}",
                            f"授权人: @{data['authorized_by']}",
                            "授权已过期",
                            f"过期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})",
                            ""
                        ])
                        
            # Level 2 users trong nhóm hiện tại
            if group_config['level2_users']:
                response.append("\n操作员:")
                for username, data in group_config['level2_users'].items():
                    # Parse thời gian với timezone
                    expiry = datetime.strptime(data['expiry_time'], '%Y-%m-%d %H:%M:%S %z').astimezone(tz)
                    auth_time = datetime.strptime(data['authorized_date'], '%Y-%m-%d %H:%M:%S %z').astimezone(tz)
                    
                    # Tính thời gian còn lại
                    remaining = expiry - current_time
                    remaining_days = remaining.days
                    remaining_hours = int(remaining.seconds / 3600)
                    remaining_minutes = int((remaining.seconds % 3600) / 60)
                    
                    if remaining.total_seconds() > 0:
                        response.extend([
                            f"用户: @{username}",
                            f"授权人: @{data['authorized_by']}",
                        #    f"授权时间: {auth_time.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})",
                            f"到期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})",
                            f"剩余时间: {remaining_days}天 {remaining_hours}小时 {remaining_minutes}分钟",
                            ""
                        ])
                    else:
                        response.extend([
                            f"用户: @{username}",
                            f"授权人: @{data['authorized_by']}",
                            "授权已过期",
                            f"过期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})",
                            ""
                        ])
                        
            if not admin_config['level1_users'] and not group_config['level2_users']:
                response.append("\n当前群组没有授权用户")
                
            return "\n".join(response)
 
        except Exception as e:
            print(f"Error in list_all_auth: {str(e)}")
            return f"获取授权列表失败: {str(e)}"

    def is_level1(self, username):
        """Kiểm tra xem user có phải là level 1 còn hạn không"""
        try:
            admin_config = self._load_admin_config()
            username = username.replace("@", "").lower()
            
            if username not in admin_config.get('level1_users', {}):
                return False
            
            # Kiểm tra thời hạn
            user_data = admin_config['level1_users'][username]
            expiry = datetime.strptime(user_data['expiry_time'], '%Y-%m-%d %H:%M:%S %z')
            current_time = datetime.now(expiry.tzinfo)
            
            return current_time < expiry

        except Exception as e:
            print(f"Error checking level1: {str(e)}")
            return False

    def is_level2(self, username, chat_id):
        """Kiểm tra xem user có phải là level 2 còn hạn không"""
        try:
            if not username:
                return False
            
            username = username.lower().replace("@", "")
            admin_config = self._load_admin_config()
            
            # Nếu là operator hoặc level1 còn hạn
            if (username == self.DEFAULT_ADMIN or 
                username in admin_config.get('operators', []) or
                self.is_level1(username)):
                return True

            if username not in admin_config.get('level2_users', {}):
                return False
            
            # Kiểm tra thời hạn
            user_data = admin_config['level2_users'][username]
            expiry = datetime.strptime(user_data['expiry_time'], '%Y-%m-%d %H:%M:%S %z')
            current_time = datetime.now(expiry.tzinfo)
            
            return current_time < expiry

        except Exception as e:
            print(f"Error checking level2: {str(e)}")
            return False

    async def list_group_auth(self, group_title, chat_id):
        """Liệt kê danh sách người dùng được cấp quyền trong nhóm"""
        try:
            admin_config = self._load_admin_config()
            
            # Lấy timezone từ group_settings
            group_settings = GroupConfig()
            settings = group_settings.get_group_settings(str(chat_id))
            timezone = settings.get('timezone', 'UTC') if settings else 'UTC'
            tz = pytz.timezone(timezone)
            
            # Lấy thời gian hiện tại theo timezone của nhóm
            current_time = datetime.now(tz)
            
            response = [f"══════════════\n👥 群组: {group_title}\n"]
            
            # Hiển thị level 1 users
            has_level1 = False
            if admin_config.get('level1_users'):
                for username, data in admin_config['level1_users'].items():
                    has_level1 = True
                    expiry = datetime.strptime(data['expiry_time'], '%Y-%m-%d %H:%M:%S %z').astimezone(tz)
                    
                    remaining = expiry - current_time
                    remaining_days = remaining.days
                    remaining_hours = int(remaining.seconds / 3600)
                    remaining_minutes = int((remaining.seconds % 3600) / 60)
                    
                    if remaining.total_seconds() > 0:
                        if remaining_days > 30:
                            time_emoji = "📅"
                        elif remaining_days > 7:
                            time_emoji = "📆"
                        elif remaining_days > 0:
                            time_emoji = "⏰"
                        else:
                            time_emoji = "⚡"
                        
                        response.extend([
                            f"👨‍💼 管理:@{username}",
                            f"📌 到期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})",
                            f"{time_emoji} 剩余: {remaining_days}天 {remaining_hours}小时 {remaining_minutes}分钟\n"
                        ])
                    else:
                        response.extend([
                            f"👨‍💼 管理:@{username}",
                            f"❌ 已过期",
                            f"⏱️ 过期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})\n"
                        ])
            
            if not has_level1:
                response.append("👨‍💼 管理: 暂无\n")

            # Hiển thị level 2 users
            has_level2 = False
            if admin_config.get('level2_users'):
                for username, data in admin_config['level2_users'].items():
                    has_level2 = True
                    expiry = datetime.strptime(data['expiry_time'], '%Y-%m-%d %H:%M:%S %z').astimezone(tz)
                    
                    remaining = expiry - current_time
                    remaining_days = remaining.days
                    remaining_hours = int(remaining.seconds / 3600)
                    remaining_minutes = int((remaining.seconds % 3600) / 60)
                    
                    if remaining.total_seconds() > 0:
                        if remaining_days > 30:
                            time_emoji = "📅"
                        elif remaining_days > 7:
                            time_emoji = "📆"
                        elif remaining_days > 0:
                            time_emoji = "⏰"
                        else:
                            time_emoji = "⚡"
                        
                        response.extend([
                            f"👨‍💻 操作员:@{username}",
                            f"📌 到期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})",
                            f"{time_emoji} 剩余: {remaining_days}天 {remaining_hours}小时 {remaining_minutes}分钟\n"
                        ])
                    else:
                        response.extend([
                            f"👨‍💻 操作员:@{username}",
                            f"❌ 已过期",
                            f"⏱️ 过期时间: {expiry.strftime('%Y-%m-%d %H:%M:%S')} ({timezone})\n"
                        ])

            if not has_level2:
                response.append("👨‍💻 操作员: 暂无\n")

            if not has_level1 and not has_level2:
                response.append("\n⚠️ 当前群组没有授权用户")

            # Thêm khung viền cuối
            response.append("══════════════")
            return "\n".join(response)

        except Exception as e:
            print(f"Error in list_group_auth: {str(e)}")
            traceback.print_exc()
            return "❌ 获取授权列表失败"

    def get_tracker(self):
        from hethong import ActivityTracker
        return ActivityTracker(self.group_name)

    async def add_admin(self, admin_username, target_username):
        """Thêm level1 mới với thời hạn bằng người cấp quyền"""
        try:
            # Chuẩn hóa username
            admin_username = admin_username.lower().replace("@", "")
            target_username = target_username.lower().replace("@", "")
            
            # Load config hiện tại
            admin_config = self._load_admin_config()
            
            # Kiểm tra quyền của admin
            if not (admin_username == self.DEFAULT_ADMIN or 
                    admin_username in admin_config.get('operators', []) or
                    admin_username in admin_config.get('level1_users', {})):
                return False, None
                
            # Nếu là level1, lấy thời hạn của họ
            if admin_username in admin_config.get('level1_users', {}):
                admin_expiry = datetime.strptime(
                    admin_config['level1_users'][admin_username]['expiry_time'],
                    '%Y-%m-%d %H:%M:%S %z'
                )
                # Kiểm tra xem admin còn hạn không
                if admin_expiry <= datetime.now(admin_expiry.tzinfo):
                    return False, None
            else:
                # Nếu là operator, cho thời hạn mặc định 30 ngày
                admin_expiry = datetime.now(pytz.UTC) + timedelta(days=30)

            # Tạo thông tin user mới
            expiry_time = admin_expiry.strftime('%Y-%m-%d %H:%M:%S %z')
            user_data = {
                "username": target_username,
                "authorized_by": admin_username,
                "authorized_date": datetime.now(admin_expiry.tzinfo).strftime('%Y-%m-%d %H:%M:%S %z'),
                "expiry_time": expiry_time,
                "group_ids": []
            }
            
            # Thêm vào config
            if 'level1_users' not in admin_config:
                admin_config['level1_users'] = {}
            admin_config['level1_users'][target_username] = user_data
            
            # Lưu lại config
            with open(self.admin_file, 'w', encoding='utf-8') as f:
                json.dump(admin_config, f, indent=2, ensure_ascii=False)
                
            return True, expiry_time
            
        except Exception as e:
            print(f"Error in add_admin: {str(e)}")
            return False, None

    def update_group_status(self, chat_id):
        """Cập nhật trạng thái của nhóm dựa trên thời hạn"""
        try:
            # Load group settings
            group_config = GroupConfig()
            settings = group_config.get_group_settings(str(chat_id))
            
            if not settings:
                return
            
            # Lấy timezone và thời gian hiện tại
            timezone = settings.get('timezone', 'UTC')
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz)
            
            # Kiểm tra thời hạn
            if settings.get('group_expiry'):
                group_expiry = datetime.strptime(settings['group_expiry'], '%Y-%m-%d %H:%M:%S %z')
                group_expiry = group_expiry.astimezone(tz)
                
                # Nếu đã hết hạn, cập nhật allow_all_members thành false
                if current_time >= group_expiry and settings.get('allow_all_members'):
                    settings['allow_all_members'] = False
                    
                    # Sử dụng config_file từ GroupConfig
                    with open(group_config.config_file, 'r', encoding='utf-8') as f:
                        all_settings = json.load(f)
                    
                    all_settings[str(chat_id)] = settings
                    
                    with open(group_config.config_file, 'w', encoding='utf-8') as f:
                        json.dump(all_settings, f, indent=4, ensure_ascii=False)
                    
                    print(f"DEBUG: Updated group {chat_id} status to inactive due to expiration")
                    
        except Exception as e:
            print(f"Error updating group status: {str(e)}")
            traceback.print_exc()
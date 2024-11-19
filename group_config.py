import json
import os
import traceback

class GroupConfig:
    def __init__(self):
        self.config_file = 'group_settings.json'
        self.settings = {}
        
        # Tạo thư mục data nếu chưa tồn tại
        os.makedirs('data', exist_ok=True)
        
        # Đảm bảo file config tồn tại
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
        
        self.load_config()

    def load_config(self):
        """Tải cấu hình từ file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            else:
                # Nếu file chưa tồn tại, tạo file mới với dict rỗng
                self.settings = {}
                self.save_config()
        except Exception as e:
            print(f"Error loading config: {str(e)}")
            self.settings = {}  # Đảm bảo settings luôn là dict hợp lệ

    def save_config(self):
        """Lưu cấu hình vào file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {str(e)}")
            return False

    def set_group_timezone(self, chat_id, group_name, timezone, country):
        """Cài đặt timezone cho nhóm"""
        try:
            chat_id = str(chat_id)  # Đảm bảo chat_id là string
            
            print(f"DEBUG: Setting timezone for chat_id: {chat_id}")
            print(f"DEBUG: Group name: {group_name}")
            print(f"DEBUG: Timezone: {timezone}")
            
            if chat_id not in self.settings:
                self.settings[chat_id] = {}
                
            self.settings[chat_id].update({
                'timezone': timezone,
                'country': country,
                'title': group_name,
                'chat_id': chat_id  # Thêm chat_id vào settings
            })
            
            print(f"DEBUG: Updated settings: {self.settings[chat_id]}")
            
            self.save_config()
            return True
        except Exception as e:
            print(f"Error setting timezone: {str(e)}")
            return False

    def set_group_auto_send_time(self, group_id, group_name, time_str):
        """Cài đặt thời gian gửi tự động cho nhóm"""
        if group_id not in self.settings:
            self.settings[group_id] = {
                'group_name': group_name,
                'timezone': 'UTC',
                'country': None,
                'auto_send_time': time_str
            }
        else:
            self.settings[group_id]['auto_send_time'] = time_str
        self.save_config()

    def get_group_settings(self, chat_id):
        """Lấy settings của nhóm"""
        try:
            print(f"DEBUG: Getting settings for chat_id: {chat_id}")  # Debug log
            print(f"DEBUG: Current settings: {self.settings}")  # Debug log
            
            # Thử tìm theo chat_id
            settings = self.settings.get(str(chat_id))
            if settings:
                print(f"DEBUG: Found settings by chat_id: {settings}")  # Debug log
                return settings
            
            # Thử tìm theo tên nhóm
            for group_id, group_settings in self.settings.items():
                if group_settings.get('title') == chat_id:
                    print(f"DEBUG: Found settings by title: {group_settings}")  # Debug log
                    return group_settings
            
            print(f"DEBUG: No settings found for {chat_id}")  # Debug log
            return {}
        except Exception as e:
            print(f"Error getting group settings: {str(e)}")
            return {}

    def get_all_groups(self):
        """Lấy cấu hình của tất cả các nhóm"""
        return self.settings

    def sync_timezone_with_tracker(self, group_id, tracker):
        """Đồng bộ timezone giữa GroupConfig và ActivityTracker"""
        settings = self.get_group_settings(str(group_id))
        if settings and 'timezone' in settings:
            tracker.timezone = settings['timezone']
        else:
            # Nếu chưa có settings, lấy từ tracker
            self.set_group_timezone(
                str(group_id),
                tracker.group_name,
                tracker.timezone,
                None
            )

    def set_group_report_schedule(self, chat_id, group_name, settings):
        """Lưu cấu hình lịch gửi báo cáo của nhóm"""
        try:
            config = self.get_all_settings()
            if chat_id not in config:
                config[chat_id] = {'group_name': group_name}
            
            config[chat_id].update({
                'monthly_report_day': settings['monthly_report_day'],
                'monthly_report_time': settings['monthly_report_time']
            })
            
            self.save_config(config)
            return True
        except Exception as e:
            print(f"Error loading config: {str(e)}")

    def get_all_settings(self):
        """Lấy tất cả cài đặt của các nhóm"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading config: {str(e)}")
            return {}

    def set_group_settings(self, chat_id, chat_title, settings):
        """Lưu cài đặt cho nhóm"""
        try:
            # Đọc config hiện tại
            config = self.get_all_settings()
            
            # Cập nhật hoặc tạo mới cài đặt cho nhóm
            if chat_id not in config:
                config[chat_id] = {
                    'group_name': chat_title
                }
            
            # Cập nhật các cài đặt mới
            config[chat_id].update(settings)
            
            # Lưu lại vào file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
                
            return True
            
        except Exception as e:
            print(f"Error saving group settings: {str(e)}")
            return False

    def get_group_settings(self, chat_id):
        """Lấy cài đặt của một nhóm cụ thể"""
        try:
            config = self.get_all_settings()
            return config.get(chat_id, {})
        except Exception as e:
            print(f"Error getting group settings: {str(e)}")
            return {}

    def remove_group_settings(self, chat_id: str):
        """Xóa cấu hình của một group"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                if chat_id in config:
                    del config[chat_id]
                    
                    with open(self.config_file, 'w', encoding='utf-8') as f:
                        json.dump(config, f, ensure_ascii=False, indent=2)
                        
        except Exception as e:
            print(f"Error removing group settings: {str(e)}")

    def update_chat_id(self, old_chat_id: str, new_chat_id: str):
        """Cập nhật chat_id khi group được nâng cấp lên supergroup"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            if old_chat_id in config:
                # Sao chép cấu hình từ chat_id cũ sang mới
                config[new_chat_id] = config[old_chat_id]
                # Xóa cấu hình cũ
                del config[old_chat_id]
                
                # Lưu cấu hình mới
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                    
                print(f"Updated chat_id from {old_chat_id} to {new_chat_id}")
                
        except Exception as e:
            print(f"Error updating chat_id: {str(e)}")

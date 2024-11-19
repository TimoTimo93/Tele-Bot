from datetime import datetime
import pytz
from group_config import GroupConfig

def is_user_authorized(username, group_id=None, admin_config=None, group_config=None):
    """Kiểm tra quyền của người dùng"""
    try:
        username = username.replace("@", "").lower()
        
        # Lấy timezone
        try:
            group_settings = GroupConfig()
            settings = group_settings.get_group_settings(str(group_id))
            timezone = settings.get('timezone', 'UTC') if settings else 'UTC'
        except:
            timezone = 'UTC'
            
        current_time = datetime.now(pytz.timezone(timezone))
        
        # Kiểm tra level 1
        if admin_config and username in admin_config.get('level1_users', {}):
            user_data = admin_config['level1_users'][username]
            expiry = datetime.strptime(user_data['expiry_time'], '%Y-%m-%d %H:%M:%S %z')
            if current_time >= expiry:
                return False
            return True
            
        # Kiểm tra level 2
        if group_config and username in group_config.get('level2_users', {}):
            user_data = group_config['level2_users'][username]
            expiry = datetime.strptime(user_data['expiry_time'], '%Y-%m-%d %H:%M:%S %z')
            if current_time >= expiry:
                return False
            return True
            
        return False
        
    except Exception as e:
        print(f"Error in is_user_authorized: {str(e)}")
        return False

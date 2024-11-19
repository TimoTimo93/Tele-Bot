import json
import os
import traceback
from datetime import datetime, timedelta
from group_config import GroupConfig
import pytz
import json
from admin_commands import AdminCommands

class ActivityTracker:
    def __init__(self, group_name):
        self.history_dir = 'statistics'
        os.makedirs(self.history_dir, exist_ok=True)
        
        self.group_name = group_name
        self.group_config = GroupConfig()
        
        # Lấy settings của nhóm
        settings = self.group_config.get_group_settings(group_name)
        if not settings:
            # Nếu không tìm thấy bằng group_name, thử tìm bằng title
            all_settings = self.group_config.get_all_settings()
            for chat_id, group_settings in all_settings.items():
                if group_settings.get('title') == group_name:
                    settings = group_settings
                    break
        
        # Lấy timezone từ settings
        self.timezone = settings.get('timezone') if settings and 'timezone' in settings else 'Asia/Ho_Chi_Minh'
        
        try:
            self.tz = pytz.timezone(self.timezone)
        except Exception as e:
            print(f"Error setting timezone: {str(e)}")
            self.timezone = 'Asia/Ho_Chi_Minh'
            self.tz = pytz.timezone(self.timezone)
        
        current_date = datetime.now(self.tz).strftime('%Y%m%d')
        clean_group_name = "".join(c for c in group_name if c.isalnum() or c.isspace()).strip()
        self.data_file = os.path.join(self.history_dir, f"{clean_group_name}_{current_date}.json")
        
        self.work_sessions = {}
        self.break_sessions = {}
        self.activity_summary = {}
        self.usernames = {}
        self.auto_send_times = {}
        self.daily_work_history = {}
        self.daily_work_duration = {}
        self.load_data()
        
        # Thêm timezone_map vào instance
        self.timezone_map = {
            'afghanistan': 'Asia/Kabul',
            'albania': 'Europe/Tirane',
            'algeria': 'Africa/Algiers',
            'andorra': 'Europe/Andorra',
            'angola': 'Africa/Luanda',
            'antigua_and_barbuda': 'America/Antigua',
            'argentina': 'America/Argentina/Buenos_Aires',
            'armenia': 'Asia/Yerevan',
            'australia': 'Australia/Sydney',
            'austria': 'Europe/Vienna',
            'azerbaijan': 'Asia/Baku',
            'bahamas': 'America/Nassau',
            'bahrain': 'Asia/Bahrain',
            'bangladesh': 'Asia/Dhaka',
            'barbados': 'America/Barbados',
            'belarus': 'Europe/Minsk',
            'belgium': 'Europe/Brussels',
            'belize': 'America/Belize',
            'benin': 'Africa/Porto-Novo',
            'bhutan': 'Asia/Thimphu',
            'bolivia': 'America/La_Paz',
            'bosnia_and_herzegovina': 'Europe/Sarajevo',
            'botswana': 'Africa/Gaborone',
            'brazil': 'America/Sao_Paulo',
            'brunei': 'Asia/Brunei',
            'bulgaria': 'Europe/Sofia',
            'burkina_faso': 'Africa/Ouagadougou',
            'burundi': 'Africa/Bujumbura',
            'cabo_verde': 'Atlantic/Cape_Verde',
            'cambodia': 'Asia/Phnom_Penh',
            'cameroon': 'Africa/Douala',
            'canada': 'America/Toronto',
            'central_african_republic': 'Africa/Bangui',
            'chad': 'Africa/Ndjamena',
            'chile': 'America/Santiago',
            'china': 'Asia/Shanghai',
            'colombia': 'America/Bogota',
            'comoros': 'Indian/Comoro',
            'congo_kinshasa': 'Africa/Kinshasa',
            'congo_brazzaville': 'Africa/Brazzaville',
            'costa_rica': 'America/Costa_Rica',
            'croatia': 'Europe/Zagreb',
            'cuba': 'America/Havana',
            'cyprus': 'Asia/Nicosia',
            'czech_republic': 'Europe/Prague',
            'denmark': 'Europe/Copenhagen',
            'djibouti': 'Africa/Djibouti',
            'dominica': 'America/Dominica',
            'dominican_republic': 'America/Santo_Domingo',
            'ecuador': 'America/Guayaquil',
            'egypt': 'Africa/Cairo',
            'el_salvador': 'America/El_Salvador',
            'equatorial_guinea': 'Africa/Malabo',
            'eritrea': 'Africa/Asmara',
            'estonia': 'Europe/Tallinn',
            'eswatini': 'Africa/Mbabane',
            'ethiopia': 'Africa/Addis_Ababa',
            'fiji': 'Pacific/Fiji',
            'finland': 'Europe/Helsinki',
            'france': 'Europe/Paris',
            'gabon': 'Africa/Libreville',
            'gambia': 'Africa/Banjul',
            'georgia': 'Asia/Tbilisi',
            'germany': 'Europe/Berlin',
            'ghana': 'Africa/Accra',
            'greece': 'Europe/Athens',
            'grenada': 'America/Grenada',
            'guatemala': 'America/Guatemala',
            'guinea': 'Africa/Conakry',
            'guinea_bissau': 'Africa/Bissau',
            'guyana': 'America/Guyana',
            'haiti': 'America/Port-au-Prince',
            'honduras': 'America/Tegucigalpa',
            'hungary': 'Europe/Budapest',
            'iceland': 'Atlantic/Reykjavik',
            'india': 'Asia/Kolkata',
            'indonesia': 'Asia/Jakarta',
            'iran': 'Asia/Tehran',
            'iraq': 'Asia/Baghdad',
            'ireland': 'Europe/Dublin',
            'israel': 'Asia/Jerusalem',
            'italy': 'Europe/Rome',
            'ivory_coast': 'Africa/Abidjan',
            'jamaica': 'America/Jamaica',
            'japan': 'Asia/Tokyo',
            'jordan': 'Asia/Amman',
            'kazakhstan': 'Asia/Almaty',
            'kenya': 'Africa/Nairobi',
            'kiribati': 'Pacific/Tarawa',
            'kosovo': 'Europe/Belgrade',
            'kuwait': 'Asia/Kuwait',
            'kyrgyzstan': 'Asia/Bishkek',
            'laos': 'Asia/Vientiane',
            'latvia': 'Europe/Riga',
            'lebanon': 'Asia/Beirut',
            'lesotho': 'Africa/Maseru',
            'liberia': 'Africa/Monrovia',
            'libya': 'Africa/Tripoli',
            'liechtenstein': 'Europe/Vaduz',
            'lithuania': 'Europe/Vilnius',
            'luxembourg': 'Europe/Luxembourg',
            'madagascar': 'Indian/Antananarivo',
            'malawi': 'Africa/Blantyre',
            'malaysia': 'Asia/Kuala_Lumpur',
            'maldives': 'Indian/Maldives',
            'mali': 'Africa/Bamako',
            'malta': 'Europe/Malta',
            'marshall_islands': 'Pacific/Majuro',
            'mauritania': 'Africa/Nouakchott',
            'mauritius': 'Indian/Mauritius',
            'mexico': 'America/Mexico_City',
            'micronesia': 'Pacific/Chuuk',
            'moldova': 'Europe/Chisinau',
            'monaco': 'Europe/Monaco',
            'mongolia': 'Asia/Ulaanbaatar',
            'montenegro': 'Europe/Podgorica',
            'morocco': 'Africa/Casablanca',
            'mozambique': 'Africa/Maputo',
            'myanmar': 'Asia/Yangon',
            'namibia': 'Africa/Windhoek',
            'nauru': 'Pacific/Nauru',
            'nepal': 'Asia/Kathmandu',
            'netherlands': 'Europe/Amsterdam',
            'new_zealand': 'Pacific/Auckland',
            'nicaragua': 'America/Managua',
            'niger': 'Africa/Niamey',
            'nigeria': 'Africa/Lagos',
            'north_korea': 'Asia/Pyongyang',
            'north_macedonia': 'Europe/Skopje',
            'norway': 'Europe/Oslo',
            'oman': 'Asia/Muscat',
            'pakistan': 'Asia/Karachi',
            'palau': 'Pacific/Palau',
            'panama': 'America/Panama',
            'papua_new_guinea': 'Pacific/Port_Moresby',
            'paraguay': 'America/Asuncion',
            'peru': 'America/Lima',
            'philippines': 'Asia/Manila',
            'poland': 'Europe/Warsaw',
            'portugal': 'Europe/Lisbon',
            'qatar': 'Asia/Qatar',
            'romania': 'Europe/Bucharest',
            'russia': 'Europe/Moscow',
            'rwanda': 'Africa/Kigali',
            'saint_kitts_and_nevis': 'America/St_Kitts',
            'saint_lucia': 'America/St_Lucia',
            'saint_vincent_and_the_grenadines': 'America/St_Vincent',
            'samoa': 'Pacific/Apia',
            'san_marino': 'Europe/San_Marino',
            'saudi_arabia': 'Asia/Riyadh',
            'senegal': 'Africa/Dakar',
            'serbia': 'Europe/Belgrade',
            'seychelles': 'Indian/Mahe',
            'sierra_leone': 'Africa/Freetown',
            'singapore': 'Asia/Singapore',
            'slovakia': 'Europe/Bratislava',
            'slovenia': 'Europe/Ljubljana',
            'solomon_islands': 'Pacific/Guadalcanal',
            'somalia': 'Africa/Mogadishu',
            'south_africa': 'Africa/Johannesburg',
            'south_korea': 'Asia/Seoul',
            'south_sudan': 'Africa/Juba',
            'spain': 'Europe/Madrid',
            'sri_lanka': 'Asia/Colombo',
            'sudan': 'Africa/Khartoum',
            'suriname': 'America/Paramaribo',
            'sweden': 'Europe/Stockholm',
            'switzerland': 'Europe/Zurich',
            'syria': 'Asia/Damascus',
            'taiwan': 'Asia/Taipei',
            'tajikistan': 'Asia/Dushanbe',
            'tanzania': 'Africa/Dar_es_Salaam',
            'thailand': 'Asia/Bangkok',
            'togo': 'Africa/Lome',
            'tonga': 'Pacific/Tongatapu',
            'trinidad_and_tobago': 'America/Port_of_Spain',
            'tunisia': 'Africa/Tunis',
            'turkey': 'Europe/Istanbul',
            'turkmenistan': 'Asia/Ashgabat',
            'tuvalu': 'Pacific/Funafuti',
            'uganda': 'Africa/Kampala',
            'ukraine': 'Europe/Kiev',
            'united_arab_emirates': 'Asia/Dubai',
            'united_kingdom': 'Europe/London',
            'united_states': 'America/New_York',
            'uruguay': 'America/Montevideo',
            'uzbekistan': 'Asia/Tashkent',
            'vanuatu': 'Pacific/Efate',
            'vatican': 'Europe/Vatican',
            'venezuela': 'America/Caracas',
            'vietnam': 'Asia/Ho_Chi_Minh',
            'yemen': 'Asia/Aden',
            'zambia': 'Africa/Lusaka',
            'zimbabwe': 'Africa/Harare'
        }

    def load_configs(self):
        """Load configs khi cần thiết"""
        if self.admin_config is None:
            from admin_commands import AdminCommands
            admin_cmd = AdminCommands(self.group_name)
            self.admin_config = admin_cmd._load_admin_config()
            self.group_config = admin_cmd._load_group_config()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.work_sessions = {int(k): v for k, v in data.get('work_sessions', {}).items()}
                self.break_sessions = {str(k): v for k, v in data.get('break_sessions', {}).items()}
                self.usernames = {int(k): v for k, v in data.get('usernames', {}).items()}
                self.auto_send_times = data.get('auto_send_times', {})
                self.timezone = data.get('timezone', 'UTC')
                self.daily_work_duration = data.get('daily_work_duration', {})
                self.daily_work_history = data.get('daily_work_history', {})
                
                # Xử lý activity_summary
                activity_summary = data.get('activity_summary', {})
                self.activity_summary = {}
                for user_id, activities in activity_summary.items():
                    self.activity_summary[int(user_id)] = {}
                    for activity, info in activities.items():
                        time_parts = info['total_duration'].split(':')
                        if len(time_parts) == 3:
                            hours, minutes, seconds = time_parts
                            seconds = float(seconds.split('.')[0])
                            total_seconds = int(hours) * 3600 + int(minutes) * 60 + seconds
                        else:
                            total_seconds = 0
                        
                        self.activity_summary[int(user_id)][activity] = {
                            'count': info['count'],
                            'total_duration': timedelta(seconds=total_seconds)
                        }

    def save_data(self):
        data = {
            'work_sessions': self.work_sessions,
            'break_sessions': self.break_sessions,
            'activity_summary': self.activity_summary,
            'usernames': self.usernames,
            'auto_send_times': self.auto_send_times,
            'timezone': self.timezone,
            'daily_work_duration': self.daily_work_duration,
            'daily_work_history': self.daily_work_history
        }
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, default=str, indent=4, ensure_ascii=False)

    def get_current_time(self):
        """Lấy thời gian hiện tại theo timezone đã cài đặt"""
        try:
            current = datetime.now(self.tz)
            return current.replace(microsecond=0)
        except Exception as e:
            print(f"Error in get_current_time: {str(e)}")
            return datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).replace(microsecond=0)

    def start_work(self, user_id, username):
        """Bắt đầu ca làm việc"""
        try:
            self.usernames[user_id] = username
            self.save_data()
            
            if not self.is_user_authorized(user_id):
                return "⚠️ 您没有使用权限或授权已过期，请联系管理员"
            
            if user_id in self.work_sessions:
                return "⚠️ 您已经在上班中，无需重复选择。如需重新开始，请先选择下班。"
            
            current_time = self.get_current_time()
            
            self.work_sessions[user_id] = current_time.isoformat()
            self.save_data()
            
            display_time = current_time.strftime('%H:%M:%S')
            
            return f"💼 {username} 已上班\n⏰ 上班时间: {display_time}"
                
        except Exception as e:
            print(f"Error in start_work: {str(e)}")
            traceback.print_exc()
            return "❌ 上班失败，请稍后再试"

    def start_break(self, user_id, break_type):
        try:
            if user_id not in self.work_sessions:
                return "⚠️ 您还没有上班！"
            
            if str(user_id) in self.break_sessions:
                current_break = self.break_sessions[str(user_id)][1]
                return f"⚠️ 正在{current_break}中，请先选择 '回' 后再选择其他功能。"
            
            current_time = self.get_current_time()
            self.break_sessions[str(user_id)] = (current_time.isoformat(), break_type)
            self.save_data()
            
            # Emoji tương ứng cho từng loại break
            break_emojis = {
                "吃饭": "🍚",
                "上厕所": "🚾",
                "抽烟": "🚬",
                "离开": "🚶‍♂️"
            }
            emoji = break_emojis.get(break_type, "")
            return f"{emoji} 开始{break_type}。"
            
        except Exception as e:
            print(f"Error in start_break: {str(e)}")
            return "❌ 操作失败，请稍后再试"

    def end_break(self, user_id, username):
        try:
            if str(user_id) not in self.break_sessions:
                return "⚠️ 您没有在休息！"
            
            start_time_str, break_type = self.break_sessions.pop(str(user_id))
            start_time = datetime.fromisoformat(start_time_str).replace(microsecond=0)
            end_time = self.get_current_time()
            
            break_duration = end_time - start_time
            
            user_id_str = str(user_id)
            if not hasattr(self, 'daily_work_history'):
                self.daily_work_history = {}
                
            if user_id_str not in self.daily_work_history:
                self.daily_work_history[user_id_str] = {
                    "work_sessions": [],
                    "total_work_duration": "0:00:00",
                    "actual_total_work_time": "0:00:00",
                    "break_history": {}
                }
                
            # Khởi tạo break_history cho loại break cụ thể nếu chưa có
            if break_type not in self.daily_work_history[user_id_str]["break_history"]:
                self.daily_work_history[user_id_str]["break_history"][break_type] = []
                
            # Thêm session break mới
            break_session = {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration": str(break_duration)
            }
            self.daily_work_history[user_id_str]["break_history"][break_type].append(break_session)
            
            # Cập nhật activity_summary
            if user_id not in self.activity_summary:
                self.activity_summary[user_id] = {}
                
            if break_type not in self.activity_summary[user_id]:
                self.activity_summary[user_id][break_type] = {
                    'count': 0,
                    'total_duration': timedelta()
                }
                
            self.activity_summary[user_id][break_type]['count'] += 1
            self.activity_summary[user_id][break_type]['total_duration'] += break_duration
            
            self.save_data()
            
            # Tạo thống kê chi tiết cho loại break này
            break_sessions = self.daily_work_history[user_id_str]["break_history"][break_type]
            sessions_summary = "\n".join([
                f"第{i+1}次 {break_type}: {session['duration']}"
                for i, session in enumerate(break_sessions)
            ])
            
            # Tính tổng thời gian của loại break này
            total_break_duration = sum(
                [datetime.strptime(s["duration"].split('.')[0], '%H:%M:%S').time().hour * 3600 +
                 datetime.strptime(s["duration"].split('.')[0], '%H:%M:%S').time().minute * 60 +
                 datetime.strptime(s["duration"].split('.')[0], '%H:%M:%S').time().second
                 for s in break_sessions],
                start=0
            )
            total_break_time = str(timedelta(seconds=total_break_duration))
            
            formatted_duration = str(break_duration).split('.')[0]
            
            # Thêm emoji vào thông báo tổng kết
            break_emojis = {
                "吃饭": "🍚",
                "上厕所": "🚾",
                "抽烟": "🚬",
                "离开": "🚶‍♂️"
            }
            emoji = break_emojis.get(break_type, "")
            
            return (
                f"{emoji} {break_type}结束\n"
                f"⏱️ 本次时长: {break_duration}\n\n"
#                f"📊 今日{break_type}统计:\n{sessions_summary}\n"
#                f"🔢 总次数: {self.activity_summary[user_id][break_type]['count']}次\n"
                f"{emoji} {break_type}: "
                f"🔢 {self.activity_summary[user_id][break_type]['count']}次\n"
                f"⌛ 总时长: {self.activity_summary[user_id][break_type]['total_duration']}"
            )
                
        except Exception as e:
            print(f"Error in end_break: {str(e)}")
            return "❌ 操作失败，请稍后再试"

    def end_work(self, user_id, username):
        try:
            if user_id not in self.work_sessions:
                return "⚠️ 您还没有上班！"
            
            if str(user_id) in self.break_sessions:
                break_type = self.break_sessions[str(user_id)][1]
                return f"⚠️ 您还在{break_type}中，请先选择 '回' 后再下班。"

            end_time = self.get_current_time()
            start_time = datetime.fromisoformat(self.work_sessions[user_id])
            
            # Đảm bảo cả hai thời gian đều có timezone
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=self.tz)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=self.tz)
            
            # Tính thời gian làm việc
            current_work_duration = end_time - start_time
            
            user_id_str = str(user_id)
            total_break_duration = timedelta()
            
            def format_timedelta(td):
                total_seconds = int(td.total_seconds())
                if total_seconds < 0:
                    total_seconds = 0
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            def parse_duration(duration_str):
                try:
                    if not duration_str or 'day' in duration_str:
                        return timedelta(0)
                    if '.' in duration_str:
                        duration_str = duration_str.split('.')[0]
                    hours, minutes, seconds = map(int, duration_str.split(':'))
                    return timedelta(hours=hours, minutes=minutes, seconds=seconds)
                except (ValueError, TypeError):
                    print(f"Warning: Invalid duration format: {duration_str}")
                    return timedelta(0)
            
            # Tính tổng thời gian nghỉ
            if hasattr(self, 'daily_work_history') and user_id_str in self.daily_work_history:
                for break_type, breaks in self.daily_work_history[user_id_str].get("break_history", {}).items():
                    for break_session in breaks:
                        break_start = datetime.fromisoformat(break_session["start_time"])
                        if start_time <= break_start <= end_time:
                            total_break_duration += parse_duration(break_session["duration"])

            actual_work_time = max(timedelta(0), current_work_duration - total_break_duration)
            
            if not hasattr(self, 'daily_work_history'):
                self.daily_work_history = {}
                
            if user_id_str not in self.daily_work_history:
                self.daily_work_history[user_id_str] = {
                    "work_sessions": [],
                    "total_work_duration": "00:00:00",
                    "actual_total_work_time": "00:00:00",
                    "break_history": {}
                }
                
            session = {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration": format_timedelta(current_work_duration),
                "actual_work_time": format_timedelta(actual_work_time),
                "break_duration": format_timedelta(total_break_duration)
            }
            
            self.daily_work_history[user_id_str]["work_sessions"].append(session)
            
            # Tính tổng thời gian làm việc trong ngày
            total_duration = timedelta()
            actual_total = timedelta()
            
            for work_session in self.daily_work_history[user_id_str]["work_sessions"]:
                total_duration += parse_duration(work_session.get("duration", "00:00:00"))
                actual_total += parse_duration(work_session.get("actual_work_time", "00:00:00"))

            self.daily_work_history[user_id_str]["total_work_duration"] = format_timedelta(total_duration)
            self.daily_work_history[user_id_str]["actual_total_work_time"] = format_timedelta(actual_total)

            if str(user_id) in self.break_sessions:
                self.break_sessions.pop(str(user_id))
            if user_id in self.work_sessions:
                self.work_sessions.pop(user_id)

            self.save_data()
            
            return (f"🏠 {username} 已下班\n"
                    f"⏰ 上班时间: <code>{start_time.strftime('%H:%M:%S')}</code>\n"
                    f"🔚 下班时间: <code>{end_time.strftime('%H:%M:%S')}</code>\n"
                    f"⌛ 本次总时长: <code>{format_timedelta(current_work_duration)}</code>\n"
                    f"☕ 本次休息时间: <code>{format_timedelta(total_break_duration)}</code>\n"
                    f"💪 本次实际工作时间: <code>{format_timedelta(actual_work_time)}</code>\n\n"
                    f"📊 今日工作记录:\n"
                    f"📈 今日总工作时长: <code>{self.daily_work_history[user_id_str]['total_work_duration']}</code>\n"
                    f"✨ 今日实际总工作时间: <code>{self.daily_work_history[user_id_str]['actual_total_work_time']}</code>\n\n"
                    f"{self.get_daily_summary(user_id)}")   

        except Exception as e:
            print(f"Error in end_work: {str(e)}")
            print(f"Full error: {traceback.format_exc()}")
            return "❌ 操作失败，请稍后再试"

    def get_daily_summary(self, user_id):
        try:
            if user_id not in self.activity_summary:
                return "今日暂无活动记录"
            
            user_id_str = str(user_id)
            summary_lines = []
            
            # Emoji cho từng loại hoạt động
            break_emojis = {
                "吃饭": "🍚",
                "上厕所": "🚾",
                "抽烟": "🚬",
                "离开": "🚶‍♂️"
            }
            
            # Thống kê cho từng loại hoạt động
            for break_type in ['上厕所', '吃饭', '抽烟', '离开']:
                if user_id_str in self.daily_work_history and \
                   break_type in self.daily_work_history[user_id_str]["break_history"]:
                    sessions = self.daily_work_history[user_id_str]["break_history"][break_type]
                    count = len(sessions)
                    total_seconds = sum(
                        [datetime.strptime(s["duration"].split('.')[0], '%H:%M:%S').time().hour * 3600 +
                         datetime.strptime(s["duration"].split('.')[0], '%H:%M:%S').time().minute * 60 +
                         datetime.strptime(s["duration"].split('.')[0], '%H:%M:%S').time().second
                         for s in sessions],
                        start=0
                    )
                    total_time = str(timedelta(seconds=total_seconds))
                    emoji = break_emojis.get(break_type, "")
                    summary_lines.append(f"{emoji} {break_type}: <code>{count}</code> 次 <code>{total_time}</code>")
            
            # Tổng hợp tất cả các hoạt động
            total_count = sum([len(sessions) for sessions in 
                              self.daily_work_history.get(user_id_str, {}).get("break_history", {}).values()])
            
            total_break_seconds = sum(
                [datetime.strptime(s["duration"].split('.')[0], '%H:%M:%S').time().hour * 3600 +
                 datetime.strptime(s["duration"].split('.')[0], '%H:%M:%S').time().minute * 60 +
                 datetime.strptime(s["duration"].split('.')[0], '%H:%M:%S').time().second
                 for sessions in self.daily_work_history.get(user_id_str, {}).get("break_history", {}).values()
                 for s in sessions],
                start=0
            )
            total_break_time = str(timedelta(seconds=total_break_seconds))
            
            summary = "\n".join(summary_lines)
            return (f"{summary}\n"
                    f"🔢 总次数: <code>{total_count}</code> 次\n"
                    f"⌛ 总时长: <code>{total_break_time}</code>")
                
        except Exception as e:
            print(f"Error in get_daily_summary: {str(e)}")
            return "无法获取统计信息"

    def record_activity(self, user_id, username, chat_id, chat_title, activity):
        # Logic để ghi lại hoạt động
        return f"✅ 活动 '{activity}' 已记录给 {username}."

    def set_auto_send_time(self, time_str):
        """Thiết lập thời gian gửi tự động cho nhóm"""
        try:
            # Kiểm tra định dạng thời gian
            datetime.strptime(time_str, '%H:%M')
            
            # Lấy tên nhóm từ tên file
            group_name = self.data_file.split('/')[-1].split('_history_')[0]
            
            # Lưu thời gian gửi tự động
            self.auto_send_times[group_name] = time_str
            self.save_data()
            return True
        except ValueError:
            return "⚠️ 时间格式错误"

    def get_auto_send_time(self, group_name):
        """Lấy thời gian gửi tự động của nhóm"""
        return self.auto_send_times.get(group_name)

    def set_timezone(self, country):
        """Cập nhật timezone"""
        try:
            country = country.lower().replace(' ', '_')
            if country in self.timezone_map:
                new_timezone = self.timezone_map[country]
                self.timezone = new_timezone
                self.tz = pytz.timezone(new_timezone)
                
                # Cập nhật vào group_config
                success = self.group_config.set_group_timezone(
                    self.group_name,
                    self.group_name,
                    new_timezone,
                    country
                )
                
                if success:
                    print(f"DEBUG: Successfully set timezone to {new_timezone}")
                    self.save_data()
                    return True, new_timezone
                else:
                    print("DEBUG: Failed to update group_config")
                    return False, None
            else:
                print(f"DEBUG: Unsupported country: {country}")
                return False, None
                
        except Exception as e:
            print(f"Error setting timezone: {str(e)}")
            traceback.print_exc()
            return False, None

    def show_menu(self, user_id):
        # Kiểm tra quyền của người dùng
        if not self.is_user_authorized(user_id):
            return "⚠️ 您没有使用权限或授权已期，请联系管理员"
        
        # Nếu người dùng có quyền, hiển thị menu
        return "🔰 这是您的菜单选项: ..."

    def is_user_authorized(self, user_id):
        """Kiểm tra quyền của người dùng"""
        try:
            username = self.usernames.get(user_id)
            if not username:
                return False
                
            # Lấy settings của nhóm từ GroupConfig
            group_config = GroupConfig()
            settings = group_config.get_group_settings(str(self.group_name))
            
            # Nếu không tìm thấy settings bằng group_name, thử tìm bằng title
            if not settings:
                all_settings = group_config.get_all_settings()
                for chat_id, group_settings in all_settings.items():
                    if group_settings.get('title') == self.group_name:
                        settings = group_settings
                        break
            
            # Kiểm tra quyền nhóm
            if settings and settings.get('allow_all_members'):
                if 'group_expiry' in settings:
                    expiry_time = datetime.strptime(settings['group_expiry'], '%Y-%m-%d %H:%M:%S %z')
                    if datetime.now(expiry_time.tzinfo) < expiry_time:
                        return True
            
            # Kiểm tra quyền admin
            admin_cmd = AdminCommands(self.group_name)
            if admin_cmd.is_user_authorized(username, settings.get('chat_id') if settings else None):
                return True
            
            return False
            
        except Exception as e:
            print(f"Error checking authorization: {str(e)}")
            traceback.print_exc()
            return False

    def set_group_timezone(self, country):
        """Cài đặt múi giờ cho nhóm"""
        try:
            # Chuẩn hóa tên quốc gia
            country = country.lower().strip()
            country = country.replace('viet nam', 'vietnam')
            country = country.replace(' ', '_')
            
            if country in self.timezone_map:
                new_timezone = self.timezone_map[country]
                
                try:
                    # Kiểm tra timezone hợp lệ
                    test_tz = pytz.timezone(new_timezone)
                    
                    # Cập nhật vào instance
                    self.timezone = new_timezone
                    self.tz = test_tz
                    
                    # Cập nhật vào group_config
                    success = self.group_config.set_group_timezone(
                        str(self.group_name),  # Chuyển thành string
                        self.group_name,
                        new_timezone,
                        country
                    )
                    
                    if success:
                        print(f"DEBUG: Successfully set timezone to {new_timezone}")
                        self.save_data()
                        return True, new_timezone
                    else:
                        print("DEBUG: Failed to update group_config")
                        return False, None
                        
                except pytz.exceptions.UnknownTimeZoneError:
                    print(f"DEBUG: Invalid timezone: {new_timezone}")
                    return False, None
            else:
                print(f"DEBUG: Unsupported country: {country}")
                return False, None
                
        except Exception as e:
            print(f"Error setting timezone: {str(e)}")
            traceback.print_exc()
            return False, None

    def update_username(self, user_id, username):
        """Cập nhật username cho user_id"""
        if username:  # Chỉ cập nhật nếu username không phải None hoặc rỗng
            self.usernames[user_id] = username
            self.save_data()  # Lưu ngay sau khi cập nhật



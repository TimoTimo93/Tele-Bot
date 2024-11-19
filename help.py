from telegram import Update
from telegram.ext import ContextTypes
from admin_commands import AdminCommands

class HelpHandler:
    def __init__(self):
        # Lệnh cho level 2 (quản lý thu chi)
        self.level2_commands = [
            "💰 管理员功能：",
            "• 入款格式：",
            "  - <code>+100</code> 或 <code>入款100</code>",
            "  - <code>+1000.5</code> (支持小数)",
            
            "• 下发格式：",
            "  - <code>-100</code> 或 <code>下发100</code>", 
            "  - <code>xf100</code> 或 <code>xf-100</code>",
            "  - <code>下发100u</code> 或 <code>下发100usdt</code>（自动按汇率换算）",
            
            "• 查询功能：",
            "  - <code>查账</code> 或 <code>checkbook</code> (查看最近交易)",
            "  - <code>OTC</code> 或 <code>币价</code> (查看USDT价格)",
            "• 查询授权期限: <code>expiretime</code>",
        ]

        # Thông báo đầy đủ cho level 1 và operator
        self.full_help = [
            "🤖 机器人使用指南",
            "━━━━━━━━━━━━━━━",
            
            "\n📋 初始设置",
            "1. 将机器人添加到群组后，需要授权机器人",
            "• 使用 <code>授权</code> 命令授权所有群组成员使用打卡功能",
            
            "2. 设置时区",
            "• 设置中国时区: <code>按国家设置时间 china</code>",
            "• 设置越南时区: <code>set time zone vietnam</code>",
            "• 查看支持的时区: <code>/timezonelist</code> 或 <code>帮助按国家设置时间</code>",
            
            "\n⏰ 自动化功能",
            "• 每天00:00自动清除当日交易记录（按设定时区）",
            "• 自动结转前日余额",
            
            "\n💰 财务操作",
            "• 入款格式:",
            "  - <code>+100</code> 或 <code>入款100</code> (入款100)",

            
            "• 下发格式:",
            "  - <code>-100</code> 或 <code>下发100</code> (下发100)",
            "  - <code>xf100</code> 或 <code>xf-100</code>",
            "  - <code>下发-100</code> (撤回下发100)",
            "  - <code>下发100u</code> (下发100 USDT)",
            
            "\n⚠️ 撤回说明",
            "• 入款撤回: 使用负数撤回之前的入款",
            "  示例: <code>入款-100</code> 撤回之前入款的100",
            
            "• 下发撤回: 在下发金额前加负号",
            "  示例: <code>下发-100</code> 撤回之前下发的100",
            "  示例: <code>下发-100u</code> 撤回之前下发的100 USDT",
            
            "\n👥 用户管理",
            "• 添加操作员: <code>add @用户账号</code>",
            "• 添加管理员: <code>add admin @用户账号</code>",
            "• 删除操作员: <code>del @用户账号</code>",
            "• 查看操作员列表: <code>list</code>",
            "• 撤销群组授权: <code>取消授权</code> 或 <code>撤销授权</code>",

            "• 日报表:",
            "  - <code>发送日报</code> 或 <code>senddaily</code> - 立即发送今日报告",
            "  - <code>发送每日报告</code> 或 <code>senddailyreport</code> - 立即发送今日报告",
                    
            "\n📊 报表功能",
            "• 月度报告:",
            "  - <code>发送报告</code> 或 <code>sendreport</code> - 立即发送本月报告",
            "  - <code>发送月报</code> 或 <code>sendmonthlyreport</code> - 立即发送本月报告",
            "• 设置月度报告: <code>设置报告发送时间</code> 7 00:00（每月7号00:00发送）",

            "\n📊 考勤报告",
            "• 立即发送打卡报告: <code>send statistics</code>",
            "• 设置定时发送: <code>set send statistics</code> 20:00",
            
            "\n⚙️ 系统设置",    
            "• 设置手续费: <code>设置费率</code> 5（设置5%手续费）",
            "• 设置USDT汇率: <code>设置USDT汇率</code> 99.6",
            
            "\n📱 常用查询",
            "• 查看近期交易: <code>查账</code> 或 <code>checkbook</code>",
            "• 清除今日记录: <code>清理今日记录</code> 或 <code>cleartodayrecord</code>（谨慎使用）",
            "• 查询USDT价格: 发送<code> OTC</code> 或 <code>币价</code>",
            "• 查询授权期限: <code>expiretime</code>",
            
            "\n⚠️ 重要说明",
            "• 费率和USDT汇率设置后将保持不变，直到下次修改",
            "• 清理今日记录后数据无法恢复，请谨慎使用",
            "• 时区设置会影响所有自动化功能的执行时间",
            "• 如群组成员未显示菜单，请发送 <code>/start</code> 命令",
            
            "\n🔍 获取帮助",
            "• 显示此帮助: <code>help</code> 或 <code>帮助</code>",
            "• 联系管理员寻求支持"
        ]

        # Thêm thông báo cho user cơ bản
        self.basic_user_help = [
            "🤖 基础功能指南",
            "━━━━━━━━━━━━━━━",
            "• 您可以通过机器人菜单使用基本功能",
            "• 如需使用高级功能，请联系管理员获取权限",
            "\n💡 温馨提示：",
            "• 使用 /help 或 帮助 查看此指南",
            "• 如有问题请联系管理员"
        ]

        # Thêm các biến cho timezone list
        self.timezone_intro = [
            "🌍 支持的时区列表",
            "━━━━━━━━━━━━━━━",
            "\n使用格式:",
            "• 中国时区: <code>按国家设置时间 china</code>",
            "• 其他国家: <code>set time zone 国家名</code>",
            "\n支持的国家列表 (A-J):"
        ]

        self.countries_1 = [
            "• <code>afghanistan</code> - 阿富汗",
            "• <code>albania</code> - 阿尔巴尼亚",  
            "• <code>algeria</code> - 阿尔及利亚",  
            "• <code>andorra</code> - 安道尔",  
            "• <code>angola</code> - 安哥拉",  
            "• <code>antigua_and_barbuda</code> - 安提瓜和巴布达",  
            "• <code>argentina</code> - 阿根廷",  
            "• <code>armenia</code> - 亚美尼亚",  
            "• <code>australia</code> - 澳大利亚",  
            "• <code>austria</code> - 奥地利",  
            "• <code>azerbaijan</code> - 阿塞拜疆",  
            "• <code>bahamas</code> - 巴哈马",  
            "• <code>bahrain</code> - 巴林",  
            "• <code>bangladesh</code> - 孟加拉国",  
            "• <code>barbados</code> - 巴巴多斯",  
            "• <code>belarus</code> - 白俄罗斯",  
            "• <code>belgium</code> - 比利时",  
            "• <code>belize</code> - 伯利兹",  
            "• <code>benin</code> - 贝宁",  
            "• <code>bhutan</code> - 不丹",  
            "• <code>bolivia</code> - 玻利维亚",  
            "• <code>bosnia_and_herzegovina</code> - 波斯尼亚和黑塞哥维那",  
            "• <code>botswana</code> - 博茨瓦纳",  
            "• <code>brazil</code> - 巴西",  
            "• <code>brunei</code> - 文莱",  
            "• <code>bulgaria</code> - 保加利亚",  
            "• <code>burkina_faso</code> - 布基纳法索",  
            "• <code>burundi</code> - 布隆迪",  
            "• <code>cabo_verde</code> - 佛得角",  
            "• <code>cambodia</code> - 柬埔寨",  
            "• <code>cameroon</code> - 喀麦隆",  
            "• <code>canada</code> - 加拿大",  
            "• <code>central_african_republic</code> - 中非共和国",  
            "• <code>chad</code> - 乍得",  
            "• <code>chile</code> - 智利",  
            "• <code>china</code> - 中国",  
            "• <code>colombia</code> - 哥伦比亚",  
            "• <code>comoros</code> - 科摩罗",  
            "• <code>congo_kinshasa</code> - 刚果（金）",  
            "• <code>congo_brazzaville</code> - 刚果（布）",  
            "• <code>costa_rica</code> - 哥斯达黎加",  
            "• <code>croatia</code> - 克罗地亚",  
            "• <code>cuba</code> - 古巴",  
            "• <code>cyprus</code> - 塞浦路斯",  
            "• <code>czech_republic</code> - 捷克共和国",  
            "• <code>denmark</code> - 丹麦",  
            "• <code>djibouti</code> - 吉布提",  
            "• <code>dominica</code> - 多米尼克",  
            "• <code>dominican_republic</code> - 多米尼加共和国",  
            "• <code>ecuador</code> - 厄瓜多尔",  
            "• <code>egypt</code> - 埃及",  
            "• <code>el_salvador</code> - 萨尔瓦多",  
            "• <code>equatorial_guinea</code> - 赤道几内亚",  
            "• <code>eritrea</code> - 厄立特里亚",  
            "• <code>estonia</code> - 爱沙尼亚",  
            "• <code>eswatini</code> - 斯威士兰",  
            "• <code>ethiopia</code> - 埃塞俄比亚",  
            "• <code>fiji</code> - 斐济",  
            "• <code>finland</code> - 芬兰",  
            "• <code>france</code> - 法国",  
            "• <code>gabon</code> - 加蓬",  
            "• <code>gambia</code> - 冈比亚",  
            "• <code>georgia</code> - 格鲁吉亚",  
            "• <code>germany</code> - 德国",  
            "• <code>ghana</code> - 加纳",  
            "• <code>greece</code> - 希腊",  
            "• <code>grenada</code> - 格林纳达",  
            "• <code>guatemala</code> - 危地马拉",  
            "• <code>guinea</code> - 几内亚",  
            "• <code>guinea_bissau</code> - 几内亚比绍",  
            "• <code>guyana</code> - 圭亚那",  
            "• <code>haiti</code> - 海地",  
            "• <code>honduras</code> - 洪都拉斯",  
            "• <code>hungary</code> - 匈牙利",  
            "• <code>iceland</code> - 冰岛",  
            "• <code>india</code> - 印度",  
            "• <code>indonesia</code> - 印度尼西亚",  
            "• <code>iran</code> - 伊朗",  
            "• <code>iraq</code> - 伊拉克",  
            "• <code>ireland</code> - 爱尔兰",  
            "• <code>israel</code> - 以色列",  
            "• <code>italy</code> - 意大利",  
            "• <code>ivory_coast</code> - 科特迪瓦",  
            "• <code>jamaica</code> - 牙买加",  
            "• <code>japan</code> - 日本",  
            "• <code>jordan</code> - 约旦"
        ]

        self.countries_2 = [
            "• <code>kazakhstan</code> - 哈萨克斯坦",  
            "• <code>kenya</code> - 肯尼亚",  
            "• <code>kiribati</code> - 基里巴斯",  
            "• <code>kosovo</code> - 科索沃",  
            "• <code>kuwait</code> - 科威特",  
            "• <code>kyrgyzstan</code> - 吉尔吉斯斯坦",  
            "• <code>laos</code> - 老挝",  
            "• <code>latvia</code> - 拉脱维亚",  
            "• <code>lebanon</code> - 黎巴嫩",  
            "• <code>lesotho</code> - 莱索托",  
            "• <code>liberia</code> - 利比里亚",  
            "• <code>libya</code> - 利比亚",  
            "• <code>liechtenstein</code> - 列支敦士登",  
            "• <code>lithuania</code> - 立陶宛",  
            "• <code>luxembourg</code> - 卢森堡",              
            "• <code>madagascar</code> - 马达加斯加",  
            "• <code>malawi</code> - 马拉维",  
            "• <code>malaysia</code> - 马来西亚",  
            "• <code>maldives</code> - 马尔代夫",  
            "• <code>mali</code> - 马里",  
            "• <code>malta</code> - 马耳他",  
            "• <code>marshall_islands</code> - 马绍尔群岛",  
            "• <code>mauritania</code> - 毛里塔尼亚",  
            "• <code>mauritius</code> - 毛里求斯",  
            "• <code>mexico</code> - 墨西哥",  
            "• <code>micronesia</code> - 密克罗尼西亚",  
            "• <code>moldova</code> - 摩尔多瓦",  
            "• <code>monaco</code> - 摩纳哥",  
            "• <code>mongolia</code> - 蒙古",  
            "• <code>montenegro</code> - 黑山",  
            "• <code>morocco</code> - 摩洛哥",  
            "• <code>mozambique</code> - 莫桑比克",  
            "• <code>myanmar</code> - 缅甸",  
            "• <code>namibia</code> - 纳米比亚",  
            "• <code>nauru</code> - 瑙鲁",  
            "• <code>nepal</code> - 尼泊尔",  
            "• <code>netherlands</code> - 荷兰",  
            "• <code>new_zealand</code> - 新西兰",  
            "• <code>nicaragua</code> - 尼加拉瓜",  
            "• <code>niger</code> - 尼日尔",  
            "• <code>nigeria</code> - 尼日利亚",  
            "• <code>north_korea</code> - 朝鲜",  
            "• <code>north_macedonia</code> - 北马其顿",  
            "• <code>norway</code> - 挪威",  
            "• <code>oman</code> - 阿曼",  
            "• <code>pakistan</code> - 巴基斯坦",  
            "• <code>palau</code> - 帕劳",  
            "• <code>panama</code> - 巴拿马",  
            "• <code>papua_new_guinea</code> - 巴布亚新几内亚",  
            "• <code>paraguay</code> - 巴拉圭",  
            "• <code>peru</code> - 秘鲁",  
            "• <code>philippines</code> - 菲律宾",  
            "• <code>poland</code> - 波兰",  
            "• <code>portugal</code> - 葡萄牙",  
            "• <code>qatar</code> - 卡塔尔",  
            "• <code>romania</code> - 罗马尼亚",  
            "• <code>russia</code> - 俄罗斯",  
            "• <code>rwanda</code> - 卢旺达"
        ]

        self.countries_3 = [
            "• <code>saint_kitts_and_nevis</code> - 圣基茨和尼维斯",  
            "• <code>saint_lucia</code> - 圣卢西亚",  
            "• <code>saint_vincent_and_the_grenadines</code> - 圣文森特和格林纳丁斯",  
            "• <code>samoa</code> - 萨摩亚",  
            "• <code>san_marino</code> - 圣马力诺",  
            "• <code>saudi_arabia</code> - 沙特阿拉伯",  
            "• <code>senegal</code> - 塞内加尔",  
            "• <code>serbia</code> - 塞尔维亚",  
            "• <code>seychelles</code> - 塞舌尔",  
            "• <code>sierra_leone</code> - 塞拉利昂",  
            "• <code>singapore</code> - 新加坡",  
            "• <code>slovakia</code> - 斯洛伐克",  
            "• <code>slovenia</code> - 斯洛文尼亚",  
            "• <code>solomon_islands</code> - 所罗门群岛",  
            "• <code>somalia</code> - 索马里",  
            "• <code>south_africa</code> - 南非",  
            "• <code>south_korea</code> - 韩国",  
            "• <code>south_sudan</code> - 南苏丹",  
            "• <code>spain</code> - 西班牙",  
            "• <code>sri_lanka</code> - 斯里兰卡",  
            "• <code>sudan</code> - 苏丹",  
            "• <code>suriname</code> - 苏里南",  
            "• <code>sweden</code> - 瑞典",  
            "• <code>switzerland</code> - 瑞士",  
            "• <code>syria</code> - 叙利亚",  
            "• <code>taiwan</code> - 台湾",  
            "• <code>tajikistan</code> - 塔吉克斯坦",  
            "• <code>tanzania</code> - 坦桑尼亚",  
            "• <code>thailand</code> - 泰国",  
            "• <code>togo</code> - 多哥",  
            "• <code>tonga</code> - 汤加",  
            "• <code>trinidad_and_tobago</code> - 特立尼达和多巴哥",  
            "• <code>tunisia</code> - 突尼斯",  
            "• <code>turkey</code> - 土耳其",  
            "• <code>turkmenistan</code> - 土库曼斯坦",  
            "• <code>tuvalu</code> - 图瓦卢",  
            "• <code>uganda</code> - 乌干达",  
            "• <code>ukraine</code> - 乌克兰",  
            "• <code>united_arab_emirates</code> - 阿联酋",  
            "• <code>united_kingdom</code> - 英国",  
            "• <code>united_states</code> - 美国",  
            "• <code>uruguay</code> - 乌拉圭",  
            "• <code>uzbekistan</code> - 乌兹别克斯坦",  
            "• <code>vanuatu</code> - 瓦努阿图",  
            "• <code>vatican</code> - 梵蒂冈",  
            "• <code>venezuela</code> - 委内瑞拉",  
            "• <code>vietnam</code> - 越南",  
            "• <code>yemen</code> - 也门",  
            "• <code>zambia</code> - 赞比亚",
            "• <code>zimbabwe</code> - 津巴布韦"
        ]

        self.timezone_outro = [
            "\n💡 提示:",
            "• 复制国家代码后直接使用即可",
            "• 时区设置会影响所有自动化功能"
        ]

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh help"""
        try:
            chat = update.effective_chat
            user = update.effective_user
            
            admin_cmd = AdminCommands(chat.title)
            is_level1 = admin_cmd.is_level1(user.username)
            is_level2 = admin_cmd.is_level2(user.username, chat.id)
            is_operator = admin_cmd.is_operator(user.username)

            # Kiểm tra level2 trước khi kiểm tra is_user_authorized
            if is_operator or is_level1:
                await update.message.reply_text(
                    "\n".join(self.full_help),
                    parse_mode='HTML'
                )
                
            elif is_level2:  # Đưa điều kiện is_level2 lên trước
                await update.message.reply_text(
                    "\n".join(self.level2_commands),
                    parse_mode='HTML'
                )
                
            elif admin_cmd.is_user_authorized(user.username, chat.id):
                await update.message.reply_text(
                    "\n".join(self.basic_user_help),
                    parse_mode='HTML'
                )
                
            else:
                await update.message.reply_text(
                    "⚠️ 您没有使用权限或授权已过期\n请联系管理员获取支持"
                )

        except Exception as e:
            print(f"Lỗi trong handle_help: {str(e)}")
            await update.message.reply_text("❌ 获取帮助信息失败，请稍后重试")

    async def handle_timezone_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh timezonelist hoặc 帮助按国家设置时间"""
        try:
            # Gửi phần đầu và danh sách A-J
            await update.message.reply_text(
                "\n".join(self.timezone_intro + self.countries_1),
                parse_mode='HTML'
            )
            
            # Gửi danh sách K-R
            await update.message.reply_text(
                "\n支持的国家列表 (K-R):\n" + "\n".join(self.countries_2),
                parse_mode='HTML'
            )
            
            # Gửi danh sách S-Z và phần kết
            await update.message.reply_text(
                "\n支持的国家列表 (S-Z):\n" + "\n".join(self.countries_3 + self.timezone_outro),
                parse_mode='HTML'
            )

        except Exception as e:
            print(f"Error in handle_timezone_list: {str(e)}")
            await update.message.reply_text("❌ 获取时区列表失败，请稍后重试 🔄")
from configs.config import Config
import nonebot

nonebot.load_plugins("plugins/alapi")

Config.add_plugin_config(
    "alapi",
    "ALAPI_TOKEN",
    None,
    help_="在https://admin.alapi.cn/user/login登录后获取token"
)

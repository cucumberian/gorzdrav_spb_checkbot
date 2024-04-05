import os


class Config:
    bot_token = os.environ.get("BOT_TOKEN")
    db_file = "sqlite.db"
    checker_timeout_secs = 120
    gorzdrav_api = "https://gorzdrav.spb.ru/_api/api"
    gorzdrav_api_v = "v2"
    api_url = f"{gorzdrav_api}/{gorzdrav_api_v}"
    headers = {"User-Agent": "gorzdrav-spb-bot"}

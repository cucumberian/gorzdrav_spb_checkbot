import os


class Config:
    bot_token = os.environ["BOT_TOKEN"]
    db_file = os.environ["DB_FILE"]
    checker_timeout_secs = int(os.environ.get("CHECKER_TIMEOUT_SECS", 120))
    gorzdrav_api = "https://gorzdrav.spb.ru/_api/api"
    gorzdrav_api_v = "v2"
    api_url = f"{gorzdrav_api}/{gorzdrav_api_v}"
    headers = {"User-Agent": "gorzdrav-spb-bot"}
    dsn_string = f"sqlite:///{db_file}"


print(f"{Config.bot_token = }")
print(f"{Config.db_file = }")

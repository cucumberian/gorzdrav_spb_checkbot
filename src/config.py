import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.environ["BOT_TOKEN"]
    DB_FILE = os.environ["DB_FILE"]
    CHECKER_TIMEOUT_SECS = int(os.environ.get("CHECKER_TIMEOUT_SECS", 120))
    GORZDRAV_API = "https://gorzdrav.spb.ru/_api/api"
    GORZDRAV_API_V = "v2"
    API_URL = f"{GORZDRAV_API}/{GORZDRAV_API_V}"
    HEADERS = {"User-Agent": "gorzdrav-spb-bot"}
    DSN_STRING = f"sqlite:///{DB_FILE}"

    LIMIT_DAYS_REGEX = r"^/\d{1,2}$"


class LoggerConfig:
    LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

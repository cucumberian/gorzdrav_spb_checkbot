import os
class Config:
    bot_token = os.environ.get('BOT_TOKEN')
    db_file = 'sqlite.db'
    checker_timeout_secs = 120

import time
from sqlalchemy import text
from gorzdrav.api import Gorzdrav
from db.database import sync_engine
from queries.orm import SyncOrm
from queries.core import SyncCore

with sync_engine.connect() as conn:
    query = text("SELECT sqlite_version()")
    result = conn.execute(query).scalars().all()
    print(result)


# SyncOrm.create_tables()
# SyncCore.create_tables()
SyncOrm.add_user(user_id=1)
SyncOrm.update_user(user_id=1, ping_status=True)
SyncOrm.delete_user(user_id=1)
user = SyncOrm.get_user(user_id=1)
print(f"{user = }")
users = SyncOrm.get_users(ping_status=False)
print(f"{users = }")

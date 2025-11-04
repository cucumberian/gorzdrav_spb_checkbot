from db.database import sync_engine
from db.models import metadata_obj


class SyncCore:
    @staticmethod
    def create_tables():
        metadata_obj.drop_all(bind=sync_engine)
        metadata_obj.create_all(bind=sync_engine)

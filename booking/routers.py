import sys

# считаем, что мы в тестах, если в sys.argv есть pytest
TESTING = any('pytest' in arg for arg in sys.argv)


class ReadReplicaRouter:
    def db_for_read(self, model, **hints):
        # в тестах — всё на default
        if any('pytest' in arg for arg in sys.argv):
            return 'default'
        # Room читаем из мастера
        if model._meta.model_name == 'room':
            return 'default'
        # Booking — из реплики
        if model._meta.model_name == 'booking':
            return 'replica'
        return 'default'

    def db_for_write(self, model, **hints):
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # миграции только на мастере
        return db == 'default'

class MultiDBRouter:
    """
    Роутер для работы с несколькими базами данных в Supabase:
    - default → service_request (заявки)
    - users_db → register_users (клиенты)
    - access_db → access_keys (ключи сотрудников)
    """
    
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'requests_app':
            if model.__name__ == 'RegisterUser':
                return 'users_db'
            elif model.__name__ == 'AccessKey':
                return 'access_db'
        return 'default'
    
    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'requests_app':
            if model.__name__ == 'RegisterUser':
                return 'users_db'
            elif model.__name__ == 'AccessKey':
                return 'access_db'
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label != 'requests_app':
            return None
        if model_name == 'registeruser':
            return db == 'users_db'
        elif model_name == 'accesskey':
            return db == 'access_db'
        else:
            return db == 'default'
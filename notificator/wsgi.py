import os
import sys

path = 'VladislavDev'  # замени на свой логин
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'notificator.settings'

from dotenv import load_dotenv
dotenv_path = os.path.join(path, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

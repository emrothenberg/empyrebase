from empyrebase import empyrebase
from tests import config


def make_db(service_account=False):
    if service_account:
        c = config.SERVICE_CONFIG
    else:
        c = config.SIMPLE_CONFIG

    return empyrebase.initialize_app(c).database()

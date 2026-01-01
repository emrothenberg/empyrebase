import requests
from requests.adapters import HTTPAdapter
from packaging.version import parse as parse_version

from google.oauth2 import service_account

from .services import Auth, Database, Firestore, Storage

PACKAGE_NAME = "empyrebase"
CURRENT_VERSION = "2.4.1"

def warn_if_outdated():
    try:
        res = requests.get(f"https://pypi.org/pypi/{PACKAGE_NAME}/json", timeout=3)
        res.raise_for_status()
        latest_version = res.json()["info"]["version"]

        if parse_version(CURRENT_VERSION) < parse_version(latest_version):
            from logging import getLogger
            logger = getLogger(__name__)
            logger.warning(f"You are using {PACKAGE_NAME} version {CURRENT_VERSION}, "
                            f"but {latest_version} is already published on PyPI.")
    except Exception as e:
        from logging import getLogger
        logger = getLogger(__name__)
        logger.warning(f"Could not check PyPI for version: {e}")
        
def initialize_app(config, skip_version_check=False):
    if not skip_version_check:
        warn_if_outdated()
    return Firebase(config)


class Firebase:
    """ Firebase Interface """
    def __init__(self, config):
        self.api_key = config["apiKey"]
        self.auth_domain = config["authDomain"]
        self.database_url = config["databaseURL"]
        self.storage_bucket = config["storageBucket"]
        self.project_id = config["projectId"]
        self.credentials = None
        self.requests = requests.Session()
        if config.get("serviceAccount"):
            scopes = [
                'https://www.googleapis.com/auth/firebase.database',
                'https://www.googleapis.com/auth/userinfo.email',
                "https://www.googleapis.com/auth/cloud-platform",
                "https://firebasestorage.googleapis.com/",
            ]
            service_account_type = type(config["serviceAccount"])
            if service_account_type is str:
                self.credentials = service_account.Credentials.from_service_account_file(config["serviceAccount"], scopes=scopes)
            if service_account_type is dict:
                self.credentials = service_account.Credentials.from_service_account_info(config["serviceAccount"], scopes=scopes)
        
        adapter = HTTPAdapter()

        for scheme in ('http://', 'https://'):
            self.requests.mount(scheme, adapter)

    def auth(self):
        return Auth(self.api_key, self.requests, self.credentials)

    def database(self):
        return Database(self.credentials, self.api_key, self.database_url, self.requests)
    
    def firestore(self, database_name="(default)", auth_id: str | None=None):
        return Firestore(self.requests, self.project_id, database_name, auth_id)

    def storage(self):
        return Storage(self.credentials, self.storage_bucket, self.requests)

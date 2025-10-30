from datetime import datetime, timezone
from requests import Session
from typing import List, Literal
from empyrebase.types.firestore import Document, Filter, OrderBy, StructuredQuery
from empyrebase.types.geopoint import GeoPoint
from empyrebase.types.private import Private
from empyrebase.utils import raise_detailed_error, replace_all
from logging import getLogger
import base64


class Firestore:
    """Firebase Firestore"""

    SERVER_TIMESTAMP = type("SERVER_TIMESTAMP", (), {})()
    project_id: str
    database_name: str
    headers: dict
    requests: Session
    firebase_path: Private[str]
    base_path: Private[str]
    __query: Private[StructuredQuery]
    __collections: Private[List[str]]
    __documents: Private[List[str]]

    def __init__(
        self,
        requests,
        project_id: str,
        database_name: str = "(default)",
        auth_id: str | None = None,
        _collections: List[str] = [],
        _documents: List[str] = [],
        _query: StructuredQuery | None = None
    ):
        firebase_path = ""

        self.project_id = project_id
        self.database_name = database_name
        self.headers = {}
        self.requests = requests
        self.__collections = Private(_collections.copy())
        self.__documents = Private(_documents.copy())
        self.__project_path = Private(
            f"projects/{project_id}/databases/{database_name}/documents")

        while len(_collections) > 0 or len(_documents) > 0:
            if len(_collections) > 0:
                firebase_path += f"/{_collections.pop(0)}"
            if len(_documents) > 0:
                firebase_path += f"/{_documents.pop(0)}"

        self.firebase_path = Private(firebase_path.strip("/"))
        self.base_path = Private(
            f"firestore.googleapis.com/v1/{self.__project_path.get()}")

        if not _query:
            _query = StructuredQuery(
                collection="",
            )

        _query.collection = replace_all(
            f"{self.__project_path.get()}/{firebase_path}", "//", "/")
        self.__query = Private(_query)

        if auth_id:
            self.headers["Authorization"] = f"Bearer {auth_id}"

    def authorize(self, auth_id: str):
        self.headers["Authorization"] = f"Bearer {auth_id}"

    def collection(self, collection: str, *path_segments: str):
        """Returns a collection reference

        Args:
            collection (str): Collection path relative to the base path passed on initialization
        """

        collections = self.__collections.get()
        documents = self.__documents.get()

        collection = "/".join([collection.strip("/"), *[segment.strip("/") for segment in path_segments]])
        path_parts = collection.split("/")

        segments_1 = path_parts[::2]
        try:
            segments_2 = path_parts[1::2]
        except IndexError:
            segments_2 = []

        if len(collections) == len(documents):
            collections.extend(segments_1)
            documents.extend(segments_2)
        else:
            collections.extend(segments_2)
            documents.extend(segments_1)

        if len(collections) == len(documents):
            raise ValueError(
                "Collection must be an odd child. Did you mean to get a document ref?")

        query = self.__query.get()
        query.collection = collections[-1]

        collection_ref = Firestore(
            self.requests,
            self.project_id,
            self.database_name,
            self.headers.get("Authorization", "").replace("Bearer ", ""),
            _collections=collections,
            _documents=documents,
            _query=query,
        )

        return collection_ref

    def document(self, document: str, *path_segments: str):
        """Returns a document reference

        Args:
            document (str): Document path relative to the base path passed on initialization
        """

        collections = self.__collections.get()
        documents = self.__documents.get()

        document = "/".join([document.strip("/"), *[segment.strip("/") for segment in path_segments]])
        path_parts = document.split("/")
        segments_1 = path_parts[::2]
        try:
            segments_2 = path_parts[1::2]
        except IndexError:
            segments_2 = []

        if len(collections) == len(documents):
            collections.extend(segments_1)
            documents.extend(segments_2)
        else:
            collections.extend(segments_2)
            documents.extend(segments_1)

        if len(collections) > len(documents):
            raise ValueError(
                "Document must be an even child. Did you mean to get a collection ref?")

        return Firestore(
            self.requests,
            self.project_id,
            self.database_name,
            self.headers.get("Authorization", "").replace("Bearer ", ""),
            _collections=collections,
            _documents=documents,
            _query=self.__query.get(),
        )

    def create_document(self, document="", data={}):
        """
        Creates a new document in the Firestore database.

        Args:
            document (str): Document path relative to the base path passed on initialization
            data (dict): Data to be stored in the document
        """

        return self.update_document(document, data, _new=True)

    def get_document(self, document: str = "", _during_update: bool = False):
        """Fetches the document from firestore database

        Args:
            document (str): document path relative to the base path passed on initialization
        """

        documents = self.__documents.get()
        collections = self.__collections.get()

        if not document and not documents:
            raise ValueError("Document path is required")
        
        if document:
            path_segments = document.strip("/").split("/")
            if len(collections) == len(documents):
                collections.extend(path_segments[0::2])
                if len(path_segments) > 1:
                    documents.extend(path_segments[1::2])
            else:
                documents.extend(path_segments[0::2])
                if len(path_segments) > 1:
                    collections.extend(path_segments[1::2])

        if len(collections) != len(documents):
            raise ValueError("Document ref must be an even child.")

        request_url = self.base_path.get() + f"/{self.firebase_path.get()}"
        if document:
            request_url += f"/{document}"

        request_url = replace_all(request_url, '//', '/')
        request_url = "https://" + request_url

        response = self.requests.get(request_url, headers=self.headers)

        if response.status_code == 200:
            data = response.json().get('fields', {})
            cleaned = self._doc_to_dict(data)
            return Document(cleaned, True)
        elif response.status_code == 404:
            return Document({}, False)
        else:
            if _during_update:
                return Document({}, False)
            raise_detailed_error(response)

    def batch_get_documents(self, documents: list):
        """Fetches multiple documents in a batch

        Args:
            documents (list): List of document paths relative to the base path passed on initialization
        """
        request_url = f"{self.base_path.get()}/{self.firebase_path.get()}:batchGet"
        request_url = replace_all(request_url, '//', '/')
        request_url = "https://" + request_url

        response = self.requests.post(request_url, headers=self.headers, json={
            "documents": [
                f"projects/{self.project_id}/databases/{self.database_name}/documents/{document.lstrip('/')}"
                for document in documents
            ]
        })
        if response.status_code == 200:
            results = response.json()
            return [self._doc_to_dict(result['found']['fields']) for result in results if 'found' in result]
        else:
            raise_detailed_error(response)

    # Query methods
    def run_query(self):
        """Runs a structured query against the collection

        Args:
            collection (str): Collection path relative to the base path passed on initialization
            structured_query (dict): Firestore structured query object
        """

        collection = self.firebase_path.get()
        if len(collection.strip("/").split("/")) % 2 == 0:
            raise ValueError(
                "Cannoot run query on a document. Use collection() instead.")

        request_url = f"{self.base_path.get()}/{collection}/:runQuery"
        request_url = replace_all(request_url, '//', '/')
        request_url = "https://" + request_url

        query = self.__query.get().to_dict()
        response = self.requests.post(
            request_url, headers=self.headers, json=query)

        if response.status_code == 200:
            results = response.json()
            return [Document(self._doc_to_dict(result['document']['fields']), True) for result in results if 'document' in result]
        else:
            raise_detailed_error(response)

    def where(self, field: str, op: str, value, new_filter: bool = False):
        """Creates a structured query filter

        Args:
            field (str): Field to filter on
            op (str): Operator to use for filtering
            value: Value to compare against
        """

        query = self.__query.get()
        if new_filter:
            query.filters = []

        composite_filter = Filter(field, op, self.__convert_to_fb(value))
        query.filters.append(composite_filter)

        return Firestore(
            self.requests,
            self.project_id,
            self.database_name,
            self.headers.get("Authorization", "").replace("Bearer ", ""),
            _collections=self.__collections.get(),
            _documents=self.__documents.get(),
            _query=query
        )

    def order_by(self, field: str, direction: Literal["ASCENDING", "DESCENDING"] = "ASCENDING", new_order: bool = False):
        """Creates a structured query order by clause

        Args:
            field (str): Field to order by
            direction (Literal["ASCENDING", "DESCENDING"]): Direction to order by
            new_order (bool): Whether to overwrite existing order by clauses
        """

        query = self.__query.get()

        if new_order:
            query.order_by = []

        order = OrderBy(field, direction)
        query.order_by.append(order)

        return Firestore(
            self.requests,
            self.project_id,
            self.database_name,
            self.headers.get("Authorization", "").replace("Bearer ", ""),
            _collections=self.__collections.get(),
            _documents=self.__documents.get(),
            _query=query
        )

    def limit(self, limit: int):
        """Creates a structured query limit clause

        Args:
            limit (int): Number of documents to return. Default is 100.
        """

        query = self.__query.get()
        query.limit = limit

        return Firestore(
            self.requests,
            self.project_id,
            self.database_name,
            self.headers.get("Authorization", "").replace("Bearer ", ""),
            _collections=self.__collections.get(),
            _documents=self.__documents.get(),
            _query=query
        )

    def update_document(self, document="", data={}, _new=False):
        logger = getLogger(__name__)
        if not _new:
            existing_data = self.get_document(document, True)
            if existing_data:
                data = {**existing_data.to_dict(), **data}
            else:
                logger.warning("Document does not exist. Creating new document.")

        firestore_data = self._dict_to_doc(data)

        firestore_data = {k: v for k,
                          v in firestore_data.items() if v is not None}

        request_url = f"{self.base_path.get()}/{self.firebase_path.get()}/{document}"
        request_url = replace_all(request_url, '//', '/')
        request_url = "https://" + request_url

        response = self.requests.patch(
            request_url, headers=self.headers, json={"fields": firestore_data})

        if response.status_code != 200:
            raise_detailed_error(response)

    def delete_document(self, document):
        """Deletes the document from the Firestore database

        Args:
            document (str): Document path relative to the base path passed on initialization
        """
        request_url = f"{self.base_path.get()}/{self.firebase_path.get()}/{document}"
        request_url = replace_all(request_url, '//', '/')
        request_url = "https://" + request_url

        response = self.requests.delete(request_url, headers=self.headers)
        if response.status_code != 200:
            raise_detailed_error(response)

    def list_documents(self, collection: str = ""):
        """Lists all documents in a collection

        Args:
            collection (str): Collection path relative to the base path passed on initialization
        """

        request_url = f"{self.base_path.get()}/{self.firebase_path.get()}"
        if collection:
            request_url += f"/{collection}"

        request_url = replace_all(request_url, '//', '/')
        request_url = f"https://{request_url}"

        response = self.requests.get(request_url, headers=self.headers)
        if response.status_code == 200:
            documents = response.json().get('documents', [])
            return {doc['name']: self._doc_to_dict(doc['fields']) if doc.get('fields') else {} for doc in documents}
        else:
            raise_detailed_error(response)

    def __process_value(self, dtype, value):
        processed = None
        match dtype:
            case 'nullValue':
                processed = None
            case 'stringValue':
                processed = str(value)
            case 'integerValue':
                processed = int(value)
            case 'doubleValue':
                processed = float(value)
            case 'booleanValue':
                processed = bool(value)
            case 'mapValue':
                processed = self._doc_to_dict(value.get('fields', {}))
            case 'timestampValue':
                processed = datetime.fromisoformat(
                    value.replace("Z", "+00:00"))
            case 'bytesValue':
                processed = base64.b64decode(value)
            case 'geoPointValue':
                processed = GeoPoint(**value)
            case 'arrayValue':
                processed = [
                    self.__process_value(v_type, v_value)
                    for item in value.get('values', [])
                    for v_type, v_value in item.items()
                ]
            case _:
                logger = getLogger(__name__)
                logger.warning(
                    "WARNING: Unsupported dtype, defaulting to NoneType:", dtype)

        return processed

    def __convert_to_fb(self, value):
        return ({"stringValue": value} if isinstance(value, str)
                else {"timestampValue": datetime.now().replace(tzinfo=timezone.utc).isoformat(timespec="seconds")} if value == self.SERVER_TIMESTAMP
                else {"booleanValue": value} if isinstance(value, bool)
                else {"integerValue": value} if isinstance(value, int)
                else {"doubleValue": value} if isinstance(value, float) or isinstance(value, int)
                else {"timestampValue": value.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")} if isinstance(value, datetime)
                else {"mapValue": {"fields": self._dict_to_doc(value)}} if isinstance(value, dict)
                else {"arrayValue": {"values": [self.__convert_to_fb(v) for v in value]}} if isinstance(value, list)
                else {"bytesValue": base64.b64encode(value).decode()} if isinstance(value, bytes)
                else {"geoPointValue": value.to_dict()} if isinstance(value, GeoPoint)
                else {"nullValue": None} if value == None
                else None)

    def _dict_to_doc(self, data: dict):
        return {key: self.__convert_to_fb(value) for key, value in data.items()}

    def _doc_to_dict(self, data: dict) -> dict:
        clean = {}
        for key in data:
            dtype = list(data[key].keys())[0]
            clean[key] = self.__process_value(dtype, data[key][dtype])

        return clean

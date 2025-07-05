from typing import List, Literal


class Document(dict):
    exists: bool

    def __init__(self, data, exists=True):
        super().__init__(data)
        self.exists = exists

    def to_dict(self):
        return dict(self)


class Filter:
    def __init__(self, field, op, value):
        filter_ops = {
            "==": "EQUAL",
            "!=": "NOT_EQUAL",
            "<": "LESS_THAN",
            "<=": "LESS_THAN_OR_EQUAL",
            ">": "GREATER_THAN",
            ">=": "GREATER_THAN_OR_EQUAL",
            "array-contains": "ARRAY_CONTAINS",
            "in": "IN",
            "not-in": "NOT_IN",
            "array-contains-any": "ARRAY_CONTAINS_ANY"
        }

        if op not in filter_ops:
            raise ValueError(
                f"Invalid operator: {op}. Supported operators are: {', '.join(filter_ops.keys())}")

        self.field = field
        self.op = filter_ops[op]
        self.value = value

    def to_dict(self):
        return {
            "fieldFilter": {
                "field": {
                    "fieldPath": self.field
                },
                "op": self.op,
                "value": self.value
            }
        }


class OrderBy:
    def __init__(self, field, direction: Literal["ASCENDING", "DESCENDING"] = "ASCENDING"):
        self.field = field
        self.direction = direction

    def to_dict(self):
        return {
            "field": {
                "fieldPath": self.field
            },
            "direction": self.direction
        }


class StructuredQuery:
    collection: str
    all_descendants: bool
    filters: List[Filter]
    limit: int
    order_by: List[OrderBy]

    def __init__(self, collection: str, all_descendants: bool = False, filters: List[Filter] = [], order_by: List[OrderBy] = [], limit: int = 100):
        self.collection = collection
        self.all_descendants = all_descendants
        self.filters = filters
        self.limit = limit
        self.order_by = order_by
        
    def to_dict(self):
        return {
            "structuredQuery": {
                "from": [
                    {
                        "collectionId": self.collection.split("/")[-1],
                        "allDescendants": self.all_descendants
                    }
                ],
                "orderBy": [o.to_dict() for o in self.order_by],
                "where": {
                    "compositeFilter": {
                        "op": "AND",
                        "filters": [f.to_dict() for f in self.filters]
                    }
                },
                "limit": self.limit
            },
            "newTransaction": {}
        }

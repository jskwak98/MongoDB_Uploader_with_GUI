from typing import Any, Dict, Generic, List, Mapping, Optional, Sequence, Tuple, Union

from bson.raw_bson import RawBSONDocument
from bson.objectid import ObjectId
from pymongo.typings import _DocumentType
from pymongo.common import validate_is_document_type
from pymongo.message import _INSERT

def add_insert(self, document):
        """Add an insert document to the list of ops."""
        validate_is_document_type("document", document)
        # Generate ObjectId client side.
        if not (isinstance(document, RawBSONDocument) or "_id" in document):
            document["_id"] = str(ObjectId())
        self.ops.append((_INSERT, document))


class InsertOne(Generic[_DocumentType]):
    """Represents an insert_one operation."""

    __slots__ = ("_doc",)

    def __init__(self, document: Union[_DocumentType, RawBSONDocument]) -> None:
        """Create an InsertOne instance.
        For use with :meth:`~pymongo.collection.Collection.bulk_write`.
        :Parameters:
          - `document`: The document to insert. If the document is missing an
            _id field one will be added.
        """
        self._doc = document

    def _add_to_bulk(self, bulkobj):
        """Add this operation to the _Bulk instance `bulkobj`."""
        bulkobj.add_insert(self._doc)

    def __repr__(self):
        return "InsertOne(%r)" % (self._doc,)

    def __eq__(self, other: Any) -> bool:
        if type(other) == type(self):
            return other._doc == self._doc
        return NotImplemented

    def __ne__(self, other: Any) -> bool:
        return not self == other


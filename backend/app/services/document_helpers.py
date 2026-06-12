from app.models.document import Document
from app.services.order_number import next_order_number
from app.enums import DocumentType

PREFIX_MAP = {
    DocumentType.purchase: "PO",
    DocumentType.retail: "RO",
    DocumentType.distribution: "DO",
    DocumentType.return_order: "RT",
    DocumentType.wastage: "WO",
    DocumentType.subscription: "SO",
    DocumentType.store_sales: "SS",
    DocumentType.inventory_check: "IC",
}


def create_document(db, doc_type: DocumentType) -> Document:
    prefix = PREFIX_MAP[doc_type]
    doc = Document(doc_type=doc_type, order_number="TEMP")
    db.add(doc)
    db.flush()
    doc.order_number = next_order_number(db, Document, prefix, doc_type)
    db.flush()
    return doc

import json
import uuid

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from exceptions.common import DocumentNotFoundError
from libs.helper import get_doc_type_by_extension
from models.account import Account
from models.common import UploadFile
from models.document import Document
from models.engine import get_db


class DocumentService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def create_document(self, upload_file: UploadFile, current_user: Account):
        # 2. 创建文档记录
        stmt = select(func.max(Document.position)).where(
            Document.tenant_id == current_user.current_tenant_id
        )
        max_pos = await self.db.scalar(stmt)
        position = (max_pos or 0) + 1

        doc_type = get_doc_type_by_extension(upload_file.extension)

        document = Document(
            tenant_id=current_user.current_tenant_id,
            data_source_type="upload_file",
            data_source_info=json.dumps({"upload_file_id": upload_file.id}),
            name=upload_file.name,
            doc_type=doc_type,
            created_by=current_user.id,
            created_from="console",
            position=position,
            batch=str(uuid.uuid4()),
            file_id=upload_file.id,
            word_count=0,
            indexing_status="waiting",
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def list_documents(
        self,
        current_user: Account,
        page: int = 1,
        page_size: int = 15,
    ):
        stmt = (
            select(Document)
            .where(Document.created_by == current_user.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        documents = (await self.db.execute(stmt)).scalars().all()
        total = await self.db.scalar(select(func.count()).select_from(Document))
        return documents, total

    async def get_document(self, document_id: str, current_user: Account):
        document = await self.db.get(Document, document_id)
        if not document:
            raise DocumentNotFoundError()
        return document

    async def delete_document(self, document_id: str, current_user: Account):
        document = await self.get_document(document_id, current_user)
        if not document:
            raise DocumentNotFoundError()
        await self.db.delete(document)
        await self.db.commit()

import logging
from celery import shared_task
from models.engine import TaskSessionLocal, run_async
from core.rag.extractor.extract_processor import ExtractProcessor
from models.common import UploadFile
from models.document import Document

logger = logging.getLogger(__name__)


@shared_task
def document_extract(document_id: str):
    """异步文档提取任务"""
    run_async(_document_extract(document_id))


async def _document_extract(document_id: str):
    async with TaskSessionLocal() as session:
        document = await session.get(Document, document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        document.indexing_status = "indexing"
        await session.commit()
        upload_file = await session.get(UploadFile, document.file_id)
        if not upload_file:
            raise ValueError(f"UploadFile {document_id} not found")
        try:
            result = await ExtractProcessor.load_from_upload_file(session, upload_file)
            logger.info(f"Document {document_id} extract successfully,result: {result}")
            document.indexing_status = "completed"
        except Exception as e:
            logger.error(f"Document {document_id} extract failed,error: {e}")
            document.indexing_status = "error"
            document.error = str(e)

        await session.commit()

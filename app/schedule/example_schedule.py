from datetime import datetime, timedelta
from pathlib import Path
from celery import shared_task
import logging


logger = logging.getLogger(__name__)


@shared_task
def cleanup_temp_files():
    logger.info("开始清理临时文件...")

    try:
        temp_dir = Path("/tmp/app_temp")
        if not temp_dir.exists():
            logger.info("临时目录不存在，跳过清理")
            return {"status": "skipped", "reason": "目录不存在"}

        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=24)
        deleted_count = 0

        for file_path in temp_dir.iterdir():
            if file_path.is_file():
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"删除过期文件: {file_path}")
                    except Exception as e:
                        logger.error(f"删除文件失败 {file_path}: {e}")

        result = {
            "status": "success",
            "deleted_count": deleted_count,
            "executed_at": current_time.isoformat(),
        }
        logger.info(f"临时文件清理完成，共删除 {deleted_count} 个文件")
        return result

    except Exception as e:
        logger.error(f"清理临时文件时发生错误: {e}", exc_info=True)
        raise

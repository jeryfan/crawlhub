from sqlalchemy import select
from configs import app_config
from models.common import FastAPISetup
from services.base_service import BaseService


class SetupService(BaseService):
    async def get_setup_status(self):
        if app_config.EDITION == "SELF_HOSTED":
            return True
        setup_status = await self.db.scalar(select(FastAPISetup))
        return setup_status

import ssl
from datetime import timedelta
from typing import Any

import pytz
from celery import Celery, Task
from celery.schedules import crontab

from configs import app_config
from fastapi import FastAPI


def _get_celery_ssl_options() -> dict[str, Any] | None:
    """Get SSL configuration for Celery broker/backend connections."""
    # Use REDIS_USE_SSL for consistency with the main Redis client
    # Only apply SSL if we're using Redis as broker/backend
    if not app_config.REDIS_USE_SSL:
        return None

    # Check if Celery is actually using Redis
    broker_is_redis = app_config.CELERY_BROKER_URL and (
        app_config.CELERY_BROKER_URL.startswith("redis://")
        or app_config.CELERY_BROKER_URL.startswith("rediss://")
    )

    if not broker_is_redis:
        return None

    # Map certificate requirement strings to SSL constants
    cert_reqs_map = {
        "CERT_NONE": ssl.CERT_NONE,
        "CERT_OPTIONAL": ssl.CERT_OPTIONAL,
        "CERT_REQUIRED": ssl.CERT_REQUIRED,
    }

    ssl_cert_reqs = cert_reqs_map.get(app_config.REDIS_SSL_CERT_REQS, ssl.CERT_NONE)

    ssl_options = {
        "ssl_cert_reqs": ssl_cert_reqs,
        "ssl_ca_certs": app_config.REDIS_SSL_CA_CERTS,
        "ssl_certfile": app_config.REDIS_SSL_CERTFILE,
        "ssl_keyfile": app_config.REDIS_SSL_KEYFILE,
    }

    return ssl_options


def init_app(app: FastAPI) -> Celery:
    broker_transport_options = {}

    if app_config.CELERY_USE_SENTINEL:
        broker_transport_options = {
            "master_name": app_config.CELERY_SENTINEL_MASTER_NAME,
            "sentinel_kwargs": {
                "socket_timeout": app_config.CELERY_SENTINEL_SOCKET_TIMEOUT,
                "password": app_config.CELERY_SENTINEL_PASSWORD,
            },
        }

    celery_app = Celery(
        app.title,
        broker=app_config.CELERY_BROKER_URL,
        backend=app_config.CELERY_BACKEND,
    )

    celery_app.conf.update(
        result_backend=app_config.CELERY_RESULT_BACKEND,
        broker_transport_options=broker_transport_options,
        broker_connection_retry_on_startup=True,
        worker_log_format=app_config.LOG_FORMAT,
        worker_task_log_format=app_config.LOG_FORMAT,
        worker_hijack_root_logger=False,
        timezone=pytz.timezone(app_config.LOG_TZ or "UTC"),
        task_ignore_result=True,
        beat_schedule_filename="/tmp/celerybeat-schedule",
        # 启用异步任务支持
        task_protocol=2,
    )

    # Apply SSL configuration if enabled
    ssl_options = _get_celery_ssl_options()
    if ssl_options:
        celery_app.conf.update(
            broker_use_ssl=ssl_options,
            # Also apply SSL to the backend if it's Redis
            redis_backend_use_ssl=(ssl_options if app_config.CELERY_BACKEND == "redis" else None),
        )

    if app_config.LOG_FILE:
        celery_app.conf.update(
            worker_logfile=app_config.LOG_FILE,
        )

    celery_app.set_default()
    app.state.celery = celery_app

    imports = [
        "tasks.document_task",
        "tasks.billing_tasks",
        "tasks.code_session_tasks",
    ]
    day = app_config.CELERY_BEAT_SCHEDULER_TIME

    # if you add a new task, please add the switch to CeleryScheduleTasksConfig
    beat_schedule = {
        "schedule.cleanup_temp_files": {
            "task": "schedule.example_schedule.cleanup_temp_files",
            "schedule": crontab(minute="0", hour="10", day_of_week="1"),
        },
        # 账单相关定时任务
        "billing.expire_recharge_orders": {
            "task": "tasks.billing_tasks.expire_recharge_orders",
            "schedule": crontab(minute="*/5"),  # 每5分钟检查过期订单
        },
        "billing.process_subscription_expiry": {
            "task": "tasks.billing_tasks.process_subscription_expiry",
            "schedule": crontab(minute="0"),  # 每小时检查订阅到期
        },
        "billing.process_pending_plan_changes": {
            "task": "tasks.billing_tasks.process_pending_plan_changes",
            "schedule": crontab(minute="0"),  # 每小时执行待降级处理
        },
        "billing.send_expiry_reminders": {
            "task": "tasks.billing_tasks.send_expiry_reminders",
            "schedule": crontab(minute="0", hour="9"),  # 每天9点发送到期提醒
        },
        # Code Session 清理任务
        "crawlhub.cleanup_code_sessions": {
            "task": "tasks.code_session_tasks.cleanup_expired_code_sessions",
            "schedule": crontab(minute="*/5"),  # 每5分钟清理过期会话
        },
    }

    celery_app.conf.update(beat_schedule=beat_schedule, imports=imports)

    return celery_app

"""Background task dispatcher.

When Celery is enabled tasks are sent to the broker, otherwise they run inline
(in-process). Inline execution is used for local development and tests.
"""

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("jobs")


def run_background(task_name: str, *args) -> None:
    full_name = f"app.workers.tasks.{task_name}"
    if settings.use_celery:
        from app.workers.celery_app import celery_app

        celery_app.send_task(full_name, args=args)
        logger.info("Dispatched celery task %s args=%s", full_name, args)
        return
    # Inline execution wrapped in a thread so the request is not blocked.
    from threading import Thread

    def _run():
        try:
            from app.workers import tasks

            fn = getattr(tasks, task_name, None)
            if fn is None:
                logger.error("Unknown task: %s", task_name)
                return
            fn(*args)
            logger.info("Ran task %s inline", task_name)
        except Exception:  # noqa: BLE001
            logger.exception("Inline task %s failed", task_name)

    Thread(target=_run, daemon=True).start()

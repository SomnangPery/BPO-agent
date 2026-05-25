import logging

from ic_agent.server import create_app as server_create_app
from ic_agent.utils import (
    _extract_student_name_from_filename,
    _identifier_from_name,
    _format_detailed_project_summary,
    _format_detailed_student_summary,
)

logger = logging.getLogger(__name__)

__all__ = [
    "create_app",
    "_extract_student_name_from_filename",
    "_identifier_from_name",
    "_format_detailed_project_summary",
    "_format_detailed_student_summary",
]


create_app = server_create_app


if __name__ == "__main__":
    from ic_agent.bot import run_telegram_bot

    run_telegram_bot()

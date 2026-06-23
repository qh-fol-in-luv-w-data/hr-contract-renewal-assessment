import frappe
import uuid
from cnb_2as.utils.activity_logger import ActivityLogger

_logger = ActivityLogger(prefix="CNB", module="cnb_2as")

@frappe.whitelist(allow_guest=False)
def get_context():
    dept = ""
    role = ""
    try:
        try:
            from ct_agent_hub.api.core import check_app_access
        except ImportError:
            from ct_agent_hub.api import check_app_access

        agents_data = check_app_access("2as-employee-assessment")
        user_depts = agents_data.get("user_departments", [])
        dept = ",".join(user_depts) if user_depts else ""
        role = agents_data.get("user_role", "")
    except ImportError:
        pass

    session_id   = str(uuid.uuid4())
    session_name = _logger.create_session(session_id, dept=dept, role=role)

    return {
        "csrf_token":   frappe.sessions.get_csrf_token(),
        "session_id":   session_id,
        "session_name": session_name,
    }

def _resolve_session(session_id: str) -> str:
    if not session_id:
        return ""
    try:
        rows = frappe.db.get_all(
            "CNB Session",
            filters={"session_id": session_id},
            fields=["name"],
            limit=1,
            ignore_permissions=True,
        )
        return rows[0].name if rows else ""
    except Exception:
        return ""

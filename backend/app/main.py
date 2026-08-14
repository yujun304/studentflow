from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin,
    archive,
    attendance,
    audit,
    auth,
    calendar,
    comments,
    dashboard,
    events,
    meeting_records,
    notices,
    notifications,
    operations,
    reminders,
    tasks,
    teams,
)
from app.core.config import settings
from app.core.errors import install_error_handlers
from app.core.security import csrf_protect

app = FastAPI(title="StudentFlow API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(settings.allowed_frontend_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_error_handlers(app)

api = FastAPI(dependencies=[Depends(csrf_protect)])
install_error_handlers(api)
api.include_router(auth.router)
api.include_router(calendar.router)
api.include_router(admin.router)
api.include_router(dashboard.router)
api.include_router(events.router)
api.include_router(tasks.router)
api.include_router(notices.router)
api.include_router(teams.router)
api.include_router(attendance.router)
api.include_router(meeting_records.router)
api.include_router(comments.router)
api.include_router(reminders.router)
api.include_router(notifications.router)
api.include_router(operations.router)
api.include_router(archive.router)
api.include_router(audit.router)


@api.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/api/v1", api)

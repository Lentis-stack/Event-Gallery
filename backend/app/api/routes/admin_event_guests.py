# ============================================================
# Lentis Gallery — Admin Event Guest Routes
# ------------------------------------------------------------
# Endpoints for the ADMIN to manage invited guests on events:
#   - GET    /api/admin/events/{event_id}/guests          list
#   - POST   /api/admin/events/{event_id}/guests          add
#   - POST   /api/admin/events/{event_id}/guests/{guest_id}/reset-password
#   - DELETE /api/admin/events/{event_id}/guests/{guest_id}  remove
#
# Every endpoint requires an ADMIN access token.
# ============================================================

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.event_guest import (
    InvitedGuestCreate,
    InvitedGuestListResponse,
    InvitedGuestOut,
    InvitedGuestUpdate,
)
from app.services import event_guests as event_guest_service

router = APIRouter(prefix="/api/admin/events", tags=["admin-event-guests"])


@router.get(
    "/{event_id}/guests",
    response_model=InvitedGuestListResponse,
    summary="List invited guests (admin)",
)
def admin_list_event_guests(
    event_id: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> InvitedGuestListResponse:
    return event_guest_service.list_invited_guests(db, event_id)


@router.post(
    "/{event_id}/guests",
    response_model=InvitedGuestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add invited guest (admin)",
)
def admin_add_event_guest(
    event_id: str,
    body: InvitedGuestCreate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> InvitedGuestOut:
    return event_guest_service.add_invited_guest(db, event_id, body)


@router.post(
    "/{event_id}/guests/{guest_id}/reset-password",
    response_model=InvitedGuestOut,
    summary="Reset invited guest password (admin)",
)
def admin_reset_event_guest_password(
    event_id: str,
    guest_id: str,
    body: InvitedGuestUpdate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> InvitedGuestOut:
    return event_guest_service.reset_invited_guest_password(db, event_id, guest_id, body)


@router.delete(
    "/{event_id}/guests/{guest_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove invited guest (admin)",
)
def admin_remove_event_guest(
    event_id: str,
    guest_id: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    event_guest_service.remove_invited_guest(db, event_id, guest_id)
    return None

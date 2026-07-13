from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.deps import _http, get_current_user, require_team_role
from app.core.rbac import ROLE_RANK, membership_for, teams_for_user
from app.db.models import Team, TeamMembership, User
from app.db.session import get_db
from app.schemas.v34 import TeamCreate, TeamMemberAdd, TeamMemberOut, TeamMemberUpdate, TeamOut

router = APIRouter(prefix="/teams", tags=["teams"])


def _out(t: Team) -> TeamOut:
    return TeamOut(id=str(t.id), name=t.name, owner_id=str(t.owner_id), created_at=t.created_at.isoformat() if t.created_at else None)


def _member_out(db: Session, m: TeamMembership) -> TeamMemberOut:
    u = db.get(User, m.user_id)
    return TeamMemberOut(
        user_id=str(m.user_id),
        email=u.email if u else "",
        display_name=u.display_name if u else "",
        role=m.role,
    )


@router.post("", response_model=TeamOut, status_code=201)
def create_team(body: TeamCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.name or not body.name.strip():
        raise _http(400, "BAD_NAME", "Team name is required.")
    team = Team(name=body.name.strip(), owner_id=user.id)
    db.add(team)
    db.flush()
    db.add(TeamMembership(team_id=team.id, user_id=user.id, role="owner"))
    db.commit()
    record_audit(db, "team.create", actor_id=user.id, team_id=team.id, target_type="team", target_id=team.id, meta={"name": team.name})
    return _out(team)


@router.get("", response_model=list[TeamOut])
def list_teams(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_out(t) for t in teams_for_user(db, user)]


@router.get("/{team_id}/members", response_model=list[TeamMemberOut])
def list_members(team_id: str, membership=Depends(require_team_role("viewer")), db: Session = Depends(get_db)):
    members = db.query(TeamMembership).filter(TeamMembership.team_id == membership.team_id).all()
    return [_member_out(db, m) for m in members]


@router.post("/{team_id}/members", response_model=TeamMemberOut, status_code=201)
def add_member(team_id: str, body: TeamMemberAdd, membership=Depends(require_team_role("admin")), db: Session = Depends(get_db)):
    if body.role not in ROLE_RANK:
        raise _http(400, "BAD_ROLE", "Invalid role.")
    try:
        tid = uuid.UUID(team_id)
    except ValueError:
        raise _http(400, "BAD_TEAM", "Invalid team id.")
    invitee = db.query(User).filter(User.email == body.email.lower().strip()).first()
    if not invitee:
        raise _http(404, "USER_NOT_FOUND", "No user with that email exists yet.")
    if db.query(TeamMembership).filter(TeamMembership.team_id == tid, TeamMembership.user_id == invitee.id).first():
        raise _http(409, "ALREADY_MEMBER", "User is already a member.")
    m = TeamMembership(team_id=tid, user_id=invitee.id, role=body.role)
    db.add(m)
    db.commit()
    record_audit(db, "team.member_add", actor_id=membership.user_id, team_id=tid, target_type="user", target_id=invitee.id, meta={"role": body.role})
    return _member_out(db, m)


@router.put("/{team_id}/members/{user_id}", response_model=TeamMemberOut)
def update_member(team_id: str, user_id: str, body: TeamMemberUpdate, membership=Depends(require_team_role("admin")), db: Session = Depends(get_db)):
    if body.role not in ROLE_RANK:
        raise _http(400, "BAD_ROLE", "Invalid role.")
    try:
        tid, uid = uuid.UUID(team_id), uuid.UUID(user_id)
    except ValueError:
        raise _http(400, "BAD_ID", "Invalid id.")
    m = db.query(TeamMembership).filter(TeamMembership.team_id == tid, TeamMembership.user_id == uid).first()
    if not m:
        raise _http(404, "NOT_FOUND", "Membership not found.")
    m.role = body.role
    db.commit()
    record_audit(db, "team.member_role", actor_id=membership.user_id, team_id=tid, target_type="user", target_id=uid, meta={"role": body.role})
    return _member_out(db, m)


@router.delete("/{team_id}/members/{user_id}", status_code=204)
def remove_member(team_id: str, user_id: str, membership=Depends(require_team_role("admin")), db: Session = Depends(get_db)):
    try:
        tid, uid = uuid.UUID(team_id), uuid.UUID(user_id)
    except ValueError:
        raise _http(400, "BAD_ID", "Invalid id.")
    m = db.query(TeamMembership).filter(TeamMembership.team_id == tid, TeamMembership.user_id == uid).first()
    if not m:
        raise _http(404, "NOT_FOUND", "Membership not found.")
    if m.role == "owner":
        raise _http(400, "CANNOT_REMOVE_OWNER", "Cannot remove the team owner.")
    db.delete(m)
    db.commit()
    record_audit(db, "team.member_remove", actor_id=membership.user_id, team_id=tid, target_type="user", target_id=uid)


@router.post("/{team_id}/leave", status_code=204)
def leave_team(team_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        tid = uuid.UUID(team_id)
    except ValueError:
        raise _http(400, "BAD_TEAM", "Invalid team id.")
    m = membership_for(db, user, tid)
    if not m:
        raise _http(404, "NOT_FOUND", "Not a member.")
    if m.role == "owner":
        raise _http(400, "OWNER_CANT_LEAVE", "Transfer ownership first or delete the team.")
    db.delete(m)
    db.commit()
    record_audit(db, "team.leave", actor_id=user.id, team_id=tid)


@router.delete("/{team_id}", status_code=204)
def delete_team(team_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        tid = uuid.UUID(team_id)
    except ValueError:
        raise _http(400, "BAD_TEAM", "Invalid team id.")
    team = db.get(Team, tid)
    if not team:
        raise _http(404, "NOT_FOUND", "Team not found.")
    if team.owner_id != user.id:
        raise _http(403, "FORBIDDEN", "Only the owner can delete the team.")
    db.query(TeamMembership).filter(TeamMembership.team_id == tid).delete()
    db.delete(team)
    db.commit()
    record_audit(db, "team.delete", actor_id=user.id, team_id=tid, target_type="team", target_id=team_id)

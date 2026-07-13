from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Team, TeamMembership, User

ROLE_RANK = {"viewer": 0, "member": 1, "admin": 2, "owner": 3}


def role_rank(role: str) -> int:
    return ROLE_RANK.get(role, -1)


def membership_for(db: Session, user: User, team_id) -> TeamMembership | None:
    return (
        db.query(TeamMembership)
        .filter(TeamMembership.user_id == user.id, TeamMembership.team_id == team_id)
        .first()
    )


def has_team_role(db: Session, user: User, team_id, min_role: str) -> bool:
    m = membership_for(db, user, team_id)
    if not m:
        return False
    return role_rank(m.role) >= role_rank(min_role)


def teams_for_user(db: Session, user: User):
    return (
        db.query(Team)
        .join(TeamMembership, TeamMembership.team_id == Team.id)
        .filter(TeamMembership.user_id == user.id)
        .all()
    )

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import relationship

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=False, default="")
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    teams = relationship("TeamMembership", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="owner", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Uuid, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    members = relationship("TeamMembership", back_populates="team", cascade="all, delete-orphan")


class TeamMembership(Base):
    __tablename__ = "team_memberships"

    id = Column(Uuid, primary_key=True, default=_uuid)
    team_id = Column(Uuid, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False, default="member")  # owner | admin | member | viewer

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="teams")

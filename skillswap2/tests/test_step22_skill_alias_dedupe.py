from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# API modules depend on FastAPI; skip this suite when dependency is unavailable.
pytest.importorskip("fastapi")

from app.api.search import get_mentors_for_skill
from app.api.skill import add_skill, get_my_skills
from app.database import Base
from app.models.session import Session
from app.models.skill import Skill, UserSkill
from app.models.user import User


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _create_user(db, *, name: str, email: str, role: str = "student") -> User:
    user = User(
        name=name,
        email=email,
        password_hash="hash",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_skill(db, *, title: str, category: str = "Programming") -> Skill:
    skill = Skill(title=title, description=f"{title} desc", category=category)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def test_get_my_skills_dedupes_alias_and_prefers_canonical_row(db_session):
    user = _create_user(db_session, name="Alias User", email="alias@test.edu")
    skill = _create_skill(db_session, title="Python")

    alias_link = UserSkill(
        user_id=user.id,
        skill_id=skill.id,
        skill_type="offer",
        proficiency_level="Intermediate",
        tags=["alias"],
    )
    canonical_link = UserSkill(
        user_id=user.id,
        skill_id=skill.id,
        skill_type="teach",
        proficiency_level="Advanced",
        tags=["canonical"],
    )
    db_session.add_all([alias_link, canonical_link])
    db_session.commit()
    db_session.refresh(alias_link)
    db_session.refresh(canonical_link)

    result = get_my_skills("teach", current_user=user, db=db_session)

    assert len(result) == 1
    # Canonical row should be chosen even if alias row exists.
    assert result[0]["id"] == canonical_link.id
    assert result[0]["proficiency_level"] == "Advanced"


def test_add_skill_collapses_alias_duplicates_when_updating_existing(db_session):
    user = _create_user(db_session, name="Updater", email="updater@test.edu")
    skill = _create_skill(db_session, title="FastAPI")

    # Simulate migration residue: both alias + canonical links exist.
    db_session.add_all(
        [
            UserSkill(
                user_id=user.id,
                skill_id=skill.id,
                skill_type="offer",
                proficiency_level="Beginner",
                tags=["old"],
            ),
            UserSkill(
                user_id=user.id,
                skill_id=skill.id,
                skill_type="teach",
                proficiency_level="Intermediate",
                tags=["older"],
            ),
        ]
    )
    db_session.commit()

    response = add_skill(
        title="FastAPI",
        description="Updated",
        category="Programming",
        proficiency_level="Expert",
        tags=["api", "fastapi", "api"],  # includes duplicate to verify normalization
        skill_type="teach",
        current_user=user,
        db=db_session,
    )

    rows = (
        db_session.query(UserSkill)
        .filter(UserSkill.user_id == user.id, UserSkill.skill_id == skill.id)
        .all()
    )

    assert response["action"] == "updated"
    assert len(rows) == 1
    assert rows[0].skill_type == "teach"
    assert rows[0].proficiency_level == "Expert"
    assert rows[0].tags == ["api", "fastapi"]


def test_get_mentors_for_skill_returns_unique_mentor_when_alias_rows_exist(db_session):
    mentor = _create_user(db_session, name="Mentor One", email="mentor1@test.edu")
    learner = _create_user(db_session, name="Learner One", email="learner1@test.edu")
    skill = _create_skill(db_session, title="JavaScript")

    # Same mentor, same skill, two legacy-equivalent rows.
    db_session.add_all(
        [
            UserSkill(
                user_id=mentor.id,
                skill_id=skill.id,
                skill_type="offer",
                proficiency_level="Advanced",
                tags=[],
            ),
            UserSkill(
                user_id=mentor.id,
                skill_id=skill.id,
                skill_type="teach",
                proficiency_level="Advanced",
                tags=[],
            ),
            Session(
                learner_id=learner.id,
                mentor_id=mentor.id,
                skill_id=skill.id,
                scheduled_time=datetime.now(UTC),
                status="Completed",
                notes="done",
            ),
        ]
    )
    db_session.commit()

    mentors = get_mentors_for_skill(skill.id, db=db_session)

    assert len(mentors) == 1
    assert mentors[0]["user_id"] == mentor.id
    assert mentors[0]["mentor_name"] == mentor.name
    assert mentors[0]["session_count"] == 1

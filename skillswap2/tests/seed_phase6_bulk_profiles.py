#!/usr/bin/env python3
"""
Seed bulk mentor profiles + diverse skills for Phase 6 testing.

What it does:
1) Normalizes user_skills.skill_type values:
   - offer -> teach
   - need -> learn
2) Creates a diverse skill catalog (idempotent)
3) Creates 20 mentor users (idempotent)
4) Creates missing mentor profiles + wallets
5) Links each mentor to 3 teach skills with tags (idempotent)
6) Optionally ensures a learner has learn skills for recommendation tests
7) Seeds named team test accounts with deterministic credentials

Usage:
  cd /Users/srisruthi/Downloads/SkillSwap-SE-Project/skillswap2
  python tests/seed_phase6_bulk_profiles.py

Optional env vars:
  SEED_PASSWORD="SkillSwap@123"
  NAMED_SEED_PASSWORD="SkillSwap@123"
  TEST_LEARNER_EMAIL="lokhinth@nitt.edu"
  ENFORCE_NAMED_ACCOUNT_PASSWORDS=1
"""

from __future__ import annotations

import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure project root is on sys.path so `from app import ...` works
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import models
from app.database import SessionLocal
from app.utils.security import get_password_hash


SEED_PASSWORD = os.getenv("SEED_PASSWORD", "SkillSwap@123")
NAMED_SEED_PASSWORD = os.getenv("NAMED_SEED_PASSWORD", SEED_PASSWORD)
TEST_LEARNER_EMAIL = os.getenv("TEST_LEARNER_EMAIL", "lokhinth@nitt.edu").strip().lower()
RESET_EXISTING_PASSWORDS = os.getenv("RESET_EXISTING_PASSWORDS", "0").strip() == "1"
ENFORCE_NAMED_ACCOUNT_PASSWORDS = os.getenv("ENFORCE_NAMED_ACCOUNT_PASSWORDS", "1").strip() == "1"


SKILLS: List[Tuple[str, str, str, List[str]]] = [
    ("Python Programming", "Core Python syntax, functions, OOP, and problem-solving", "Programming", ["python", "oop", "functions"]),
    ("FastAPI Backend Development", "Build REST APIs with FastAPI, validation, and auth", "Programming", ["fastapi", "backend", "api"]),
    ("Data Analysis with Python", "NumPy, Pandas, EDA, and reporting", "Data Science", ["python", "numpy", "pandas"]),
    ("SQL and Database Fundamentals", "Joins, indexes, normalization, and query tuning", "Data Science", ["sql", "postgresql", "joins"]),
    ("Web Design Basics", "HTML, CSS, responsive layouts, and accessibility basics", "Design", ["html", "css", "responsive"]),
    ("UI/UX Design with Figma", "Wireframes, prototypes, and usability workflows", "Design", ["figma", "wireframe", "prototype"]),
    ("Digital Marketing Fundamentals", "SEO, SEM, social strategy, and funnels", "Business", ["seo", "social-media", "content"]),
    ("Public Speaking and Communication", "Presentation structure and confident delivery", "Business", ["communication", "presentation"]),
    ("Guitar Basics", "Chords, rhythm, strumming, and practice plans", "General", ["guitar", "chords", "rhythm"]),
    ("Project Management with Agile", "Scrum, planning, retrospectives, and execution", "Business", ["agile", "scrum", "sprints"]),
    ("Software Engineering Principles", "Clean architecture, modularity, and maintainability", "Programming", ["architecture", "clean-code"]),
    ("Testing and Debugging in Python", "Pytest, debugging, and test design", "Programming", ["pytest", "debugging", "quality"]),
    ("Machine Learning Basics", "Regression, classification, validation, and metrics", "Data Science", ["ml", "scikit-learn", "models"]),
    ("Statistics for Data Science", "Probability, distributions, hypothesis testing", "Data Science", ["statistics", "probability", "hypothesis"]),
    ("Graphic Design Essentials", "Typography, color, composition, and branding", "Design", ["typography", "color", "branding"]),
    ("Product Management Basics", "Roadmaps, prioritization, stakeholder communication", "Business", ["product", "roadmap", "prioritization"]),
]


MENTORS: List[Dict[str, str]] = [
    {"name": "Ananya", "email": "ananya.p6@abcuniversity.edu", "qualification": "BTech CSE", "experience": "2", "age": "22"},
    {"name": "Pranav", "email": "pranav.p6@abcuniversity.edu", "qualification": "BSc IT", "experience": "3", "age": "23"},
    {"name": "Ishita", "email": "ishita.p6@abcuniversity.edu", "qualification": "MCA", "experience": "4", "age": "24"},
    {"name": "Vikram", "email": "vikram.p6@abcuniversity.edu", "qualification": "BTech IT", "experience": "3", "age": "23"},
    {"name": "Sneha", "email": "sneha.p6@abcuniversity.edu", "qualification": "MSc Data Science", "experience": "5", "age": "26"},
    {"name": "Rahul", "email": "rahul.p6@abcuniversity.edu", "qualification": "BTech ECE", "experience": "2", "age": "22"},
    {"name": "Pooja", "email": "pooja.p6@abcuniversity.edu", "qualification": "BDes", "experience": "3", "age": "23"},
    {"name": "Yash", "email": "yash.p6@abcuniversity.edu", "qualification": "MBA", "experience": "4", "age": "25"},
    {"name": "Kavya", "email": "kavya.p6@abcuniversity.edu", "qualification": "BSc Statistics", "experience": "3", "age": "23"},
    {"name": "Arvind", "email": "arvind.p6@abcuniversity.edu", "qualification": "MTech SE", "experience": "6", "age": "28"},
    {"name": "Neha", "email": "neha.p6@abcuniversity.edu", "qualification": "BTech CSE", "experience": "2", "age": "22"},
    {"name": "Harsh", "email": "harsh.p6@abcuniversity.edu", "qualification": "BSc Computer Science", "experience": "2", "age": "22"},
    {"name": "Ritika", "email": "ritika.p6@abcuniversity.edu", "qualification": "MCA", "experience": "4", "age": "24"},
    {"name": "Manoj", "email": "manoj.p6@abcuniversity.edu", "qualification": "BTech Mechanical", "experience": "3", "age": "24"},
    {"name": "Aditi", "email": "aditi.p6@abcuniversity.edu", "qualification": "MSc Design", "experience": "5", "age": "27"},
    {"name": "Kiran", "email": "kiran.p6@abcuniversity.edu", "qualification": "BCom", "experience": "4", "age": "25"},
    {"name": "Sonia", "email": "sonia.p6@abcuniversity.edu", "qualification": "BTech AI", "experience": "2", "age": "22"},
    {"name": "Dev", "email": "dev.p6@abcuniversity.edu", "qualification": "BTech CSE", "experience": "3", "age": "23"},
    {"name": "Maya", "email": "maya.p6@abcuniversity.edu", "qualification": "MSc Mathematics", "experience": "4", "age": "25"},
    {"name": "Naveen", "email": "naveen.p6@abcuniversity.edu", "qualification": "MBA", "experience": "5", "age": "27"},
]

NAMED_ACCOUNTS: List[Dict[str, Any]] = [
    {"name": "Apsara", "email": "apsara@gmail.com", "role": "student"},
    {"name": "Lokhinth", "email": "lokhinth@nitt.edu", "role": "student", "age": 20},
    {"name": "Harini", "email": "harini@abcuniversity.edu", "role": "student"},
    {"name": "Jeevika", "email": "jeevika@abcuniversity.edu", "role": "student"},
    {"name": "Kanishma", "email": "kanishma@abcuniversity.edu", "role": "student"},
    {"name": "Sona", "email": "sona@abcuniversity.edu", "role": "student"},
]

NAMED_ACCOUNT_SKILLS: Dict[str, Dict[str, List[str]]] = {
    "apsara@gmail.com": {
        "teach": ["Python Programming", "FastAPI Backend Development"],
        "learn": [],
    },
    "lokhinth@nitt.edu": {
        "teach": [],
        "learn": [
            "Python Programming",
            "FastAPI Backend Development",
            "Data Analysis with Python",
            "UI/UX Design with Figma",
        ],
    },
    "harini@abcuniversity.edu": {
        "teach": ["Web Design Basics", "UI/UX Design with Figma"],
        "learn": [],
    },
    "jeevika@abcuniversity.edu": {
        "teach": ["Digital Marketing Fundamentals", "Public Speaking and Communication"],
        "learn": [],
    },
    "kanishma@abcuniversity.edu": {
        "teach": ["Testing and Debugging in Python", "Project Management with Agile"],
        "learn": [],
    },
    "sona@abcuniversity.edu": {
        "teach": ["Graphic Design Essentials", "Public Speaking and Communication"],
        "learn": [],
    },
}


def normalize_skill_types(db) -> None:
    db.query(models.UserSkill).filter(models.UserSkill.skill_type == "offer").update(
        {models.UserSkill.skill_type: "teach"}, synchronize_session=False
    )
    db.query(models.UserSkill).filter(models.UserSkill.skill_type == "need").update(
        {models.UserSkill.skill_type: "learn"}, synchronize_session=False
    )
    db.commit()


def upsert_skills(db) -> Dict[str, int]:
    title_to_id: Dict[str, int] = {}
    for title, description, category, _ in SKILLS:
        skill = db.query(models.Skill).filter(models.Skill.title == title).first()
        if not skill:
            skill = models.Skill(title=title, description=description, category=category)
            db.add(skill)
            db.flush()
        title_to_id[title] = skill.id
    db.commit()
    return title_to_id


def ensure_user_profile_wallet(
    db,
    *,
    name: str,
    email: str,
    role: str,
    qualification: str | None = None,
    experience: str | None = None,
    age: int | None = None,
    studying: str | None = None,
    password_override: str | None = None,
    force_reset_password: bool = False,
) -> models.User:
    resolved_password = password_override or SEED_PASSWORD
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(
            name=name,
            email=email,
            password_hash=get_password_hash(resolved_password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.flush()
    elif RESET_EXISTING_PASSWORDS or force_reset_password:
        user.password_hash = get_password_hash(resolved_password)
        user.is_active = True

    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user.id).first()
    if not profile:
        profile = models.UserProfile(
            user_id=user.id,
            full_name=name,
            qualification=qualification,
            experience=experience,
            age=age,
            studying=studying,
        )
        db.add(profile)
    else:
        profile.full_name = profile.full_name or name
        profile.qualification = profile.qualification or qualification
        profile.experience = profile.experience or experience
        profile.age = profile.age or age
        profile.studying = profile.studying or studying

    wallet = db.query(models.TokenWallet).filter(models.TokenWallet.user_id == user.id).first()
    if not wallet:
        db.add(models.TokenWallet(user_id=user.id, balance=20))

    db.commit()
    return user


def ensure_user_skill(
    db,
    *,
    user_id: int,
    skill_id: int,
    skill_type: str,
    proficiency_level: str,
    tags: List[str],
) -> None:
    existing = db.query(models.UserSkill).filter(
        models.UserSkill.user_id == user_id,
        models.UserSkill.skill_id == skill_id,
        models.UserSkill.skill_type == skill_type,
    ).first()
    if existing:
        if (existing.tags or []) != tags:
            existing.tags = tags
        if not existing.proficiency_level:
            existing.proficiency_level = proficiency_level
        return

    db.add(
        models.UserSkill(
            user_id=user_id,
            skill_id=skill_id,
            skill_type=skill_type,
            proficiency_level=proficiency_level,
            tags=tags,
        )
    )


def seed_mentors(db, skill_ids: Dict[str, int]) -> None:
    rng = random.Random(42)
    titles = [s[0] for s in SKILLS]
    created_or_existing = []

    for idx, mentor in enumerate(MENTORS):
        user = ensure_user_profile_wallet(
            db,
            name=mentor["name"],
            email=mentor["email"].lower(),
            role="mentor",
            qualification=mentor["qualification"],
            experience=mentor["experience"],
            age=int(mentor["age"]),
        )
        created_or_existing.append((mentor["name"], mentor["email"]))

        # 3 diverse teach skills per mentor.
        # deterministic but varied across categories
        start = (idx * 3) % len(titles)
        picked = {titles[start], titles[(start + 5) % len(titles)], titles[(start + 10) % len(titles)]}
        if "Python Programming" not in picked and idx % 2 == 0:
            picked.add("Python Programming")
            if len(picked) > 3:
                picked.pop()

        for title in picked:
            base_tags = next(t[3] for t in SKILLS if t[0] == title)
            extra_tag = rng.choice(["mentor", "hands-on", "beginner-friendly", "project-based"])
            tags = list(dict.fromkeys(base_tags + [extra_tag]))
            ensure_user_skill(
                db,
                user_id=user.id,
                skill_id=skill_ids[title],
                skill_type="teach",
                proficiency_level=rng.choice(["intermediate", "advanced"]),
                tags=tags,
            )

    db.commit()
    print(f"Created/updated mentor profiles: {len(created_or_existing)}")
    if RESET_EXISTING_PASSWORDS:
        print("Password reset applied for seeded mentor accounts.")
    print("Seeded mentor login password:", SEED_PASSWORD)


def seed_named_accounts(db, skill_ids: Dict[str, int]) -> None:
    seeded_emails: List[str] = []
    for account in NAMED_ACCOUNTS:
        email = str(account["email"]).strip().lower()
        user = ensure_user_profile_wallet(
            db,
            name=str(account["name"]),
            email=email,
            role=str(account.get("role", "student")),
            qualification=account.get("qualification"),
            experience=account.get("experience"),
            age=account.get("age"),
            studying=account.get("studying"),
            password_override=NAMED_SEED_PASSWORD if ENFORCE_NAMED_ACCOUNT_PASSWORDS else None,
            force_reset_password=ENFORCE_NAMED_ACCOUNT_PASSWORDS,
        )
        seeded_emails.append(email)

        for title in NAMED_ACCOUNT_SKILLS.get(email, {}).get("teach", []):
            ensure_user_skill(
                db,
                user_id=user.id,
                skill_id=skill_ids[title],
                skill_type="teach",
                proficiency_level="advanced",
                tags=["named-seed", "mentor"],
            )
        for title in NAMED_ACCOUNT_SKILLS.get(email, {}).get("learn", []):
            ensure_user_skill(
                db,
                user_id=user.id,
                skill_id=skill_ids[title],
                skill_type="learn",
                proficiency_level="beginner",
                tags=["named-seed", "learner"],
            )

    db.commit()
    print(f"Created/updated named team accounts: {len(seeded_emails)}")
    if ENFORCE_NAMED_ACCOUNT_PASSWORDS:
        print("Named account passwords reset to NAMED_SEED_PASSWORD.")
        print("Named account login password:", NAMED_SEED_PASSWORD)
    else:
        print("Named account passwords not reset (ENFORCE_NAMED_ACCOUNT_PASSWORDS=0).")


def ensure_test_learner_skills(db, skill_ids: Dict[str, int]) -> None:
    learner = db.query(models.User).filter(models.User.email == TEST_LEARNER_EMAIL).first()
    if not learner:
        print(f"[NOTE] Learner '{TEST_LEARNER_EMAIL}' not found; skipped learner learn-skill seeding.")
        return

    learn_titles = [
        "Python Programming",
        "FastAPI Backend Development",
        "Data Analysis with Python",
        "UI/UX Design with Figma",
    ]
    for title in learn_titles:
        ensure_user_skill(
            db,
            user_id=learner.id,
            skill_id=skill_ids[title],
            skill_type="learn",
            proficiency_level="beginner",
            tags=["learning", "phase6"],
        )
    db.commit()
    print(f"Ensured learner learn-skills for: {TEST_LEARNER_EMAIL}")


def print_summary(db) -> None:
    mentor_count = db.query(models.User).filter(models.User.role == "mentor").count()
    teach_links = db.query(models.UserSkill).filter(models.UserSkill.skill_type == "teach").count()
    learn_links = db.query(models.UserSkill).filter(models.UserSkill.skill_type == "learn").count()
    skill_count = db.query(models.Skill).count()
    print(f"Summary -> mentors: {mentor_count}, skills: {skill_count}, teach links: {teach_links}, learn links: {learn_links}")


def main() -> None:
    db = SessionLocal()
    try:
        normalize_skill_types(db)
        skill_ids = upsert_skills(db)
        seed_mentors(db, skill_ids)
        seed_named_accounts(db, skill_ids)
        ensure_test_learner_skills(db, skill_ids)
        print_summary(db)
        print("✅ Phase 6 bulk seed completed.")
        print(f"RESET_EXISTING_PASSWORDS={int(RESET_EXISTING_PASSWORDS)}")
        print(f"ENFORCE_NAMED_ACCOUNT_PASSWORDS={int(ENFORCE_NAMED_ACCOUNT_PASSWORDS)}")
        print("Named account password source: NAMED_SEED_PASSWORD")
    finally:
        db.close()


if __name__ == "__main__":
    main()

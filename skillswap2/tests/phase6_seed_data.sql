BEGIN;

-- =========================================================
-- 1) Normalize skill_type values used across modules
-- =========================================================
UPDATE user_skills
SET skill_type = 'teach'
WHERE LOWER(skill_type) = 'offer';

UPDATE user_skills
SET skill_type = 'learn'
WHERE LOWER(skill_type) = 'need';

-- Optional cleanup for accidental mixed-case values
UPDATE user_skills
SET skill_type = LOWER(skill_type)
WHERE LOWER(skill_type) IN ('teach', 'learn')
  AND skill_type <> LOWER(skill_type);

-- =========================================================
-- 2) Ensure a diverse global skill catalog exists
-- =========================================================
INSERT INTO skills (title, description, category)
VALUES
  ('Python Programming', 'Core Python syntax, functions, OOP, and problem-solving', 'Programming'),
  ('FastAPI Backend Development', 'Build REST APIs with FastAPI, routing, validation, auth', 'Programming'),
  ('Data Analysis with Python', 'NumPy, Pandas, cleaning, EDA, and reporting', 'Data Science'),
  ('SQL and Database Fundamentals', 'Relational modeling, joins, indexing, and query optimization', 'Data Science'),
  ('Web Design Basics', 'HTML, CSS, responsive layouts, and UI foundations', 'Design'),
  ('UI/UX Design with Figma', 'Wireframing, prototypes, user flows, and usability basics', 'Design'),
  ('Digital Marketing Fundamentals', 'SEO, SEM, social media strategy, and content planning', 'Business'),
  ('Public Speaking and Communication', 'Presentation structure, confidence, and delivery skills', 'Business'),
  ('Guitar Basics', 'Chords, strumming patterns, rhythm, and practice routines', 'General'),
  ('Project Management with Agile', 'Scrum basics, sprint planning, and backlog management', 'Business'),
  ('Software Engineering Principles', 'System design basics, clean architecture, and code quality', 'Programming'),
  ('Testing and Debugging in Python', 'Pytest, unit tests, integration tests, and debugging workflows', 'Programming')
ON CONFLICT (title) DO NOTHING;

-- =========================================================
-- 3) Mentor skill assignments (teach) with tags
--    Only inserts links when mentor+skill rows are missing.
-- =========================================================
WITH mentor_skill_map(email, skill_title, proficiency_level, tags) AS (
  VALUES
    -- Existing mentors
    ('apsara@gmail.com', 'Python Programming', 'advanced', ARRAY['python','oop','problem-solving']::varchar[]),
    ('apsara@gmail.com', 'FastAPI Backend Development', 'advanced', ARRAY['fastapi','backend','api']::varchar[]),
    ('harini@abcuniversity.edu', 'Web Design Basics', 'intermediate', ARRAY['html','css','responsive']::varchar[]),
    ('harini@abcuniversity.edu', 'UI/UX Design with Figma', 'intermediate', ARRAY['figma','wireframe','prototype']::varchar[]),
    ('jeevika@abcuniversity.edu', 'Digital Marketing Fundamentals', 'intermediate', ARRAY['seo','social-media','content']::varchar[]),
    ('jeevika@abcuniversity.edu', 'Public Speaking and Communication', 'intermediate', ARRAY['communication','presentation']::varchar[]),

    -- Seeded mentors from previous phase
    ('nithya@abcuniversity.edu', 'Data Analysis with Python', 'advanced', ARRAY['python','numpy','pandas']::varchar[]),
    ('nithya@abcuniversity.edu', 'Python Programming', 'advanced', ARRAY['python','basics']::varchar[]),
    ('karthik@abcuniversity.edu', 'SQL and Database Fundamentals', 'advanced', ARRAY['sql','postgresql','joins']::varchar[]),
    ('karthik@abcuniversity.edu', 'Python Programming', 'intermediate', ARRAY['python','dsa']::varchar[]),
    ('meera@abcuniversity.edu', 'Data Analysis with Python', 'advanced', ARRAY['analysis','statistics','python']::varchar[]),
    ('meera@abcuniversity.edu', 'Public Speaking and Communication', 'intermediate', ARRAY['storytelling','communication']::varchar[]),
    ('rohit@abcuniversity.edu', 'FastAPI Backend Development', 'advanced', ARRAY['fastapi','authentication','api']::varchar[]),
    ('rohit@abcuniversity.edu', 'Software Engineering Principles', 'intermediate', ARRAY['design','architecture','quality']::varchar[]),
    ('divya@abcuniversity.edu', 'Testing and Debugging in Python', 'advanced', ARRAY['pytest','debugging','quality']::varchar[]),
    ('divya@abcuniversity.edu', 'Project Management with Agile', 'intermediate', ARRAY['scrum','agile','sprints']::varchar[]),
    ('sanjay@abcuniversity.edu', 'Software Engineering Principles', 'advanced', ARRAY['architecture','clean-code']::varchar[]),
    ('sanjay@abcuniversity.edu', 'Project Management with Agile', 'advanced', ARRAY['scrum','kanban','delivery']::varchar[])
)
INSERT INTO user_skills (user_id, skill_id, skill_type, proficiency_level, tags)
SELECT
  u.id,
  s.id,
  'teach',
  msm.proficiency_level,
  msm.tags
FROM mentor_skill_map msm
JOIN users u ON u.email = msm.email
JOIN skills s ON s.title = msm.skill_title
LEFT JOIN user_skills us
  ON us.user_id = u.id
 AND us.skill_id = s.id
 AND LOWER(us.skill_type) = 'teach'
WHERE us.id IS NULL;

-- =========================================================
-- 4) Ensure learner has "learn" skills for recommendation
--    (phase6 test account: lokhinth@nitt.edu)
-- =========================================================
WITH learner_skill_map(email, skill_title, proficiency_level, tags) AS (
  VALUES
    ('lokhinth@nitt.edu', 'Python Programming', 'beginner', ARRAY['python','oop']::varchar[]),
    ('lokhinth@nitt.edu', 'FastAPI Backend Development', 'beginner', ARRAY['api','backend']::varchar[]),
    ('lokhinth@nitt.edu', 'Data Analysis with Python', 'beginner', ARRAY['numpy','pandas']::varchar[]),
    ('lokhinth@nitt.edu', 'UI/UX Design with Figma', 'beginner', ARRAY['figma','design']::varchar[])
)
INSERT INTO user_skills (user_id, skill_id, skill_type, proficiency_level, tags)
SELECT
  u.id,
  s.id,
  'learn',
  lsm.proficiency_level,
  lsm.tags
FROM learner_skill_map lsm
JOIN users u ON u.email = lsm.email
JOIN skills s ON s.title = lsm.skill_title
LEFT JOIN user_skills us
  ON us.user_id = u.id
 AND us.skill_id = s.id
 AND LOWER(us.skill_type) = 'learn'
WHERE us.id IS NULL;

-- =========================================================
-- 5) Basic de-duplication in user_skills
--    Keep lowest id for each (user_id, skill_id, skill_type)
-- =========================================================
DELETE FROM user_skills a
USING user_skills b
WHERE a.id > b.id
  AND a.user_id = b.user_id
  AND a.skill_id = b.skill_id
  AND LOWER(a.skill_type) = LOWER(b.skill_type);

COMMIT;

-- =========================================================
-- Verification queries (run separately if needed)
-- =========================================================
-- SELECT skill_type, COUNT(*) FROM user_skills GROUP BY skill_type ORDER BY skill_type;
--
-- SELECT u.name, u.email, us.skill_type, s.title
-- FROM user_skills us
-- JOIN users u ON u.id = us.user_id
-- JOIN skills s ON s.id = us.skill_id
-- WHERE u.role = 'mentor'
-- ORDER BY u.name, us.skill_type, s.title;
--
-- SELECT u.name, u.email, us.skill_type, s.title
-- FROM user_skills us
-- JOIN users u ON u.id = us.user_id
-- JOIN skills s ON s.id = us.skill_id
-- WHERE u.email = 'lokhinth@nitt.edu'
-- ORDER BY us.skill_type, s.title;

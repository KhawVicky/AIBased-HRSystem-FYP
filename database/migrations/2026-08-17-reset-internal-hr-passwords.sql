-- One-time reset for active HR and Candidate Portal accounts after the
-- password minimum was raised to eight characters.
UPDATE users
SET password_hash = '$2y$10$QMKEHXrK2iG2l9iW4tqFvu11oPPfWj0D.pjil/I3/rK0DyLGCIsve'
WHERE status = 'active'
  AND role_id IN (1, 2);

UPDATE candidate_accounts
SET password_hash = '$2y$10$QMKEHXrK2iG2l9iW4tqFvu11oPPfWj0D.pjil/I3/rK0DyLGCIsve'
WHERE status = 'active';

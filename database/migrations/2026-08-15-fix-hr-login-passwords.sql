-- Replace the invalid prototype hash used by the original demo accounts.
-- The password for this development hash is username123@.
UPDATE users
SET password_hash = '$2y$10$jG1cXjTQxMqF0CsaKdX7nu2Ks7yLwRVuMdU16I8gJFBlDXePNmC2m'
WHERE password_hash = '$2y$10$demo.hash.for.prototype.only';

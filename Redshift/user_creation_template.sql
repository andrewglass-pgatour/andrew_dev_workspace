-- 1) Create user
CREATE USER pgat_username PASSWORD 'TempPassword123!';
-- SSO/IAM-only? Use: CREATE USER pgat_username PASSWORD DISABLE;

-- 2) Assign role
GRANT ROLE events_analyst TO pgat_username;
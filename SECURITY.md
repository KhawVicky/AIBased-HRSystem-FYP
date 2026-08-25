# Security and Handling

- Keep this repository private and use the smallest possible collaborator list.
- Never commit `.env.local`, API keys, SMTP passwords, database passwords, uploaded resumes, production database exports, or model weights.
- The repository contents are a source handoff, not a production credential bundle. A recipient must supply authorized environment values, database access, parser/model service access, and deployment settings before the system can run.
- If access must be revoked, remove the collaborator from both repositories and rotate any credentials that may have been exposed.
- A private repository and missing runtime secrets reduce unauthorized use; no software repository can technically prevent copying by a person who is authorized to download it.

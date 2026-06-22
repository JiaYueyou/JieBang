# Repository security

Local credentials belong in ignored `.env` files. Copy the nearest
`.env.example` file and replace its placeholders locally. Never commit API
keys, passwords, private keys, access tokens, database files, build outputs,
dependency directories, IDE state, or AI-tool session data.

## History rewrite notice

The repository history was rewritten after credentials and generated files
were found in earlier commits. Treat every credential that appeared before the
rewrite as compromised and rotate it at its provider.

Existing clones must not push their old history. The safest recovery is a fresh
clone. If local work must be preserved, export it as patches first, fetch the
rewritten remote, reset onto `origin/main`, and then reapply only reviewed
source changes.

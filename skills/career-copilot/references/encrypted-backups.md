# Encrypted private-workspace backups

Use `workspace_backup.py` only for a private Career Copilot workspace outside a Git repository and outside the installed profile/distribution. It uses the established authenticated-encryption tool [`age`](https://age-encryption.org/); it never uploads a backup.

## Dependency

Install `age` and keep its identity key outside the workspace, source clone and any synced public folder.

- macOS: `brew install age`
- Debian/Ubuntu/WSL: install the distribution `age` package.
- Linux/WSL/macOS: verify `age --version` and `age-keygen --help`.

Losing every identity key or a passphrase makes the backup unrecoverable. Keep at least one tested recovery key in an independently protected location. Do not commit, paste, log, or send an identity key or passphrase.

## Recipient-key workflow (recommended)

Generate an identity in a private secure location, then derive its public recipient:

```bash
age-keygen -o "$HOME/.config/career-copilot-backup.agekey"
age-keygen -y "$HOME/.config/career-copilot-backup.agekey"
```

Create, verify, and restore a backup:

```bash
BACKUP="$SKILL_DIR/scripts/workspace_backup.py"
python3 "$BACKUP" create --source "$WORKSPACE" --output "$HOME/Backups/career-copilot.age" --recipient 'age1...'
python3 "$BACKUP" verify --archive "$HOME/Backups/career-copilot.age" --identity "$HOME/.config/career-copilot-backup.agekey"
python3 "$BACKUP" restore --archive "$HOME/Backups/career-copilot.age" --identity "$HOME/.config/career-copilot-backup.agekey" --target "$HOME/Documents/CareerCopilot-restored"
```

Passphrase mode is also available with `--passphrase`. `age` prompts directly in the terminal; this script never accepts a passphrase as an argument, environment variable, or repository file.

## Safety and recovery

- The encrypted archive contains a manifest with file paths, sizes and SHA-256 checksums.
- Create rejects symlinks and unsafe workspace paths. It will not replace an output unless `--overwrite-output` is explicit.
- Verify decrypts to a temporary location and validates the manifest before reporting success.
- Restore rejects unsafe archive entries before extraction, stages the entire restore, requires a new/empty target, normalizes directories to `0700` and files to `0600`, then verifies the manifest after restore.
- Test restoration into a fresh temporary directory before relying on a backup for recovery.
- Backup media and identity keys need independent protection; encryption does not protect against deletion, endpoint compromise, or key loss.

import hashlib
import json
from pathlib import Path

import pytest

from pipeline.sir_saathi_pipeline import backups


def _executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o700)


def test_backup_directory_must_be_private_absolute_and_outside_repository(tmp_path: Path) -> None:
    relative = Path("relative-backups")
    with pytest.raises(ValueError, match="absolute"):
        backups._private_directory(str(relative))

    inside = backups.ROOT / "data/local/backups"
    with pytest.raises(ValueError, match="outside the repository"):
        backups._private_directory(str(inside))

    external = tmp_path / "backups"
    assert backups._private_directory(str(external)) == external.resolve()
    external.chmod(0o750)
    with pytest.raises(ValueError, match="0700"):
        backups._private_directory(str(external))


def test_encrypted_backup_verification_rejects_checksum_tampering(tmp_path: Path, monkeypatch) -> None:
    backup = tmp_path / "sample.dump.age"
    backup.write_bytes(b"encrypted fixture")
    backup.chmod(0o600)
    identity = tmp_path / "identity.txt"
    identity.write_text("synthetic identity", encoding="utf-8")
    identity.chmod(0o600)
    checksum = hashlib.sha256(backup.read_bytes()).hexdigest()
    checksum_path = backup.with_name(f"{backup.name}.sha256")
    checksum_path.write_text(f"{'0' * 64}  {backup.name}\n", encoding="ascii")
    checksum_path.chmod(0o600)
    monkeypatch.setattr(backups, "_require_command", lambda name: name)

    with pytest.raises(ValueError, match="does not match"):
        backups.verify_backup(backup_path=backup, identity_path=identity)

    checksum_path.write_text(f"{checksum}  wrong.dump.age\n", encoding="ascii")
    with pytest.raises(ValueError, match="malformed"):
        backups.verify_backup(backup_path=backup, identity_path=identity)


def test_backup_cli_failure_is_secret_safe(monkeypatch, capsys) -> None:
    secret_url = "postgresql://private-user:private-password@database/private"
    monkeypatch.setenv(backups.DATABASE_URL_ENV, secret_url)
    monkeypatch.delenv(backups.BACKUP_DIR_ENV, raising=False)
    monkeypatch.delenv(backups.AGE_RECIPIENT_ENV, raising=False)

    assert backups.main(["create"]) == 1
    output = capsys.readouterr().out
    assert json.loads(output) == {"error": "backup operation failed", "ready": False}
    assert secret_url not in output


def test_backup_create_and_verify_stream_without_plaintext_files(tmp_path: Path, monkeypatch) -> None:
    commands = tmp_path / "commands"
    commands.mkdir()
    _executable(
        commands / "pg_dump",
        "#!/bin/sh\n[ -n \"$PGDATABASE\" ] || exit 9\nprintf 'synthetic custom archive'\n",
    )
    _executable(
        commands / "age",
        "#!/bin/sh\n"
        "if [ \"$1\" = '--decrypt' ]; then\n"
        "  for value in \"$@\"; do input=$value; done\n"
        "  /bin/cat \"$input\"\n"
        "else\n"
        "  /bin/cat\n"
        "fi\n",
    )
    _executable(commands / "pg_restore", "#!/bin/sh\n/bin/cat >/dev/null\n")
    monkeypatch.setenv("PATH", f"{commands}:{Path('/usr/bin')}:{Path('/bin')}")
    backup_dir = tmp_path / "private-backups"
    backup_dir.mkdir(mode=0o700)

    created = backups.create_backup(
        database_url="postgresql://synthetic.invalid/test",
        backup_dir=backup_dir,
        recipient="age1syntheticrecipient",
    )
    backup_path = backup_dir / created["backup_filename"]
    identity = tmp_path / "identity.txt"
    identity.write_text("synthetic identity", encoding="utf-8")
    identity.chmod(0o600)

    assert created["plaintext_written_to_disk"] is False
    assert backup_path.read_bytes() == b"synthetic custom archive"
    assert not list(backup_dir.glob("*.dump"))
    verified = backups.verify_backup(backup_path=backup_path, identity_path=identity)
    assert verified["archive_valid"] is True
    assert verified["plaintext_written_to_disk"] is False


def test_backup_implementation_never_writes_a_plaintext_dump() -> None:
    source = (backups.ROOT / "pipeline/sir_saathi_pipeline/backups.py").read_text(encoding="utf-8")

    assert '"PGDATABASE": database_url' in source
    assert '[pg_dump, "--format=custom", "--no-owner", "--no-privileges"]' in source
    assert '[age, "--encrypt", "--recipient", recipient]' in source
    assert "plaintext_written_to_disk" in source
    dump_arguments = source.split("dump = subprocess.Popen(", 1)[1].split("env=child_env", 1)[0]
    assert "database_url" not in dump_arguments

"""Private consistent MySQL backup for the shared website/assistant business data.

对应文档：docs/18_助手业务接口与共享数据.md「运行与恢复」。
Requires --output-dir pointing to a new absolute directory. Never stops services.
Includes backend/.env, assistant token and service unit; never prints credentials.
Fusion state/source needs its own backup; see Fusion document23.
"""
import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    target = Path(args.output_dir)
    if not target.is_absolute() or target.exists():
        raise SystemExit('需要新的绝对备份目录；不覆盖已有资料')
    from app.database import engine
    if engine.dialect.name != 'mysql':
        raise SystemExit('此备份脚本只支持MySQL')
    token = Path(os.getenv('KM_ASSISTANT_TOKEN_FILE', str(Path.home() / '.config/knowledgemap/assistant-token')))
    if not token.is_file() or token.stat().st_mode & 0o077:
        raise SystemExit('专用token缺失或权限不正确')
    os.umask(0o077)
    target.mkdir(parents=True, mode=0o700)
    incomplete = target / 'INCOMPLETE.json'
    incomplete.write_text('{"phase":"collecting"}\n')
    private = target / 'private-state'
    private.mkdir(mode=0o700)
    private_files = {}
    for source, name in [(BACKEND / '.env', 'portal.env'), (token, 'assistant-token'),
                         (Path.home() / '.config/systemd/user/knowledgemap-assistant.service', 'knowledgemap-assistant.service')]:
        if not source.is_file():
            raise RuntimeError('必需私密备份资料缺失；保留INCOMPLETE标记')
        payload = source.read_bytes()
        (private / name).write_bytes(payload)
        private_files[name] = hashlib.sha256(payload).hexdigest()
    with tempfile.TemporaryDirectory(prefix='km-assistant-backup-') as temporary:
        auth = Path(temporary) / 'mysql.cnf'
        def quote(value):
            return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
        auth.write_text('[client]\n' + '\n'.join(f'{key}={quote(value)}' for key, value in {
            'host': engine.url.host, 'port': engine.url.port or 3306, 'user': engine.url.username,
            'password': engine.url.password, 'default-character-set': 'utf8mb4'}.items()))
        auth.chmod(0o600)
        raw = Path(temporary) / 'database.sql'
        with raw.open('wb') as stream:
            result = subprocess.run([os.getenv('KM_MYSQLDUMP', 'mysqldump'), '--defaults-extra-file=' + str(auth),
                '--single-transaction', '--no-tablespaces', '--set-gtid-purged=OFF', '--skip-comments',
                '--routines', '--triggers', engine.url.database], stdout=stream, stderr=subprocess.PIPE, timeout=120)
        if result.returncode or not raw.stat().st_size:
            raise RuntimeError('MySQL导出失败；不打印含私密信息的stderr，保留INCOMPLETE标记')
        compressed = private / 'database.sql.gz'
        with raw.open('rb') as source, gzip.open(compressed, 'wb') as output:
            shutil.copyfileobj(source, output)
    payload = compressed.read_bytes()
    gzip.decompress(payload)
    manifest = {'createdAt': datetime.now(timezone.utc).isoformat(), 'mysqlDatabase': engine.url.database,
                'mysqlDumpSha256': hashlib.sha256(payload).hexdigest(), 'privateFiles': private_files,
                'consistency': 'MySQL single-transaction; Fusion not captured; not a cross-system quiesced snapshot'}
    (private / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    incomplete.unlink()
    print(json.dumps({'ok': True, 'backup': str(target), 'compressedBytes': len(payload),
                      'boundary': manifest['consistency']}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('备份失败；保留INCOMPLETE标记，不能作为恢复点。检查私密目录和服务配置。') from None

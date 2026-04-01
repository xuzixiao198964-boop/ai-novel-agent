# -*- coding: utf-8 -*-
"""
通过 SSH 自动部署到 Ubuntu 服务器。
上传超过约 2 分钟则分多段上传，每段新建连接，直至传完。

用法（在仓库根目录）:
  set DEPLOY_SSH_PASSWORD=你的SSH密码
  set LLM_API_KEY=你的DeepSeek密钥
  python deploy/deploy_ssh.py

凭据仅从环境变量读取，见 deploy/ssh_env.py、deploy/README.md。
"""
import os
import sys
import time
from pathlib import Path

_DEPLOY = Path(__file__).resolve().parent
if str(_DEPLOY) not in sys.path:
    sys.path.insert(0, str(_DEPLOY))
from ssh_env import require_llm_api_key, require_ssh_password, ssh_host, ssh_port, ssh_user

REMOTE_DIR = "/opt/ai-novel-agent"

# 每段上传最长时长（秒），超过则本段结束后下一段用新连接
CHUNK_MAX_SECONDS = 15

# DeepSeek API（部署时写入服务器 .env，密钥来自环境变量）
LLM_API_BASE = "https://api.deepseek.com"
LLM_MODEL = "deepseek-chat"

_ssh_cfg: dict | None = None


def _creds() -> dict:
    global _ssh_cfg
    if _ssh_cfg is None:
        _ssh_cfg = {
            "host": ssh_host(),
            "port": ssh_port(),
            "user": ssh_user(),
            "password": require_ssh_password(),
        }
    return _ssh_cfg


def run_ssh(cmd: str, check: bool = True):
    """执行远程命令（使用 paramiko）"""
    import paramiko
    c = _creds()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(c["host"], port=c["port"], username=c["user"], password=c["password"], timeout=15)
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=False)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    client.close()
    if check and code != 0:
        raise RuntimeError(f"Exit {code}\n{err or out}")
    return type("R", (), {"returncode": code, "stdout": out, "stderr": err})()


def collect_files(local: Path, remote_base: str, exclude_dirs: tuple = ("__pycache__",), exclude_suffix: tuple = (".pyc",)):
    """收集要上传的文件列表：(local_path, remote_path)"""
    out = []
    for f in local.rglob("*"):
        if f.is_dir():
            continue
        if any(x in f.parts for x in exclude_dirs) or (f.suffix and f.suffix in exclude_suffix):
            continue
        rel = f.relative_to(local)
        rpath = f"{remote_base}/{rel}".replace("\\", "/")
        out.append((f, rpath))
    return out


def upload_chunk(files_chunk: list, run_ssh_fn, open_sftp_fn):
    """上传一批文件，使用传入的 sftp。open_sftp_fn() -> (sftp, transport)。"""
    sftp, trans = open_sftp_fn()
    try:
        for local_path, rpath in files_chunk:
            run_ssh_fn(f"mkdir -p $(dirname '{rpath}')")
            sftp.put(str(local_path), rpath)
            print(f"  上传 {local_path.relative_to(local_path.parents[len(Path(rpath).parts)-1])} -> {rpath}")
    finally:
        sftp.close()
        trans.close()


def main():
    import paramiko
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)

    print("1. 检查服务器连接...")
    try:
        r = run_ssh("echo ok")
        if getattr(r, "stdout", "").strip() == "ok" or getattr(r, "returncode", 0) == 0:
            print("   连接成功")
        else:
            print("   连接异常:", getattr(r, "stderr", r))
    except Exception as e:
        print("   连接失败:", e)
        sys.exit(1)

    print("2. 创建远程目录并收集待上传文件...")
    run_ssh(f"mkdir -p {REMOTE_DIR}")
    # 排除本地生成产出/缓存，避免上传巨量历史数据导致 SFTP 中断与服务器磁盘膨胀
    all_backend = collect_files(
        root / "backend",
        f"{REMOTE_DIR}/backend",
        exclude_dirs=("__pycache__", "data", "memory"),
    )
    # 强制包含前端脚本，避免因文件列表/分段上传问题导致线上 app.js 未更新
    forced = []
    for rel in ["static/app.js", "static/styles.css", "static/index.html"]:
        lp = root / "backend" / rel
        rp = f"{REMOTE_DIR}/backend/{rel}".replace("\\", "/")
        if lp.exists():
            forced.append((lp, rp))
    forced_remote_paths = {rp for _, rp in forced}
    existing_remote_paths = {rp for _, rp in all_backend}
    for lp, rp in forced:
        if rp not in existing_remote_paths:
            all_backend.append((lp, rp))
    root_files = []
    for name in ["Dockerfile", "docker-compose.yml"]:
        p = root / name
        if p.exists():
            root_files.append((p, f"{REMOTE_DIR}/{name}"))
    print(f"   backend 文件数: {len(all_backend)}, 根目录文件数: {len(root_files)}")

    def open_sftp():
        cr = _creds()
        trans = paramiko.Transport((cr["host"], cr["port"]))
        trans.connect(username=cr["user"], password=cr["password"])
        try:
            trans.set_keepalive(15)
        except Exception:
            pass
        sftp = paramiko.SFTPClient.from_transport(trans)
        return sftp, trans

    # 分段上传 backend：每段在 CHUNK_MAX_SECONDS 内完成，否则下一段新连接
    chunk_start = time.time()
    chunk_files = []
    segment = 0
    for i, (local_path, rpath) in enumerate(all_backend):
        chunk_files.append((local_path, rpath))
        # 每约 30 个文件或预计超时则上传一段
        if len(chunk_files) >= 5 or (time.time() - chunk_start) >= CHUNK_MAX_SECONDS:
            segment += 1
            print(f"  第 {segment} 段上传（共 {len(chunk_files)} 个文件）...")
            run_ssh(f"mkdir -p {REMOTE_DIR}/backend")
            sftp, trans = open_sftp()
            try:
                for lp, rp in chunk_files:
                    uploaded = False
                    last_err = None
                    for _retry in range(3):
                        try:
                            run_ssh(f"mkdir -p $(dirname '{rp}')", check=False)
                            sftp.put(str(lp), rp)
                            print(f"    上传 {lp.relative_to(root)}")
                            uploaded = True
                            break
                        except Exception as e:
                            last_err = e
                            try:
                                sftp.close()
                                trans.close()
                            except Exception:
                                pass
                            time.sleep(2)
                            sftp, trans = open_sftp()
                    if not uploaded:
                        raise RuntimeError(f"SFTP 上传失败：{lp} -> {rp}；{last_err}")
            finally:
                sftp.close()
                trans.close()
            chunk_files = []
            chunk_start = time.time()
    if chunk_files:
        segment += 1
        print(f"  第 {segment} 段上传（共 {len(chunk_files)} 个文件）...")
        sftp, trans = open_sftp()
        try:
            for lp, rp in chunk_files:
                uploaded = False
                last_err = None
                for _retry in range(3):
                    try:
                        run_ssh(f"mkdir -p $(dirname '{rp}')", check=False)
                        sftp.put(str(lp), rp)
                        print(f"    上传 {lp.relative_to(root)}")
                        uploaded = True
                        break
                    except Exception as e:
                        last_err = e
                        try:
                            sftp.close()
                            trans.close()
                        except Exception:
                            pass
                        time.sleep(2)
                        sftp, trans = open_sftp()
                if not uploaded:
                    raise RuntimeError(f"SFTP 上传失败：{lp} -> {rp}；{last_err}")
        finally:
            sftp.close()
            trans.close()

    # 根目录文件 + .env
    print("  上传根目录文件与 .env ...")
    sftp, trans = open_sftp()
    try:
        for local_path, rpath in root_files:
            uploaded = False
            last_err = None
            for _retry in range(3):
                try:
                    sftp.put(str(local_path), rpath)
                    print(f"  上传 {local_path.name}")
                    uploaded = True
                    break
                except Exception as e:
                    last_err = e
                    try:
                        sftp.close()
                        trans.close()
                    except Exception:
                        pass
                    time.sleep(2)
                    sftp, trans = open_sftp()
            if not uploaded:
                raise RuntimeError(f"SFTP 上传失败：{local_path} -> {rpath}；{last_err}")
        llm_key = require_llm_api_key()
        env_content = f"""LLM_API_BASE={LLM_API_BASE}
LLM_API_KEY={llm_key}
LLM_MODEL={LLM_MODEL}
# 验证：关闭 MOCK_LLM，使用真实 LLM，尽早暴露 JSON/解析问题
MOCK_LLM=0
# 测试用：生成固定小范围章节大纲（降低 JSON 截断概率）+ 只写前 N 章
TOTAL_CHAPTERS=0
WORDS_PER_CHAPTER=1500
MAX_CHAPTERS_TO_WRITE=4
CHAPTER_RANGE_MIN=8
CHAPTER_RANGE_MAX=8
"""
        from io import BytesIO
        sftp.putfo(BytesIO(env_content.encode("utf-8")), f"{REMOTE_DIR}/.env")
        print("  已写入 .env（API Key）")
    finally:
        sftp.close()
        trans.close()

    print("3. 安装 Docker（如未安装）并启动...")
    run_ssh(
        f"cd {REMOTE_DIR} && "
        "(command -v docker >/dev/null 2>&1 || (apt-get update && apt-get install -y docker.io docker-compose-v2)) && "
        "docker compose up -d || docker-compose up -d",
        check=False
    )

    # 直接把前端静态文件拷贝进运行容器，避免因为 build 缓存/构建失败导致 app.js 未更新
    run_ssh(
        (
            "sh -lc "
            "\""
            f"cid=$(docker compose ps -q app 2>/dev/null || docker-compose ps -q app 2>/dev/null); "
            "if [ -n \\\"$cid\\\" ]; then "
            f"docker cp {REMOTE_DIR}/backend/static/app.js $cid:/app/static/app.js 2>/dev/null || true; "
            f"docker cp {REMOTE_DIR}/backend/static/styles.css $cid:/app/static/styles.css 2>/dev/null || true; "
            f"docker cp {REMOTE_DIR}/backend/static/index.html $cid:/app/static/index.html 2>/dev/null || true; "
            "fi"
            "\""
        ),
        check=False,
    )

    print("4. 等待服务就绪...")
    run_ssh("sleep 5 && curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9000/api/health || true", check=False)

    print("完成。请访问: http://104.244.90.202:9000")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)

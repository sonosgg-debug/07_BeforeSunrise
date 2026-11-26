# -*- coding: utf-8 -*-
"""
BeforeSunrise Deploy & Sync to Oracle 2nd Server (168.110.34.155)
Packages BeforeSunrise files (including .env), deploys to Oracle Server,
sets up Python venv, and configures Crontab.
"""

import os
import sys
import tarfile
import subprocess
import tempfile
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
KEY_FILE = ROOT_DIR / "00 API Key" / "ssh-key-2026-10-24.key"
HOST_IP = "168.110.34.155"  # Oracle 2nd Server
USER = "ubuntu"
REMOTE_DIR = "/home/ubuntu/BeforeSunrise"

EXCLUDE_NAMES = {
    ".git", "__pycache__", "execution.log", "*.log",
    "venv", ".venv", "env", ".vscode", "candle_images",
    "page_source.html", "api_response.json", "update_script.py"
}

def tar_filter(tarinfo):
    parts = Path(tarinfo.name).parts
    if any(x in EXCLUDE_NAMES for x in parts):
        return None
    # Skip temporary excel lock files, .xlsx, or test images
    basename = os.path.basename(tarinfo.name)
    if basename.startswith("~$") or basename.endswith(".xlsx"):
        return None
    if tarinfo.issym():
        return None
    return tarinfo

def run_ssh(cmd_str):
    ssh_cmd = [
        "ssh", "-i", str(KEY_FILE),
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=15",
        f"{USER}@{HOST_IP}",
        cmd_str
    ]
    return subprocess.run(ssh_cmd, text=True, capture_output=True, encoding='utf-8', errors='replace')

def run_scp(local_file, remote_dest):
    scp_cmd = [
        "scp", "-i", str(KEY_FILE),
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=15",
        str(local_file),
        f"{USER}@{HOST_IP}:{remote_dest}"
    ]
    return subprocess.run(scp_cmd, text=True, capture_output=True, encoding='utf-8', errors='replace')

def main():
    print("=" * 65)
    print(f"  BeforeSunrise Deployment to Oracle 2nd Server ({HOST_IP})")
    print("=" * 65)

    if not KEY_FILE.exists():
        print(f"[ERROR] SSH Key not found at {KEY_FILE}")
        return False

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp_tar = Path(tmp.name)

    try:
        # 1. Package files
        print("\n[1/5] 로컬 파일 패키징 중 (.env 포함)...")
        with tarfile.open(tmp_tar, "w:gz") as tar:
            for item in CURRENT_DIR.iterdir():
                if item.name not in EXCLUDE_NAMES:
                    tar.add(item, arcname=item.name, filter=tar_filter)

        sz_kb = tmp_tar.stat().st_size / 1024
        print(f"      패키지 크기: {sz_kb:.1f} KB")

        # 2. Upload to Oracle Server
        print(f"\n[2/5] 오라클 제2서버({HOST_IP})로 업로드 중...")
        run_ssh(f"mkdir -p {REMOTE_DIR}")
        res = run_scp(tmp_tar, f"/home/ubuntu/tmp_beforesunrise.tar.gz")
        if res.returncode != 0:
            print(f"[FAIL] 업로드 실패: {res.stderr}")
            return False
        print("      업로드 완료.")

        # 3. Unpack on Remote Server
        print("\n[3/5] 원격 서버에 파일 압축 해제 중...")
        unpack_cmd = (
            f"tar -xzf /home/ubuntu/tmp_beforesunrise.tar.gz -C {REMOTE_DIR}/ && "
            f"rm -f /home/ubuntu/tmp_beforesunrise.tar.gz && "
            f"chmod +x {REMOTE_DIR}/run_oracle.sh"
        )
        res_unpack = run_ssh(unpack_cmd)
        if res_unpack.returncode != 0:
            print(f"[FAIL] 압축 해제 실패: {res_unpack.stderr}")
            return False
        print("      압축 해제 및 권한 설정 완료.")

        # 4. Setup venv and requirements on Remote Server
        print("\n[4/5] 원격 서버 Python 가상환경 및 라이브러리 설정 중...")
        setup_cmd = (
            f"cd {REMOTE_DIR} && "
            f"python3 -m venv venv && "
            f"./venv/bin/pip install --upgrade pip && "
            f"./venv/bin/pip install -r requirements.txt"
        )
        res_setup = run_ssh(setup_cmd)
        if res_setup.returncode != 0:
            print(f"[WARN] 가상환경 설정 출력: {res_setup.stderr}")
        else:
            print("      가상환경 및 패키지 설치 완료.")

        # 5. Configure Crontab (KST 05:05 & 06:05 / Monday-Saturday with NY 16:xx DST guard)
        print("\n[5/5] Crontab 스케줄러 등록 중 (미국 시장 마감 5분 후: 비서머타임 06:05 / 서머타임 05:05)...")
        cron_entry = f"5 5,6 * * 1-6 {REMOTE_DIR}/run_oracle.sh --cron"
        
        # Read existing crontab
        res_cron_read = run_ssh("crontab -l 2>/dev/null || true")
        existing_cron = res_cron_read.stdout.strip()
        
        new_cron_lines = []
        for line in existing_cron.splitlines():
            # Clean up old CRON_TZ or old morningwatch entries
            if line.startswith("CRON_TZ="):
                continue
            if "run_oracle.sh" in line or "MorningWatch" in line or "BeforeSunrise" in line:
                continue
            new_cron_lines.append(line)

        new_cron_lines.append(cron_entry)
        crontab_content = "\n".join(new_cron_lines) + "\n"
        crontab_update_cmd = f"cat << 'EOF' | crontab -\n{crontab_content}EOF"
        res_cron_write = run_ssh(crontab_update_cmd)
        if res_cron_write.returncode == 0:
            print(f"      Crontab 등록 완료! ({cron_entry})")
        else:
            print(f"[FAIL] Crontab 등록 오류: {res_cron_write.stderr}")

        print("\n" + "=" * 65)
        print("  오라클 제2서버 동기화 및 설정이 성공적으로 완료되었습니다!")
        print("=" * 65)
        return True

    finally:
        if tmp_tar.exists():
            tmp_tar.unlink()

if __name__ == "__main__":
    main()

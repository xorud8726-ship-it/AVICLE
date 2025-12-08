import requests
import zipfile
import io
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import sys, os, time, datetime, requests, configparser


# ====================================================
# 0. 실행 파일 기준 경로 가져오기
# ====================================================
def base_path():
    try:
        return sys._MEIPASS   # exe로 빌드된 경우
    except Exception:
        return os.path.abspath(".")  # py 실행

BASE_DIR = base_path()
TARGET_FOLDER = os.path.join(BASE_DIR, "AVICLE")   # 압축 풀릴 폴더


# ====================================================
# 1. GitHub ZIP 다운로드 + 자동 압축 해제
# ====================================================
def download_and_extract_avicle():
    zip_url = "https://github.com/xorud8726-ship-it/AVICLE/archive/refs/heads/main.zip"

    print("GitHub ZIP 다운로드 중...")
    response = requests.get(zip_url)

    if response.status_code != 200:
        raise Exception("ZIP 다운로드 실패!")

    print("ZIP 다운로드 성공 → 압축 해제 중...")

    # ZIP 파일 메모리에 로드
    zip_file = zipfile.ZipFile(io.BytesIO(response.content))

    # 기존 폴더 삭제 후 다시 생성
    if os.path.exists(TARGET_FOLDER):
        import shutil
        shutil.rmtree(TARGET_FOLDER)

    os.makedirs(TARGET_FOLDER, exist_ok=True)

    # ZIP 내부에서 /AVICLE 폴더만 추출
    for member in zip_file.namelist():
        if "AVICLE-main/AVICLE/" not in member:
            continue

        relative_path = member.replace("AVICLE-main/AVICLE/", "")

        if not relative_path.strip():
            continue  # 폴더 자체라면 skip

        extract_path = os.path.join(TARGET_FOLDER, relative_path)

        # 폴더인지 파일인지 구분
        if member.endswith("/"):
            os.makedirs(extract_path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(extract_path), exist_ok=True)
            with open(extract_path, "wb") as f:
                f.write(zip_file.read(member))

    print("AVICLE 폴더 압축 해제 완료:", TARGET_FOLDER)


# ====================================================
# 2. test.py 다운로드 + 실행
# ====================================================
def load_and_run_test():
    url = "https://raw.githubusercontent.com/xorud8726-ship-it/AVICLE/main/test.py"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception("test.py 다운로드 실패!")

    print("test.py 다운로드 성공 → 실행합니다.")
    exec(response.text, {})


# ====================================================
# 메인 실행
# ====================================================
if __name__ == "__main__":
    download_and_extract_avicle()
    load_and_run_test()

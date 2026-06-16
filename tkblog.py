import os
import sys
import json
import shutil
import time
import random
import itertools
import threading
import subprocess
import base64
import re
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog, filedialog
from typing import Optional
import ctypes

import pyautogui
import pyperclip
import pygetwindow as gw
from pynput import keyboard
from pynput.keyboard import Key, Controller
from PIL import Image, ImageOps

# HEIC / HEIF 지원
HEIC_AVAILABLE = False
HEIC_ERROR = ""

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIC_AVAILABLE = True
except Exception as e:
    HEIC_AVAILABLE = False
    HEIC_ERROR = str(e)
    print("pillow_heif import 실패:", e)

CURSOR_API_BASE_URL = "https://api.cursor.com/v1"
CURSOR_RUN_TERMINAL_STATUSES = frozenset({"FINISHED", "ERROR", "CANCELLED", "EXPIRED"})

# ---------------- 전역 설정 및 변수 ----------------
CONFIG_FILE = "config.json"
SUPPORTED_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".heic",
    ".heif",
)

IMG_TITLE_KEYWORDS = (
    "순정연동", "시공", "가격", "라이트", "튜닝", "kc인증", "스피커", "에이비클",
    "시공후기", "아크릴", "전용어플", "전문점", "광주", "전주", "순천", "목포",
    "군산", "여수", "익산", "광양",
)

running = False
stop_flag = False

pyautogui.FAILSAFE = True

# 현재 선택된 txt 파일명
current_selected_file = None
preferred_browser_hwnd = None
preferred_browser_kind = "chrome"

DEFAULT_PROMPT_TEMPLATE = """Convert the following YouTube script into a Naver blog post optimized for TOP search ranking.

[PRIMARY GOAL]
- Maximize Naver SEO exposure
- Make it 100% human-written (NOT AI-like)
- Natural blog style

[CRITICAL RULE]
- ALWAYS use "엠비언트" (NOT 앰비언트)

[ANTI-AI RULE]
- Avoid robotic tone
- Vary sentence structure
- Make it feel like a real person wrote it

[SEO RULE]
1. If contains "은하수" or "스타라이트":
- Use: 광주, 에이비클, 은하수, 차량명 repeatedly

2. If about "엠비언트":
- Use: 엠비언트, 광주, 차량명, 에이비클 repeatedly

3. Extract vehicle name automatically

4. Keyword placement:
- Title
- First paragraph (2~3 times)
- Middle distribution
- Final paragraph again

5. Use related keywords:
- 엠비언트 → 무드등, 실내조명, 차량 실내튜닝
- 은하수 → 스타라이트, 천장무드등

6. Vehicle name MUST appear at least 6~10 times naturally in the content

7. Avoid keyword stuffing

[TITLE RULE]
- Title must include: 광주 + 차량명 + 엠비언트 or 은하수
- Make it clickable and SEO optimized

[STRUCTURE]
- Title
- Introduction
- Vehicle intro
- Installation
- Features
- Conclusion

[IMPORTANT FINAL RULE]
- DO NOT include:
"상단 연락처로 문의 주세요"
"연락 주세요"
"전화 주세요"
- ALWAYS end with "문의하기" 유도 문장

[READABILITY]
- Short paragraphs
- Subheadings (■)
- Mobile optimized

[TAGS]
- 10~15 hashtags

[OUTPUT]
- Blog post only

------------------------------------
[YouTube Script]
{script}
"""

DEFAULT_PROMPT_NAMES = [
    "프롬프트 1 복사",
    "프롬프트 2 복사",
    "프롬프트 3 복사",
    "프롬프트 4 복사",
]

prompt_templates = [DEFAULT_PROMPT_TEMPLATE for _ in range(4)]
prompt_button_names = DEFAULT_PROMPT_NAMES.copy()
prompt_copy_buttons = []
prompt_edit_buttons = []
prompt_name_buttons = []
cursor_ai_buttons = []
blog_copy_snippets = ["", "", ""]

# ---------------- 리소스 경로 ----------------
def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))

    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)

    # 원본.py 폴더에서 실행해도 launcher.exe 가 있는 실제 작업 폴더를 사용
    if os.path.basename(script_dir).lower() in ("원본.py", "src", "source"):
        if (
            os.path.isfile(os.path.join(parent_dir, "launcher.exe"))
            or os.path.isdir(os.path.join(parent_dir, "posts"))
            or os.path.isfile(os.path.join(parent_dir, "config.json"))
            or os.path.isdir(os.path.join(parent_dir, "config"))
        ):
            return parent_dir

    return script_dir

BASE_DIR = get_base_dir()

POSTS_DIR_NAME = "posts"
CONFIG_DIR_NAME = "config"
ASSETS_DIR_NAME = "assets"
OUTPUT_DIR_NAME = "output"
DATA_DIR_NAME = "data"

MIGRATION_MARKER = ".folders_migrated"

ASSET_FILENAMES = (
    "naver_login.png",
    "help_header.png",
    "se.png",
    "emdfhr.png",
    "cnlth.png",
    "rink.png",
    "url.png",
    "map.png",
    "avicle.png",
    "avicle_edge.png",
    "add.png",
    "check.png",
    "66.PNG",
)

def get_posts_dir():
    return os.path.join(BASE_DIR, POSTS_DIR_NAME)

def get_config_dir():
    return os.path.join(BASE_DIR, CONFIG_DIR_NAME)

def get_assets_dir():
    return os.path.join(BASE_DIR, ASSETS_DIR_NAME)

def get_output_dir():
    return os.path.join(BASE_DIR, OUTPUT_DIR_NAME)

def get_data_dir():
    return os.path.join(BASE_DIR, DATA_DIR_NAME)

def ensure_app_directories():
    for folder_name in (
        POSTS_DIR_NAME,
        CONFIG_DIR_NAME,
        ASSETS_DIR_NAME,
        OUTPUT_DIR_NAME,
        DATA_DIR_NAME,
    ):
        os.makedirs(os.path.join(BASE_DIR, folder_name), exist_ok=True)

def _safe_move_file(source_path: str, target_dir: str) -> None:
    if not os.path.isfile(source_path):
        return

    file_name = os.path.basename(source_path)
    target_path = os.path.join(target_dir, file_name)

    if os.path.abspath(source_path) == os.path.abspath(target_path):
        return

    if os.path.exists(target_path):
        return

    os.makedirs(target_dir, exist_ok=True)
    os.replace(source_path, target_path)

def resolve_asset_path(file_name: str) -> str:
    name_candidates = [file_name]
    if file_name.lower().endswith(".png"):
        stem = file_name[:-4]
        name_candidates.append(stem + ".png")
        name_candidates.append(stem + ".PNG")

    deduped_names = []
    seen_names = set()
    for name in name_candidates:
        key = name.lower()
        if key in seen_names:
            continue
        seen_names.add(key)
        deduped_names.append(name)

    search_dirs = (get_assets_dir(), BASE_DIR)
    for asset_dir in search_dirs:
        for name in deduped_names:
            path = os.path.join(asset_dir, name)
            if os.path.isfile(path):
                return path

    return os.path.join(get_assets_dir(), deduped_names[0])

def iter_txt_folders():
    folders = []
    posts_dir = get_posts_dir()
    if os.path.isdir(posts_dir):
        folders.append(posts_dir)
    if os.path.abspath(BASE_DIR) not in {os.path.abspath(folder) for folder in folders}:
        folders.append(BASE_DIR)
    return folders

def resolve_txt_path(file_name: str) -> str:
    for folder in iter_txt_folders():
        path = os.path.join(folder, file_name)
        if os.path.isfile(path):
            return path
    return os.path.join(get_posts_dir(), file_name)

def resolve_config_path(for_write: bool = False) -> str:
    if for_write:
        return os.path.join(get_config_dir(), CONFIG_FILE)

    candidates = (
        os.path.join(get_config_dir(), CONFIG_FILE),
        os.path.join(BASE_DIR, CONFIG_FILE),
    )
    for path in candidates:
        if os.path.isfile(path):
            return path
    return candidates[0]

def bind_template_paths():
    global LOGIN_TEMPLATE, HELP_HEADER_TEMPLATE, SE_TEMPLATE
    global EMDFHR_TEMPLATE, CNLTH_TEMPLATE, RINK_TEMPLATE, URL_TEMPLATE
    global MAP_TEMPLATE, AVICLE_TEMPLATE, AVICLE_EDGE_TEMPLATE, ADD_TEMPLATE, CHECK_TEMPLATE, QUOTE_TEMPLATE

    LOGIN_TEMPLATE = resolve_asset_path("naver_login.png")
    HELP_HEADER_TEMPLATE = resolve_asset_path("help_header.png")
    SE_TEMPLATE = resolve_asset_path("se.png")
    EMDFHR_TEMPLATE = resolve_asset_path("emdfhr.png")
    CNLTH_TEMPLATE = resolve_asset_path("cnlth.png")
    RINK_TEMPLATE = resolve_asset_path("rink.png")
    URL_TEMPLATE = resolve_asset_path("url.png")
    MAP_TEMPLATE = resolve_asset_path("map.png")
    AVICLE_TEMPLATE = resolve_asset_path("avicle.png")
    AVICLE_EDGE_TEMPLATE = resolve_asset_path("avicle_edge.png")
    ADD_TEMPLATE = resolve_asset_path("add.png")
    CHECK_TEMPLATE = resolve_asset_path("check.png")
    QUOTE_TEMPLATE = resolve_asset_path("66.PNG")

def ensure_launcher_secrets():
    """런처가 exe 옆 secret.key 를 찾는 경우를 위해 루트에도 유지합니다."""
    root_key = os.path.join(BASE_DIR, "secret.key")
    config_key = os.path.join(get_config_dir(), "secret.key")

    if os.path.isfile(config_key) and not os.path.isfile(root_key):
        try:
            shutil.copy2(config_key, root_key)
        except Exception:
            pass

def init_app_storage():
    ensure_app_directories()
    migrate_legacy_files()
    ensure_launcher_secrets()
    bind_template_paths()

def migrate_legacy_files():
    ensure_app_directories()

    posts_dir = get_posts_dir()
    config_dir = get_config_dir()
    assets_dir = get_assets_dir()
    output_dir = get_output_dir()

    reserved_names = {
        POSTS_DIR_NAME,
        CONFIG_DIR_NAME,
        ASSETS_DIR_NAME,
        OUTPUT_DIR_NAME,
        DATA_DIR_NAME,
        "원본.py",
    }

    try:
        for entry in os.listdir(BASE_DIR):
            source_path = os.path.join(BASE_DIR, entry)

            if not os.path.isfile(source_path):
                continue

            lower_name = entry.lower()

            if entry in reserved_names:
                continue

            if lower_name.endswith(".txt"):
                _safe_move_file(source_path, posts_dir)
            elif lower_name == CONFIG_FILE.lower():
                _safe_move_file(source_path, config_dir)
            elif lower_name == "secret.key":
                _safe_move_file(source_path, config_dir)
                ensure_launcher_secrets()
            elif lower_name.endswith(".md"):
                _safe_move_file(source_path, output_dir)
            elif lower_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
                _safe_move_file(source_path, assets_dir)

        for asset_name in ASSET_FILENAMES:
            _safe_move_file(os.path.join(BASE_DIR, asset_name), assets_dir)

        marker_path = os.path.join(get_config_dir(), MIGRATION_MARKER)
        with open(marker_path, "w", encoding="utf-8") as marker_file:
            marker_file.write("ok")
    except Exception as exc:
        print("legacy migration warning:", exc)

CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
)

EDGE_CANDIDATES = (
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)

BROWSER_TITLE_FRAGMENTS = {
    "chrome": ("Chrome", "네이버", "Naver", "naver.com"),
    "edge": ("Edge", "Microsoft Edge", "네이버", "Naver", "naver.com"),
}

LOGIN_TEMPLATE = ""
HELP_HEADER_TEMPLATE = ""
SE_TEMPLATE = ""
EMDFHR_TEMPLATE = ""
CNLTH_TEMPLATE = ""
RINK_TEMPLATE = ""
URL_TEMPLATE = ""
MAP_TEMPLATE = ""
AVICLE_TEMPLATE = ""
AVICLE_EDGE_TEMPLATE = ""
ADD_TEMPLATE = ""
CHECK_TEMPLATE = ""
QUOTE_TEMPLATE = ""

init_app_storage()

WIN_X, WIN_Y = 0, 0
WIN_W, WIN_H = 837, 1037

# 네이버 글쓰기 화면 좌표 보정값
# se.png 인식이 실패하거나 두 번째 블로그에서 포커스가 꼬일 때 사용하는 안전 클릭 좌표입니다.
# 크롬 창을 837x1037 / 좌상단 0,0 으로 고정하는 현재 코드 기준입니다.
TITLE_CLICK_X = WIN_X + WIN_W // 2
TITLE_CLICK_Y = WIN_Y + 285
BODY_CLICK_X = WIN_X + WIN_W // 2
BODY_CLICK_Y = WIN_Y + 500

DEFAULT_NAVER_ID_1 = ""
DEFAULT_NAVER_PASSWORD_1 = ""
DEFAULT_BLOG_WRITE_URL_1 = ""
DEFAULT_NAVER_ID_2 = ""
DEFAULT_NAVER_PASSWORD_2 = ""
DEFAULT_BLOG_WRITE_URL_2 = ""
DEFAULT_NAVER_ID_3 = ""
DEFAULT_NAVER_PASSWORD_3 = ""
DEFAULT_BLOG_WRITE_URL_3 = ""
BLOG_STORAGE_MARKER_TITLE = "\n<<<BLOG2_TITLE>>>\n"
BLOG_STORAGE_MARKER_BODY = "\n<<<BLOG2_BODY>>>\n"
BLOG_STORAGE_MARKER_TITLE_3 = "\n<<<BLOG3_TITLE>>>\n"
BLOG_STORAGE_MARKER_BODY_3 = "\n<<<BLOG3_BODY>>>\n"

DEFAULT_CONFIDENCE = 0.85
SEARCH_INTERVAL = 0.25
DEFAULT_PHONE_NUMBER = "010-8075-8066"
DEFAULT_SPEED_CPM = 450
SPECIAL_LINK_TEXT = "견적상담하기"
QUOTE_MARKER = "-인용구-"

kb_controller = Controller()

# ---------------- 입력 유틸 ----------------
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
wintypes = ctypes.wintypes
VK_CAPITAL = 0x14
VK_HANGUL = 0x15
KEYEVENTF_KEYUP = 0x0002
SW_RESTORE = 9
SW_NORMAL = 1
SW_MINIMIZE = 6
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
ASFW_ANY = -1

BROWSER_PROCESS_NAMES = {
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
}

def is_capslock_on() -> bool:
    try:
        return bool(user32.GetKeyState(VK_CAPITAL) & 0x0001)
    except Exception:
        return False

def press_virtual_key(vk_code: int) -> None:
    try:
        user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.03)
        user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)
    except Exception:
        pass

def ensure_capslock_off() -> None:
    if is_capslock_on():
        press_virtual_key(VK_CAPITAL)
        time.sleep(0.05)

def text_needs_hangul_mode(text: str) -> bool:
    return any("가" <= ch <= "힣" or "ㄱ" <= ch <= "ㅎ" or "ㅏ" <= ch <= "ㅣ" for ch in text)

def text_needs_english_mode(text: str) -> bool:
    return any(("a" <= ch.lower() <= "z") for ch in text)

def ensure_input_mode_for_text(text: str) -> None:
    ensure_capslock_off()
    try:
        if text_needs_hangul_mode(text):
            if user32.GetKeyboardLayout(0) & 0xFFFF == 0x0412:
                pass
            else:
                press_virtual_key(VK_HANGUL)
        elif text_needs_english_mode(text):
            if user32.GetKeyboardLayout(0) & 0xFFFF == 0x0412:
                press_virtual_key(VK_HANGUL)
    except Exception:
        pass

def paste_text_safely(text: str) -> None:
    ensure_input_mode_for_text(text)
    try:
        previous_clipboard = pyperclip.paste()
    except Exception:
        previous_clipboard = None

    try:
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.08)
    finally:
        if previous_clipboard is not None:
            try:
                pyperclip.copy(previous_clipboard)
            except Exception:
                pass

def clear_current_input_field() -> None:
    ensure_capslock_off()
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.05)
    pyautogui.press("backspace")
    time.sleep(0.08)

# ---------------- [공통] 설정 저장/불러오기 ----------------
DEFAULT_WINDOW_GEOMETRY = "1500x960"

def _read_config_file_data():
    config_path = resolve_config_path()
    if not os.path.isfile(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def capture_window_geometry() -> Optional[str]:
    try:
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = root.winfo_x()
        y = root.winfo_y()
        if width > 100 and height > 100:
            return f"{width}x{height}+{x}+{y}"
    except Exception:
        pass
    return None

def apply_window_geometry(geometry: str) -> None:
    if not geometry or not isinstance(geometry, str):
        return
    try:
        root.geometry(geometry.strip())
        root.update_idletasks()
    except Exception:
        pass

def _build_config_data():
    return {
        "folder_path": img_folder_path.get(),
        "img_split_count": int(img_split_count.get()),
        "car_type": car_type_var.get().strip(),
        "prompt_templates": prompt_templates,
        "prompt_button_names": prompt_button_names,
        "blog_copy_snippets": blog_copy_snippets,
        "phone_number_1": phone_number_var_1.get().strip(),
        "phone_number_2": phone_number_var_2.get().strip(),
        "phone_number_3": phone_number_var_3.get().strip(),
        "naver_id_1": naver_id_var_1.get().strip(),
        "naver_password_1": naver_password_var_1.get().strip(),
        "blog_write_url_1": blog_write_url_var_1.get().strip(),
        "naver_id_2": naver_id_var_2.get().strip(),
        "naver_password_2": naver_password_var_2.get().strip(),
        "blog_write_url_2": blog_write_url_var_2.get().strip(),
        "naver_id_3": naver_id_var_3.get().strip(),
        "naver_password_3": naver_password_var_3.get().strip(),
        "blog_write_url_3": blog_write_url_var_3.get().strip(),
        "blog_run_mode": int(blog_run_mode_var.get()),
        "speed_cpm": int(speed_scale.get()),
    }

def save_config(save_window_geometry: bool = False):
    existing = _read_config_file_data()
    data = _build_config_data()

    if save_window_geometry:
        geometry = capture_window_geometry()
        if geometry:
            data["window_geometry"] = geometry
    elif existing.get("window_geometry"):
        data["window_geometry"] = existing["window_geometry"]

    try:
        config_path = resolve_config_path(for_write=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def on_root_close():
    save_config(save_window_geometry=True)
    root.destroy()

def load_config():
    global prompt_templates, prompt_button_names, blog_copy_snippets

    config_path = resolve_config_path()
    if not os.path.isfile(config_path):
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        img_folder_path.set(data.get("folder_path", ""))
        img_split_count.set(int(data.get("img_split_count", 2)))
        saved_car_type = data.get("car_type", "")
        if saved_car_type:
            car_type_var.set(saved_car_type)

        legacy_prompt = data.get("prompt_template")
        if legacy_prompt:
            prompt_templates = [legacy_prompt for _ in range(4)]
        else:
            loaded_templates = data.get("prompt_templates", [])
            if isinstance(loaded_templates, list) and loaded_templates:
                for i in range(4):
                    if i < len(loaded_templates) and loaded_templates[i]:
                        prompt_templates[i] = loaded_templates[i]

        loaded_names = data.get("prompt_button_names", [])
        if isinstance(loaded_names, list) and loaded_names:
            for i in range(4):
                if i < len(loaded_names) and str(loaded_names[i]).strip():
                    prompt_button_names[i] = str(loaded_names[i]).strip()

        loaded_copy_snippets = data.get("blog_copy_snippets", [])
        if isinstance(loaded_copy_snippets, list) and loaded_copy_snippets:
            for i in range(3):
                if i < len(loaded_copy_snippets):
                    blog_copy_snippets[i] = str(loaded_copy_snippets[i])

        loaded_phone_number_1 = str(data.get("phone_number_1", DEFAULT_PHONE_NUMBER)).strip()
        if loaded_phone_number_1:
            phone_number_var_1.set(loaded_phone_number_1)

        loaded_phone_number_2 = str(data.get("phone_number_2", DEFAULT_PHONE_NUMBER)).strip()
        if loaded_phone_number_2:
            phone_number_var_2.set(loaded_phone_number_2)

        loaded_phone_number_3 = str(data.get("phone_number_3", DEFAULT_PHONE_NUMBER)).strip()
        if loaded_phone_number_3:
            phone_number_var_3.set(loaded_phone_number_3)

        naver_id_var_1.set(str(data.get("naver_id_1", DEFAULT_NAVER_ID_1)).strip())
        naver_password_var_1.set(str(data.get("naver_password_1", DEFAULT_NAVER_PASSWORD_1)).strip())
        blog_write_url_var_1.set(str(data.get("blog_write_url_1", DEFAULT_BLOG_WRITE_URL_1)).strip())
        naver_id_var_2.set(str(data.get("naver_id_2", DEFAULT_NAVER_ID_2)).strip())
        naver_password_var_2.set(str(data.get("naver_password_2", DEFAULT_NAVER_PASSWORD_2)).strip())
        blog_write_url_var_2.set(str(data.get("blog_write_url_2", DEFAULT_BLOG_WRITE_URL_2)).strip())
        naver_id_var_3.set(str(data.get("naver_id_3", DEFAULT_NAVER_ID_3)).strip())
        naver_password_var_3.set(str(data.get("naver_password_3", DEFAULT_NAVER_PASSWORD_3)).strip())
        blog_write_url_var_3.set(str(data.get("blog_write_url_3", DEFAULT_BLOG_WRITE_URL_3)).strip())
        blog_run_mode_var.set(int(data.get("blog_run_mode", 1)))
        speed_scale.set(int(data.get("speed_cpm", DEFAULT_SPEED_CPM)))
        update_speed_label()

        apply_window_geometry(str(data.get("window_geometry", "")).strip())

    except Exception:
        pass

def update_speed_label(value=None):
    try:
        current_value = int(float(speed_scale.get()))
    except Exception:
        current_value = DEFAULT_SPEED_CPM
    speed_value_var.set(f"현재 타수: {current_value} CPM")

# ---------------- [공통] 상태 업데이트 ----------------
def set_status(text: str):
    status_var.set(text)
    root.update_idletasks()

# ---------------- [탭 1] 파일 관리 및 자동 타이핑 ----------------
def get_txt_folder():
    os.makedirs(get_posts_dir(), exist_ok=True)
    return get_posts_dir()

def split_blog_file_content(raw_text: str):
    raw_text = raw_text.replace("\r\n", "\n")
    title3, body3 = "", ""

    if BLOG_STORAGE_MARKER_TITLE_3 in raw_text and BLOG_STORAGE_MARKER_BODY_3 in raw_text:
        try:
            before_blog3, rest3 = raw_text.split(BLOG_STORAGE_MARKER_TITLE_3, 1)
            title3_raw, body3_raw = rest3.split(BLOG_STORAGE_MARKER_BODY_3, 1)
            title3 = title3_raw.strip()
            body3 = body3_raw.lstrip("\n")
            raw_text = before_blog3
        except Exception:
            title3, body3 = "", ""

    if BLOG_STORAGE_MARKER_TITLE in raw_text and BLOG_STORAGE_MARKER_BODY in raw_text:
        try:
            blog1_raw, rest = raw_text.split(BLOG_STORAGE_MARKER_TITLE, 1)
            blog2_title_raw, blog2_body_raw = rest.split(BLOG_STORAGE_MARKER_BODY, 1)
            title1, body1 = split_legacy_title_and_body(blog1_raw)
            title2 = blog2_title_raw.strip()
            body2 = blog2_body_raw.lstrip("\n")
            return title1, body1, title2, body2, title3, body3
        except Exception:
            pass

    title1, body1 = split_legacy_title_and_body(raw_text)
    return title1, body1, "", "", title3, body3

def split_legacy_title_and_body(raw_text: str):
    raw_text = raw_text.replace("\r\n", "\n")
    lines = raw_text.split("\n")

    if not lines:
        return "", ""

    title = lines[0].strip()
    body = "\n".join(lines[1:]).lstrip("\n")
    return title, body

def combine_blog_file_content(title1: str, body1: str, title2: str, body2: str, title3: str = "", body3: str = ""):
    primary = combine_legacy_title_and_body(title1, body1)
    title2 = title2.rstrip()
    body2 = body2.rstrip()
    title3 = title3.rstrip()
    body3 = body3.rstrip()

    if title2 or body2:
        primary = f"{primary}{BLOG_STORAGE_MARKER_TITLE}{title2}{BLOG_STORAGE_MARKER_BODY}{body2}"

    if title3 or body3:
        primary = f"{primary}{BLOG_STORAGE_MARKER_TITLE_3}{title3}{BLOG_STORAGE_MARKER_BODY_3}{body3}"

    return primary

def combine_legacy_title_and_body(title: str, body: str):
    title = title.rstrip()
    body = body.rstrip()

    if title and body:
        return f"{title}\n{body}"
    if title:
        return title
    return body

def get_title_and_content_values():
    return (
        title_var_1.get().strip(),
        editor_1.get("1.0", tk.END).rstrip(),
        title_var_2.get().strip(),
        editor_2.get("1.0", tk.END).rstrip(),
        title_var_3.get().strip(),
        editor_3.get("1.0", tk.END).rstrip(),
    )

def get_blog_editor_by_index(blog_index: int):
    mapping = {
        1: (title_var_1, editor_1),
        2: (title_var_2, editor_2),
        3: (title_var_3, editor_3),
    }
    return mapping[blog_index]

def append_text_to_body_bottom(body: str, insert_text: str) -> str:
    insert_text = insert_text.strip()
    if not insert_text:
        return body
    if body.strip():
        return f"{body.rstrip()}\n\n{insert_text}"
    return insert_text

def edit_blog_copy_snippet(blog_index: int):
    win = tk.Toplevel(root)
    win.title(f"블로그 {blog_index} 복사할 텍스트")
    win.geometry("520x260")
    win.transient(root)
    win.configure(bg=BG_MAIN)

    tk.Label(
        win,
        text="복사 시 본문 맨 아래 단락에 삽입됩니다. (제목은 복사되지 않음)",
        font=("맑은 고딕", 10, "bold"),
        bg=BG_MAIN,
        fg=TEXT_MUTED,
    ).pack(pady=(12, 8))

    text = tk.Text(
        win, font=("맑은 고딕", 11), height=6, relief="flat",
        highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, padx=12, pady=12,
    )
    text.pack(fill="both", expand=True, padx=16, pady=4)
    text.insert("1.0", blog_copy_snippets[blog_index - 1])

    bottom = tk.Frame(win, bg=BG_MAIN)
    bottom.pack(fill="x", padx=16, pady=12)

    def save_snippet():
        blog_copy_snippets[blog_index - 1] = text.get("1.0", tk.END).strip()
        save_config()
        win.destroy()

    create_flat_button(bottom, "닫기", win.destroy, SECONDARY, SECONDARY_HOVER).pack(side="right", padx=4)
    create_flat_button(bottom, "저장", save_snippet, ACCENT, ACCENT_HOVER).pack(side="right", padx=4)

def copy_blog_with_snippet(blog_index: int):
    _, editor = get_blog_editor_by_index(blog_index)
    body = editor.get("1.0", tk.END).rstrip()
    snippet = blog_copy_snippets[blog_index - 1].strip()

    if not body:
        messagebox.showwarning("알림", f"블로그 {blog_index} 내용을 입력하세요.")
        return

    if not snippet:
        messagebox.showwarning("알림", "먼저 '복사할 텍스트' 버튼에서 문구를 입력하세요.")
        return

    copy_text = append_text_to_body_bottom(body, snippet)

    try:
        root.clipboard_clear()
        root.clipboard_append(copy_text)
        root.update()
        messagebox.showinfo("완료", f"블로그 {blog_index} 본문이 클립보드에 복사되었습니다!")
    except Exception as e:
        messagebox.showerror("오류", f"클립보드 복사 실패: {e}")

def create_blog_action_row(parent, blog_index: int, test_label: str):
    row = tk.Frame(parent, bg=BG_PANEL)
    row.pack(fill="x", pady=(0, 10))
    row.grid_columnconfigure(0, weight=2)
    row.grid_columnconfigure(1, weight=1)
    row.grid_columnconfigure(2, weight=1)

    create_flat_button(
        row, test_label, lambda idx=blog_index: start_blog_test(idx),
        SUCCESS, SUCCESS_HOVER, font=("맑은 고딕", 9, "bold"), pady=7,
    ).grid(row=0, column=0, sticky="ew", padx=(0, 4))

    create_flat_button(
        row, "복사할 텍스트", lambda idx=blog_index: edit_blog_copy_snippet(idx),
        SECONDARY, SECONDARY_HOVER, font=("맑은 고딕", 9, "bold"), pady=7,
    ).grid(row=0, column=1, sticky="ew", padx=4)

    create_flat_button(
        row, "복사", lambda idx=blog_index: copy_blog_with_snippet(idx),
        ACCENT, ACCENT_HOVER, font=("맑은 고딕", 9, "bold"), pady=7,
    ).grid(row=0, column=2, sticky="ew", padx=(4, 0))

def load_txt_files(restore_selection=True):
    global current_selected_file

    previous_file = current_selected_file if restore_selection else None

    listbox.delete(0, tk.END)

    files = []
    seen = set()
    for txt_folder in iter_txt_folders():
        try:
            for file_name in os.listdir(txt_folder):
                if file_name.lower().endswith(".txt") and file_name not in seen:
                    files.append(file_name)
                    seen.add(file_name)
        except OSError:
            pass
    files.sort()

    selected_index = None
    for idx, file_name in enumerate(files):
        listbox.insert(tk.END, file_name)
        if previous_file and file_name == previous_file:
            selected_index = idx

    if selected_index is not None:
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(selected_index)
        listbox.activate(selected_index)
        listbox.see(selected_index)

def keep_listbox_selection():
    global current_selected_file

    if current_selected_file:
        files = list(listbox.get(0, tk.END))
        if current_selected_file in files:
            idx = files.index(current_selected_file)
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(idx)
            listbox.activate(idx)
            listbox.see(idx)

def save_txt_file():
    global current_selected_file

    file_name = current_selected_file

    if not file_name:
        selected = listbox.curselection()
        if selected:
            file_name = listbox.get(selected[0])

    if not file_name:
        messagebox.showwarning("알림", "저장할 파일을 선택하세요.")
        return

    title1, content1, title2, content2, title3, content3 = get_title_and_content_values()

    if not title1 and not content1 and not title2 and not content2 and not title3 and not content3:
        messagebox.showwarning("알림", "제목 또는 내용을 입력하세요.")
        return

    save_text = combine_blog_file_content(title1, content1, title2, content2, title3, content3)

    try:
        full_path = os.path.join(get_txt_folder(), file_name)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(save_text)

        legacy_path = os.path.join(BASE_DIR, file_name)
        if (
            os.path.isfile(legacy_path)
            and os.path.abspath(legacy_path) != os.path.abspath(full_path)
        ):
            os.remove(legacy_path)

        current_selected_file = file_name
        keep_listbox_selection()
        set_status(f"[{file_name}] 저장 완료")
    except Exception as e:
        messagebox.showerror("오류", f"저장 실패: {e}")

def _sanitize_file_stem(name: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if ch in invalid else ch for ch in name.strip())
    return cleaned.strip(" .") or "blog"

def _make_car_type_filename(car_type: str) -> str:
    stem = _sanitize_file_stem(car_type)
    date_part = time.strftime("%Y%m%d")
    time_part = time.strftime("%H%M%S")
    base_name = f"{stem}_{date_part}_{time_part}.txt"
    full_path = os.path.join(get_txt_folder(), base_name)
    if not os.path.isfile(full_path):
        return base_name

    suffix = 2
    while True:
        candidate = f"{stem}_{date_part}_{time_part}_{suffix}.txt"
        if not os.path.isfile(os.path.join(get_txt_folder(), candidate)):
            return candidate
        suffix += 1

def auto_save_blog_content_silent(car_type: str = "") -> str:
    """Cursor AI 생성 후 차종+날짜 파일명으로 txt 저장합니다."""
    global current_selected_file

    file_name = _make_car_type_filename(car_type or "blog")

    title1, content1, title2, content2, title3, content3 = get_title_and_content_values()
    save_text = combine_blog_file_content(title1, content1, title2, content2, title3, content3)
    full_path = os.path.join(get_txt_folder(), file_name)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(save_text)

    current_selected_file = file_name
    load_txt_files()
    keep_listbox_selection()
    set_status(f"[{file_name}] Cursor AI 저장 완료")
    return file_name

def create_txt_file():
    global current_selected_file

    new_name = simpledialog.askstring("새 파일", "파일명 입력 (확장자 제외):")
    if not new_name:
        return

    new_name = new_name.strip()
    if not new_name:
        messagebox.showwarning("알림", "파일명을 입력하세요.")
        return

    full_name = f"{new_name}.txt"
    full_path = os.path.join(get_txt_folder(), full_name)

    if os.path.isfile(resolve_txt_path(full_name)):
        messagebox.showerror("오류", "이미 존재하는 파일명입니다.")
        return

    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write("")
        current_selected_file = full_name
        load_txt_files()
        on_select_txt()
        set_status(f"새 파일 생성: {full_name}")
    except Exception as e:
        messagebox.showerror("오류", f"파일 생성 실패: {e}")

def rename_txt_file():
    global current_selected_file

    file_name = current_selected_file
    if not file_name:
        selected = listbox.curselection()
        if selected:
            file_name = listbox.get(selected[0])

    if not file_name:
        messagebox.showwarning("알림", "이름을 변경할 파일을 선택하세요.")
        return

    old_name = file_name
    default_name = old_name[:-4] if old_name.lower().endswith(".txt") else old_name

    new_name = simpledialog.askstring("이름 변경", "새 이름:", initialvalue=default_name)
    if not new_name:
        return

    new_name = new_name.strip()
    if not new_name:
        messagebox.showwarning("알림", "새 이름을 입력하세요.")
        return

    new_full_name = f"{new_name}.txt"
    old_full_path = resolve_txt_path(old_name)
    new_full_path = os.path.join(get_txt_folder(), new_full_name)

    if os.path.isfile(new_full_path) and new_full_name != old_name:
        messagebox.showerror("오류", "이미 존재하는 파일명입니다.")
        return

    try:
        os.rename(old_full_path, new_full_path)
        current_selected_file = new_full_name
        load_txt_files()
        on_select_txt()
        set_status("파일명 변경 완료")
    except Exception as e:
        messagebox.showerror("오류", f"이름 변경 실패: {e}")

def on_select_txt(event=None):
    global current_selected_file

    selected = listbox.curselection()
    if not selected:
        if current_selected_file:
            keep_listbox_selection()
        return

    file_name = listbox.get(selected[0])
    current_selected_file = file_name

    try:
        full_path = resolve_txt_path(file_name)
        if not os.path.isfile(full_path):
            messagebox.showerror("오류", f"파일을 찾을 수 없습니다:\n{file_name}")
            return

        with open(full_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        title1, body1, title2, body2, title3, body3 = split_blog_file_content(raw_text)

        title_var_1.set(title1)
        editor_1.delete("1.0", tk.END)
        editor_1.insert("1.0", body1)

        title_var_2.set(title2)
        editor_2.delete("1.0", tk.END)
        editor_2.insert("1.0", body2)

        title_var_3.set(title3)
        editor_3.delete("1.0", tk.END)
        editor_3.insert("1.0", body3)

        set_status(f"선택됨: {file_name}")
        keep_listbox_selection()
    except Exception as e:
        messagebox.showerror("오류", f"파일 열기 실패: {e}")

def on_listbox_focus_out(event=None):
    root.after(10, keep_listbox_selection)

def get_phone_number(blog_index: int) -> str:
    if blog_index == 2:
        value = phone_number_var_2.get().strip()
    elif blog_index == 3:
        value = phone_number_var_3.get().strip()
    else:
        value = phone_number_var_1.get().strip()
    return value or DEFAULT_PHONE_NUMBER

def get_tel_link(blog_index: int) -> str:
    return f"TEL:{get_phone_number(blog_index)}"

def select_recent_typed_text(char_count: int) -> None:
    if char_count <= 0:
        return

    activate_browser_window()
    time.sleep(0.5)

    with kb_controller.pressed(Key.shift):
        for _ in range(char_count):
            if stop_flag:
                break
            kb_controller.press(Key.left)
            kb_controller.release(Key.left)
            time.sleep(0.08)

    time.sleep(0.2)

def run_post_estimate_location_action(blog_index: int = 1) -> None:
    set_status("견적상담하기 후 지도/주소 작업 중...")

    pyautogui.press("enter", presses=2, interval=0.15)
    time.sleep(0.3)

    if not click_image_forever(MAP_TEMPLATE, confidence=0.85):
        raise RuntimeError("map.png 이미지를 찾지 못했습니다.")

    time.sleep(0.2)
    paste_text_safely("자동차로 53")
    time.sleep(0.4)
    pyautogui.press("enter")
    time.sleep(0.4)

    if blog_index == 3:
        avicle_template = AVICLE_EDGE_TEMPLATE
        avicle_name = "avicle_edge.png"
        avicle_confidence = 0.80
    else:
        avicle_template = AVICLE_TEMPLATE
        avicle_name = "avicle.png"
        avicle_confidence = 0.85

    if not click_image_forever(avicle_template, confidence=avicle_confidence):
        raise RuntimeError(f"{avicle_name} 이미지를 찾지 못했습니다.")

    if not click_image_forever(ADD_TEMPLATE, confidence=0.85):
        raise RuntimeError("add.png 이미지를 찾지 못했습니다.")

    if not click_image_forever(CHECK_TEMPLATE, confidence=0.85):
        raise RuntimeError("check.png 이미지를 찾지 못했습니다.")

    time.sleep(0.2)
    pyautogui.press("enter", presses=2, interval=0.15)
    time.sleep(0.3)

def run_estimate_link_action(blog_index: int = 1) -> None:
    set_status("견적상담하기 링크 작업 중...")

    select_recent_typed_text(len(SPECIAL_LINK_TEXT))

    if not click_image_forever(RINK_TEMPLATE, confidence=0.85):
        raise RuntimeError("rink.png 이미지를 찾지 못했습니다.")

    if not click_image_forever(URL_TEMPLATE, confidence=0.85):
        raise RuntimeError("url.png 이미지를 찾지 못했습니다.")

    time.sleep(0.2)
    pyperclip.copy(get_tel_link(blog_index))
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.15)
    pyautogui.press("enter")
    time.sleep(0.15)
    pyautogui.press("right")
    time.sleep(0.2)

    run_post_estimate_location_action(blog_index)

def extract_quote_text(block_text: str) -> str:
    value = block_text.strip()
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        value = value[1:-1].strip()
    return value

def run_quote_block_action(quote_text: str) -> None:
    set_status("인용구 입력 작업 중...")

    if not click_image_forever(QUOTE_TEMPLATE, confidence=0.85):
        raise RuntimeError("66.PNG 이미지를 찾지 못했습니다.")

    time.sleep(0.2)
    paste_text_safely(quote_text)
    time.sleep(0.2)
    pyautogui.press("down", presses=2)
    time.sleep(0.2)

def human_like_typing(text: str, blog_index: int = 1):
    global stop_flag

    if not text:
        return

    cpm = speed_scale.get()
    delay = 60 / cpm
    error_rate = 0.02
    typo_chars = "asdfghjklqwertyuiop"

    index = 0
    text_length = len(text)
    chars_since_focus_check = 0
    focus_check_interval = 80

    while index < text_length:
        if stop_flag:
            break

        chars_since_focus_check += 1
        if chars_since_focus_check >= focus_check_interval:
            activate_browser_window()
            time.sleep(0.15)
            chars_since_focus_check = 0

        if text.startswith(SPECIAL_LINK_TEXT, index):
            for special_char in SPECIAL_LINK_TEXT:
                pyperclip.copy(special_char)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(delay * random.uniform(0.8, 1.2))

            run_estimate_link_action(blog_index)
            index += len(SPECIAL_LINK_TEXT)
            continue

        if text.startswith(QUOTE_MARKER, index):
            quote_start = index + len(QUOTE_MARKER)
            quote_end = text.find(QUOTE_MARKER, quote_start)

            if quote_end != -1:
                quote_raw = text[quote_start:quote_end]
                quote_text = extract_quote_text(quote_raw)

                if quote_text:
                    run_quote_block_action(quote_text)
                    index = quote_end + len(QUOTE_MARKER)
                    while index < text_length and text[index] in "\r\n":
                        index += 1
                    continue

        char = text[index]

        if char == "\n":
            pyautogui.press("enter")
            time.sleep(delay * 2)
            index += 1
            continue

        if char == " ":
            pyautogui.press("space")
            time.sleep(delay * 0.5)
            index += 1
            continue

        if char.isalnum() and random.random() < error_rate:
            wrong = random.choice(typo_chars)
            pyperclip.copy(wrong)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(delay * 1.5)
            pyautogui.press("backspace")
            time.sleep(delay * 0.7)

        pyperclip.copy(char)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(delay * random.uniform(0.8, 1.2))
        index += 1

# ---------------- Win32 브라우저 창 제어 ----------------
def win32_is_valid_hwnd(hwnd) -> bool:
    try:
        return bool(hwnd) and bool(user32.IsWindow(hwnd))
    except Exception:
        return False

def win32_get_process_exe_name(pid: int) -> str:
    if pid <= 0:
        return ""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(512)
        size = ctypes.c_uint(len(buffer))
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return os.path.basename(buffer.value).lower()
    except Exception:
        pass
    finally:
        kernel32.CloseHandle(handle)
    return ""

def win32_get_window_rect(hwnd):
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return rect

def win32_get_window_area(hwnd) -> int:
    rect = win32_get_window_rect(hwnd)
    if rect is None:
        return 0
    return max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)

def win32_minimize_hwnd(hwnd) -> None:
    if not win32_is_valid_hwnd(hwnd):
        return
    try:
        user32.ShowWindow(hwnd, SW_MINIMIZE)
        time.sleep(0.1)
    except Exception:
        pass


def minimize_other_browser_windows(keep_hwnd, browser_kind: str = "chrome") -> None:
    """이전 블로그 창이 포커스를 빼앗지 않도록 다른 브라우저 창을 최소화합니다."""
    for hwnd in get_browser_hwnds(browser_kind):
        if hwnd != keep_hwnd:
            win32_minimize_hwnd(hwnd)


def win32_is_maximized(hwnd) -> bool:
    try:
        return bool(user32.IsZoomed(hwnd))
    except Exception:
        return False


def win32_set_window_geometry(hwnd, x: int, y: int, width: int, height: int) -> bool:
    if not win32_is_valid_hwnd(hwnd):
        return False
    try:
        if user32.IsIconic(hwnd) or win32_is_maximized(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.15)
        user32.ShowWindow(hwnd, SW_NORMAL)
        time.sleep(0.05)
        ok = bool(user32.MoveWindow(hwnd, x, y, width, height, True))
        time.sleep(0.1)
        if win32_is_maximized(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.1)
            user32.ShowWindow(hwnd, SW_NORMAL)
            time.sleep(0.05)
            ok = bool(user32.MoveWindow(hwnd, x, y, width, height, True))
        return ok
    except Exception:
        return False


def win32_ensure_browser_geometry(hwnd, retries: int = 4) -> bool:
    """Edge 등 최대화로 열리는 브라우저를 837x1037 고정 크기로 맞춥니다."""
    for attempt in range(retries):
        if stop_flag:
            return False
        win32_force_foreground(hwnd)
        win32_set_window_geometry(hwnd, WIN_X, WIN_Y, WIN_W, WIN_H)
        time.sleep(0.2 + attempt * 0.1)
        rect = win32_get_window_rect(hwnd)
        if rect is None:
            continue
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        if not win32_is_maximized(hwnd) and abs(width - WIN_W) <= 80 and abs(height - WIN_H) <= 80:
            return True
    return win32_set_window_geometry(hwnd, WIN_X, WIN_Y, WIN_W, WIN_H)

def win32_force_foreground(hwnd) -> bool:
    if not win32_is_valid_hwnd(hwnd):
        return False
    try:
        if user32.IsIconic(hwnd) or win32_is_maximized(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.1)

        try:
            user32.AllowSetForegroundWindow(ASFW_ANY)
        except Exception:
            pass

        foreground_hwnd = user32.GetForegroundWindow()
        if foreground_hwnd == hwnd:
            return True

        foreground_thread = user32.GetWindowThreadProcessId(foreground_hwnd, None)
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)
        attached = False

        if foreground_thread and target_thread and foreground_thread != target_thread:
            attached = bool(user32.AttachThreadInput(foreground_thread, target_thread, True))

        user32.BringWindowToTop(hwnd)
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)

        if attached:
            user32.AttachThreadInput(foreground_thread, target_thread, False)

        time.sleep(0.15)
        return user32.GetForegroundWindow() == hwnd
    except Exception:
        return False

def win32_activate_browser_hwnd(hwnd, adjust_geometry: bool = True) -> bool:
    if not win32_is_valid_hwnd(hwnd):
        return False
    if adjust_geometry:
        win32_ensure_browser_geometry(hwnd)
    return win32_force_foreground(hwnd)

def get_browser_hwnds(browser_kind: str = "chrome") -> set:
    process_name = BROWSER_PROCESS_NAMES.get(browser_kind, BROWSER_PROCESS_NAMES["chrome"])
    hwnds = set()

    def _callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if win32_get_window_area(hwnd) < 120000:
            return True

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if win32_get_process_exe_name(pid.value) == process_name:
            hwnds.add(hwnd)
        return True

    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(_callback)
    user32.EnumWindows(enum_proc, 0)
    return hwnds

def pick_largest_browser_hwnd(hwnds) -> Optional[int]:
    best_hwnd = None
    best_area = 0
    for hwnd in hwnds:
        area = win32_get_window_area(hwnd)
        if area > best_area:
            best_area = area
            best_hwnd = hwnd
    return best_hwnd

def wait_for_new_browser_hwnd(browser_kind: str, before_hwnds: set, timeout_sec: float = 12.0) -> Optional[int]:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if stop_flag:
            return None

        new_hwnds = get_browser_hwnds(browser_kind) - before_hwnds
        if new_hwnds:
            return pick_largest_browser_hwnd(new_hwnds)

        time.sleep(0.2)

    current_hwnds = get_browser_hwnds(browser_kind) - before_hwnds
    if current_hwnds:
        return pick_largest_browser_hwnd(current_hwnds)

    all_hwnds = get_browser_hwnds(browser_kind)
    return pick_largest_browser_hwnd(all_hwnds)

# ---------------- 사전 실행 자동화 함수 ----------------
def find_chrome() -> Optional[str]:
    for path in CHROME_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None

def find_edge() -> Optional[str]:
    for path in EDGE_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None

def find_browser(browser_kind: str) -> Optional[str]:
    if browser_kind == "edge":
        return find_edge()
    return find_chrome()

def force_browser_window_geometry(window) -> None:
    hwnd = getattr(window, "_hWnd", None)
    if win32_activate_browser_hwnd(hwnd, adjust_geometry=True):
        return
    try:
        window.moveTo(WIN_X, WIN_Y)
        time.sleep(0.05)
        window.resizeTo(WIN_W, WIN_H)
        time.sleep(0.1)
    except Exception:
        pass

def _window_matches_browser_kind(window, browser_kind: str) -> bool:
    title = (getattr(window, "title", "") or "").lower()
    if "edge" in title or "microsoft edge" in title:
        return browser_kind == "edge"
    if "chrome" in title and "edge" not in title:
        return browser_kind == "chrome"
    return False

def get_browser_windows(browser_kind: str = "chrome"):
    seen = set()
    windows = []

    if preferred_browser_hwnd is not None and win32_is_valid_hwnd(preferred_browser_hwnd):
        for w in gw.getAllWindows():
            hwnd = getattr(w, "_hWnd", None)
            if hwnd == preferred_browser_hwnd:
                return [w]

    title_fragments = BROWSER_TITLE_FRAGMENTS.get(browser_kind, BROWSER_TITLE_FRAGMENTS["chrome"])
    for title_fragment in title_fragments:
        for w in gw.getWindowsWithTitle(title_fragment):
            hwnd = getattr(w, "_hWnd", None)
            if hwnd in seen:
                continue

            if _window_matches_browser_kind(w, browser_kind):
                seen.add(hwnd)
                windows.append(w)
            elif (
                preferred_browser_kind == browser_kind
                and preferred_browser_hwnd is not None
                and hwnd == preferred_browser_hwnd
            ):
                seen.add(hwnd)
                windows.append(w)

    if not windows:
        for hwnd in get_browser_hwnds(browser_kind):
            if preferred_browser_hwnd is not None and hwnd != preferred_browser_hwnd:
                continue
            for w in gw.getAllWindows():
                if getattr(w, "_hWnd", None) == hwnd:
                    windows.append(w)
                    break
    return windows

def get_chrome_windows():
    return get_browser_windows("chrome")

def get_edge_windows():
    return get_browser_windows("edge")

def activate_specific_browser_window(window, adjust_geometry: bool = False) -> bool:
    if window is None:
        return False

    hwnd = getattr(window, "_hWnd", None)
    if win32_activate_browser_hwnd(hwnd, adjust_geometry=True):
        return True

    try:
        if window.isMinimized:
            window.restore()
            time.sleep(0.15)
        if adjust_geometry:
            force_browser_window_geometry(window)
            time.sleep(0.1)
        window.activate()
        time.sleep(0.2)
        return True
    except Exception:
        return False

def activate_specific_chrome_window(window, adjust_geometry: bool = False) -> bool:
    return activate_specific_browser_window(window, adjust_geometry=adjust_geometry)

def activate_browser_window(adjust_geometry: bool = False) -> bool:
    global preferred_browser_hwnd, preferred_browser_kind

    if preferred_browser_hwnd is not None and win32_is_valid_hwnd(preferred_browser_hwnd):
        if win32_activate_browser_hwnd(preferred_browser_hwnd, adjust_geometry=True):
            return True

    browser_kind = preferred_browser_kind or "chrome"
    browser_windows = get_browser_windows(browser_kind)

    if preferred_browser_hwnd is not None:
        for w in browser_windows:
            if getattr(w, "_hWnd", None) == preferred_browser_hwnd:
                if activate_specific_browser_window(w, adjust_geometry=adjust_geometry):
                    return True

    for w in browser_windows:
        if activate_specific_browser_window(w, adjust_geometry=adjust_geometry):
            return True
    return False

def get_search_region():
    return (WIN_X, WIN_Y, WIN_W, WIN_H)

def locate_image_forever(template_path: str, confidence: float = DEFAULT_CONFIDENCE):
    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"템플릿 이미지가 없습니다: {template_path}")

    region = get_search_region()

    while True:
        if stop_flag:
            return None

        activate_browser_window()

        try:
            loc = pyautogui.locateOnScreen(
                template_path,
                confidence=confidence,
                region=region,
            )
        except pyautogui.ImageNotFoundException:
            loc = None
        except Exception:
            loc = None

        if loc is not None:
            return loc

        time.sleep(SEARCH_INTERVAL)

def locate_image_once(template_path: str, confidence: float = DEFAULT_CONFIDENCE):
    if stop_flag:
        return None

    if not os.path.isfile(template_path):
        return None

    activate_browser_window()

    try:
        return pyautogui.locateOnScreen(
            template_path,
            confidence=confidence,
            region=get_search_region(),
        )
    except pyautogui.ImageNotFoundException:
        return None
    except Exception:
        return None

def click_image_forever(template_path: str, confidence: float = DEFAULT_CONFIDENCE) -> bool:
    loc = locate_image_forever(template_path, confidence=confidence)
    if loc is None:
        return False
    cx, cy = pyautogui.center(loc)
    pyautogui.click(cx, cy)
    time.sleep(0.2)
    return True

def click_image_limited(template_path: str, attempts: int = 2, confidence: float = DEFAULT_CONFIDENCE, delay_sec: float = 0.35) -> bool:
    if not os.path.isfile(template_path):
        return False

    for _ in range(attempts):
        if stop_flag:
            return False

        loc = locate_image_once(template_path, confidence=confidence)
        if loc is not None:
            cx, cy = pyautogui.center(loc)
            pyautogui.click(cx, cy)
            time.sleep(0.2)
            return True

        time.sleep(delay_sec)

    return False

def scroll_horizontal_to_right() -> None:
    activate_browser_window()
    if preferred_browser_hwnd is not None and win32_is_valid_hwnd(preferred_browser_hwnd):
        win32_ensure_browser_geometry(preferred_browser_hwnd)

    try:
        original_x, original_y = pyautogui.position()
    except Exception:
        original_x, original_y = None, None

    target_x = WIN_X + max(120, WIN_W - 220)
    target_y = WIN_Y + max(180, min(320, WIN_H // 3))

    try:
        pyautogui.moveTo(target_x, target_y, duration=0.03)
    except Exception:
        pass

    pyautogui.keyDown("shift")
    try:
        for _ in range(18):
            if stop_flag:
                break
            pyautogui.scroll(-800)
    finally:
        pyautogui.keyUp("shift")

    if original_x is not None and original_y is not None:
        try:
            pyautogui.moveTo(original_x, original_y, duration=0.03)
        except Exception:
            pass

def click_login_template() -> bool:
    return click_image_forever(LOGIN_TEMPLATE, confidence=0.85)

def type_login_credentials(naver_id: str, naver_password: str) -> None:
    time.sleep(1.0)

    clear_current_input_field()
    paste_text_safely(naver_id)

    pyautogui.press("tab", presses=2)
    time.sleep(0.15)

    clear_current_input_field()
    paste_text_safely(naver_password)

    pyautogui.press("enter")

def click_emdfhr_after_login() -> bool:
    time.sleep(2.0)
    return click_image_limited(
        EMDFHR_TEMPLATE,
        attempts=3,
        confidence=0.85,
        delay_sec=0.5,
    )

def navigate_to_blog_write(blog_write_url: str) -> None:
    time.sleep(1.5)
    activate_browser_window()
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.05)
    paste_text_safely(blog_write_url)
    pyautogui.press("enter")

def try_cnlth_before_help_header() -> None:
    time.sleep(1.5)
    activate_browser_window()
    time.sleep(0.2)

    click_image_limited(CNLTH_TEMPLATE, attempts=2, confidence=0.85, delay_sec=0.4)

def dismiss_help_popup_or_arrow_up() -> None:
    time.sleep(1.0)
    activate_browser_window()
    time.sleep(0.2)

    if not os.path.isfile(HELP_HEADER_TEMPLATE):
        pyautogui.press("up")
        time.sleep(0.1)
        return

    region = get_search_region()
    found = None

    for _ in range(3):
        if stop_flag:
            return

        activate_browser_window()
        try:
            found = pyautogui.locateOnScreen(
                HELP_HEADER_TEMPLATE,
                confidence=0.85,
                region=region,
            )
        except pyautogui.ImageNotFoundException:
            found = None
        except Exception:
            found = None

        if found is not None:
            break

        time.sleep(SEARCH_INTERVAL)

    if found is not None:
        inset = max(22, min(40, found.width // 14))
        click_x = found.left + found.width - inset
        click_y = found.top + found.height // 2
        pyautogui.click(click_x, click_y)
        time.sleep(0.2)
    else:
        pyautogui.press("up")
        time.sleep(0.1)

def click_title_area_by_coordinate() -> None:
    """이미지 인식이 실패했을 때 제목 입력칸을 좌표로 클릭합니다."""
    activate_browser_window()
    time.sleep(0.15)
    pyautogui.click(TITLE_CLICK_X, TITLE_CLICK_Y)
    time.sleep(0.25)

def click_body_area_by_coordinate() -> None:
    """본문 입력칸을 좌표로 클릭합니다."""
    activate_browser_window()
    time.sleep(0.15)
    pyautogui.click(BODY_CLICK_X, BODY_CLICK_Y)
    time.sleep(0.25)

def center_align_title_only() -> None:
    """제목칸만 가운데 정렬합니다. 본문은 제목 입력 후에 처리합니다."""
    time.sleep(0.25)
    click_title_area_by_coordinate()
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "alt", "c")
    time.sleep(0.2)


def center_align_body_only() -> None:
    click_body_area_by_coordinate()
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "alt", "c")
    time.sleep(0.2)


def center_align_title_and_body() -> None:
    center_align_title_only()
    center_align_body_only()
    click_title_area_by_coordinate()
    time.sleep(0.2)


def ensure_title_field_ready(blog_index: int = 1, blog_label: str = "") -> None:
    """두 번째/세 번째 블로그에서 제목칸 포커스가 빗나가는 문제를 방지합니다."""
    if blog_label:
        set_status(f"{blog_label} 제목칸 포커스 확인 중...")

    activate_browser_window()
    time.sleep(0.25)

    ok = click_image_limited(SE_TEMPLATE, attempts=6, confidence=0.80, delay_sec=0.35)
    if not ok:
        click_title_area_by_coordinate()
        time.sleep(0.2)
        click_title_area_by_coordinate()
        time.sleep(0.2)

    if blog_index >= 2:
        time.sleep(0.35)
        click_title_area_by_coordinate()
        time.sleep(0.25)

    center_align_title_only()
    time.sleep(0.15)


def type_blog_title(title: str, blog_index: int = 1, blog_label: str = "") -> None:
    """제목은 한 번에 붙여넣기합니다. 긴 제목·연속 실행 시 한 글자씩 치면 포커스가 빠지는 문제를 방지합니다."""
    if not title:
        return

    ensure_title_field_ready(blog_index=blog_index, blog_label=blog_label)
    activate_browser_window()
    time.sleep(0.25)
    click_title_area_by_coordinate()
    time.sleep(0.2)
    clear_current_input_field()
    time.sleep(0.1)
    paste_text_safely(title)
    time.sleep(0.35)


def run_se_action(blog_label: str = "", blog_index: int = 1) -> bool:
    """
    제목 입력칸을 준비합니다.
    se.png를 무한정 기다리지 않고, 못 찾으면 좌표 클릭으로 넘어가게 해서
    두 번째 블로그에서 멈추는 문제를 방지합니다.
    """
    if blog_label:
        set_status(f"{blog_label} 제목칸 찾는 중...")

    ok = click_image_limited(
        SE_TEMPLATE,
        attempts=8,
        confidence=0.80,
        delay_sec=0.45,
    )

    if not ok:
        if blog_label:
            set_status(f"{blog_label} se.png 인식 실패, 좌표로 제목칸 클릭")
        click_title_area_by_coordinate()

    center_align_title_only()
    if blog_index >= 2:
        time.sleep(0.2)
        click_title_area_by_coordinate()
    return True

def run_pre_typing_action(
    naver_id: str,
    naver_password: str,
    blog_write_url: str,
    blog_label: str,
    use_incognito: bool = True,
    browser_kind: str = "chrome",
    blog_index: int = 1,
) -> None:
    global preferred_browser_hwnd, preferred_browser_kind

    browser_kind = browser_kind if browser_kind in ("chrome", "edge") else "chrome"
    preferred_browser_kind = browser_kind

    browser_exe = find_browser(browser_kind)
    if not browser_exe:
        browser_name = "Edge" if browser_kind == "edge" else "Chrome"
        raise RuntimeError(f"{browser_name} 설치 경로를 찾을 수 없습니다.")

    if not naver_id:
        raise RuntimeError(f"{blog_label} 네이버 아이디를 입력하세요.")
    if not naver_password:
        raise RuntimeError(f"{blog_label} 네이버 비밀번호를 입력하세요.")
    if not blog_write_url:
        raise RuntimeError(f"{blog_label} 블로그 글쓰기 주소를 입력하세요.")

    browser_label = "Edge" if browser_kind == "edge" else "크롬"
    before_hwnds = get_browser_hwnds(browser_kind)

    launch_cmd = [
        browser_exe,
        "--new-window",
        f"--window-size={WIN_W},{WIN_H}",
        f"--window-position={WIN_X},{WIN_Y}",
        "https://www.naver.com",
    ]
    if use_incognito:
        if browser_kind == "edge":
            launch_cmd.insert(1, "--inprivate")
            set_status(f"{blog_label} 사전 작업: InPrivate Edge 창 실행 중...")
        else:
            launch_cmd.insert(1, "--incognito")
            set_status(f"{blog_label} 사전 작업: 시크릿 크롬 창 실행 중...")
    else:
        set_status(f"{blog_label} 사전 작업: 일반 {browser_label} 창 실행 중...")

    subprocess.Popen(launch_cmd)
    time.sleep(2.5 if browser_kind == "edge" else 2.0)

    new_hwnd = wait_for_new_browser_hwnd(browser_kind, before_hwnds, timeout_sec=12.0)
    if new_hwnd is None:
        raise RuntimeError(f"{blog_label} 새 {browser_label} 창을 찾지 못했습니다.")

    preferred_browser_hwnd = new_hwnd

    if blog_index >= 2:
        minimize_other_browser_windows(preferred_browser_hwnd, browser_kind)
        if browser_kind == "edge":
            minimize_other_browser_windows(preferred_browser_hwnd, "chrome")

    set_status(f"{blog_label} 사전 작업: {browser_label} 창 활성화 중...")
    geometry_retries = 6 if browser_kind == "edge" else 4
    win32_ensure_browser_geometry(preferred_browser_hwnd, retries=geometry_retries)
    if not win32_activate_browser_hwnd(preferred_browser_hwnd, adjust_geometry=True):
        activate_browser_window()

    time.sleep(0.3)

    if browser_kind == "edge":
        set_status(f"{blog_label} 사전 작업: Edge 창 크기 재조정 중...")
        win32_ensure_browser_geometry(preferred_browser_hwnd, retries=6)
        time.sleep(0.25)

    if stop_flag:
        return

    set_status(f"{blog_label} 사전 작업: 화면 정렬 중...")
    scroll_horizontal_to_right()

    if stop_flag:
        return

    set_status(f"{blog_label} 사전 작업: 로그인 버튼 찾는 중...")
    if not click_login_template():
        return

    if stop_flag:
        return

    set_status(f"{blog_label} 사전 작업: 로그인 정보 입력 중...")
    type_login_credentials(naver_id, naver_password)

    if stop_flag:
        return

    set_status(f"{blog_label} 사전 작업: emdfhr 이미지 확인 중...")
    click_emdfhr_after_login()

    if stop_flag:
        return

    set_status(f"{blog_label} 사전 작업: 블로그 글쓰기 이동 중...")
    navigate_to_blog_write(blog_write_url)

    if stop_flag:
        return

    set_status(f"{blog_label} 사전 작업: cnlth 이미지 확인 중...")
    try_cnlth_before_help_header()

    if stop_flag:
        return

    set_status(f"{blog_label} 사전 작업: help_header / 커서 위치 정리 중...")
    dismiss_help_popup_or_arrow_up()

    if stop_flag:
        return

    set_status(f"{blog_label} 사전 작업: 제목칸 / 가운데 정렬 준비 중...")
    if not run_se_action(blog_label, blog_index=blog_index):
        return

    set_status(f"{blog_label} 사전 작업 완료")


def move_to_body_after_title(blog_index: int) -> None:
    pyautogui.press("enter")
    if blog_index == 1:
        time.sleep(1.2)
    else:
        time.sleep(1.8)

    # 엔터 후 포커스가 본문으로 안 내려가는 경우가 있어 본문 위치를 한 번 더 클릭합니다.
    click_body_area_by_coordinate()
    center_align_body_only()

def run_blog_typing_workflow(
    blog_label: str,
    blog_index: int,
    naver_id: str,
    naver_password: str,
    blog_write_url: str,
    title: str,
    content: str,
    use_incognito: bool = True,
    browser_kind: str = "chrome",
) -> None:
    run_pre_typing_action(
        naver_id,
        naver_password,
        blog_write_url,
        blog_label,
        use_incognito=use_incognito,
        browser_kind=browser_kind,
        blog_index=blog_index,
    )

    if stop_flag:
        return

    wait_sec = 1.5 if blog_index == 1 else 2.5
    time.sleep(wait_sec)

    set_status(f"{blog_label} 제목 입력 중...")
    type_blog_title(title, blog_index=blog_index, blog_label=blog_label)

    if stop_flag:
        return

    activate_browser_window()
    time.sleep(0.2)

    move_to_body_after_title(blog_index)

    if content:
        set_status(f"{blog_label} 본문 입력 중...")
        human_like_typing(content, blog_index=blog_index)

BLOG_RUN_PROFILES = {
    1: {
        "label": "블로그 1",
        "use_incognito": True,
        "browser_kind": "chrome",
        "complete_message": "블로그 1 테스트 완료",
    },
    2: {
        "label": "블로그 2",
        "use_incognito": False,
        "browser_kind": "chrome",
        "complete_message": "블로그 2 테스트 완료",
    },
    3: {
        "label": "블로그 3",
        "use_incognito": False,
        "browser_kind": "edge",
        "complete_message": "블로그 3 테스트 완료",
    },
}

def get_blog_account_values(blog_index: int):
    if blog_index == 1:
        return (
            naver_id_var_1.get().strip(),
            naver_password_var_1.get().strip(),
            blog_write_url_var_1.get().strip(),
        )
    if blog_index == 2:
        return (
            naver_id_var_2.get().strip(),
            naver_password_var_2.get().strip(),
            blog_write_url_var_2.get().strip(),
        )
    if blog_index == 3:
        return (
            naver_id_var_3.get().strip(),
            naver_password_var_3.get().strip(),
            blog_write_url_var_3.get().strip(),
        )
    raise ValueError(f"지원하지 않는 블로그 번호: {blog_index}")

def validate_blog_content(blog_index: int):
    title1, content1, title2, content2, title3, content3 = get_title_and_content_values()
    titles = {1: title1, 2: title2, 3: title3}
    contents = {1: content1, 2: content2, 3: content3}
    title = titles.get(blog_index, "").strip() if blog_index in titles else ""
    content = contents.get(blog_index, "").rstrip() if blog_index in contents else ""
    order_label = {1: "첫번째", 2: "두번째", 3: "세번째"}.get(blog_index, f"{blog_index}번째")

    if not title and not content:
        messagebox.showwarning("경고", f"{order_label} 블로그 제목 또는 내용을 입력하세요.")
        return None, None
    if not title:
        messagebox.showwarning("경고", f"{order_label} 블로그 제목을 입력하세요.")
        return None, None
    return title, content

def _run_automation_in_thread(workflow_callable, complete_message: str, start_message: str = "3초 후 시작 (입력창 클릭 준비)...") -> bool:
    global running, stop_flag

    if running:
        messagebox.showwarning("알림", "이미 작업이 실행 중입니다.")
        return False

    running = True
    stop_flag = False

    def task():
        global running

        set_status(start_message)
        time.sleep(3)

        try:
            if stop_flag:
                set_status("작업 중지됨")
                return

            workflow_callable()

            if stop_flag:
                set_status("작업 중지됨")
            else:
                set_status(complete_message)
        except Exception as e:
            set_status("오류 발생")
            root.after(0, lambda: messagebox.showerror("오류", f"자동 실행 중 오류 발생:\n{e}"))
        finally:
            running = False

    threading.Thread(target=task, daemon=True).start()
    return True

def start_blog_test(blog_index: int):
    profile = BLOG_RUN_PROFILES.get(blog_index)
    if profile is None:
        messagebox.showerror("오류", f"지원하지 않는 블로그 번호: {blog_index}")
        return

    title, content = validate_blog_content(blog_index)
    if title is None:
        return

    naver_id, naver_password, blog_write_url = get_blog_account_values(blog_index)
    blog_label = profile["label"]

    def workflow():
        run_blog_typing_workflow(
            blog_label,
            blog_index,
            naver_id,
            naver_password,
            blog_write_url,
            title,
            content,
            use_incognito=profile["use_incognito"],
            browser_kind=profile["browser_kind"],
        )

    _run_automation_in_thread(
        workflow,
        complete_message=profile["complete_message"],
        start_message=f"{blog_label} 테스트: 3초 후 시작...",
    )

def start_typing():
    global running, stop_flag

    if running:
        return

    title1, content1, title2, content2, title3, content3 = get_title_and_content_values()
    blog_mode = int(blog_run_mode_var.get())

    if not title1 and not content1:
        messagebox.showwarning("경고", "첫번째 블로그 제목 또는 내용을 입력하세요.")
        return

    if not title1:
        messagebox.showwarning("경고", "첫번째 블로그 제목을 입력하세요.")
        return

    if blog_mode >= 2:
        if not title2 and not content2:
            messagebox.showwarning("경고", "두번째 블로그 쓰기를 선택했으면 두번째 제목 또는 내용을 입력하세요.")
            return
        if not title2:
            messagebox.showwarning("경고", "두번째 블로그 제목을 입력하세요.")
            return

    if blog_mode == 3:
        if not title3 and not content3:
            messagebox.showwarning("경고", "세번째 블로그 쓰기를 선택했으면 세번째 제목 또는 내용을 입력하세요.")
            return
        if not title3:
            messagebox.showwarning("경고", "세번째 블로그 제목을 입력하세요.")
            return

    running = True
    stop_flag = False

    def task():
        global running

        set_status("3초 후 시작 (입력창 클릭 준비)...")
        time.sleep(3)

        try:
            if stop_flag:
                set_status("작업 중지됨")
                return

            run_blog_typing_workflow(
                "블로그 1",
                1,
                naver_id_var_1.get().strip(),
                naver_password_var_1.get().strip(),
                blog_write_url_var_1.get().strip(),
                title1,
                content1,
                use_incognito=True,
            )

            if stop_flag:
                set_status("작업 중지됨")
                return

            if blog_mode >= 2:
                set_status("블로그 1 완료, 블로그 2 일반 크롬 새 창 준비 중...")

                if stop_flag:
                    set_status("작업 중지됨")
                    return

                time.sleep(3.0)

                run_blog_typing_workflow(
                    "블로그 2",
                    2,
                    naver_id_var_2.get().strip(),
                    naver_password_var_2.get().strip(),
                    blog_write_url_var_2.get().strip(),
                    title2,
                    content2,
                    use_incognito=False,
                    browser_kind="chrome",
                )

            if stop_flag:
                set_status("작업 중지됨")
                return

            if blog_mode == 3:
                set_status("블로그 2 완료, 블로그 3 Edge 새 창 준비 중...")

                if stop_flag:
                    set_status("작업 중지됨")
                    return

                time.sleep(3.0)

                run_blog_typing_workflow(
                    "블로그 3",
                    3,
                    naver_id_var_3.get().strip(),
                    naver_password_var_3.get().strip(),
                    blog_write_url_var_3.get().strip(),
                    title3,
                    content3,
                    use_incognito=False,
                    browser_kind="edge",
                )

            if stop_flag:
                set_status("작업 중지됨")
            else:
                if blog_mode == 3:
                    set_status("블로그 1, 2, 3 사전 작업 + 타이핑 완료")
                elif blog_mode == 2:
                    set_status("블로그 1, 2 사전 작업 + 타이핑 완료")
                else:
                    set_status("블로그 1 사전 작업 + 타이핑 완료")

        except Exception as e:
            set_status("오류 발생")
            root.after(0, lambda: messagebox.showerror("오류", f"자동 실행 중 오류 발생:\n{e}"))
        finally:
            running = False

    threading.Thread(target=task, daemon=True).start()

# ---------------- [탭 2] 블로그 프롬프트 ----------------
def get_cursor_api_key() -> str:
    for name in ("CURSOR_API_KEY", "CURSOR_AI_API_KEY", "CURSOR_API"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""

def build_blog_ai_prompt(template_index: int, script: str) -> str:
    return prompt_templates[template_index].format(script=script)

def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text

    lines = text.split("\n")
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()

def _extract_fenced_codeblocks(text: str) -> list[str]:
    blocks = []
    seen = set()
    patterns = (
        r"```(?:[\w-]+)?\s*\n(.*?)```",
        r"```(?:[\w-]+)?\s*(.*?)```",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.DOTALL):
            content = match.group(1).strip()
            if content and content not in seen:
                seen.add(content)
                blocks.append(content)
    return blocks

BLOG_POST_LABEL_RE = re.compile(
    r"(?:\*\*)?\s*Blog\s*Post\s*(\d+)\s*(Title|Body)\s*[:：]?\s*(?:\*\*)?",
    flags=re.IGNORECASE,
)

def _normalize_section_content(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""

    blocks = _extract_fenced_codeblocks(raw)
    if blocks:
        if len(blocks) == 1:
            return blocks[0]
        return "\n".join(blocks).strip()

    if raw.startswith("```"):
        return _strip_markdown_fence(raw)
    return raw

def _posts_from_blog_post_labels(text: str) -> list[tuple[str, str]]:
    """Blog Post 1 Title / Body 라벨 기준으로 구간을 잘라냅니다."""
    matches = list(BLOG_POST_LABEL_RE.finditer(text))
    if not matches:
        return []

    sections: dict[int, dict[str, str]] = {
        1: {"title": "", "body": ""},
        2: {"title": "", "body": ""},
        3: {"title": "", "body": ""},
    }

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = _normalize_section_content(text[start:end])
        post_num = int(match.group(1))
        field = match.group(2).lower()
        if post_num in sections and field in ("title", "body"):
            sections[post_num][field] = content

    posts = []
    for post_num in (1, 2, 3):
        title = sections[post_num]["title"].strip()
        body = sections[post_num]["body"].strip()
        if title:
            posts.append((title, body))
    return posts

def _posts_from_blog_post_codeblocks(text: str) -> list[tuple[str, str]]:
    """A-VICLE 프롬프트 형식: Blog Post N Title/Body + 6개 마크다운 코드블록."""
    label_posts = _posts_from_blog_post_labels(text)
    if label_posts:
        return label_posts

    blocks = _extract_fenced_codeblocks(text)
    if len(blocks) >= 6:
        return [(blocks[0], blocks[1]), (blocks[2], blocks[3]), (blocks[4], blocks[5])]
    if len(blocks) >= 4:
        return [(blocks[0], blocks[1]), (blocks[2], blocks[3])]
    if len(blocks) >= 2:
        return [(blocks[0], blocks[1])]

    return []

def _save_cursor_debug_response(text: str) -> str:
    os.makedirs(get_output_dir(), exist_ok=True)
    debug_path = os.path.join(get_output_dir(), "cursor_ai_last_response.txt")
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write(text)
    return debug_path

def _posts_from_storage_markers(text: str) -> list[tuple[str, str]]:
    title1, body1, title2, body2, title3, body3 = split_blog_file_content(text)
    return [
        (title1.strip(), body1.strip()),
        (title2.strip(), body2.strip()),
        (title3.strip(), body3.strip()),
    ]

def _append_post(posts: list[tuple[str, str]], title: str, body: str):
    title = title.strip()
    body = body.strip()
    if title:
        posts.append((title, body))

def _posts_from_section_split(text: str) -> list[tuple[str, str]]:
    parts = re.split(
        r"\n(?:={3,}|-{3,}|━{3,}|#{3,}\s*(?:원고|글|POST|Blog)\s*[123]\s*#{0,3}|"
        r"(?:원고|글)\s*[123]\s*[:：]|\[(?:원고|글)\s*[123]\]|POST\s*[123]\s*[:：]?|Blog\s*[123]\s*[:：]?|"
        r"(?:첫|두|세)\s*번째\s*(?:원고|글)?\s*[:：]?)\s*\n",
        text,
        flags=re.IGNORECASE,
    )

    posts = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        title, body = split_legacy_title_and_body(part)
        _append_post(posts, title, body)
    return posts

def _posts_from_labeled_title_body(text: str) -> list[tuple[str, str]]:
    chunks = re.split(r"\n(?=(?:제목|TITLE)\s*[:：])", text, flags=re.IGNORECASE)
    posts = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        match = re.match(
            r"^(?:제목|TITLE)\s*[:：]\s*(.+?)(?:\n(?:본문|내용|BODY|Body)\s*[:：]\s*)?\n([\s\S]*)$",
            chunk,
            flags=re.IGNORECASE,
        )
        if match:
            _append_post(posts, match.group(1), match.group(2))
            continue

        lines = chunk.split("\n")
        if re.match(r"^(?:제목|TITLE)\s*[:：]", lines[0], flags=re.IGNORECASE):
            title = re.sub(r"^(?:제목|TITLE)\s*[:：]\s*", "", lines[0], flags=re.IGNORECASE).strip()
            body = "\n".join(lines[1:]).strip()
            _append_post(posts, title, body)

    return posts

def _posts_from_heading_blocks(text: str) -> list[tuple[str, str]]:
    parts = re.split(
        r"\n(?=(?:\[|\【)?(?:원고|글|POST|Blog)\s*\d+[^\n]*(?:\]|\】)?\s*\n|"
        r"(?:\[|\【)?(?:첫|두|세)\s*번째[^\n]*(?:\]|\】)?\s*\n)",
        text,
        flags=re.IGNORECASE,
    )

    posts = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        title, body = split_legacy_title_and_body(part)
        _append_post(posts, title, body)
    return posts

def _posts_from_blank_line_blocks(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"\n{3,}", text.strip())
    posts = []

    for part in parts:
        part = part.strip()
        if not part:
            continue
        title, body = split_legacy_title_and_body(part)
        if title and len(title) <= 150:
            _append_post(posts, title, body)

    return posts

def _choose_best_posts(text: str, expected_count: int) -> list[tuple[str, str]]:
    codeblock_posts = [post for post in _posts_from_blog_post_codeblocks(text) if post[0].strip()]
    if len(codeblock_posts) >= expected_count:
        return codeblock_posts[:expected_count]

    strategies = (
        _posts_from_storage_markers,
        _posts_from_labeled_title_body,
        _posts_from_section_split,
        _posts_from_heading_blocks,
        _posts_from_blank_line_blocks,
    )

    best_posts: list[tuple[str, str]] = codeblock_posts
    for strategy in strategies:
        posts = [post for post in strategy(text) if post[0].strip()]
        if len(posts) > len(best_posts):
            best_posts = posts
        if len(posts) >= expected_count:
            return posts[:expected_count]

    if expected_count == 1 and not best_posts:
        title, body = split_legacy_title_and_body(text)
        if title.strip():
            return [(title.strip(), body.strip())]

    return best_posts

def parse_blog_posts(text: str, expected_count: int) -> list[tuple[str, str]]:
    candidates = []
    for candidate in (text.strip(), _strip_markdown_fence(text.strip())):
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    posts: list[tuple[str, str]] = []
    for candidate in candidates:
        parsed = _choose_best_posts(candidate, expected_count)
        if len(parsed) > len(posts):
            posts = parsed
        if len(parsed) >= expected_count:
            posts = parsed
            break

    result = []
    for index in range(expected_count):
        if index >= len(posts):
            debug_path = _save_cursor_debug_response(text)
            raise ValueError(
                f"블로그 {index + 1} 원고를 추출하지 못했습니다. (응답에서 {len(posts)}개만 인식됨)\n\n"
                "AI 응답 전문이 아래 파일에 저장되었습니다:\n"
                f"{debug_path}\n\n"
                "프롬프트 Output Format대로 아래 라벨이 있어야 합니다:\n"
                "Blog Post 1 Title / Body, Blog Post 2 Title / Body, Blog Post 3 Title / Body"
            )
        title, body = posts[index]
        if not title:
            debug_path = _save_cursor_debug_response(text)
            raise ValueError(
                f"블로그 {index + 1} 제목을 추출하지 못했습니다.\n\n"
                f"AI 응답 전문: {debug_path}"
            )
        result.append((title, body))
    return result

def _cursor_api_auth_header(api_key: str) -> str:
    token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    return f"Basic {token}"

def _cursor_api_request(
    method: str,
    path: str,
    api_key: str,
    body: dict | None = None,
    timeout: int = 120,
) -> dict:
    url = f"{CURSOR_API_BASE_URL}{path}"
    headers = {
        "Authorization": _cursor_api_auth_header(api_key),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=payload, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError(f"Cursor API 오류 ({e.code}): {detail or e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Cursor API 연결 실패: {e.reason}") from e

def _fetch_run_stream_text(agent_id: str, run_id: str, api_key: str) -> str:
    """run.result가 요약만 줄 때 stream의 assistant 전문을 수집합니다."""
    url = f"{CURSOR_API_BASE_URL}/agents/{agent_id}/runs/{run_id}/stream"
    headers = {
        "Authorization": _cursor_api_auth_header(api_key),
        "Accept": "text/event-stream",
    }
    request = urllib.request.Request(url, headers=headers, method="GET")

    assistant_chunks: list[str] = []
    result_text = ""
    event_type = ""

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    continue
                if not line.startswith("data:"):
                    continue

                payload_raw = line.split(":", 1)[1].strip()
                if not payload_raw:
                    continue

                try:
                    payload = json.loads(payload_raw)
                except json.JSONDecodeError:
                    continue

                if not isinstance(payload, dict):
                    continue

                if event_type == "assistant":
                    assistant_chunks.append(str(payload.get("text", "")))
                elif event_type == "result":
                    result_text = str(payload.get("text", "")).strip()
                elif event_type == "done":
                    break
    except Exception:
        pass

    assistant_text = "".join(assistant_chunks).strip()
    if len(assistant_text) >= len(result_text):
        return assistant_text
    return result_text

def _wait_cursor_run_result(agent_id: str, run_id: str, api_key: str) -> str:
    for _ in range(180):
        run_data = _cursor_api_request(
            "GET",
            f"/agents/{agent_id}/runs/{run_id}",
            api_key,
            timeout=60,
        )
        status = str(run_data.get("status", "")).upper()

        if status in CURSOR_RUN_TERMINAL_STATUSES:
            if status == "FINISHED":
                response_text = str(run_data.get("result", "")).strip()
                stream_text = _fetch_run_stream_text(agent_id, run_id, api_key)
                if len(stream_text) > len(response_text):
                    response_text = stream_text
                if not response_text:
                    raise RuntimeError("Cursor AI가 빈 응답을 반환했습니다.")
                _save_cursor_debug_response(response_text)
                return response_text
            raise RuntimeError(f"Cursor AI 실행 실패 (상태: {status})")

        time.sleep(5)

    raise RuntimeError("Cursor AI 응답 시간이 초과되었습니다.")

def call_cursor_ai(prompt: str, api_key: str) -> str:
    """Cursor Cloud REST API로 블로그 글을 생성합니다 (로컬 SDK 소켓 충돌 방지)."""
    create_response = _cursor_api_request(
        "POST",
        "/agents",
        api_key,
        {
            "prompt": {"text": prompt},
            "model": {"id": "composer-2.5"},
            "autoCreatePR": False,
        },
        timeout=180,
    )

    agent_id = str((create_response.get("agent") or {}).get("id", "")).strip()
    run_id = str((create_response.get("run") or {}).get("id", "")).strip()

    if not agent_id:
        agent_id = str((create_response.get("run") or {}).get("agentId", "")).strip()
    if not run_id:
        run_id = str((create_response.get("agent") or {}).get("latestRunId", "")).strip()

    if not agent_id or not run_id:
        raise RuntimeError("Cursor API 응답에 agent/run ID가 없습니다.")

    return _wait_cursor_run_result(agent_id, run_id, api_key)

def apply_blog_contents(blogs: list[tuple[str, str]]):
    editors = (
        (title_var_1, editor_1),
        (title_var_2, editor_2),
        (title_var_3, editor_3),
    )

    for index, (title_var, editor) in enumerate(editors):
        if index < len(blogs):
            title, content = blogs[index]
            title_var.set(title)
            editor.delete("1.0", tk.END)
            editor.insert("1.0", content)
        else:
            title_var.set("")
            editor.delete("1.0", tk.END)

def set_cursor_ai_buttons_enabled(enabled: bool):
    state = tk.NORMAL if enabled else tk.DISABLED
    for btn in cursor_ai_buttons:
        btn.config(state=state)

def start_cursor_ai_workflow(blog_count: int):
    global running

    if running:
        messagebox.showwarning("알림", "이미 작업이 실행 중입니다.")
        return

    script = prompt_text_input.get("1.0", tk.END).strip()
    if not script:
        messagebox.showerror("오류", "유튜브 대본(멘트)을 입력하세요.")
        return

    car_type = car_type_var.get().strip()
    if not car_type:
        messagebox.showerror("오류", "차종을 입력하세요.")
        return

    api_key = get_cursor_api_key()
    if not api_key:
        messagebox.showerror(
            "오류",
            "Cursor API 키가 없습니다.\n\n"
            "환경 변수 CURSOR_API_KEY 를 설정해주세요.\n"
            "(Cursor 대시보드 → Integrations → API Keys)"
        )
        return

    set_cursor_ai_buttons_enabled(False)
    cursor_ai_status_var.set(f"Cursor AI: 프롬프트 {blog_count}로 원고 {blog_count}개 생성 중...")

    def task():
        global running
        running = True

        try:
            prompt = build_blog_ai_prompt(blog_count - 1, script)
            response_text = call_cursor_ai(prompt, api_key)
            blogs = parse_blog_posts(response_text, blog_count)

            def apply_results():
                global running

                apply_blog_contents(blogs)
                blog_run_mode_var.set(blog_count)
                save_config()

                try:
                    saved_name = auto_save_blog_content_silent(car_type)
                except Exception as e:
                    running = False
                    set_cursor_ai_buttons_enabled(True)
                    cursor_ai_status_var.set("Cursor AI 저장 실패")
                    messagebox.showerror("오류", f"파일 저장 실패:\n{e}")
                    return

                cursor_ai_status_var.set(
                    f"Cursor AI 완료 ({saved_name}) - 블로그 {blog_count}개 작성란에 반영됨"
                )
                notebook.select(tab1)
                running = False
                set_cursor_ai_buttons_enabled(True)
                messagebox.showinfo(
                    "완료",
                    f"원고 {blog_count}개가 블로그 작성란에 채워졌습니다.\n"
                    f"파일 저장: {saved_name}\n\n"
                    "네이버 자동 실행은 하지 않습니다. 필요 시 F2로 직접 실행하세요."
                )

            root.after(0, apply_results)
        except Exception as e:
            running = False
            root.after(0, lambda: set_cursor_ai_buttons_enabled(True))
            root.after(0, lambda: cursor_ai_status_var.set("Cursor AI 오류"))
            root.after(0, lambda: messagebox.showerror("오류", f"Cursor AI 처리 실패:\n{e}"))

    threading.Thread(target=task, daemon=True).start()

def copy_prompt(index: int):
    script = prompt_text_input.get("1.0", tk.END).strip()

    if not script:
        messagebox.showerror("오류", "내용을 입력하세요.")
        return

    try:
        prompt = build_blog_ai_prompt(index, script)
    except KeyError as e:
        messagebox.showerror(
            "오류",
            f"프롬프트 템플릿 형식이 올바르지 않습니다.\n누락되면 안 되는 항목: {e}\n\n"
            "반드시 마지막에 {{script}} 를 포함해야 합니다."
        )
        return
    except Exception as e:
        messagebox.showerror("오류", f"프롬프트 생성 실패: {e}")
        return

    try:
        root.clipboard_clear()
        root.clipboard_append(prompt)
        root.update()
        messagebox.showinfo("완료", f"{prompt_button_names[index]} 내용이 클립보드에 복사되었습니다!")
    except Exception as e:
        messagebox.showerror("오류", f"클립보드 복사 실패: {e}")

def edit_prompt_template(index: int):
    win = tk.Toplevel(root)
    win.title(f"프롬프트 {index + 1} 수정")
    win.geometry("900x700")
    win.transient(root)
    win.configure(bg=BG_MAIN)

    tk.Label(
        win,
        text="아래 프롬프트를 수정하세요. 반드시 마지막에 {script} 를 포함해야 합니다.",
        font=("맑은 고딕", 11, "bold"),
        bg=BG_MAIN,
        fg=ACCENT
    ).pack(pady=15)

    text = tk.Text(win, font=("맑은 고딕", 11), undo=True, relief="flat", highlightthickness=1, 
                   highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, padx=15, pady=15)
    text.pack(fill="both", expand=True, padx=20, pady=5)
    text.insert("1.0", prompt_templates[index])

    bottom = tk.Frame(win, bg=BG_MAIN)
    bottom.pack(fill="x", padx=20, pady=15)

    def reset_default():
        text.delete("1.0", tk.END)
        text.insert("1.0", DEFAULT_PROMPT_TEMPLATE)

    def save_prompt():
        value = text.get("1.0", tk.END).strip()

        if not value:
            messagebox.showwarning("알림", "프롬프트 내용을 입력하세요.", parent=win)
            return

        if "{script}" not in value:
            messagebox.showwarning(
                "알림",
                "프롬프트 안에 반드시 {script} 문구가 포함되어야 합니다.",
                parent=win
            )
            return

        prompt_templates[index] = value
        save_config()
        messagebox.showinfo("완료", f"프롬프트 {index + 1} 내용이 저장되었습니다.", parent=win)
        win.destroy()

    btn_reset = create_flat_button(bottom, "기본값 복원", reset_default, SECONDARY, SECONDARY_HOVER)
    btn_reset.pack(side="left", padx=5)
    
    btn_close = create_flat_button(bottom, "닫기", win.destroy, SECONDARY, SECONDARY_HOVER)
    btn_close.pack(side="right", padx=5)
    
    btn_save = create_flat_button(bottom, "저장", save_prompt, ACCENT, ACCENT_HOVER)
    btn_save.pack(side="right", padx=5)

def edit_prompt_button_name(index: int):
    current_name = prompt_button_names[index]
    new_name = simpledialog.askstring(
        f"프롬프트 {index + 1} 버튼 이름 수정",
        "새 버튼 이름을 입력하세요:",
        initialvalue=current_name,
        parent=root,
    )

    if new_name is None:
        return

    new_name = new_name.strip()
    if not new_name:
        messagebox.showwarning("알림", "버튼 이름을 입력하세요.")
        return

    prompt_button_names[index] = new_name
    refresh_prompt_buttons()
    save_config()
    messagebox.showinfo("완료", f"프롬프트 {index + 1} 버튼 이름이 변경되었습니다.")

def refresh_prompt_buttons():
    for i in range(4):
        prompt_copy_buttons[i].config(text=prompt_button_names[i])
        prompt_edit_buttons[i].config(text=f"프롬프트 {i + 1} 내용 수정")
        prompt_name_buttons[i].config(text=f"프롬프트 {i + 1} 버튼 이름 수정")

def load_image_with_exif_fix(path: str):
    img = Image.open(path)
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    return img

# ---------------- [탭 3] 이미지 일괄 변환 및 이름 변경 ----------------
def get_image_files(folder: str):
    files = []
    for file_name in os.listdir(folder):
        if file_name.lower().endswith(SUPPORTED_EXTENSIONS):
            files.append(file_name)
    files.sort()
    return files

def generate_unique_image_names(car_type: str, count: int) -> list[str]:
    """차종과 고정 키워드를 조합해 서로 다른 파일명을 생성합니다."""
    candidates = []
    for combo_size in (2, 3, 1, 4):
        for combo in itertools.combinations(IMG_TITLE_KEYWORDS, combo_size):
            candidates.append(f"{car_type}_{'_'.join(combo)}")

    unique_candidates = list(dict.fromkeys(candidates))
    random.shuffle(unique_candidates)

    if count > len(unique_candidates):
        raise ValueError(
            f"고유한 파일명을 {count}개 만들 수 없습니다. (최대 {len(unique_candidates)}개)"
        )

    return unique_candidates[:count]

def img_select_folder():
    folder = filedialog.askdirectory()
    if folder:
        img_folder_path.set(folder)
        save_config()

def _folder_has_heic(folder: str) -> bool:
    return any(
        file_name.lower().endswith((".heic", ".heif"))
        for file_name in os.listdir(folder)
    )

def _save_images_to_subfolder(
    source_folder: str,
    image_files: list[str],
    dest_folder: str,
    title_names: list[str],
):
    os.makedirs(dest_folder, exist_ok=True)

    shuffled_files = image_files.copy()
    random.shuffle(shuffled_files)

    for file_name, title in zip(shuffled_files, title_names):
        old_path = os.path.join(source_folder, file_name)
        new_path = os.path.join(dest_folder, f"{title}.jpg")
        with load_image_with_exif_fix(old_path) as img:
            rgb_img = img.convert("RGB")
            rgb_img.save(new_path, "JPEG", quality=100)

def start_img_process():
    car_type = car_type_var.get().strip()
    source_folder = img_folder_path.get().strip()
    split_count = int(img_split_count.get())

    if not source_folder or not os.path.isdir(source_folder):
        messagebox.showerror("오류", "폴더를 먼저 선택해주세요.")
        return

    if not car_type:
        messagebox.showerror("오류", "차종을 입력해주세요.")
        return

    if split_count not in (2, 3, 4):
        messagebox.showerror("오류", "분할 폴더 개수를 선택해주세요. (2폴더 / 3폴더 / 4폴더)")
        return

    if not HEIC_AVAILABLE and _folder_has_heic(source_folder):
        messagebox.showerror(
            "오류",
            "HEIC/HEIF 파일이 있습니다.\n"
            "처리하려면 pillow-heif 설치가 필요합니다.\n\n"
            "설치 명령어:\n"
            "C:\\Users\\uc808\\AppData\\Local\\Programs\\Python\\Python313\\python.exe -m pip install pillow-heif"
        )
        return

    image_files = get_image_files(source_folder)
    if not image_files:
        messagebox.showerror("오류", "선택한 폴더에 이미지 파일이 없습니다.")
        return

    images_per_folder = len(image_files)
    total_output = images_per_folder * split_count

    try:
        all_title_names = generate_unique_image_names(car_type, total_output)
    except ValueError as e:
        messagebox.showerror("오류", str(e))
        return

    try:
        title_index = 0
        processed_count = 0

        for folder_num in range(1, split_count + 1):
            subfolder_name = f"폴더{folder_num}"
            dest_folder = os.path.join(source_folder, subfolder_name)
            folder_titles = all_title_names[title_index:title_index + images_per_folder]
            title_index += images_per_folder

            _save_images_to_subfolder(source_folder, image_files, dest_folder, folder_titles)

            processed_count += images_per_folder
            img_status_var.set(f"{subfolder_name} 완료 ({processed_count}/{total_output})")
            root.update_idletasks()

        img_status_var.set("완료되었습니다. 분할 폴더 생성 + JPG 변환 완료")
        save_config()
        messagebox.showinfo(
            "완료",
            f"총 {total_output}개 이미지가 {split_count}개 폴더에 저장되었습니다.\n"
            f"(폴더당 {images_per_folder}개, 파일명 중복 없음, 순서 랜덤)"
        )
    except Exception as e:
        messagebox.showerror("오류", f"처리 중 오류 발생:\n{str(e)}")

# =====================================================================
# ---------------- GUI 고급화 설정 (모던 테마 & 헬퍼 함수) ----------------
# =====================================================================

BG_MAIN = "#F4F6F9"
BG_PANEL = "#FFFFFF"
TEXT_MAIN = "#2B2D42"
TEXT_MUTED = "#6C757D"
ACCENT = "#3A86FF"
ACCENT_HOVER = "#2563EB"
SUCCESS = "#10B981"
SUCCESS_HOVER = "#059669"
WARNING = "#F59E0B"
WARNING_HOVER = "#D97706"
DANGER = "#EF4444"
DANGER_HOVER = "#DC2626"
SECONDARY = "#8D99AE"
SECONDARY_HOVER = "#6C757D"
BORDER = "#E2E8F0"
INPUT_BG = "#F8FAFC"

def create_flat_button(parent, text, command, bg_color, hover_color, fg="white", font=("맑은 고딕", 11, "bold"), pady=8):
    btn = tk.Button(parent, text=text, command=command, bg=bg_color, fg=fg,
                    font=font, relief="flat", bd=0, cursor="hand2", pady=pady)
    btn.bind("<Enter>", lambda e, b=btn, c=hover_color: b.config(bg=c))
    btn.bind("<Leave>", lambda e, b=btn, c=bg_color: b.config(bg=c))
    return btn

root = tk.Tk()
root.title("블로그 마스터 자동화 툴 (통합 버전)")
root.geometry(DEFAULT_WINDOW_GEOMETRY)
root.configure(bg=BG_MAIN)
root.protocol("WM_DELETE_WINDOW", on_root_close)

# 최신 UI 스타일(ttk) 적용
style = ttk.Style()
style.theme_use('clam')
style.configure("TNotebook", background=BG_MAIN, borderwidth=0)
style.configure("TNotebook.Tab", background="#E2E8F0", foreground=TEXT_MUTED, padding=[25, 12], font=("맑은 고딕", 11, "bold"), borderwidth=0)
style.map("TNotebook.Tab", background=[("selected", BG_PANEL)], foreground=[("selected", ACCENT)])
style.configure("TLabelframe", background=BG_PANEL, bordercolor=BORDER, borderwidth=1)
style.configure("TLabelframe.Label", font=("맑은 고딕", 10, "bold"), background=BG_PANEL, foreground=TEXT_MAIN)
style.configure("TRadiobutton", background=BG_PANEL, font=("맑은 고딕", 10), foreground=TEXT_MAIN)
style.configure("TScale", background=BG_PANEL, troughcolor=BORDER)
style.configure("TPanedwindow", background=BG_MAIN)

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

# --- 탭1: 파일 관리 및 자동 타이핑 ---
tab1 = tk.Frame(notebook, bg=BG_MAIN)
notebook.add(tab1, text="  자동 타이핑 및 파일 관리  ")

left_f = tk.Frame(tab1, width=280, bg=BG_MAIN)
left_f.pack(side="left", fill="y", padx=(10, 5), pady=10)

right_container = tk.Frame(tab1, bg=BG_MAIN)
right_container.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

right_canvas = tk.Canvas(right_container, bg=BG_MAIN, highlightthickness=0)
right_scrollbar = ttk.Scrollbar(right_container, orient="vertical", command=right_canvas.yview)
right_f = tk.Frame(right_canvas, bg=BG_MAIN)

right_f.bind(
    "<Configure>",
    lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
)

right_canvas_window = right_canvas.create_window((0, 0), window=right_f, anchor="nw")

def _on_right_canvas_configure(event):
    right_canvas.itemconfigure(right_canvas_window, width=event.width)

right_canvas.bind("<Configure>", _on_right_canvas_configure)
right_canvas.configure(yscrollcommand=right_scrollbar.set)

right_canvas.pack(side="left", fill="both", expand=True)
right_scrollbar.pack(side="right", fill="y")

def _bind_right_scroll(event=None):
    right_canvas.bind_all("<MouseWheel>", _on_right_mousewheel)
    right_canvas.bind_all("<Button-4>", _on_right_mousewheel)
    right_canvas.bind_all("<Button-5>", _on_right_mousewheel)

def _unbind_right_scroll(event=None):
    right_canvas.unbind_all("<MouseWheel>")
    right_canvas.unbind_all("<Button-4>")
    right_canvas.unbind_all("<Button-5>")

def _on_right_mousewheel(event):
    try:
        if hasattr(event, "delta") and event.delta:
            right_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif getattr(event, "num", None) == 4:
            right_canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            right_canvas.yview_scroll(3, "units")
    except Exception:
        pass

right_canvas.bind("<Enter>", _bind_right_scroll)
right_canvas.bind("<Leave>", _unbind_right_scroll)
right_f.bind("<Enter>", _bind_right_scroll)
right_f.bind("<Leave>", _unbind_right_scroll)

tk.Label(left_f, text="📁 파일 목록", font=("맑은 고딕", 11, "bold"), bg=BG_MAIN, fg=TEXT_MAIN).pack(pady=(0, 8))

listbox = tk.Listbox(left_f, height=25, font=("맑은 고딕", 10), exportselection=False,
                     relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, 
                     bg=BG_PANEL, fg=TEXT_MAIN, selectbackground=ACCENT, selectforeground="white", activestyle="none")
listbox.pack(fill="both", expand=True)
listbox.bind("<<ListboxSelect>>", on_select_txt)
listbox.bind("<FocusOut>", on_listbox_focus_out)

f_btn_f = tk.Frame(left_f, bg=BG_MAIN)
f_btn_f.pack(fill="x", pady=8)

btn_new = create_flat_button(f_btn_f, "새 파일", create_txt_file, ACCENT, ACCENT_HOVER, font=("맑은 고딕", 10, "bold"), pady=6)
btn_new.pack(side="left", expand=True, fill="x", padx=(0, 2))

btn_ren = create_flat_button(f_btn_f, "이름 변경", rename_txt_file, WARNING, WARNING_HOVER, font=("맑은 고딕", 10, "bold"), pady=6)
btn_ren.pack(side="left", expand=True, fill="x", padx=(2, 0))

btn_refresh = create_flat_button(left_f, "목록 새로고침", load_txt_files, SUCCESS, SUCCESS_HOVER, font=("맑은 고딕", 10, "bold"), pady=6)
btn_refresh.pack(fill="x")

blog_run_mode_var = tk.IntVar(value=1)
naver_id_var_1 = tk.StringVar(value=DEFAULT_NAVER_ID_1)
naver_password_var_1 = tk.StringVar(value=DEFAULT_NAVER_PASSWORD_1)
blog_write_url_var_1 = tk.StringVar(value=DEFAULT_BLOG_WRITE_URL_1)
naver_id_var_2 = tk.StringVar(value=DEFAULT_NAVER_ID_2)
naver_password_var_2 = tk.StringVar(value=DEFAULT_NAVER_PASSWORD_2)
blog_write_url_var_2 = tk.StringVar(value=DEFAULT_BLOG_WRITE_URL_2)
naver_id_var_3 = tk.StringVar(value=DEFAULT_NAVER_ID_3)
naver_password_var_3 = tk.StringVar(value=DEFAULT_NAVER_PASSWORD_3)
blog_write_url_var_3 = tk.StringVar(value=DEFAULT_BLOG_WRITE_URL_3)

settings_frame = ttk.LabelFrame(right_f, text="  ⚙️ 블로그 계정 / 실행 설정  ", padding=(15, 15))
settings_frame.pack(fill="x", pady=(0, 10))

mode_frame = tk.Frame(settings_frame, bg=BG_PANEL)
mode_frame.pack(fill="x", pady=(0, 12))
tk.Label(mode_frame, text="실행 방식", font=("맑은 고딕", 10, "bold"), bg=BG_PANEL, fg=TEXT_MAIN).pack(side="left")
ttk.Radiobutton(mode_frame, text="블로그 1개 쓰기", variable=blog_run_mode_var, value=1, command=save_config).pack(side="left", padx=(15, 10))
ttk.Radiobutton(mode_frame, text="블로그 2개 쓰기", variable=blog_run_mode_var, value=2, command=save_config).pack(side="left", padx=(0, 10))
ttk.Radiobutton(mode_frame, text="블로그 3개 쓰기 (3번째 Edge)", variable=blog_run_mode_var, value=3, command=save_config).pack(side="left")

account_wrap = tk.Frame(settings_frame, bg=BG_PANEL)
account_wrap.pack(fill="x")

account_row1 = tk.Frame(account_wrap, bg=BG_PANEL)
account_row1.pack(fill="x")

account1_frame = ttk.LabelFrame(account_row1, text="  첫번째 블로그 계정 (Chrome 시크릿)  ", padding=(12, 12))
account1_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
account2_frame = ttk.LabelFrame(account_row1, text="  두번째 블로그 계정 (Chrome)  ", padding=(12, 12))
account2_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

account_row2 = tk.Frame(account_wrap, bg=BG_PANEL)
account_row2.pack(fill="x", pady=(8, 0))

account3_frame = ttk.LabelFrame(account_row2, text="  세번째 블로그 계정 (Edge)  ", padding=(12, 12))
account3_frame.pack(side="left", fill="both", expand=True)

for parent, id_var, pw_var, url_var in (
    (account1_frame, naver_id_var_1, naver_password_var_1, blog_write_url_var_1),
    (account2_frame, naver_id_var_2, naver_password_var_2, blog_write_url_var_2),
    (account3_frame, naver_id_var_3, naver_password_var_3, blog_write_url_var_3),
):
    tk.Label(parent, text="네이버 아이디", font=("맑은 고딕", 9, "bold"), bg=BG_PANEL, fg=TEXT_MUTED).pack(anchor="w")
    entry_id = tk.Entry(parent, textvariable=id_var, font=("맑은 고딕", 10), relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG)
    entry_id.pack(fill="x", ipady=6, pady=(2, 10))
    entry_id.bind("<FocusOut>", lambda event: save_config())

    tk.Label(parent, text="네이버 비밀번호", font=("맑은 고딕", 9, "bold"), bg=BG_PANEL, fg=TEXT_MUTED).pack(anchor="w")
    entry_pw = tk.Entry(parent, textvariable=pw_var, font=("맑은 고딕", 10), show="*", relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG)
    entry_pw.pack(fill="x", ipady=6, pady=(2, 10))
    entry_pw.bind("<FocusOut>", lambda event: save_config())

    tk.Label(parent, text="블로그 글쓰기 주소", font=("맑은 고딕", 9, "bold"), bg=BG_PANEL, fg=TEXT_MUTED).pack(anchor="w")
    entry_url = tk.Entry(parent, textvariable=url_var, font=("맑은 고딕", 10), relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG)
    entry_url.pack(fill="x", ipady=6, pady=(2, 0))
    entry_url.bind("<FocusOut>", lambda event: save_config())

phone_wrap_frame = tk.Frame(right_f, bg=BG_MAIN)
phone_wrap_frame.pack(fill="x", pady=(0, 10))

phone_left_frame = ttk.LabelFrame(phone_wrap_frame, text="  📞 블로그 1 견적상담 전화번호  ", padding=(12, 12))
phone_left_frame.pack(side="left", fill="x", expand=True, padx=(0, 5))
phone_center_frame = ttk.LabelFrame(phone_wrap_frame, text="  📞 블로그 2 견적상담 전화번호  ", padding=(12, 12))
phone_center_frame.pack(side="left", fill="x", expand=True, padx=(0, 5))
phone_right_frame = ttk.LabelFrame(phone_wrap_frame, text="  📞 블로그 3 견적상담 전화번호  ", padding=(12, 12))
phone_right_frame.pack(side="left", fill="x", expand=True)

phone_number_var_1 = tk.StringVar(value=DEFAULT_PHONE_NUMBER)
phone_number_var_2 = tk.StringVar(value=DEFAULT_PHONE_NUMBER)
phone_number_var_3 = tk.StringVar(value=DEFAULT_PHONE_NUMBER)

phone_entry_1 = tk.Entry(phone_left_frame, textvariable=phone_number_var_1, font=("맑은 고딕", 11, "bold"), relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, justify="center", fg=TEXT_MAIN)
phone_entry_1.pack(fill="x", ipady=6)
phone_entry_1.bind("<FocusOut>", lambda event: save_config())

phone_entry_2 = tk.Entry(phone_center_frame, textvariable=phone_number_var_2, font=("맑은 고딕", 11, "bold"), relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, justify="center", fg=TEXT_MAIN)
phone_entry_2.pack(fill="x", ipady=6)
phone_entry_2.bind("<FocusOut>", lambda event: save_config())

phone_entry_3 = tk.Entry(phone_right_frame, textvariable=phone_number_var_3, font=("맑은 고딕", 11, "bold"), relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, justify="center", fg=TEXT_MAIN)
phone_entry_3.pack(fill="x", ipady=6)
phone_entry_3.bind("<FocusOut>", lambda event: save_config())

editor_wrap = ttk.PanedWindow(right_f, orient=tk.HORIZONTAL)
editor_wrap.pack(fill="both", expand=True, pady=5)

blog1_editor_frame = ttk.LabelFrame(editor_wrap, text="  📝 첫번째 블로그 글  ", padding=(12, 12))
blog2_editor_frame = ttk.LabelFrame(editor_wrap, text="  📝 두번째 블로그 글  ", padding=(12, 12))
blog3_editor_frame = ttk.LabelFrame(editor_wrap, text="  📝 세번째 블로그 글  ", padding=(12, 12))
editor_wrap.add(blog1_editor_frame, weight=1)
editor_wrap.add(blog2_editor_frame, weight=1)
editor_wrap.add(blog3_editor_frame, weight=1)

# 첫번째 블로그 입력창
create_blog_action_row(blog1_editor_frame, 1, "▶ 블로그 1 테스트")

tk.Label(blog1_editor_frame, text="📰 첫번째 제목", font=("맑은 고딕", 10, "bold"), bg=BG_PANEL, fg=TEXT_MAIN).pack(anchor="w", pady=(0,4))
title_var_1 = tk.StringVar()
title_entry_1 = tk.Entry(blog1_editor_frame, textvariable=title_var_1, font=("맑은 고딕", 11), relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG)
title_entry_1.pack(fill="x", pady=(0, 10), ipady=8)

tk.Label(blog1_editor_frame, text="✍️ 첫번째 내용", font=("맑은 고딕", 10, "bold"), bg=BG_PANEL, fg=TEXT_MAIN).pack(anchor="w", pady=(0,4))
editor_1 = tk.Text(blog1_editor_frame, font=("맑은 고딕", 11), undo=True, relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, padx=10, pady=10)
editor_1.pack(fill="both", expand=True)

# 두번째 블로그 입력창
create_blog_action_row(blog2_editor_frame, 2, "▶ 블로그 2 테스트")

tk.Label(blog2_editor_frame, text="📰 두번째 제목", font=("맑은 고딕", 10, "bold"), bg=BG_PANEL, fg=TEXT_MAIN).pack(anchor="w", pady=(0,4))
title_var_2 = tk.StringVar()
title_entry_2 = tk.Entry(blog2_editor_frame, textvariable=title_var_2, font=("맑은 고딕", 11), relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG)
title_entry_2.pack(fill="x", pady=(0, 10), ipady=8)

tk.Label(blog2_editor_frame, text="✍️ 두번째 내용", font=("맑은 고딕", 10, "bold"), bg=BG_PANEL, fg=TEXT_MAIN).pack(anchor="w", pady=(0,4))
editor_2 = tk.Text(blog2_editor_frame, font=("맑은 고딕", 11), undo=True, relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, padx=10, pady=10)
editor_2.pack(fill="both", expand=True)

# 세번째 블로그 입력창
create_blog_action_row(blog3_editor_frame, 3, "▶ 블로그 3 테스트")

tk.Label(blog3_editor_frame, text="📰 세번째 제목", font=("맑은 고딕", 10, "bold"), bg=BG_PANEL, fg=TEXT_MAIN).pack(anchor="w", pady=(0,4))
title_var_3 = tk.StringVar()
title_entry_3 = tk.Entry(blog3_editor_frame, textvariable=title_var_3, font=("맑은 고딕", 11), relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG)
title_entry_3.pack(fill="x", pady=(0, 10), ipady=8)

tk.Label(blog3_editor_frame, text="✍️ 세번째 내용", font=("맑은 고딕", 10, "bold"), bg=BG_PANEL, fg=TEXT_MAIN).pack(anchor="w", pady=(0,4))
editor_3 = tk.Text(blog3_editor_frame, font=("맑은 고딕", 11), undo=True, relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, padx=10, pady=10)
editor_3.pack(fill="both", expand=True)

speed_frame = ttk.LabelFrame(right_f, text="  ⚡ 타이핑 속도 설정 (CPM)  ", padding=(12, 12))
speed_frame.pack(fill="x", pady=(15, 5))

speed_value_var = tk.StringVar(value=f"현재 타수: {DEFAULT_SPEED_CPM} CPM")
tk.Label(speed_frame, textvariable=speed_value_var, font=("맑은 고딕", 11, "bold"), fg=ACCENT, bg=BG_PANEL).pack(anchor="w", pady=(0, 5))

speed_scale = ttk.Scale(
    speed_frame,
    from_=100,
    to_=1200,
    orient=tk.HORIZONTAL,
    command=update_speed_label,
)
speed_scale.set(DEFAULT_SPEED_CPM)
speed_scale.pack(fill="x")
update_speed_label()
speed_scale.bind("<ButtonRelease-1>", lambda event: save_config())

btn_save_all = create_flat_button(right_f, "💾 작성 내용 저장하기", save_txt_file, ACCENT, ACCENT_HOVER, font=("맑은 고딕", 12, "bold"), pady=12)
btn_save_all.pack(fill="x", pady=15)

status_var = tk.StringVar(value="현재 상태: 대기 중")
tk.Label(right_f, textvariable=status_var, fg=SUCCESS, bg=BG_MAIN, font=("맑은 고딕", 13, "bold")).pack()
tk.Label(
    right_f,
    text="[F2] 블로그 자동 작성 시작  |  [ESC] 작업 강제 중지",
    fg=DANGER,
    bg=BG_MAIN,
    font=("맑은 고딕", 11, "bold")
).pack(pady=(5, 0))

# --- 탭2: 블로그 프롬프트 생성 ---
tab2 = tk.Frame(notebook, bg=BG_MAIN)
notebook.add(tab2, text="  블로그 AI 프롬프트  ")

tab2_scroll_container = tk.Frame(tab2, bg=BG_MAIN)
tab2_scroll_container.pack(fill="both", expand=True)

tab2_canvas = tk.Canvas(tab2_scroll_container, bg=BG_MAIN, highlightthickness=0)
tab2_scrollbar = ttk.Scrollbar(tab2_scroll_container, orient="vertical", command=tab2_canvas.yview)
tab2_f = tk.Frame(tab2_canvas, bg=BG_MAIN)

tab2_f.bind(
    "<Configure>",
    lambda e: tab2_canvas.configure(scrollregion=tab2_canvas.bbox("all"))
)
tab2_canvas_window = tab2_canvas.create_window((0, 0), window=tab2_f, anchor="nw")

def _on_tab2_canvas_configure(event):
    tab2_canvas.itemconfigure(tab2_canvas_window, width=event.width)

tab2_canvas.bind("<Configure>", _on_tab2_canvas_configure)
tab2_canvas.configure(yscrollcommand=tab2_scrollbar.set)

tab2_canvas.pack(side="left", fill="both", expand=True)
tab2_scrollbar.pack(side="right", fill="y")

def _bind_tab2_scroll(event=None):
    tab2_canvas.bind_all("<MouseWheel>", _on_tab2_mousewheel)
    tab2_canvas.bind_all("<Button-4>", _on_tab2_mousewheel)
    tab2_canvas.bind_all("<Button-5>", _on_tab2_mousewheel)

def _unbind_tab2_scroll(event=None):
    tab2_canvas.unbind_all("<MouseWheel>")
    tab2_canvas.unbind_all("<Button-4>")
    tab2_canvas.unbind_all("<Button-5>")

def _on_tab2_mousewheel(event):
    try:
        if hasattr(event, "delta") and event.delta:
            tab2_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif getattr(event, "num", None) == 4:
            tab2_canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            tab2_canvas.yview_scroll(3, "units")
    except Exception:
        pass

tab2_canvas.bind("<Enter>", _bind_tab2_scroll)
tab2_canvas.bind("<Leave>", _unbind_tab2_scroll)
tab2_f.bind("<Enter>", _bind_tab2_scroll)
tab2_f.bind("<Leave>", _unbind_tab2_scroll)

tk.Label(tab2_f, text="유튜브 대본(멘트) 입력", font=("맑은 고딕", 12, "bold"), bg=BG_MAIN, fg=TEXT_MAIN).pack(pady=(20, 5))

prompt_text_input = tk.Text(tab2_f, font=("맑은 고딕", 11), height=12, relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, padx=15, pady=15)
prompt_text_input.pack(fill="x", padx=30, pady=5)

car_type_var = tk.StringVar()
car_type_frame = tk.Frame(tab2_f, bg=BG_MAIN)
car_type_frame.pack(fill="x", padx=30, pady=(8, 0))
tk.Label(car_type_frame, text="차종 입력 (파일명 저장용)", font=("맑은 고딕", 11, "bold"), bg=BG_MAIN, fg=TEXT_MAIN).pack(side="left")
car_type_entry = tk.Entry(
    car_type_frame, textvariable=car_type_var, font=("맑은 고딕", 11), width=30,
    relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG,
)
car_type_entry.pack(side="left", padx=(12, 0), ipady=6)
car_type_entry.bind("<FocusOut>", lambda event: save_config())

cursor_ai_status_var = tk.StringVar()

cursor_ai_wrap = ttk.LabelFrame(tab2_f, text="  Cursor AI 자동 작성  ", padding=(12, 12))
cursor_ai_wrap.pack(fill="x", padx=30, pady=(10, 5))

cursor_ai_btn_row = tk.Frame(cursor_ai_wrap, bg=BG_PANEL)
cursor_ai_btn_row.pack(fill="x")

for blog_count, label in ((1, "🤖 Cursor AI 1개"), (2, "🤖 Cursor AI 2개"), (3, "🤖 Cursor AI 3개")):
    btn = create_flat_button(
        cursor_ai_btn_row,
        label,
        lambda count=blog_count: start_cursor_ai_workflow(count),
        ACCENT if blog_count == 1 else SUCCESS if blog_count == 2 else WARNING,
        ACCENT_HOVER if blog_count == 1 else SUCCESS_HOVER if blog_count == 2 else WARNING_HOVER,
        font=("맑은 고딕", 11, "bold"),
        pady=10,
    )
    btn.pack(side="left", fill="x", expand=True, padx=(0 if blog_count == 1 else 4, 0 if blog_count == 3 else 4))
    cursor_ai_buttons.append(btn)

if get_cursor_api_key():
    cursor_key_text = "✅ Cursor API 키 감지됨 (Cloud API)"
    cursor_key_color = SUCCESS
else:
    cursor_key_text = "❌ CURSOR_API_KEY 환경 변수 없음"
    cursor_key_color = DANGER

tk.Label(
    cursor_ai_wrap,
    text="대본+차종 입력 → 버튼 클릭 → 해당 프롬프트+멘트를 API에 그대로 전달 → 작성란 반영 → 차종_날짜.txt 저장",
    font=("맑은 고딕", 9),
    bg=BG_PANEL,
    fg=TEXT_MUTED,
).pack(pady=(8, 4))
tk.Label(cursor_ai_wrap, text=cursor_key_text, fg=cursor_key_color, bg=BG_PANEL, font=("맑은 고딕", 9, "bold")).pack()
tk.Label(tab2_f, textvariable=cursor_ai_status_var, fg=WARNING, bg=BG_MAIN, font=("맑은 고딕", 10, "bold")).pack(pady=(4, 0))

prompt_manage_wrap = tk.Frame(tab2_f, bg=BG_MAIN)
prompt_manage_wrap.pack(fill="x", padx=30, pady=(20, 30))

for i in range(4):
    row = ttk.LabelFrame(prompt_manage_wrap, text=f"  프롬프트 {i + 1}  ", padding=(12, 12))
    row.pack(fill="x", pady=8)

    copy_btn = create_flat_button(row, prompt_button_names[i], lambda idx=i: copy_prompt(idx), SUCCESS, SUCCESS_HOVER, font=("맑은 고딕", 11, "bold"), pady=10)
    copy_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
    prompt_copy_buttons.append(copy_btn)

    edit_btn = create_flat_button(row, f"내용 수정", lambda idx=i: edit_prompt_template(idx), SECONDARY, SECONDARY_HOVER, font=("맑은 고딕", 10, "bold"), pady=10)
    edit_btn.pack(side="left", fill="x", expand=True, padx=5)
    prompt_edit_buttons.append(edit_btn)

    name_btn = create_flat_button(row, f"버튼 이름 변경", lambda idx=i: edit_prompt_button_name(idx), WARNING, WARNING_HOVER, font=("맑은 고딕", 10, "bold"), pady=10)
    name_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))
    prompt_name_buttons.append(name_btn)

# --- 탭3: 이미지 변환 도구 ---
tab3 = tk.Frame(notebook, bg=BG_MAIN)
notebook.add(tab3, text="  이미지 일괄 변환  ")

img_folder_path = tk.StringVar()
img_split_count = tk.IntVar(value=2)
img_status_var = tk.StringVar()

init_app_storage()
load_config()

tk.Label(tab3, text="작업할 폴더 선택", font=("맑은 고딕", 12, "bold"), bg=BG_MAIN, fg=TEXT_MAIN).pack(pady=(30, 10))

create_flat_button(
    tab3, "📂 폴더 찾아보기", img_select_folder,
    SECONDARY, SECONDARY_HOVER, font=("맑은 고딕", 10, "bold"), pady=8,
).pack()
tk.Label(tab3, textvariable=img_folder_path, fg=ACCENT, bg=BG_MAIN, font=("맑은 고딕", 10, "bold"), wraplength=700).pack(pady=(10, 5))

split_frame = tk.Frame(tab3, bg=BG_MAIN)
split_frame.pack(pady=(15, 5))
tk.Label(split_frame, text="분할 폴더 개수", font=("맑은 고딕", 12, "bold"), bg=BG_MAIN, fg=TEXT_MAIN).pack(side="left", padx=(0, 15))
ttk.Radiobutton(split_frame, text="2폴더", variable=img_split_count, value=2, command=save_config).pack(side="left", padx=8)
ttk.Radiobutton(split_frame, text="3폴더", variable=img_split_count, value=3, command=save_config).pack(side="left", padx=8)
ttk.Radiobutton(split_frame, text="4폴더", variable=img_split_count, value=4, command=save_config).pack(side="left", padx=8)
tk.Label(
    tab3,
    text="선택한 경로에 폴더1, 폴더2 … 를 만들고, 원본 이미지를 각 폴더에 동일 개수로 복사합니다 (순서 랜덤, 파일명 중복 없음)",
    font=("맑은 고딕", 9), bg=BG_MAIN, fg=TEXT_MUTED, wraplength=720, justify="center",
).pack(pady=(5, 10))

if HEIC_AVAILABLE:
    heic_text = "✅ HEIC/HEIF 이미지 지원 활성화됨"
    heic_color = SUCCESS
else:
    heic_text = f"❌ HEIC 지원 비활성화됨: {HEIC_ERROR}" if HEIC_ERROR else "❌ HEIC 지원 비활성화됨"
    heic_color = DANGER

tk.Label(tab3, text=heic_text, fg=heic_color, font=("맑은 고딕", 10, "bold"), bg=BG_MAIN).pack(pady=(5, 20))

tk.Label(tab3, text="차종 입력", font=("맑은 고딕", 12, "bold"), bg=BG_MAIN, fg=TEXT_MAIN).pack(pady=(10, 5))
tk.Label(
    tab3,
    text="키워드는 자동 조합됩니다 (순정연동, 시공, 가격, 라이트, 튜닝, kc인증, 스피커, 에이비클, 시공후기, 아크릴, 전용어플, 전문점, 광주, 전주, 순천, 목포, 군산, 여수, 익산, 광양)",
    font=("맑은 고딕", 9), bg=BG_MAIN, fg=TEXT_MUTED, wraplength=720, justify="center",
).pack(pady=(0, 8))
img_entry = tk.Entry(tab3, textvariable=car_type_var, font=("맑은 고딕", 11), width=50, relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, justify="center")
img_entry.pack(pady=5, ipady=8)
img_entry.bind("<FocusOut>", lambda event: save_config())

btn_start_img = create_flat_button(tab3, "🚀 변환 및 이름 변경 시작", start_img_process, ACCENT, ACCENT_HOVER, font=("맑은 고딕", 12, "bold"), pady=12)
btn_start_img.pack(pady=30, ipadx=20)

tk.Label(tab3, textvariable=img_status_var, fg=WARNING, bg=BG_MAIN, font=("맑은 고딕", 11, "bold")).pack()

refresh_prompt_buttons()
load_txt_files()

# ---------------- 단축키 감지 및 실행 ----------------
def on_press(key):
    global stop_flag
    try:
        if key == keyboard.Key.f2:
            root.after(0, start_typing)
        elif key == keyboard.Key.esc:
            stop_flag = True
    except Exception:
        pass

keyboard.Listener(on_press=on_press, daemon=True).start()

root.mainloop()

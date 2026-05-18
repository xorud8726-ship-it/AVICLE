import os
import sys
import json
import shutil
import time
import random
import threading
import subprocess
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

running = False
stop_flag = False

pyautogui.FAILSAFE = True

# 현재 선택된 txt 파일명
current_selected_file = None
preferred_chrome_hwnd = None

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

    path_candidates = []
    for name in name_candidates:
        path_candidates.append(os.path.join(get_assets_dir(), name))
        path_candidates.append(os.path.join(BASE_DIR, name))

    for path in path_candidates:
        if os.path.isfile(path):
            return path
    return path_candidates[0]


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
    global MAP_TEMPLATE, AVICLE_TEMPLATE, ADD_TEMPLATE, CHECK_TEMPLATE, QUOTE_TEMPLATE

    LOGIN_TEMPLATE = resolve_asset_path("naver_login.png")
    HELP_HEADER_TEMPLATE = resolve_asset_path("help_header.png")
    SE_TEMPLATE = resolve_asset_path("se.png")
    EMDFHR_TEMPLATE = resolve_asset_path("emdfhr.png")
    CNLTH_TEMPLATE = resolve_asset_path("cnlth.png")
    RINK_TEMPLATE = resolve_asset_path("rink.png")
    URL_TEMPLATE = resolve_asset_path("url.png")
    MAP_TEMPLATE = resolve_asset_path("map.png")
    AVICLE_TEMPLATE = resolve_asset_path("avicle.png")
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

LOGIN_TEMPLATE = ""
HELP_HEADER_TEMPLATE = ""
SE_TEMPLATE = ""
EMDFHR_TEMPLATE = ""
CNLTH_TEMPLATE = ""
RINK_TEMPLATE = ""
URL_TEMPLATE = ""
MAP_TEMPLATE = ""
AVICLE_TEMPLATE = ""
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
BLOG_STORAGE_MARKER_TITLE = "\n<<<BLOG2_TITLE>>>\n"
BLOG_STORAGE_MARKER_BODY = "\n<<<BLOG2_BODY>>>\n"

DEFAULT_CONFIDENCE = 0.85
SEARCH_INTERVAL = 0.25
DEFAULT_PHONE_NUMBER = "010-8075-8066"
DEFAULT_SPEED_CPM = 450
SPECIAL_LINK_TEXT = "견적상담하기"
QUOTE_MARKER = "-인용구-"


kb_controller = Controller()


# ---------------- 입력 유틸 ----------------
user32 = ctypes.WinDLL("user32", use_last_error=True)
VK_CAPITAL = 0x14
VK_HANGUL = 0x15
KEYEVENTF_KEYUP = 0x0002


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
        "prompt_templates": prompt_templates,
        "prompt_button_names": prompt_button_names,
        "phone_number_1": phone_number_var_1.get().strip(),
        "phone_number_2": phone_number_var_2.get().strip(),
        "naver_id_1": naver_id_var_1.get().strip(),
        "naver_password_1": naver_password_var_1.get().strip(),
        "blog_write_url_1": blog_write_url_var_1.get().strip(),
        "naver_id_2": naver_id_var_2.get().strip(),
        "naver_password_2": naver_password_var_2.get().strip(),
        "blog_write_url_2": blog_write_url_var_2.get().strip(),
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
    global prompt_templates, prompt_button_names

    config_path = resolve_config_path()
    if not os.path.isfile(config_path):
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        img_folder_path.set(data.get("folder_path", ""))

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

        loaded_phone_number_1 = str(data.get("phone_number_1", DEFAULT_PHONE_NUMBER)).strip()
        if loaded_phone_number_1:
            phone_number_var_1.set(loaded_phone_number_1)

        loaded_phone_number_2 = str(data.get("phone_number_2", DEFAULT_PHONE_NUMBER)).strip()
        if loaded_phone_number_2:
            phone_number_var_2.set(loaded_phone_number_2)

        naver_id_var_1.set(str(data.get("naver_id_1", DEFAULT_NAVER_ID_1)).strip())
        naver_password_var_1.set(str(data.get("naver_password_1", DEFAULT_NAVER_PASSWORD_1)).strip())
        blog_write_url_var_1.set(str(data.get("blog_write_url_1", DEFAULT_BLOG_WRITE_URL_1)).strip())
        naver_id_var_2.set(str(data.get("naver_id_2", DEFAULT_NAVER_ID_2)).strip())
        naver_password_var_2.set(str(data.get("naver_password_2", DEFAULT_NAVER_PASSWORD_2)).strip())
        blog_write_url_var_2.set(str(data.get("blog_write_url_2", DEFAULT_BLOG_WRITE_URL_2)).strip())
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

    if BLOG_STORAGE_MARKER_TITLE in raw_text and BLOG_STORAGE_MARKER_BODY in raw_text:
        try:
            blog1_raw, rest = raw_text.split(BLOG_STORAGE_MARKER_TITLE, 1)
            blog2_title_raw, blog2_body_raw = rest.split(BLOG_STORAGE_MARKER_BODY, 1)
            title1, body1 = split_legacy_title_and_body(blog1_raw)
            title2 = blog2_title_raw.strip()
            body2 = blog2_body_raw.lstrip("\n")
            return title1, body1, title2, body2
        except Exception:
            pass

    title1, body1 = split_legacy_title_and_body(raw_text)
    return title1, body1, "", ""


def split_legacy_title_and_body(raw_text: str):
    raw_text = raw_text.replace("\r\n", "\n")
    lines = raw_text.split("\n")

    if not lines:
        return "", ""

    title = lines[0].strip()
    body = "\n".join(lines[1:]).lstrip("\n")
    return title, body


def combine_blog_file_content(title1: str, body1: str, title2: str, body2: str):
    primary = combine_legacy_title_and_body(title1, body1)
    title2 = title2.rstrip()
    body2 = body2.rstrip()

    if not title2 and not body2:
        return primary

    return f"{primary}{BLOG_STORAGE_MARKER_TITLE}{title2}{BLOG_STORAGE_MARKER_BODY}{body2}"


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
    )


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

    title1, content1, title2, content2 = get_title_and_content_values()

    if not title1 and not content1 and not title2 and not content2:
        messagebox.showwarning("알림", "제목 또는 내용을 입력하세요.")
        return

    save_text = combine_blog_file_content(title1, content1, title2, content2)

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

        title1, body1, title2, body2 = split_blog_file_content(raw_text)

        title_var_1.set(title1)
        editor_1.delete("1.0", tk.END)
        editor_1.insert("1.0", body1)

        title_var_2.set(title2)
        editor_2.delete("1.0", tk.END)
        editor_2.insert("1.0", body2)

        set_status(f"선택됨: {file_name}")
        keep_listbox_selection()
    except Exception as e:
        messagebox.showerror("오류", f"파일 열기 실패: {e}")


def on_listbox_focus_out(event=None):
    root.after(10, keep_listbox_selection)


def get_phone_number(blog_index: int) -> str:
    if blog_index == 2:
        value = phone_number_var_2.get().strip()
    else:
        value = phone_number_var_1.get().strip()
    return value or DEFAULT_PHONE_NUMBER


def get_tel_link(blog_index: int) -> str:
    return f"TEL:{get_phone_number(blog_index)}"


def select_recent_typed_text(char_count: int) -> None:
    if char_count <= 0:
        return

    activate_chrome_window()
    time.sleep(0.5)

    with kb_controller.pressed(Key.shift):
        for _ in range(char_count):
            if stop_flag:
                break
            kb_controller.press(Key.left)
            kb_controller.release(Key.left)
            time.sleep(0.08)

    time.sleep(0.2)


def run_post_estimate_location_action() -> None:
    set_status("견적상담하기 후 지도/주소 작업 중...")

    pyautogui.press("enter", presses=2, interval=0.15)
    time.sleep(0.3)

    if not click_image_forever(MAP_TEMPLATE, confidence=0.85):
        raise RuntimeError("map.png 이미지를 찾지 못했습니다.")

    time.sleep(0.2)
    paste_text_safely("자동차로 53")
    time.sleep(0.15)
    pyautogui.press("enter")
    time.sleep(0.4)

    if not click_image_forever(AVICLE_TEMPLATE, confidence=0.85):
        raise RuntimeError("avicle.png 이미지를 찾지 못했습니다.")

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

    run_post_estimate_location_action()


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

    while index < text_length:
        if stop_flag:
            break

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


# ---------------- 사전 실행 자동화 함수 ----------------
def find_chrome() -> Optional[str]:
    for path in CHROME_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


def force_chrome_window_geometry(window) -> None:
    try:
        window.moveTo(WIN_X, WIN_Y)
        time.sleep(0.05)
        window.resizeTo(WIN_W, WIN_H)
        time.sleep(0.1)
    except Exception:
        pass


def get_chrome_windows():
    seen = set()
    windows = []
    for title_fragment in ("Chrome", "네이버", "Naver", "naver.com"):
        for w in gw.getWindowsWithTitle(title_fragment):
            hwnd = getattr(w, "_hWnd", None)
            if hwnd in seen:
                continue
            seen.add(hwnd)
            windows.append(w)
    return windows


def activate_specific_chrome_window(window, adjust_geometry: bool = False) -> bool:
    if window is None:
        return False
    try:
        if window.isMinimized:
            window.restore()
            time.sleep(0.15)
        if adjust_geometry:
            force_chrome_window_geometry(window)
            time.sleep(0.1)
        window.activate()
        time.sleep(0.2)
        return True
    except Exception:
        return False


def activate_chrome_window(adjust_geometry: bool = False) -> bool:
    global preferred_chrome_hwnd

    if preferred_chrome_hwnd is not None:
        for w in get_chrome_windows():
            if getattr(w, "_hWnd", None) == preferred_chrome_hwnd:
                if activate_specific_chrome_window(w, adjust_geometry=adjust_geometry):
                    return True

    for w in get_chrome_windows():
        if activate_specific_chrome_window(w, adjust_geometry=adjust_geometry):
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

        activate_chrome_window()

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

    activate_chrome_window()

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
    activate_chrome_window()

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
    activate_chrome_window()
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.05)
    paste_text_safely(blog_write_url)
    pyautogui.press("enter")


def try_cnlth_before_help_header() -> None:
    time.sleep(1.5)
    activate_chrome_window()
    time.sleep(0.2)

    click_image_limited(CNLTH_TEMPLATE, attempts=2, confidence=0.85, delay_sec=0.4)


def dismiss_help_popup_or_arrow_up() -> None:
    time.sleep(1.0)
    activate_chrome_window()
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

        activate_chrome_window()
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
    activate_chrome_window()
    time.sleep(0.15)
    pyautogui.click(TITLE_CLICK_X, TITLE_CLICK_Y)
    time.sleep(0.25)


def click_body_area_by_coordinate() -> None:
    """본문 입력칸을 좌표로 클릭합니다."""
    activate_chrome_window()
    time.sleep(0.15)
    pyautogui.click(BODY_CLICK_X, BODY_CLICK_Y)
    time.sleep(0.25)


def center_align_title_and_body() -> None:
    """
    제목과 본문을 모두 가운데 정렬로 맞춘 뒤 다시 제목칸으로 돌아옵니다.
    기존 down/up 방식은 두 번째 블로그에서 포커스가 꼬이면 다음 동작이 멈출 수 있어
    제목 클릭 -> 제목 가운데 정렬 -> 본문 클릭 -> 본문 가운데 정렬 -> 제목 재클릭 방식으로 변경했습니다.
    """
    time.sleep(0.25)

    pyautogui.hotkey("ctrl", "alt", "c")
    time.sleep(0.2)

    click_body_area_by_coordinate()
    pyautogui.hotkey("ctrl", "alt", "c")
    time.sleep(0.2)

    click_title_area_by_coordinate()
    time.sleep(0.2)


def run_se_action(blog_label: str = "") -> bool:
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

    center_align_title_and_body()
    return True


def run_pre_typing_action(naver_id: str, naver_password: str, blog_write_url: str, blog_label: str, use_incognito: bool = True) -> None:
    global preferred_chrome_hwnd

    chrome = find_chrome()
    if not chrome:
        raise RuntimeError("Chrome 설치 경로를 찾을 수 없습니다.")

    if not naver_id:
        raise RuntimeError(f"{blog_label} 네이버 아이디를 입력하세요.")
    if not naver_password:
        raise RuntimeError(f"{blog_label} 네이버 비밀번호를 입력하세요.")
    if not blog_write_url:
        raise RuntimeError(f"{blog_label} 블로그 글쓰기 주소를 입력하세요.")

    before_hwnds = {getattr(w, "_hWnd", None) for w in get_chrome_windows()}

    launch_cmd = [
        chrome,
        "--new-window",
        f"--window-size={WIN_W},{WIN_H}",
        f"--window-position={WIN_X},{WIN_Y}",
        "https://www.naver.com",
    ]
    if use_incognito:
        launch_cmd.insert(1, "--incognito")
        set_status(f"{blog_label} 사전 작업: 시크릿 크롬 창 실행 중...")
    else:
        set_status(f"{blog_label} 사전 작업: 일반 크롬 창 실행 중...")

    subprocess.Popen(launch_cmd)
    time.sleep(3.0)

    target_window = None
    deadline = time.time() + 8.0
    while time.time() < deadline:
        if stop_flag:
            return
        current_windows = get_chrome_windows()
        new_windows = [w for w in current_windows if getattr(w, "_hWnd", None) not in before_hwnds]
        if new_windows:
            target_window = new_windows[-1]
            break
        time.sleep(0.2)

    if target_window is None:
        current_windows = get_chrome_windows()
        if current_windows:
            target_window = current_windows[-1]

    if target_window is None:
        raise RuntimeError(f"{blog_label} 새 크롬 창을 찾지 못했습니다.")

    preferred_chrome_hwnd = getattr(target_window, "_hWnd", None)

    set_status(f"{blog_label} 사전 작업: 크롬 창 활성화 중...")
    force_chrome_window_geometry(target_window)
    if not activate_specific_chrome_window(target_window):
        activate_chrome_window()

    time.sleep(0.2)

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
    if not run_se_action(blog_label):
        return

    set_status(f"{blog_label} 사전 작업 완료")


def move_to_body_after_title(blog_label: str) -> None:
    pyautogui.press("enter")
    if "2" in blog_label:
        time.sleep(1.8)
    else:
        time.sleep(1.2)

    # 엔터 후 포커스가 본문으로 안 내려가는 경우가 있어 본문 위치를 한 번 더 클릭합니다.
    click_body_area_by_coordinate()


def run_blog_typing_workflow(blog_label: str, blog_index: int, naver_id: str, naver_password: str, blog_write_url: str, title: str, content: str, use_incognito: bool = True) -> None:
    run_pre_typing_action(naver_id, naver_password, blog_write_url, blog_label, use_incognito=use_incognito)

    if stop_flag:
        return

    time.sleep(1.0)

    set_status(f"{blog_label} 제목 입력 중...")
    human_like_typing(title, blog_index=blog_index)

    if stop_flag:
        return

    move_to_body_after_title(blog_label)

    if content:
        set_status(f"{blog_label} 본문 입력 중...")
        human_like_typing(content, blog_index=blog_index)


def start_typing():
    global running, stop_flag

    if running:
        return

    title1, content1, title2, content2 = get_title_and_content_values()
    blog_mode = int(blog_run_mode_var.get())

    if not title1 and not content1:
        messagebox.showwarning("경고", "첫번째 블로그 제목 또는 내용을 입력하세요.")
        return

    if not title1:
        messagebox.showwarning("경고", "첫번째 블로그 제목을 입력하세요.")
        return

    if blog_mode == 2:
        if not title2 and not content2:
            messagebox.showwarning("경고", "두번째 블로그 쓰기를 선택했으면 두번째 제목 또는 내용을 입력하세요.")
            return
        if not title2:
            messagebox.showwarning("경고", "두번째 블로그 제목을 입력하세요.")
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

            if blog_mode == 2:
                set_status("블로그 1 완료, 블로그 2 일반 크롬 새 창 준비 중...")

                if stop_flag:
                    set_status("작업 중지됨")
                    return

                time.sleep(1.0)

                run_blog_typing_workflow(
                    "블로그 2",
                    2,
                    naver_id_var_2.get().strip(),
                    naver_password_var_2.get().strip(),
                    blog_write_url_var_2.get().strip(),
                    title2,
                    content2,
                    use_incognito=False,
                )

            if stop_flag:
                set_status("작업 중지됨")
            else:
                if blog_mode == 2:
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
def copy_prompt(index: int):
    script = prompt_text_input.get("1.0", tk.END).strip()

    if not script:
        messagebox.showerror("오류", "내용을 입력하세요.")
        return

    try:
        prompt = prompt_templates[index].format(script=script)
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


def img_select_folder():
    folder = filedialog.askdirectory()
    if folder:
        img_folder_path.set(folder)
        save_config()


def start_img_process():
    folder = img_folder_path.get().strip()
    keyword_input = img_keywords.get().strip()

    if not folder or not os.path.exists(folder):
        messagebox.showerror("오류", "폴더를 먼저 선택해주세요.")
        return

    if not keyword_input:
        messagebox.showerror("오류", "키워드를 입력해주세요.")
        return

    if not HEIC_AVAILABLE:
        has_heic = any(
            file_name.lower().endswith((".heic", ".heif"))
            for file_name in os.listdir(folder)
        )
        if has_heic:
            messagebox.showerror(
                "오류",
                "HEIC/HEIF 파일을 처리하려면 pillow-heif 설치가 필요합니다.\n\n"
                "설치 명령어:\n"
                "C:\\Users\\uc808\\AppData\\Local\\Programs\\Python\\Python313\\python.exe -m pip install pillow-heif"
            )
            return

    image_files = get_image_files(folder)
    if not image_files:
        messagebox.showerror("오류", "이미지 파일이 없습니다.")
        return

    keywords = [k.strip() for k in keyword_input.split(",") if k.strip()]
    if not keywords:
        messagebox.showerror("오류", "유효한 키워드를 입력해주세요.")
        return

    base_name = "_".join(keywords)

    try:
        total = len(image_files)
        count = 1

        for file_name in image_files:
            old_path = os.path.join(folder, file_name)
            new_filename = f"{base_name}_{count}.jpg"
            new_path = os.path.join(folder, new_filename)

            with load_image_with_exif_fix(old_path) as img:
                rgb_img = img.convert("RGB")
                rgb_img.save(new_path, "JPEG", quality=100)

            if os.path.abspath(old_path) != os.path.abspath(new_path):
                os.remove(old_path)

            img_status_var.set(f"처리 중. ({count}/{total})")
            root.update_idletasks()
            count += 1

        img_status_var.set("완료되었습니다. 이름 변경 + JPG 변환 완료")
        messagebox.showinfo("완료", "모든 이미지가 변환 및 이름 변경 완료되었습니다.")
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

settings_frame = ttk.LabelFrame(right_f, text="  ⚙️ 블로그 계정 / 실행 설정  ", padding=(15, 15))
settings_frame.pack(fill="x", pady=(0, 10))

mode_frame = tk.Frame(settings_frame, bg=BG_PANEL)
mode_frame.pack(fill="x", pady=(0, 12))
tk.Label(mode_frame, text="실행 방식", font=("맑은 고딕", 10, "bold"), bg=BG_PANEL, fg=TEXT_MAIN).pack(side="left")
ttk.Radiobutton(mode_frame, text="블로그 1개 쓰기", variable=blog_run_mode_var, value=1, command=save_config).pack(side="left", padx=(15, 10))
ttk.Radiobutton(mode_frame, text="블로그 2개 쓰기", variable=blog_run_mode_var, value=2, command=save_config).pack(side="left")

account_wrap = tk.Frame(settings_frame, bg=BG_PANEL)
account_wrap.pack(fill="x")

account1_frame = ttk.LabelFrame(account_wrap, text="  첫번째 블로그 계정  ", padding=(12, 12))
account1_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
account2_frame = ttk.LabelFrame(account_wrap, text="  두번째 블로그 계정  ", padding=(12, 12))
account2_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

for parent, id_var, pw_var, url_var in (
    (account1_frame, naver_id_var_1, naver_password_var_1, blog_write_url_var_1),
    (account2_frame, naver_id_var_2, naver_password_var_2, blog_write_url_var_2),
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
phone_right_frame = ttk.LabelFrame(phone_wrap_frame, text="  📞 블로그 2 견적상담 전화번호  ", padding=(12, 12))
phone_right_frame.pack(side="left", fill="x", expand=True, padx=(5, 0))

phone_number_var_1 = tk.StringVar(value=DEFAULT_PHONE_NUMBER)
phone_number_var_2 = tk.StringVar(value=DEFAULT_PHONE_NUMBER)

phone_entry_1 = tk.Entry(phone_left_frame, textvariable=phone_number_var_1, font=("맑은 고딕", 11, "bold"), relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, justify="center", fg=TEXT_MAIN)
phone_entry_1.pack(fill="x", ipady=6)
phone_entry_1.bind("<FocusOut>", lambda event: save_config())

phone_entry_2 = tk.Entry(phone_right_frame, textvariable=phone_number_var_2, font=("맑은 고딕", 11, "bold"), relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, justify="center", fg=TEXT_MAIN)
phone_entry_2.pack(fill="x", ipady=6)
phone_entry_2.bind("<FocusOut>", lambda event: save_config())

editor_wrap = ttk.PanedWindow(right_f, orient=tk.HORIZONTAL)
editor_wrap.pack(fill="both", expand=True, pady=5)

blog1_editor_frame = ttk.LabelFrame(editor_wrap, text="  📝 첫번째 블로그 글  ", padding=(12, 12))
blog2_editor_frame = ttk.LabelFrame(editor_wrap, text="  📝 두번째 블로그 글  ", padding=(12, 12))
editor_wrap.add(blog1_editor_frame, weight=1)
editor_wrap.add(blog2_editor_frame, weight=1)

# 첫번째 블로그 입력창
tk.Label(blog1_editor_frame, text="📰 첫번째 제목", font=("맑은 고딕", 10, "bold"), bg=BG_PANEL, fg=TEXT_MAIN).pack(anchor="w", pady=(0,4))
title_var_1 = tk.StringVar()
title_entry_1 = tk.Entry(blog1_editor_frame, textvariable=title_var_1, font=("맑은 고딕", 11), relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG)
title_entry_1.pack(fill="x", pady=(0, 10), ipady=8)

tk.Label(blog1_editor_frame, text="✍️ 첫번째 내용", font=("맑은 고딕", 10, "bold"), bg=BG_PANEL, fg=TEXT_MAIN).pack(anchor="w", pady=(0,4))
editor_1 = tk.Text(blog1_editor_frame, font=("맑은 고딕", 11), undo=True, relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, padx=10, pady=10)
editor_1.pack(fill="both", expand=True)

# 두번째 블로그 입력창
tk.Label(blog2_editor_frame, text="📰 두번째 제목", font=("맑은 고딕", 10, "bold"), bg=BG_PANEL, fg=TEXT_MAIN).pack(anchor="w", pady=(0,4))
title_var_2 = tk.StringVar()
title_entry_2 = tk.Entry(blog2_editor_frame, textvariable=title_var_2, font=("맑은 고딕", 11), relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG)
title_entry_2.pack(fill="x", pady=(0, 10), ipady=8)

tk.Label(blog2_editor_frame, text="✍️ 두번째 내용", font=("맑은 고딕", 10, "bold"), bg=BG_PANEL, fg=TEXT_MAIN).pack(anchor="w", pady=(0,4))
editor_2 = tk.Text(blog2_editor_frame, font=("맑은 고딕", 11), undo=True, relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, padx=10, pady=10)
editor_2.pack(fill="both", expand=True)

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

tk.Label(tab2, text="유튜브 대본(멘트) 입력", font=("맑은 고딕", 12, "bold"), bg=BG_MAIN, fg=TEXT_MAIN).pack(pady=(20, 5))

prompt_text_input = tk.Text(tab2, font=("맑은 고딕", 11), height=16, relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, padx=15, pady=15)
prompt_text_input.pack(fill="both", expand=True, padx=30, pady=5)

prompt_manage_wrap = tk.Frame(tab2, bg=BG_MAIN)
prompt_manage_wrap.pack(fill="both", padx=30, pady=20)

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
img_keywords = tk.StringVar()
img_status_var = tk.StringVar()

init_app_storage()
load_config()

tk.Label(tab3, text="작업할 폴더 선택", font=("맑은 고딕", 12, "bold"), bg=BG_MAIN, fg=TEXT_MAIN).pack(pady=(30, 10))

btn_folder = create_flat_button(tab3, "📂 폴더 찾아보기", img_select_folder, SECONDARY, SECONDARY_HOVER, font=("맑은 고딕", 10, "bold"), pady=8)
btn_folder.pack()
tk.Label(tab3, textvariable=img_folder_path, fg=ACCENT, bg=BG_MAIN, font=("맑은 고딕", 10, "bold"), wraplength=700).pack(pady=(10, 5))

if HEIC_AVAILABLE:
    heic_text = "✅ HEIC/HEIF 이미지 지원 활성화됨"
    heic_color = SUCCESS
else:
    heic_text = f"❌ HEIC 지원 비활성화됨: {HEIC_ERROR}" if HEIC_ERROR else "❌ HEIC 지원 비활성화됨"
    heic_color = DANGER

tk.Label(tab3, text=heic_text, fg=heic_color, font=("맑은 고딕", 10, "bold"), bg=BG_MAIN).pack(pady=(5, 20))

tk.Label(tab3, text="이미지 키워드 입력 (쉼표 구분)", font=("맑은 고딕", 12, "bold"), bg=BG_MAIN, fg=TEXT_MAIN).pack(pady=(10, 10))
img_entry = tk.Entry(tab3, textvariable=img_keywords, font=("맑은 고딕", 11), width=50, relief="flat", highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT, bg=INPUT_BG, justify="center")
img_entry.pack(pady=5, ipady=8)

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

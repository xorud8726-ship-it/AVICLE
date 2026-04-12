import os
import sys
import json
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
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()

CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
)

LOGIN_TEMPLATE = os.path.join(BASE_DIR, "naver_login.png")
HELP_HEADER_TEMPLATE = os.path.join(BASE_DIR, "help_header.png")
SE_TEMPLATE = os.path.join(BASE_DIR, "se.png")
EMDFHR_TEMPLATE = os.path.join(BASE_DIR, "emdfhr.png")
CNLTH_TEMPLATE = os.path.join(BASE_DIR, "cnlth.png")
RINK_TEMPLATE = os.path.join(BASE_DIR, "rink.png")
URL_TEMPLATE = os.path.join(BASE_DIR, "url.png")

WIN_X, WIN_Y = 0, 0
WIN_W, WIN_H = 837, 1037

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

DEFAULT_WATERMARK_FILENAME = "Gemini_Generated_Image_owskk1owskk1owsk.png"
DEFAULT_WATERMARK_SCALE_RATIO = 0.27
DEFAULT_WATERMARK_TOP_MARGIN_PX = 0
DEFAULT_WATERMARK_RIGHT_MARGIN_PX = 0

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
def save_config():
    data = {
        "folder_path": img_folder_path.get(),
        "watermark_path": img_watermark_path.get().strip(),
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
    try:
        config_path = os.path.join(BASE_DIR, CONFIG_FILE)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass


def load_config():
    global prompt_templates, prompt_button_names

    config_path = os.path.join(BASE_DIR, CONFIG_FILE)
    if not os.path.exists(config_path):
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        img_folder_path.set(data.get("folder_path", ""))
        img_watermark_path.set(str(data.get("watermark_path", get_default_watermark_path())).strip())

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
    return BASE_DIR


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

    txt_folder = get_txt_folder()
    files = [f for f in os.listdir(txt_folder) if f.lower().endswith(".txt")]
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

    if os.path.exists(full_path):
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
    old_full_path = os.path.join(get_txt_folder(), old_name)
    new_full_path = os.path.join(get_txt_folder(), new_full_name)

    if os.path.exists(new_full_path) and new_full_name != old_name:
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
        full_path = os.path.join(get_txt_folder(), file_name)
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


def activate_specific_chrome_window(window) -> bool:
    if window is None:
        return False
    try:
        if window.isMinimized:
            window.restore()
            time.sleep(0.15)
        window.activate()
        time.sleep(0.2)
        force_chrome_window_geometry(window)
        return True
    except Exception:
        return False


def activate_chrome_window() -> bool:
    global preferred_chrome_hwnd

    if preferred_chrome_hwnd is not None:
        for w in get_chrome_windows():
            if getattr(w, "_hWnd", None) == preferred_chrome_hwnd:
                if activate_specific_chrome_window(w):
                    return True

    for w in get_chrome_windows():
        if activate_specific_chrome_window(w):
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
    pyautogui.click(WIN_X + WIN_W // 2, WIN_Y + 110)
    time.sleep(0.03)

    pyautogui.keyDown("shift")
    try:
        for _ in range(60):
            if stop_flag:
                break
            pyautogui.scroll(-120)
    finally:
        pyautogui.keyUp("shift")

    time.sleep(0.1)


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
    """
    help_header.png 찾기 전에 cnlth.png를 먼저 최대 2번 찾습니다.
    찾으면 클릭하고,
    2번 찾아도 없으면 바로 다음 help_header 로직으로 넘어갑니다.
    """
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


def center_align_twice_with_down_then_up() -> None:
    time.sleep(0.25)
    pyautogui.hotkey("ctrl", "alt", "c")
    time.sleep(0.12)

    pyautogui.press("down")
    time.sleep(0.12)

    pyautogui.hotkey("ctrl", "alt", "c")
    time.sleep(0.12)

    pyautogui.press("up")
    time.sleep(0.2)


def run_se_action() -> bool:
    ok = click_image_forever(SE_TEMPLATE, confidence=0.85)
    if not ok:
        return False
    center_align_twice_with_down_then_up()
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

    set_status(f"{blog_label} 사전 작업: se 동작 실행 중...")
    if not run_se_action():
        return

    set_status(f"{blog_label} 사전 작업 완료")


def move_to_body_after_title(blog_label: str) -> None:
    pyautogui.press("enter")
    if "2" in blog_label:
        time.sleep(1.8)
    else:
        time.sleep(1.2)


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

    tk.Label(
        win,
        text="아래 프롬프트를 수정하세요. 반드시 마지막에 {script} 를 포함해야 합니다.",
        font=("맑은 고딕", 10, "bold"),
        fg="blue"
    ).pack(pady=10)

    text = tk.Text(win, font=("맑은 고딕", 10), undo=True)
    text.pack(fill="both", expand=True, padx=15, pady=10)
    text.insert("1.0", prompt_templates[index])

    bottom = tk.Frame(win)
    bottom.pack(fill="x", padx=15, pady=10)

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

    tk.Button(bottom, text="기본값 복원", command=reset_default).pack(side="left", padx=5)
    tk.Button(bottom, text="저장", command=save_prompt, bg="#007bff", fg="white").pack(side="right", padx=5)
    tk.Button(bottom, text="닫기", command=win.destroy).pack(side="right", padx=5)


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


# ---------------- [탭 3] 이미지 일괄 변환 및 이름 변경 ----------------
def get_default_watermark_path():
    return os.path.join(BASE_DIR, DEFAULT_WATERMARK_FILENAME)


def ensure_rgba(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        return img.convert("RGBA")
    return img


def trim_transparent_edges(img: Image.Image) -> Image.Image:
    img = ensure_rgba(img)
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def load_image_with_exif_fix(path: str) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return img


def apply_top_right_watermark(base_img: Image.Image, watermark_img: Image.Image) -> Image.Image:
    base = ensure_rgba(base_img.copy())
    watermark = trim_transparent_edges(watermark_img.copy())

    base_w, base_h = base.size
    wm_w, wm_h = watermark.size

    if base_w <= 0 or base_h <= 0 or wm_w <= 0 or wm_h <= 0:
        return base

    target_wm_width = max(1, int(base_w * DEFAULT_WATERMARK_SCALE_RATIO))
    new_w = target_wm_width
    new_h = max(1, int(wm_h * (new_w / wm_w)))
    watermark = watermark.resize((new_w, new_h), Image.LANCZOS)

    wm_w, wm_h = watermark.size
    x = max(0, base_w - wm_w - DEFAULT_WATERMARK_RIGHT_MARGIN_PX)
    y = max(0, DEFAULT_WATERMARK_TOP_MARGIN_PX)

    base.alpha_composite(watermark, (x, y))
    return base


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


def img_select_watermark():
    file_path = filedialog.askopenfilename(
        title="워터마크 이미지 선택",
        filetypes=[
            ("이미지 파일", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"),
            ("모든 파일", "*.*"),
        ],
    )
    if file_path:
        img_watermark_path.set(file_path)
        save_config()


def start_img_process():
    folder = img_folder_path.get().strip()
    keyword_input = img_keywords.get().strip()
    watermark_path = img_watermark_path.get().strip()

    if not folder or not os.path.exists(folder):
        messagebox.showerror("오류", "폴더를 먼저 선택해주세요.")
        return

    if not keyword_input:
        messagebox.showerror("오류", "키워드를 입력해주세요.")
        return

    if not watermark_path or not os.path.isfile(watermark_path):
        messagebox.showerror("오류", "워터마크 이미지를 먼저 선택해주세요.")
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
        watermark_source = load_image_with_exif_fix(watermark_path).convert("RGBA")
        watermark_source = trim_transparent_edges(watermark_source)
    except Exception as e:
        messagebox.showerror("오류", f"워터마크 이미지 로드 실패:\n{str(e)}")
        return

    try:
        total = len(image_files)
        count = 1

        for file_name in image_files:
            old_path = os.path.join(folder, file_name)
            new_filename = f"{base_name}_{count}.jpg"
            new_path = os.path.join(folder, new_filename)

            with load_image_with_exif_fix(old_path) as img:
                result_img = apply_top_right_watermark(img, watermark_source)
                rgb_img = result_img.convert("RGB")
                rgb_img.save(new_path, "JPEG", quality=100)

            if os.path.abspath(old_path) != os.path.abspath(new_path):
                os.remove(old_path)

            img_status_var.set(f"처리 중... ({count}/{total})")
            root.update_idletasks()
            count += 1

        img_status_var.set("완료되었습니다. 이름 변경 + JPG 변환 + 워터마크 삽입 완료")
        messagebox.showinfo("완료", "모든 이미지가 변환, 이름 변경, 워터마크 삽입까지 완료되었습니다.")
    except Exception as e:
        messagebox.showerror("오류", f"처리 중 오류 발생:\n{str(e)}")



# ---------------- GUI ----------------
root = tk.Tk()
root.title("블로그 마스터 자동화 툴 (통합 버전)")
root.geometry("1500x960")

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

# --- 탭1: 파일 관리 및 자동 타이핑 ---
tab1 = tk.Frame(notebook)
notebook.add(tab1, text="자동 타이핑 및 파일 관리")

left_f = tk.Frame(tab1, width=280)
left_f.pack(side="left", fill="y", padx=10, pady=10)

right_container = tk.Frame(tab1)
right_container.pack(side="right", fill="both", expand=True, padx=10, pady=10)

right_canvas = tk.Canvas(right_container, highlightthickness=0)
right_scrollbar = ttk.Scrollbar(right_container, orient="vertical", command=right_canvas.yview)
right_f = tk.Frame(right_canvas)

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

tk.Label(left_f, text="📁 파일 목록", font=("맑은 고딕", 10, "bold")).pack()

listbox = tk.Listbox(left_f, height=25, font=("맑은 고딕", 9), exportselection=False)
listbox.pack(fill="both", expand=True)
listbox.bind("<<ListboxSelect>>", on_select_txt)
listbox.bind("<FocusOut>", on_listbox_focus_out)

f_btn_f = tk.Frame(left_f)
f_btn_f.pack(fill="x", pady=5)

tk.Button(f_btn_f, text="새 파일", command=create_txt_file).pack(side="left", expand=True, fill="x")
tk.Button(f_btn_f, text="이름 변경", command=rename_txt_file).pack(side="left", expand=True, fill="x")
tk.Button(left_f, text="목록 새로고침", command=load_txt_files).pack(fill="x")

blog_run_mode_var = tk.IntVar(value=1)
naver_id_var_1 = tk.StringVar(value=DEFAULT_NAVER_ID_1)
naver_password_var_1 = tk.StringVar(value=DEFAULT_NAVER_PASSWORD_1)
blog_write_url_var_1 = tk.StringVar(value=DEFAULT_BLOG_WRITE_URL_1)
naver_id_var_2 = tk.StringVar(value=DEFAULT_NAVER_ID_2)
naver_password_var_2 = tk.StringVar(value=DEFAULT_NAVER_PASSWORD_2)
blog_write_url_var_2 = tk.StringVar(value=DEFAULT_BLOG_WRITE_URL_2)

settings_frame = tk.LabelFrame(right_f, text="블로그 계정 / 실행 설정", padx=10, pady=10)
settings_frame.pack(fill="x", pady=(0, 8))

mode_frame = tk.Frame(settings_frame)
mode_frame.pack(fill="x", pady=(0, 8))
tk.Label(mode_frame, text="실행 방식", font=("맑은 고딕", 10, "bold")).pack(side="left")
tk.Radiobutton(mode_frame, text="블로그 1개 쓰기", variable=blog_run_mode_var, value=1, command=save_config).pack(side="left", padx=(15, 10))
tk.Radiobutton(mode_frame, text="블로그 2개 쓰기", variable=blog_run_mode_var, value=2, command=save_config).pack(side="left")

account_wrap = tk.Frame(settings_frame)
account_wrap.pack(fill="x")

account1_frame = tk.LabelFrame(account_wrap, text="첫번째 블로그 계정", padx=8, pady=8)
account1_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
account2_frame = tk.LabelFrame(account_wrap, text="두번째 블로그 계정", padx=8, pady=8)
account2_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

for parent, id_var, pw_var, url_var in (
    (account1_frame, naver_id_var_1, naver_password_var_1, blog_write_url_var_1),
    (account2_frame, naver_id_var_2, naver_password_var_2, blog_write_url_var_2),
):
    tk.Label(parent, text="네이버 아이디", font=("맑은 고딕", 9, "bold")).pack(anchor="w")
    entry_id = tk.Entry(parent, textvariable=id_var, font=("맑은 고딕", 10))
    entry_id.pack(fill="x", ipady=4, pady=(0, 6))
    entry_id.bind("<FocusOut>", lambda event: save_config())

    tk.Label(parent, text="네이버 비밀번호", font=("맑은 고딕", 9, "bold")).pack(anchor="w")
    entry_pw = tk.Entry(parent, textvariable=pw_var, font=("맑은 고딕", 10), show="*")
    entry_pw.pack(fill="x", ipady=4, pady=(0, 6))
    entry_pw.bind("<FocusOut>", lambda event: save_config())

    tk.Label(parent, text="블로그 글쓰기 주소", font=("맑은 고딕", 9, "bold")).pack(anchor="w")
    entry_url = tk.Entry(parent, textvariable=url_var, font=("맑은 고딕", 10))
    entry_url.pack(fill="x", ipady=4)
    entry_url.bind("<FocusOut>", lambda event: save_config())

phone_wrap_frame = tk.Frame(right_f)
phone_wrap_frame.pack(fill="x", pady=(0, 8))

phone_left_frame = tk.LabelFrame(phone_wrap_frame, text="블로그 1 견적상담하기 전화번호", padx=8, pady=8)
phone_left_frame.pack(side="left", fill="x", expand=True, padx=(0, 4))
phone_right_frame = tk.LabelFrame(phone_wrap_frame, text="블로그 2 견적상담하기 전화번호", padx=8, pady=8)
phone_right_frame.pack(side="left", fill="x", expand=True, padx=(4, 0))

phone_number_var_1 = tk.StringVar(value=DEFAULT_PHONE_NUMBER)
phone_number_var_2 = tk.StringVar(value=DEFAULT_PHONE_NUMBER)

phone_entry_1 = tk.Entry(phone_left_frame, textvariable=phone_number_var_1, font=("맑은 고딕", 11))
phone_entry_1.pack(fill="x", ipady=6)
phone_entry_1.bind("<FocusOut>", lambda event: save_config())

phone_entry_2 = tk.Entry(phone_right_frame, textvariable=phone_number_var_2, font=("맑은 고딕", 11))
phone_entry_2.pack(fill="x", ipady=6)
phone_entry_2.bind("<FocusOut>", lambda event: save_config())

editor_wrap = tk.PanedWindow(right_f, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
editor_wrap.pack(fill="both", expand=True, pady=5)

blog1_editor_frame = tk.LabelFrame(editor_wrap, text="첫번째 블로그 글", padx=8, pady=8)
blog2_editor_frame = tk.LabelFrame(editor_wrap, text="두번째 블로그 글", padx=8, pady=8)
editor_wrap.add(blog1_editor_frame, stretch="always")
editor_wrap.add(blog2_editor_frame, stretch="always")

# 첫번째 블로그 입력창

tk.Label(blog1_editor_frame, text="📰 첫번째 제목", font=("맑은 고딕", 10, "bold")).pack(anchor="w")
title_var_1 = tk.StringVar()
title_entry_1 = tk.Entry(blog1_editor_frame, textvariable=title_var_1, font=("맑은 고딕", 11))
title_entry_1.pack(fill="x", pady=(0, 8), ipady=6)

tk.Label(blog1_editor_frame, text="📝 첫번째 내용", font=("맑은 고딕", 10, "bold")).pack(anchor="w")
editor_1 = tk.Text(blog1_editor_frame, font=("맑은 고딕", 11), undo=True)
editor_1.pack(fill="both", expand=True)

# 두번째 블로그 입력창

tk.Label(blog2_editor_frame, text="📰 두번째 제목", font=("맑은 고딕", 10, "bold")).pack(anchor="w")
title_var_2 = tk.StringVar()
title_entry_2 = tk.Entry(blog2_editor_frame, textvariable=title_var_2, font=("맑은 고딕", 11))
title_entry_2.pack(fill="x", pady=(0, 8), ipady=6)

tk.Label(blog2_editor_frame, text="📝 두번째 내용", font=("맑은 고딕", 10, "bold")).pack(anchor="w")
editor_2 = tk.Text(blog2_editor_frame, font=("맑은 고딕", 11), undo=True)
editor_2.pack(fill="both", expand=True)

speed_frame = tk.LabelFrame(right_f, text="⚡ 타이핑 속도 설정 (CPM)")
speed_frame.pack(fill="x", pady=5)

speed_value_var = tk.StringVar(value=f"현재 타수: {DEFAULT_SPEED_CPM} CPM")
tk.Label(speed_frame, textvariable=speed_value_var, font=("맑은 고딕", 10, "bold"), fg="#0d6efd").pack(anchor="w", padx=10, pady=(6, 0))

speed_scale = tk.Scale(
    speed_frame,
    from_=100,
    to_=1200,
    orient=tk.HORIZONTAL,
    resolution=10,
    showvalue=False,
    command=update_speed_label,
)
speed_scale.set(DEFAULT_SPEED_CPM)
speed_scale.pack(fill="x", padx=10)
update_speed_label()
speed_scale.bind("<ButtonRelease-1>", lambda event: save_config())

tk.Button(
    right_f,
    text="💾 첫번째 제목/내용 + 두번째 제목/내용 저장",
    command=save_txt_file,
    bg="#007bff",
    fg="white",
    font=("맑은 고딕", 11, "bold"),
    height=2,
).pack(fill="x", pady=10)

status_var = tk.StringVar(value="대기 중")
tk.Label(right_f, textvariable=status_var, fg="#28a745", font=("맑은 고딕", 13, "bold")).pack()
tk.Label(
    right_f,
    text="[F2] 블로그 1 시크릿 창 실행 → 필요시 블로그 2 일반 크롬 새 창 실행 → 제목 입력 → Enter 1번 → 내용 입력 | 견적상담하기 자동 전화링크 | [ESC] 중지",
    fg="#dc3545",
    font=("맑은 고딕", 10, "bold")
).pack()

# --- 탭2: 블로그 프롬프트 생성 ---
tab2 = tk.Frame(notebook)
notebook.add(tab2, text="블로그 프롬프트")

tk.Label(tab2, text="유튜브 대본(멘트) 입력", font=("맑은 고딕", 10, "bold")).pack(pady=10)

prompt_text_input = tk.Text(tab2, font=("맑은 고딕", 10), height=16)
prompt_text_input.pack(fill="both", expand=True, padx=20, pady=5)

prompt_manage_wrap = tk.Frame(tab2)
prompt_manage_wrap.pack(fill="both", padx=20, pady=15)

for i in range(4):
    row = tk.LabelFrame(prompt_manage_wrap, text=f"프롬프트 {i + 1}", padx=10, pady=10)
    row.pack(fill="x", pady=6)

    copy_btn = tk.Button(
        row,
        text=prompt_button_names[i],
        command=lambda idx=i: copy_prompt(idx),
        bg="#28a745",
        fg="white",
        font=("맑은 고딕", 11, "bold"),
        height=2,
    )
    copy_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
    prompt_copy_buttons.append(copy_btn)

    edit_btn = tk.Button(
        row,
        text=f"프롬프트 {i + 1} 내용 수정",
        command=lambda idx=i: edit_prompt_template(idx),
        bg="#6c757d",
        fg="white",
        font=("맑은 고딕", 10, "bold"),
        height=2,
    )
    edit_btn.pack(side="left", fill="x", expand=True, padx=5)
    prompt_edit_buttons.append(edit_btn)

    name_btn = tk.Button(
        row,
        text=f"프롬프트 {i + 1} 버튼 이름 수정",
        command=lambda idx=i: edit_prompt_button_name(idx),
        bg="#fd7e14",
        fg="white",
        font=("맑은 고딕", 10, "bold"),
        height=2,
    )
    name_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))
    prompt_name_buttons.append(name_btn)

# --- 탭3: 이미지 변환 도구 ---
tab3 = tk.Frame(notebook)
notebook.add(tab3, text="이미지 일괄 변환 및 이름 변경")

img_folder_path = tk.StringVar()
img_watermark_path = tk.StringVar(value=get_default_watermark_path())
img_keywords = tk.StringVar()
img_status_var = tk.StringVar()

load_config()

tk.Label(tab3, text="폴더 선택", font=("맑은 고딕", 10, "bold")).pack(pady=10)
tk.Button(tab3, text="폴더 선택", command=img_select_folder, width=15).pack()
tk.Label(tab3, textvariable=img_folder_path, fg="blue", wraplength=700).pack(pady=5)

tk.Label(tab3, text="워터마크 이미지 선택", font=("맑은 고딕", 10, "bold")).pack(pady=(12, 6))
tk.Button(tab3, text="워터마크 선택", command=img_select_watermark, width=15).pack()
tk.Label(tab3, textvariable=img_watermark_path, fg="#6f42c1", wraplength=700).pack(pady=5)

tk.Label(
    tab3,
    text="워터마크는 오른쪽 상단에 자동 삽입됩니다. 투명 여백은 자동 제거되며, 이전 요청값대로 더 크게 붙습니다.",
    fg="#0d6efd",
    font=("맑은 고딕", 9, "bold"),
).pack(pady=3)

if HEIC_AVAILABLE:
    heic_text = "HEIC 지원 활성화됨"
    heic_color = "green"
else:
    heic_text = f"HEIC 지원 비활성화됨: {HEIC_ERROR}" if HEIC_ERROR else "HEIC 지원 비활성화됨"
    heic_color = "red"
heic_color = "green" if HEIC_AVAILABLE else "red"
tk.Label(tab3, text=heic_text, fg=heic_color, font=("맑은 고딕", 9, "bold")).pack(pady=2)

tk.Label(tab3, text="키워드 입력 (쉼표로 구분)", font=("맑은 고딕", 10, "bold")).pack(pady=10)
tk.Entry(tab3, textvariable=img_keywords, width=50).pack(pady=5)

tk.Button(
    tab3,
    text="시작",
    command=start_img_process,
    bg="green",
    fg="white",
    font=("맑은 고딕", 10, "bold"),
    width=15,
).pack(pady=20)

tk.Label(tab3, textvariable=img_status_var, fg="red", font=("맑은 고딕", 10, "bold")).pack()

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

# filepath: c:/IFIRST/bridge_auto_fast_final.py
from __future__ import annotations
import json, os, sys, time, threading, tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict, Optional, List, Tuple

from pywinauto import Application
from pywinauto.base_wrapper import BaseWrapper
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.timings import TimeoutError as PwaTimeout
from pywinauto.timings import Timings

# ===== 기본 설정 =====
TARGET_WINDOW_TITLE      = r"A-VICLE CODING SOFTWARE"
RETRY_CONNECT_SEC        = 5

# 기본라인 초기값
DEFAULT_COUNT            = "20"
DEFAULT_LUMA             = "50"
DEFAULT_MID              = "0"
DEFAULT_DUAL_ENABLED     = False

# 오디오(항상 적용; 빈칸이면 skip)
DEFAULT_AUDIO_OFF1       = "170"
DEFAULT_AUDIO_GAIN1      = "12000"
DEFAULT_AUDIO_OFF2       = "170"
DEFAULT_AUDIO_GAIN2      = "120"

# 속도/안정성(공격적)
EXPAND_DELAY   = 0.02
TYPE_PAUSE     = 0.0
VERIFY_DELAY   = 0.015
RETRY_SET      = 2

Timings.after_clickinput_wait    = 0.02
Timings.after_setfocus_wait      = 0.01
Timings.after_sendkeys_key_wait  = 0.0
Timings.window_find_timeout      = max(Timings.window_find_timeout, 5)

# ===== 유틸 =====
def norm_text(s: str) -> str:
    return " ".join((s or "").strip().split())

def is_key_valid(car: str, real: str) -> bool:
    return bool(norm_text(car)) and bool(norm_text(real))

def is_from_dipswitch(s: str) -> bool:
    return norm_text(s).lower() == "from dip switch"

def make_key(car: str, real: str, color: str, act: str) -> str:
    return "|".join([
        norm_text(car).casefold(),
        norm_text(real).casefold(),
        norm_text(color).casefold(),
        norm_text(act).casefold(),
    ])

def get_app_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_preset_path() -> str:
    return os.path.join(get_app_base_dir(), "avicle_presets.json")

def load_presets() -> Dict[str, Any]:
    p = get_preset_path()
    if not os.path.exists(p): return {}
    try:
        with open(p, "r", encoding="utf-8") as f: return json.load(f)
    except Exception:
        return {}

def save_presets(data: Dict[str, Any]) -> None:
    p = get_preset_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===== 실제 차종(프리셋 키 전용) =====
_REAL_MODELS_RAW = """
투싼NX4 | 2023 | 하이브리드
투싼NX4 | 2023 | 가솔린
투싼 NX4 페이스리프트 | 2024 | 가솔린
싼타페MX5 | 2024 | 가솔린
싼타페MX5 | 2024 | 하이브리드
싼타페MX5 | 2024 | 가솔린
싼타페MX5 | 2024 | 하이브리드
더뉴 싼타페 TM | 2021 | 가솔린
쏘나타DN8 | 2021 | 가솔린
쏘나타디엣지 | 2023 | 가솔린
팰리세이드 | 2019 | 가솔린
팰리세이드 | 2020 | 가솔린
팰리세이드 | 2021 | 디젤
더뉴팰리세이드 | 2023 | 가솔린
디올뉴 팰리세이드 | 2025 | 하이브리드
제네시스 GV70 Sports | 2023 | 가솔린
제네시스 G80 | 2021 | 가솔린
제네시스 G80 ELECTRIFIED | 2022 | 가솔린
제네시스 G80 스포츠 | 2022 | 가솔린
제네시스 G80 페이스리프트 | 2025 | 가솔린
제네시스 GV80 | 2020 | 가솔린
제네시스 GV80 페이스리프트 | 2020 | 가솔린
제네시스 G90 | 2020 | 가솔린
제네시스 G90 RS4 | 2022 | 가솔린
제네시스 EQ900 | 2018 | 가솔린
더뉴그랜져 IG | 2021 | LPG
더뉴그랜져 IG | 2019 | 하이브리드
그랜져GN7 | 2022 | 가솔린
그랜져GN7 | 2023 | LPG
그랜져GN7 | 2022 | 하이브리드
아이오닉5 | 2023 | 일렉
아이오닉5 페리 | 2024 | 일렉
아이오닉6 | 2024 | 일렉
아반떼 CN7 | 2023 | 가솔린
아반떼 CN7 페리 | 2024 | 가솔린
아반떼 CN7 페리 | 2024 | 하이브리드
쏘렌토 MQ4 | 2022 | 가솔린
쏘렌토 MQ4 | 2022 | 하이브리드
쏘렌토 페이스리프트 | 2024 | 가솔린
쏘렌토 페이스리프트 | 2024 | 하이브리드
카니발 페이스리프트 | 2024 | 가솔린
카니발 페이스리프트 | 2024 | 하이브리드
카니발 페이스리프트(듀얼) | 2024 | 가솔린
스포티지NQ5 | 2023 | 가솔린
스포티지NQ5 | 2023 | 하이브리드
스포티지 페이스리프트 | 2025 | 하이브리드
스포티지 페이스리프트 | 2025 | 가솔린
스팅어 마이스터 | 2023 | 가솔린
스팅어 계기판연동 | 2019 | 가솔린
모하비더마스터 | 2020 | 가솔린
모하비더마스터 | 2022 | 가솔린
K9 | 2021 | 가솔린
K9 | 2022 | 가솔린
K8 | 2022 | 가솔린,LPG
K8 | 2022 | 하이브리드
K8 페이스리프트 | 2024 | 하이브리드
K8 페이스리프트 | 2024 | 가솔린
K7 프리미어 | 2018 | 가솔린
K7 프리미어 | 2020 | LPG
K5 DL3 | 2020 | 기어봉
K5 DL3 | 2020 | 가솔린
K5 페이스리프트 | 2023 | 가솔린
K5 페이스리프트 | 2023 | 하이브리드
K5 페이스리프트(TAXI)
K3 GT | 2021 | 가솔린
셀토스 | 2024 | 가솔린
소울 부스터 | 2024 | 일렉
EV6 | 2021 | 일렉
EV6 페이스리프트 | 2024 | 일렉
EV9 | 2024 | 일렉
EV9 | 2024 | 일렉
렉스턴 칸 스포츠 | 2020 | 가솔린
그랑 콜레오스 | 2025 | 하이브리드
토레스 | 2022 | 가솔린
G70 | 2019 | 가솔린
G70 | 2025 | 가솔린
그랜저 IG OLD | 2018 | 가솔린
쏘나타 DN8 NAVI NONE | 2019 | 가솔린
K5 DL3 NAVI NONE | 2019 | 가솔린
스팅어구형 | 2017 | 가솔린
스팅어 계기판 | 2019 | 가솔린
스팅어 계기판 | 2019 | 가솔린
제네시스 DH | 2015 | 가솔린
제네시스 DH | 2016 | 가솔린
구형 G80 | 2019 | 가솔린
카니발 KA4 | 2022 | 가솔린
싼타페 TM 구형 | 2019 | 가솔린
올뉴 K7 | 2018 | 가솔린
벤츠 E W213 | 2018 | 가솔린
벤츠 S 클래스 64컬러 | 2020 | 가솔린
BMW 7 G11 | 2018 | 가솔린
BMW7 F10 | 2024 | 일렉
포르쉐 파나메라 | 2017
""".strip().splitlines()

def dedup_keep_order(seq: List[str]) -> List[str]:
    seen=set(); out=[]
    for s in seq:
        t = norm_text(s)
        if t and t not in seen:
            seen.add(t); out.append(t)
    return out

REAL_MODELS: List[str] = dedup_keep_order(_REAL_MODELS_RAW)

# ===== 원 GUI 컨트롤 맵 =====
IDs = {
    "CAR_COMBO":   "MainWindow.centralWidget.comboBox_CAR_TYPE",
    "COLOR_COMBO": "MainWindow.centralWidget.comboBox_COLOR_TYPE",
    "ACT_COMBO":   "MainWindow.centralWidget.comboBox_ACTIVATION",

    "CL_LEFT":  "MainWindow.centralWidget.radioButton_CL_LEFT",
    "CL_RIGHT": "MainWindow.centralWidget.radioButton_CL_RIGHT",
    "CL_COUNT": "MainWindow.centralWidget.spinBox_CL_LED_COUNT",
    "CL_LUMA":  "MainWindow.centralWidget.spinBox_CL_LUMA",

    "CR_LEFT":  "MainWindow.centralWidget.radioButton_CR_LEFT",
    "CR_RIGHT": "MainWindow.centralWidget.radioButton_CR_RIGHT",
    "CR_COUNT": "MainWindow.centralWidget.spinBox_CR_LED_COUNT",
    "CR_LUMA":  "MainWindow.centralWidget.spinBox_CR_LUMA",
    "CR_MID":   "MainWindow.centralWidget.spinBox_CR_LED_MID_POSITION",

    "FL_FRONT": "MainWindow.centralWidget.radioButton_FL_FRONT",
    "FL_BACK":  "MainWindow.centralWidget.radioButton_FL_BACK",
    "FL_COUNT": "MainWindow.centralWidget.spinBox_FL_LED_COUNT",
    "FL_LUMA":  "MainWindow.centralWidget.spinBox_FL_LUMA",

    "FR_FRONT": "MainWindow.centralWidget.radioButton_FR_FRONT",
    "FR_BACK":  "MainWindow.centralWidget.radioButton_FR_BACK",
    "FR_COUNT": "MainWindow.centralWidget.spinBox_FR_LED_COUNT",
    "FR_LUMA":  "MainWindow.centralWidget.spinBox_FR_LUMA",

    "RL_FRONT": "MainWindow.centralWidget.radioButton_RL_FRONT",
    "RL_BACK":  "MainWindow.centralWidget.radioButton_RL_BACK",
    "RL_COUNT": "MainWindow.centralWidget.spinBox_RL_LED_COUNT",
    "RL_LUMA":  "MainWindow.centralWidget.spinBox_RL_LUMA",

    "RR_FRONT": "MainWindow.centralWidget.radioButton_RR_FRONT",
    "RR_BACK":  "MainWindow.centralWidget.radioButton_RR_BACK",
    "RR_COUNT": "MainWindow.centralWidget.spinBox_RR_LED_COUNT",
    "RR_LUMA":  "MainWindow.centralWidget.spinBox_RR_LUMA",

    "FL_FRONT_B": "MainWindow.centralWidget.radioButton_FL_FRONT_BOTTOM",
    "FL_BACK_B":  "MainWindow.centralWidget.radioButton_FL__BACK_BOTTOM",
    "FL_COUNT_B": "MainWindow.centralWidget.spinBox_FL_LED_COUNT__BOTTOM",
    "FL_LUMA_B":  "MainWindow.centralWidget.spinBox_FL_LUMA__BOTTOM",

    "FR_FRONT_B": "MainWindow.centralWidget.radioButton_FR_FRONT_BOTTOM",
    "FR_BACK_B":  "MainWindow.centralWidget.radioButton_FR_BACK_BOTTOM",
    "FR_COUNT_B": "MainWindow.centralWidget.spinBox_FR_LED_COUNT__BOTTOM",
    "FR_LUMA_B":  "MainWindow.centralWidget.spinBox_FR_LUMA_BOTTOM",

    "RL_FRONT_B": "MainWindow.centralWidget.radioButton_RL_FRONT_BOTTOM",
    "RL_BACK_B":  "MainWindow.centralWidget.radioButton_RL_BACK_BOTTOM",
    "RL_COUNT_B": "MainWindow.centralWidget.spinBox_RL_LED_COUNT__BOTTOM",
    "RL_LUMA_B":  "MainWindow.centralWidget.spinBox_RL_LUMA_BOTTOM",

    "RR_FRONT_B": "MainWindow.centralWidget.radioButton_RR_FRONT_BOTTOM",
    "RR_BACK_B":  "MainWindow.centralWidget.radioButton_RR_BACK_BOTTOM",
    "RR_COUNT_B": "MainWindow.centralWidget.spinBox_RR_LED_COUNT__BOTTOM",
    "RR_LUMA_B":  "MainWindow.centralWidget.spinBox_RR_LUMA_BOTTOM",

    "AUDIO_OFF_1": "MainWindow.centralWidget.spinBox_AUDIO_OFFSET",
    "AUDIO_GAIN_1":"MainWindow.centralWidget.spinBox_AUDIO_GAIN",
    "AUDIO_OFF_2": "MainWindow.centralWidget.spinBox_AUDIO_OFFSET_2",
    "AUDIO_GAIN_2":"MainWindow.centralWidget.spinBox_AUDIO_GAIN_2",

    "BTN_SAVE":       "MainWindow.centralWidget.pushButton_OK",
    "BTN_DISCONNECT": "MainWindow.centralWidget.pushButton_DISCONNECT",  # 최종확인에서 사용
}

# ===== pywinauto helpers =====
def connect_window() -> BaseWrapper:
    app = Application(backend="uia").connect(title_re=TARGET_WINDOW_TITLE, timeout=RETRY_CONNECT_SEC)
    win = app.window(title_re=TARGET_WINDOW_TITLE)
    win.set_focus()
    return win

def _cw(win: BaseWrapper, aid: str, ctype: str):
    return win.child_window(auto_id=aid, control_type=ctype).wrapper_object()

def set_checkbox(win: BaseWrapper, aid: str, checked: bool) -> None:
    cb = _cw(win, aid, "CheckBox")
    try:
        want = 1 if checked else 0
        if cb.get_toggle_state() != want:
            cb.click_input()
    except Exception:
        cb.click_input()

def set_radio_pair(win: BaseWrapper, aid_true: str, aid_false: str, choose_true: bool) -> None:
    set_checkbox(win, aid_true, choose_true)
    set_checkbox(win, aid_false, not choose_true)

def _read_spinner_text(sp):
    try:
        edit = sp.child_window(control_type="Edit").wrapper_object()
        return edit.window_text().strip()
    except Exception:
        return sp.window_text().strip()

def set_spinner(win: BaseWrapper, aid: str, value: str | int) -> None:
    sp = _cw(win, aid, "Spinner")
    s  = str(value)
    for _ in range(RETRY_SET):
        try:
            try:
                edit = sp.child_window(control_type="Edit").wrapper_object()
            except Exception:
                edit = sp
            edit.set_focus()
            try: edit.type_keys("^a{BACKSPACE}", pause=TYPE_PAUSE)
            except Exception: pass
            edit.type_keys(s, with_spaces=False, pause=TYPE_PAUSE)
            edit.type_keys("{ENTER}", pause=TYPE_PAUSE)
            time.sleep(VERIFY_DELAY)
            if _read_spinner_text(sp) == s:
                return
        except Exception:
            time.sleep(VERIFY_DELAY)
    raise RuntimeError(f"스피너 입력 실패: {aid} -> {s}")

def click_button(win: BaseWrapper, aid: str) -> None:
    _cw(win, aid, "Button").click_input()
    time.sleep(VERIFY_DELAY)

# ===== 콤보 도우미 =====
class ComboHelper:
    def __init__(self, win: BaseWrapper, aid: str) -> None:
        self.win = win; self.aid = aid; self.cache: List[str] = []

    def _combo(self):
        return _cw(self.win, self.aid, "ComboBox")

    def _expand(self):
        combo = self._combo()
        combo.set_focus()
        try: combo.expand()
        except Exception: combo.click_input()
        time.sleep(EXPAND_DELAY)
        return combo

    def fetch_titles(self) -> List[str]:
        combo = self._expand()
        titles: List[str] = []
        for el in self.win.descendants(control_type="ListItem"):
            try:
                t = el.window_text()
                if t and t != "---":
                    titles.append(t)
            except Exception:
                pass
        try: combo.collapse()
        except Exception: pass
        self.cache = dedup_keep_order(titles)
        return self.cache

    def commit(self, text: str) -> str:
        q = norm_text(text)
        if not q: raise RuntimeError("빈 텍스트")
        if not self.cache: self.fetch_titles()
        exact = next((t for t in self.cache if t == q), None)
        cand  = exact or next((t for t in self.cache if q.casefold() in t.casefold()), None)
        combo = self._expand()
        if cand:
            self.win.child_window(title=cand, control_type="ListItem").wrapper_object().click_input()
            try: combo.collapse()
            except Exception: pass
            return cand
        for _ in range(RETRY_SET):
            try:
                edit = combo.child_window(control_type="Edit").wrapper_object()
                edit.set_focus()
                edit.type_keys("^a{BACKSPACE}", pause=TYPE_PAUSE)
                edit.type_keys(q, with_spaces=True, pause=TYPE_PAUSE)
                edit.type_keys("{ENTER}", pause=TYPE_PAUSE)
                time.sleep(VERIFY_DELAY)
                return q
            except Exception:
                time.sleep(VERIFY_DELAY)
        raise RuntimeError(f"콤보 선택 실패: {q}")

    def current_text(self) -> str:
        combo = self._combo()
        try:
            edit = combo.child_window(control_type="Edit").wrapper_object()
            return norm_text(edit.window_text())
        except Exception:
            return norm_text(combo.window_text())

# ===== 자동완성 Entry =====
class AutoCompleteEntry(ttk.Entry):
    NAV_KEYS = {"Up", "Down", "Left", "Right", "Return", "Escape"}
    def __init__(self, master: tk.Widget, values: List[str], on_commit=None, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.all_values: List[str] = values
        self.on_commit = on_commit
        self.popup = tk.Toplevel(self); self.popup.overrideredirect(True); self.popup.withdraw()
        self.listbox = tk.Listbox(self.popup, height=8); self.listbox.pack(fill="both", expand=True)
        self.bind("<KeyRelease>", self._on_keyrelease)
        self.bind("<KeyPress-Down>", self._on_down)
        self.bind("<KeyPress-Up>", self._on_up)
        self.bind("<Return>", self._on_return)
        self.bind("<FocusOut>", lambda e: self._maybe_commit())
        self.bind("<Escape>", lambda e: self._hide())
        self.listbox.bind("<Button-1>", self._on_click)

    def set_values(self, values: List[str]) -> None:
        self.all_values = values

    def _place_popup(self) -> None:
        if not self.winfo_ismapped(): return
        x = self.winfo_rootx(); y = self.winfo_rooty() + self.winfo_height(); w = self.winfo_width()
        self.popup.geometry(f"{w}x180+{x}+{y}")

    def _filter(self, text: str) -> List[str]:
        if not text: return []
        start = [v for v in self.all_values if v.lower().startswith(text.lower())]
        cont  = [v for v in self.all_values if text.lower() in v.lower() and v not in start]
        return (start + cont)[:200]

    def _show(self) -> None:
        self._place_popup(); self.popup.deiconify(); self.popup.lift()

    def _hide(self) -> None:
        self.popup.withdraw()

    def _refresh(self, matches: List[str]) -> None:
        self.listbox.delete(0, tk.END)
        for v in matches: self.listbox.insert(tk.END, v)
        if matches:
            self._show()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(0); self.listbox.activate(0)
        else:
            self._hide()

    def _on_keyrelease(self, e=None) -> None:
        if e and e.keysym in self.NAV_KEYS: return
        txt = self.get().strip()
        self._refresh(self._filter(txt) if txt else [])

    def _on_down(self, _e=None) -> str:
        if self.popup.state() == "normal":
            cur = self.listbox.curselection(); idx = cur[0] if cur else -1
            if idx < self.listbox.size() - 1:
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(idx + 1); self.listbox.activate(idx + 1)
            return "break"
        return ""

    def _on_up(self, _e=None) -> str:
        if self.popup.state() == "normal":
            cur = self.listbox.curselection(); idx = cur[0] if cur else 0
            if idx > 0:
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(idx - 1); self.listbox.activate(idx - 1)
            return "break"
        return ""

    def _selected_text(self) -> Optional[str]:
        cur = self.listbox.curselection()
        return self.listbox.get(cur[0]) if cur else None

    def _commit_text(self, text: str) -> None:
        self.delete(0, tk.END); self.insert(0, text); self._hide()
        if callable(self.on_commit): self.on_commit()

    def _on_return(self, _e=None) -> str:
        sel = self._selected_text()
        self._commit_text(sel or self.get().strip())
        return "break"

    def _on_click(self, _e=None) -> None:
        sel = self._selected_text()
        if sel: self._commit_text(sel)

    def _maybe_commit(self) -> None:
        if self.get().strip() and callable(self.on_commit):
            self.on_commit()

# ===== 메인 앱 =====
class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Bridge → A-VICLE (Auto/Fast)")
        self.geometry("1000x700")
        self.resizable(False, False)
        self.win: Optional[BaseWrapper] = None

        self.h_car: Optional[ComboHelper] = None
        self.h_color: Optional[ComboHelper] = None
        self.h_act: Optional[ComboHelper] = None

        self._ext_monitor_thread: Optional[threading.Thread] = None
        self._ext_stop = threading.Event()

        # 상단: 상태
        top = ttk.Frame(self, padding=10); top.pack(fill="x")
        ttk.Button(top, text="연결", command=self.on_connect_manual).pack(side="left")
        self.st = tk.StringVar(value="미연결(자동 연결 시도중)"); ttk.Label(top, textvariable=self.st).pack(side="left", padx=10)

        # 헤더
        head = ttk.Frame(self, padding=8); head.pack(fill="x")
        ttk.Label(head, text="차종(원 GUI)").grid(row=0, column=0, sticky="e")
        self.car_values: List[str] = []
        self.car_entry = AutoCompleteEntry(head, self.car_values, on_commit=self.try_autoload, width=60)
        self.car_entry.grid(row=0, column=1, sticky="w")

        ttk.Label(head, text="실제 차종(프리셋 키)").grid(row=1, column=0, sticky="e", pady=(4,0))
        self.real_entry = AutoCompleteEntry(head, REAL_MODELS, on_commit=self.try_autoload, width=60)
        self.real_entry.grid(row=1, column=1, sticky="w", pady=(4,0))

        ttk.Label(head, text="색상모델").grid(row=2, column=0, sticky="e", pady=4)
        self.color_combo = ttk.Combobox(head, state="readonly", width=40, values=[])
        self.color_combo.grid(row=2, column=1, sticky="w", pady=4)
        self.color_combo.bind("<<ComboboxSelected>>", lambda e: self.try_autoload())

        ttk.Label(head, text="활성화").grid(row=3, column=0, sticky="e")
        self.act_combo = ttk.Combobox(head, state="readonly", width=40, values=[])
        self.act_combo.grid(row=3, column=1, sticky="w")
        self.act_combo.bind("<<ComboboxSelected>>", lambda e: self.try_autoload())

        # 본문
        content = ttk.Frame(self, padding=8); content.pack(fill="both", expand=True)

        base = ttk.Labelframe(content, text="기본라인", padding=8); base.grid(row=0, column=0, sticky="nw")
        self.ui_basic: Dict[str, Dict[str, Any]] = {}
        def mk_basic(title, lr=False, fb=False, has_mid=False, row=0):
            frm = ttk.Frame(base, padding=4); frm.grid(row=row, column=0, sticky="w")
            ttk.Label(frm, text=title, width=15).grid(row=0, column=0, sticky="w")
            side = tk.StringVar(value=("LEFT" if lr else "FRONT"))
            if lr:
                ttk.Radiobutton(frm, text="LEFT", variable=side, value="LEFT").grid(row=0, column=1, sticky="w")
                ttk.Radiobutton(frm, text="RIGHT", variable=side, value="RIGHT").grid(row=0, column=2, sticky="w")
            if fb:
                ttk.Radiobutton(frm, text="FRONT", variable=side, value="FRONT").grid(row=0, column=1, sticky="w")
                ttk.Radiobutton(frm, text="BACK",  variable=side, value="BACK").grid(row=0, column=2, sticky="w")
            ttk.Label(frm, text="COUNT").grid(row=0, column=3, padx=(8,2))
            e_cnt, v_cnt = self._spin(frm); e_cnt.grid(row=0, column=4)
            ttk.Label(frm, text="밝기(%)").grid(row=0, column=5, padx=(8,2))
            e_luma, v_luma = self._spin(frm); e_luma.grid(row=0, column=6)
            e_mid, v_mid = None, None
            if has_mid:
                ttk.Label(frm, text="MID").grid(row=0, column=7, padx=(8,2))
                e_mid, v_mid = self._spin(frm); e_mid.grid(row=0, column=8)
            return {"side": side, "cnt": v_cnt, "luma": v_luma, "mid": v_mid}
        self.ui_basic["CL"] = mk_basic("CENTER LEFT", lr=True, row=0)
        self.ui_basic["CR"] = mk_basic("CENTER RIGHT", lr=True, has_mid=True, row=1)
        self.ui_basic["FL"] = mk_basic("FRONT LEFT",  fb=True, row=2)
        self.ui_basic["FR"] = mk_basic("FRONT RIGHT", fb=True, row=3)
        self.ui_basic["RL"] = mk_basic("REAR LEFT",   fb=True, row=4)
        self.ui_basic["RR"] = mk_basic("REAR RIGHT",  fb=True, row=5)

        dual = ttk.Labelframe(content, text="듀얼라인", padding=8); dual.grid(row=1, column=0, sticky="nw", pady=(8,0))
        self.var_dual_enable = tk.BooleanVar(value=DEFAULT_DUAL_ENABLED)
        ttk.Checkbutton(dual, text="듀얼라인 적용", variable=self.var_dual_enable).grid(row=0, column=0, sticky="w")
        self.ui_dual: Dict[str, Dict[str, Any]] = {}
        def mk_dual(title, prefix, row):
            frm = ttk.Frame(dual, padding=4); frm.grid(row=row, column=0, sticky="w")
            ttk.Label(frm, text=title, width=20).grid(row=0, column=0, sticky="w")
            side = tk.StringVar(value="FRONT")
            ttk.Radiobutton(frm, text="FRONT", variable=side, value="FRONT").grid(row=0, column=1, sticky="w")
            ttk.Radiobutton(frm, text="BACK",  variable=side, value="BACK").grid(row=0, column=2, sticky="w")
            ttk.Label(frm, text="COUNT").grid(row=0, column=3, padx=(8,2))
            e_cnt, v_cnt = self._spin(frm); e_cnt.grid(row=0, column=4)
            ttk.Label(frm, text="밝기(%)").grid(row=0, column=5, padx=(8,2))
            e_luma, v_luma = self._spin(frm); e_luma.grid(row=0, column=6)
            return {"side": side, "cnt": v_cnt, "luma": v_luma, "prefix": prefix}
        self.ui_dual["FL_B"] = mk_dual("FRONT LEFT (DUAL)",  "FL", 1)
        self.ui_dual["FR_B"] = mk_dual("FRONT RIGHT (DUAL)", "FR", 2)
        self.ui_dual["RL_B"] = mk_dual("REAR LEFT (DUAL)",   "RL", 3)
        self.ui_dual["RR_B"] = mk_dual("REAR RIGHT (DUAL)",  "RR", 4)

        right = ttk.Labelframe(content, text="오디오", padding=8); right.grid(row=0, column=1, rowspan=2, sticky="n", padx=(16,0))
        ttk.Label(right, text="OFFSET 1").grid(row=0, column=0, sticky="e"); self.e_off1, self.v_off1 = self._spin(right, defv=DEFAULT_AUDIO_OFF1); self.e_off1.grid(row=0, column=1, sticky="w")
        ttk.Label(right, text="GAIN 1").grid(row=0, column=2, sticky="e");  self.e_gain1, self.v_gain1 = self._spin(right, defv=DEFAULT_AUDIO_GAIN1); self.e_gain1.grid(row=0, column=3, sticky="w")
        ttk.Label(right, text="OFFSET 2").grid(row=1, column=0, sticky="e"); self.e_off2, self.v_off2 = self._spin(right, defv=DEFAULT_AUDIO_OFF2); self.e_off2.grid(row=1, column=1, sticky="w")
        ttk.Label(right, text="GAIN 2").grid(row=1, column=2, sticky="e");  self.e_gain2, self.v_gain2 = self._spin(right, defv=DEFAULT_AUDIO_GAIN2); self.e_gain2.grid(row=1, column=3, sticky="w")

        bottom = ttk.Frame(self, padding=10); bottom.pack(fill="x")
        ttk.Button(bottom, text="적용(저장 포함)", command=self.apply_and_save).pack(side="left")
        ttk.Button(bottom, text="저장 버튼 클릭", command=self.on_save).pack(side="left", padx=8)
        ttk.Button(bottom, text="최종확인", command=self.on_final_confirm).pack(side="left", padx=8)

        self.set_defaults()
        self.after(50, self._auto_connect_then_apply_once)

    def destroy(self):
        self._stop_external_monitor()
        super().destroy()

    def _spin(self, parent, width=6, defv=""):
        v = tk.StringVar(value=defv); e = ttk.Entry(parent, textvariable=v, width=width); return e, v

    def set_defaults(self) -> None:
        for key, ui in self.ui_basic.items():
            if ui["cnt"].get() == "":  ui["cnt"].set(DEFAULT_COUNT)
            if ui["luma"].get() == "": ui["luma"].set(DEFAULT_LUMA)
            if key == "CR":
                if ui.get("mid") is not None and ui["mid"].get() == "":
                    ui["mid"].set(DEFAULT_MID)
        for ui in self.ui_dual.values():
            if ui["luma"].get() == "": ui["luma"].set(DEFAULT_LUMA)

    # ---- 자동 연결 → (DIP SWITCH면 스킵) → 자동 1회 적용 ----
    def _auto_connect_then_apply_once(self) -> None:
        ok = self._connect_impl(show_popup=False)
        if not ok:
            return
        car0   = self.h_car.current_text()   if self.h_car else ""
        color0 = self.h_color.current_text() if self.h_color else ""
        act0   = self.h_act.current_text()   if self.h_act else ""
        if any(map(is_from_dipswitch, [car0, color0, act0])):
            self.st.set("연결됨(DIP SWITCH 상태: 자동 적용 스킵)")
            return
        self.after(50, self.apply_and_save)

    def on_connect_manual(self) -> None:
        self._connect_impl(show_popup=True)

    def _connect_impl(self, show_popup: bool) -> bool:
        try:
            self.win = connect_window()
            self.h_car   = ComboHelper(self.win, IDs["CAR_COMBO"])
            self.h_color = ComboHelper(self.win, IDs["COLOR_COMBO"])
            self.h_act   = ComboHelper(self.win, IDs["ACT_COMBO"])

            cars   = self.h_car.fetch_titles()
            colors = self.h_color.fetch_titles()
            acts   = self.h_act.fetch_titles()

            self.car_entry.set_values(cars)
            self.real_entry.set_values(REAL_MODELS)
            self.color_combo["values"] = colors;  self.color_combo.current(0 if colors else -1)
            self.act_combo["values"]   = acts;    self.act_combo.current(0 if acts else -1)

            self.st.set(f"연결됨(차종 {len(cars)}개)")
            self.try_autoload()
            self._start_external_monitor()
            return True
        except (ElementNotFoundError, PwaTimeout) as e:
            self.st.set("미연결")
            if show_popup:
                messagebox.showerror("연결 실패", str(e))
            return False
        except Exception as e:
            self.st.set("미연결")
            if show_popup:
                messagebox.showerror("연결 실패", str(e))
            return False

    # ---- 프리셋 ----
    def current_key(self) -> str:
        return make_key(self.car_entry.get(), self.real_entry.get(), self.color_combo.get(), self.act_combo.get())

    def try_autoload(self) -> None:
        car  = self.car_entry.get()
        real = self.real_entry.get()
        if not is_key_valid(car, real):
            self.set_defaults()
            return
        data = load_presets().get(self.current_key())
        if not data:
            self.set_defaults(); return
        for sec in ["CL","CR","FL","FR","RL","RR"]:
            ui = self.ui_basic[sec]; src = data["basic"][sec]
            ui["side"].set(src["side"])
            ui["cnt"].set(src.get("count", DEFAULT_COUNT) or DEFAULT_COUNT)
            ui["luma"].set(src.get("luma", DEFAULT_LUMA) or DEFAULT_LUMA)
            if ui.get("mid") is not None:
                ui["mid"].set(src.get("mid", DEFAULT_MID) or DEFAULT_MID)
        self.var_dual_enable.set(data.get("dual_enabled", DEFAULT_DUAL_ENABLED))
        for key2 in ["FL_B","FR_B","RL_B","RR_B"]:
            ui = self.ui_dual[key2]; src = data["dual"][key2]
            ui["side"].set(src["side"])
            ui["cnt"].set(src.get("count",""))
            ui["luma"].set(src.get("luma", DEFAULT_LUMA) or DEFAULT_LUMA)
        self.v_off1.set(data.get("audio",{}).get("off1", DEFAULT_AUDIO_OFF1))
        self.v_gain1.set(data.get("audio",{}).get("gain1", DEFAULT_AUDIO_GAIN1))
        self.v_off2.set(data.get("audio",{}).get("off2", DEFAULT_AUDIO_OFF2))
        self.v_gain2.set(data.get("audio",{}).get("gain2", DEFAULT_AUDIO_GAIN2))

    def collect_values(self) -> Dict[str, Any]:
        def _lum(v): return v if v != "" else DEFAULT_LUMA
        def _mid(v): return v if v != "" else DEFAULT_MID
        def _cnt(v): return v if v != "" else DEFAULT_COUNT
        pack = {
            "key": self.current_key(),
            "car": norm_text(self.car_entry.get()),
            "real_model": norm_text(self.real_entry.get()),
            "color": norm_text(self.color_combo.get()),
            "activation": norm_text(self.act_combo.get()),
            "basic": {},
            "dual_enabled": bool(self.var_dual_enable.get()),
            "dual": {},
            "audio": {
                "off1": self.v_off1.get(), "gain1": self.v_gain1.get(),
                "off2": self.v_off2.get(), "gain2": self.v_gain2.get()
            },
        }
        for sec in ["CL","CR","FL","FR","RL","RR"]:
            ui = self.ui_basic[sec]
            pack["basic"][sec] = {
                "side": ui["side"].get(),
                "count": _cnt(ui["cnt"].get()),
                "luma": _lum(ui["luma"].get()),
                "mid": _mid(ui["mid"].get()) if ui.get("mid") is not None else None,
            }
        for key2 in ["FL_B","FR_B","RL_B","RR_B"]:
            ui = self.ui_dual[key2]
            pack["dual"][key2] = {"side": ui["side"].get(), "count": ui["cnt"].get(), "luma": _lum(ui["luma"].get())}
        return pack

    # ---- 외부 저장 감지 → 프리셋 저장(키 유효 시) ----
    def _on_external_save(self) -> None:
        if not self.win: return
        try:
            car   = norm_text(self.h_car.current_text()   if self.h_car   else self.car_entry.get())
            color = norm_text(self.h_color.current_text() if self.h_color else self.color_combo.get())
            act   = norm_text(self.h_act.current_text()   if self.h_act   else self.act_combo.get())
            real  = norm_text(self.real_entry.get())
            if not is_key_valid(car, real):
                self.st.set("원 GUI 저장 감지(키 무효) → 저장 생략")
                return
            vals = self.collect_values()
            vals["car"] = car; vals["real_model"] = real; vals["color"] = color; vals["activation"] = act
            vals["key"] = make_key(car, real, color, act)
            presets = load_presets(); presets[vals["key"]] = vals; save_presets(presets)
            self.st.set("원 GUI 저장 감지→프리셋 저장됨")
        except Exception:
            self.st.set("원 GUI 저장 감지 실패")

    def _start_external_monitor(self) -> None:
        self._stop_external_monitor()
        self._ext_stop.clear()
        t = threading.Thread(target=self._monitor_worker, daemon=True)
        t.start()
        self._ext_monitor_thread = t

    def _stop_external_monitor(self) -> None:
        self._ext_stop.set()
        t = self._ext_monitor_thread
        if t and t.is_alive(): t.join(timeout=0.2)
        self._ext_monitor_thread = None

    def _monitor_worker(self) -> None:
        try:
            import uiautomation as auto
            win = auto.WindowControl(Name=TARGET_WINDOW_TITLE)
            if not win.Exists(3, 0.2): raise RuntimeError("win not found")
            btn = auto.ButtonControl(AutomationId=IDs["BTN_SAVE"].split(".")[-1], searchFromControl=win)
            if not btn.Exists(3, 0.2): raise RuntimeError("btn not found")
            def on_invoked(sender, args):
                self.after(0, self._on_external_save)
            btn.AddAutomationEventHandler(auto.Invoke_InvokedEventId, on_invoked)
            try:
                while not self._ext_stop.is_set():
                    auto.WaitForIdle(0.2)
            finally:
                try: btn.RemoveAutomationEventHandler(auto.Invoke_InvokedEventId, on_invoked)
                except Exception: pass
            return
        except Exception:
            pass
        try:
            btn = _cw(self.win, IDs["BTN_SAVE"], "Button")
        except Exception:
            return
        prev_enabled = btn.is_enabled() if hasattr(btn, "is_enabled") else None
        while not self._ext_stop.is_set():
            try:
                cur = btn.is_enabled()
                if prev_enabled and cur is False:
                    self.after(0, self._on_external_save)
                prev_enabled = cur
            except Exception:
                pass
            time.sleep(0.1)

    # ---- 적용 & 저장(키 유효 시 저장) ----
    def apply_and_save(self) -> None:
        if not self.win:
            messagebox.showwarning("알림", "먼저 [연결]을 눌러주세요."); return
        try:
            vals = self.collect_values()

            # 콤보 커밋(실제차종은 원 GUI 미적용)
            if self.h_car and vals["car"]:
                official = self.h_car.commit(vals["car"])
                self.car_entry.delete(0, tk.END); self.car_entry.insert(0, official)
            if self.h_color and vals["color"]:
                official = self.h_color.commit(vals["color"]); self.color_combo.set(official)
            if self.h_act and vals["activation"]:
                official = self.h_act.commit(vals["activation"]); self.act_combo.set(official)

            # 기본라인
            self._apply_basic_pair("CL", lr=("CL_LEFT","CL_RIGHT"), count="CL_COUNT", luma="CL_LUMA", val=vals)
            self._apply_basic_pair("CR", lr=("CR_LEFT","CR_RIGHT"), count="CR_COUNT", luma="CR_LUMA", mid="CR_MID", val=vals)
            self._apply_basic_pair("FL", fb=("FL_FRONT","FL_BACK"), count="FL_COUNT", luma="FL_LUMA", val=vals)
            self._apply_basic_pair("FR", fb=("FR_FRONT","FR_BACK"), count="FR_COUNT", luma="FR_LUMA", val=vals)
            self._apply_basic_pair("RL", fb=("RL_FRONT","RL_BACK"), count="RL_COUNT", luma="RL_LUMA", val=vals)
            self._apply_basic_pair("RR", fb=("RR_FRONT","RR_BACK"), count="RR_COUNT", luma="RR_LUMA", val=vals)

            # 듀얼라인
            if vals["dual_enabled"]:
                self._apply_dual("FL_B", vals)
                self._apply_dual("FR_B", vals)
                self._apply_dual("RL_B", vals)
                self._apply_dual("RR_B", vals)

            # 오디오(빈칸은 skip)
            if vals["audio"]["off1"] != "":  set_spinner(self.win, IDs["AUDIO_OFF_1"], vals["audio"]["off1"])
            if vals["audio"]["gain1"] != "": set_spinner(self.win, IDs["AUDIO_GAIN_1"], vals["audio"]["gain1"])
            if vals["audio"]["off2"] != "":  set_spinner(self.win, IDs["AUDIO_OFF_2"], vals["audio"]["off2"])
            if vals["audio"]["gain2"] != "": set_spinner(self.win, IDs["AUDIO_GAIN_2"], vals["audio"]["gain2"])

            # 프리셋 저장(키 유효 시에만)
            if is_key_valid(vals["car"], vals["real_model"]):
                presets = load_presets()
                presets[self.current_key()] = self.collect_values()
                save_presets(presets)
                self.st.set(f"적용 & 저장 완료: {get_preset_path()}")
            else:
                self.st.set("적용 완료(키 무효로 저장 생략)")
        except Exception as e:
            messagebox.showerror("실패", str(e))

    def _apply_basic_pair(self, key: str, lr: Tuple[str,str]=None, fb: Tuple[str,str]=None,
                          count: str=None, luma: str=None, mid: str=None, val: Dict[str,Any]=None) -> None:
        src = val["basic"][key]
        if lr: set_radio_pair(self.win, IDs[lr[0]], IDs[lr[1]], src["side"] in ("LEFT","FRONT"))
        if fb: set_radio_pair(self.win, IDs[fb[0]], IDs[fb[1]], src["side"] == "FRONT")
        cnt = src.get("count", DEFAULT_COUNT)
        if cnt: set_spinner(self.win, IDs[count], cnt)
        lum = src.get("luma", DEFAULT_LUMA)
        if lum: set_spinner(self.win, IDs[luma], lum)
        if mid and src.get("mid") is not None:
            set_spinner(self.win, IDs[mid], src.get("mid", DEFAULT_MID))

    def _apply_dual(self, key: str, val: Dict[str,Any]) -> None:
        src = val["dual"][key]; p = self.ui_dual[key]["prefix"]
        set_radio_pair(self.win, IDs[f"{p}_FRONT_B"], IDs[f"{p}_BACK_B"], src["side"] == "FRONT")
        cnt = src.get("count","")
        if cnt: set_spinner(self.win, IDs[f"{p}_COUNT_B"], cnt)
        lum = src.get("luma", DEFAULT_LUMA)
        if lum: set_spinner(self.win, IDs[f"{p}_LUMA_B"], lum)

    def on_save(self) -> None:
        if not self.win:
            messagebox.showwarning("알림", "먼저 [연결]을 눌러주세요."); return
        try:
            click_button(self.win, IDs["BTN_SAVE"])
        except Exception as e:
            messagebox.showerror("저장 실패", str(e))

    # ---- 최종확인: 적용 → 원GUI 저장 → DISCONNECT ----
    def on_final_confirm(self) -> None:
        if not self.win:
            messagebox.showwarning("알림", "먼저 [연결]을 눌러주세요."); 
            return
        try:
            self.apply_and_save()
            click_button(self.win, IDs["BTN_SAVE"])
            click_button(self.win, IDs["BTN_DISCONNECT"])
            self.st.set("최종확인 완료(적용→저장→DISCONNECT)")
        except Exception as e:
            messagebox.showerror("최종확인 실패", str(e))

if __name__ == "__main__":
    try:
        App().mainloop()
    except KeyboardInterrupt:
        sys.exit(0)


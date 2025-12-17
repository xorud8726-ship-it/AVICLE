# filepath: c:/IFIRST/RGB.py
from __future__ import annotations
import sys, time, tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional

from pywinauto import Application
from pywinauto.base_wrapper import BaseWrapper
from pywinauto.findwindows import ElementNotFoundError
from pywinauto.timings import TimeoutError as PwaTimeout
from pywinauto.timings import Timings

# ===== 설정 =====
TARGET_WINDOW_TITLE   = r"A-VICLE CODING SOFTWARE"
RETRY_CONNECT_SEC     = 5

# 기본값(요청: 전부 1)
DEFAULT_AUDIO_OFF1    = "1"
DEFAULT_AUDIO_OFF2    = "1"
DEFAULT_AUDIO_GAIN1   = "1"
DEFAULT_AUDIO_GAIN2   = "1"

# 속도
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

# ===== 원 GUI 컨트롤 맵 =====
IDs = {
    "CAR_COMBO":   "MainWindow.centralWidget.comboBox_CAR_TYPE",
    "COLOR_COMBO": "MainWindow.centralWidget.comboBox_COLOR_TYPE",
    "ACT_COMBO":   "MainWindow.centralWidget.comboBox_ACTIVATION",

    "AUDIO_OFF_1":  "MainWindow.centralWidget.spinBox_AUDIO_OFFSET",
    "AUDIO_OFF_2":  "MainWindow.centralWidget.spinBox_AUDIO_OFFSET_2",
    "AUDIO_GAIN_1": "MainWindow.centralWidget.spinBox_AUDIO_GAIN",
    "AUDIO_GAIN_2": "MainWindow.centralWidget.spinBox_AUDIO_GAIN_2",

    "BTN_SAVE":       "MainWindow.centralWidget.pushButton_OK",
    "BTN_DISCONNECT": "MainWindow.centralWidget.pushButton_DISCONNECT",
}

# ===== pywinauto helpers =====
def connect_window() -> BaseWrapper:
    # 왜: 이전 핸들이 죽어 있을 수 있어 매번 fresh connect
    app = Application(backend="uia").connect(title_re=TARGET_WINDOW_TITLE, timeout=RETRY_CONNECT_SEC)
    win = app.window(title_re=TARGET_WINDOW_TITLE)
    win.set_focus()
    return win

def _cw(win: BaseWrapper, aid: str, ctype: str):
    return win.child_window(auto_id=aid, control_type=ctype).wrapper_object()

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
        seen=set(); out=[]
        for t in titles:
            tt = norm_text(t)
            if tt and tt not in seen:
                seen.add(tt); out.append(tt)
        self.cache = out
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
                edit.type_keys("^a{BACKSPACE}", pause=0.0)
                edit.type_keys(q, with_spaces=True, pause=0.0)  # 띄어쓰기 강제 X
                edit.type_keys("{ENTER}", pause=0.0)
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

# ===== 검색+목록 Entry =====
class AutoCompleteEntry(ttk.Entry):
    NAV_KEYS = {"Up", "Down", "Left", "Right", "Return", "Escape"}
    def __init__(self, master: tk.Widget, values: List[str], on_commit=None, **kwargs):
        super().__init__(master, **kwargs)
        self.all_values: List[str] = values
        self.on_commit = on_commit
        self.popup = tk.Toplevel(self); self.popup.overrideredirect(True); self.popup.withdraw()
        self.listbox = tk.Listbox(self.popup, height=10); self.listbox.pack(fill="both", expand=True)
        self.bind("<KeyRelease>", self._on_keyrelease)
        self.bind("<Return>", self._on_return)
        self.bind("<FocusOut>", lambda e: self._maybe_commit())
        self.bind("<Escape>", lambda e: self._hide())
        self.listbox.bind("<Button-1>", self._on_click)

    def attach_button(self, btn: ttk.Button) -> None:
        btn.configure(command=self._toggle_popup)

    def set_values(self, values: List[str]) -> None:
        self.all_values = values

    def _place_popup(self) -> None:
        if not self.winfo_ismapped(): return
        x = self.winfo_rootx(); y = self.winfo_rooty() + self.winfo_height(); w = self.winfo_width()
        self.popup.geometry(f"{w}x220+{x}+{y}")

    def _filter(self, text: str) -> List[str]:
        if not text: return self.all_values[:200]
        s = text.lower()
        start = [v for v in self.all_values if v.lower().startswith(s)]
        cont  = [v for v in self.all_values if s in v.lower() and v not in start]
        return (start + cont)[:200]

    def _show(self, matches: List[str]) -> None:
        self._place_popup()
        self.listbox.delete(0, tk.END)
        for v in matches: self.listbox.insert(tk.END, v)
        self.popup.deiconify(); self.popup.lift()

    def _hide(self) -> None:
        self.popup.withdraw()

    def _toggle_popup(self) -> None:
        if self.popup.state() == "normal":
            self._hide()
        else:
            self._show(self._filter(self.get().strip()))

    def _on_keyrelease(self, e=None) -> None:
        if e and e.keysym in self.NAV_KEYS: return
        self._show(self._filter(self.get().strip()))

    def _on_return(self, _e=None) -> str:
        cur = self.listbox.curselection()
        text = self.listbox.get(cur[0]) if cur else self.get().strip()
        self._commit_text(text)
        return "break"

    def _on_click(self, _e=None) -> None:
        cur = self.listbox.curselection()
        if cur:
            self._commit_text(self.listbox.get(cur[0]))

    def _commit_text(self, text: str) -> None:
        self.delete(0, tk.END); self.insert(0, text); self._hide()

    def _maybe_commit(self) -> None:
        if self.get().strip() and callable(self.on_commit):
            self.on_commit()

# ===== 메인 앱 =====
class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Bridge → A-VICLE (RGB)")
        self.geometry("550x300")
        self.resizable(False, False)
        self.win: Optional[BaseWrapper] = None

        self.h_car: Optional[ComboHelper] = None
        self.h_color: Optional[ComboHelper] = None
        self.h_act: Optional[ComboHelper] = None

        # 상단: 연결/상태
        top = ttk.Frame(self, padding=10); top.pack(fill="x")
        ttk.Button(top, text="연결", command=self.on_connect_manual).pack(side="left")
        self.st = tk.StringVar(value="미연결"); ttk.Label(top, textvariable=self.st).pack(side="left", padx=10)

        # 좌: 차종/색상/활성화
        head = ttk.Frame(self, padding=8); head.pack(fill="x")
        ttk.Label(head, text="차종선택").grid(row=0, column=0, sticky="e")
        self.car_values: List[str] = []
        self.car_entry = AutoCompleteEntry(head, self.car_values, width=52)
        self.car_entry.grid(row=0, column=1, sticky="w")
        btn_list_car = ttk.Button(head, width=2, text="▼"); btn_list_car.grid(row=0, column=2, padx=(4,0))
        self.car_entry.attach_button(btn_list_car)

        ttk.Label(head, text="색상모델").grid(row=1, column=0, sticky="e", pady=4)
        self.color_combo = ttk.Combobox(head, state="readonly", width=42, values=[])
        self.color_combo.grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(head, text="활성화").grid(row=2, column=0, sticky="e")
        self.act_combo = ttk.Combobox(head, state="readonly", width=42, values=[])
        self.act_combo.grid(row=2, column=1, sticky="w")

        # 우: 오디오 옵셋/게인
        right = ttk.Labelframe(self, text="AUDIO", padding=8)
        right.pack(fill="x", padx=10, pady=(6,0))
        ttk.Label(right, text="OFFSET 1").grid(row=0, column=0, sticky="e")
        self.v_off1 = tk.StringVar(value=DEFAULT_AUDIO_OFF1)
        ttk.Entry(right, textvariable=self.v_off1, width=8).grid(row=0, column=1, sticky="w", padx=(6,12))

        ttk.Label(right, text="OFFSET 2").grid(row=0, column=2, sticky="e")
        self.v_off2 = tk.StringVar(value=DEFAULT_AUDIO_OFF2)
        ttk.Entry(right, textvariable=self.v_off2, width=8).grid(row=0, column=3, sticky="w", padx=(6,12))

        ttk.Label(right, text="GAIN 1").grid(row=1, column=0, sticky="e", pady=(6,0))
        self.v_gain1 = tk.StringVar(value=DEFAULT_AUDIO_GAIN1)
        ttk.Entry(right, textvariable=self.v_gain1, width=8).grid(row=1, column=1, sticky="w", padx=(6,12), pady=(6,0))

        ttk.Label(right, text="GAIN 2").grid(row=1, column=2, sticky="e", pady=(6,0))
        self.v_gain2 = tk.StringVar(value=DEFAULT_AUDIO_GAIN2)
        ttk.Entry(right, textvariable=self.v_gain2, width=8).grid(row=1, column=3, sticky="w", padx=(6,12), pady=(6,0))

        # 하단 버튼
        bottom = ttk.Frame(self, padding=10); bottom.pack(fill="x")
        ttk.Button(bottom, text="적용", command=self.apply_only).pack(side="left")
        ttk.Button(bottom, text="원GUI 저장 버튼 클릭", command=self.click_save_only).pack(side="left", padx=8)
        ttk.Button(bottom, text="최종확인(적용→저장→DISCONNECT)", command=self.on_final_confirm).pack(side="left", padx=8)

    # 연결
    def on_connect_manual(self) -> None:
        try:
            self.win = connect_window()
            # 왜: 재연결 시 stale helper 대비해 항상 재생성
            self.h_car   = ComboHelper(self.win, IDs["CAR_COMBO"])
            self.h_color = ComboHelper(self.win, IDs["COLOR_COMBO"])
            self.h_act   = ComboHelper(self.win, IDs["ACT_COMBO"])

            cars   = self.h_car.fetch_titles()
            colors = self.h_color.fetch_titles()
            acts   = self.h_act.fetch_titles()

            self.car_entry.set_values(cars)

            # === 핵심 Fix: 빈 목록이면 current() 호출하지 말고 비우기 ===
            if colors:
                self.color_combo["values"] = colors
                self.color_combo.current(0)
            else:
                self.color_combo["values"] = []
                self.color_combo.set("")

            if acts:
                self.act_combo["values"] = acts
                self.act_combo.current(0)
            else:
                self.act_combo["values"] = []
                self.act_combo.set("")
            # =========================================================

            self.st.set(f"연결됨(차종 {len(cars)}개)")
        except (ElementNotFoundError, PwaTimeout) as e:
            self.st.set("미연결"); messagebox.showerror("연결 실패", str(e))
        except Exception as e:
            self.st.set("미연결"); messagebox.showerror("연결 실패", str(e))

    # 적용
    def apply_only(self) -> None:
        if not self.win:
            messagebox.showwarning("알림", "먼저 [연결]을 눌러주세요."); return
        try:
            car = norm_text(self.car_entry.get())
            col = norm_text(self.color_combo.get())
            act = norm_text(self.act_combo.get())

            if self.h_car and car:
                official = self.h_car.commit(car)
                self.car_entry.delete(0, tk.END); self.car_entry.insert(0, official)
            if self.h_color and col:
                official = self.h_color.commit(col); self.color_combo.set(official)
            if self.h_act and act:
                official = self.h_act.commit(act); self.act_combo.set(official)

            off1 = norm_text(self.v_off1.get())
            off2 = norm_text(self.v_off2.get())
            gain1 = norm_text(self.v_gain1.get())
            gain2 = norm_text(self.v_gain2.get())

            if off1 != "":  set_spinner(self.win, IDs["AUDIO_OFF_1"],  off1)
            if off2 != "":  set_spinner(self.win, IDs["AUDIO_OFF_2"],  off2)
            if gain1 != "": set_spinner(self.win, IDs["AUDIO_GAIN_1"], gain1)
            if gain2 != "": set_spinner(self.win, IDs["AUDIO_GAIN_2"], gain2)

            self.st.set("적용 완료")
        except Exception as e:
            messagebox.showerror("적용 실패", str(e))

    # 저장만
    def click_save_only(self) -> None:
        if not self.win:
            messagebox.showwarning("알림", "먼저 [연결]을 눌러주세요."); return
        try:
            click_button(self.win, IDs["BTN_SAVE"])
        except Exception as e:
            messagebox.showerror("저장 실패", str(e))

    # 최종확인
    def on_final_confirm(self) -> None:
        if not self.win:
            messagebox.showwarning("알림", "먼저 [연결]을 눌러주세요.")
            return
        try:
            self.apply_only()
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

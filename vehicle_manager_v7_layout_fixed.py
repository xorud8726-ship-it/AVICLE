import json
import os
import re
import shutil
import sys
import webbrowser
import zipfile
from datetime import datetime

import requests
import pyotp
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
from PIL import Image, ImageTk
from tkinterdnd2 import TkinterDnD, DND_FILES

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


class DraggableNotebook(ttk.Notebook):
    def __init__(self, master=None, on_reorder=None, **kw):
        super().__init__(master, **kw)
        self._drag_index = None
        self._on_reorder = on_reorder
        self.bind("<ButtonPress-1>", self.on_start, add="+")
        self.bind("<B1-Motion>", self.on_drag, add="+")
        self.bind("<ButtonRelease-1>", self.on_release, add="+")

    def on_start(self, event):
        try:
            self._drag_index = self.index(f"@{event.x},{event.y}")
        except Exception:
            self._drag_index = None

    def on_drag(self, event):
        if self._drag_index is None:
            return
        try:
            new_index = self.index(f"@{event.x},{event.y}")
            current_tab = self.select()
            if new_index != self._drag_index and current_tab:
                self.insert(new_index, current_tab)
                self._drag_index = new_index
        except Exception:
            pass

    def on_release(self, _event):
        if self._drag_index is not None and callable(self._on_reorder):
            self._on_reorder()
        self._drag_index = None


class VehicleManagerApp:
    IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.heic', '.webp')
    VIDEO_EXTS = ('.mp4', '.avi', '.mkv', '.mov', '.wmv')

    def __init__(self, root):
        self.root = root
        self.app_dir = self.get_app_dir()
        self.data_dir = os.path.join(self.app_dir, 'vehicle_data')
        self.backup_dir = os.path.join(self.app_dir, 'backups')
        self.credentials_path = os.path.join(self.app_dir, 'credentials.json')
        self.templates_path = os.path.join(self.app_dir, 'templates.json')
        self.tab_order_path = os.path.join(self.app_dir, 'tab_order.json')
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

        self.root.title("차량 정보 통합 관리 프로그램")
        self.root.geometry("1680x980")
        self.root.minsize(1100, 680)
        self.root.configure(bg="#eef2f6")

        self.TELEGRAM_TOKEN = "8189345934:AAHAE77W34KJXMEFavPF_egC8j4RAIGUoWw"
        self.CHAT_ID = "6736797941"

        self.credentials = self.load_credentials()
        self.templates = self.load_templates()

        self.text_widgets = {}
        self.tab_frames = {}
        self.tab_ids_by_name = {}
        self.undo_stack = {}
        self.image_storage = {}
        self.pdf_listboxes = {}
        self.video_listboxes = {}
        self.image_listboxes = {}
        self.search_results = []
        self.current_search_idx = -1
        self.copy_buffer = []
        self.dragging_img_name = None
        self.dragging_img_source_index = None
        self.current_tab_for_menu = None
        self.current_active_lb = None
        self.current_image_context = None
        self.text_save_jobs = {}
        self.status_clear_job = None

        self.setup_styles()
        self.setup_main_ui()
        self.load_all_tabs()
        self.update_otp_loop()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    @staticmethod
    def get_app_dir():
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background="#eef2f6", borderwidth=0)
        style.configure("TNotebook.Tab", padding=[16, 8], font=("Malgun Gothic", 10), background="#d9e2ec", foreground="#243b53")
        style.map("TNotebook.Tab",
                  background=[("selected", "#ffffff")],
                  foreground=[("selected", "#102a43")])
        style.configure("Card.TFrame", background="#ffffff")

    def setup_main_ui(self):
        self.top_search_bar = tk.Frame(self.root, bg="#102a43", height=54)
        self.top_search_bar.pack(side='top', fill='x')
        self.top_search_bar.pack_propagate(False)

        search_left = tk.Frame(self.top_search_bar, bg="#102a43")
        search_left.pack(side='left', padx=16)

        tk.Label(search_left, text="통합 검색", bg="#102a43", fg="white", font=("Malgun Gothic", 10, "bold")).pack(side='left', padx=(0, 8))
        self.search_entry = tk.Entry(search_left, width=30, font=("Malgun Gothic", 10), relief='flat')
        self.search_entry.pack(side='left', ipady=4)
        self.search_entry.bind("<Return>", lambda e: self.execute_search())

        self.btn_search = self.make_button(search_left, "검색", self.execute_search, "secondary")
        self.btn_search.pack(side='left', padx=(8, 4))
        self.btn_prev_search = self.make_button(search_left, "이전", self.prev_search_result, "secondary")
        self.btn_prev_search.pack(side='left', padx=4)
        self.btn_next_search = self.make_button(search_left, "다음", self.next_search_result, "secondary")
        self.btn_next_search.pack(side='left', padx=4)
        self.search_result_label = tk.Label(search_left, text="0 / 0", bg="#102a43", fg="#d9e2ec", font=("Malgun Gothic", 10, "bold"))
        self.search_result_label.pack(side='left', padx=(10, 0))

        action_right = tk.Frame(self.top_search_bar, bg="#102a43")
        action_right.pack(side='right', padx=16)
        self.make_button(action_right, "새 차량 탭 추가", self.add_sub_tab, "success").pack(side='left', padx=4)
        self.make_button(action_right, "전체 저장", self.save_all_data, "primary").pack(side='left', padx=4)
        self.make_button(action_right, "백업", self.create_backup, "accent").pack(side='left', padx=4)
        self.make_button(action_right, "복원", self.restore_backup, "danger").pack(side='left', padx=4)
        self.make_button(action_right, "상용구 관리", self.open_template_manager, "secondary").pack(side='left', padx=4)

        self.account_bar = tk.Frame(self.root, bg="#f7f9fb", height=56, bd=1, relief='solid', highlightbackground="#d9e2ec", highlightthickness=1)
        self.account_bar.pack(side='top', fill='x', padx=12, pady=(8, 6))
        self.account_bar.pack_propagate(False)

        gsw_frame = tk.Frame(self.account_bar, bg="#f7f9fb")
        gsw_frame.pack(side='left', padx=10)
        self.make_button(gsw_frame, "GSW KIA", lambda: webbrowser.open("https://gsw.kia.com/"), "danger").pack(side='left', padx=(0, 4), pady=10)
        self.make_button(gsw_frame, "GSW HND", lambda: webbrowser.open("https://gsw.hyundai.com/"), "primary").pack(side='left', padx=4, pady=10)

        cred_frame = tk.Frame(self.account_bar, bg="#f7f9fb")
        cred_frame.pack(side='left', padx=(16, 6))
        self.make_button(cred_frame, "아이디 복사", lambda: self.copy_to_clipboard(self.credentials.get("id", ""), "아이디"), "light").pack(side='left', padx=4, pady=10)
        self.make_button(cred_frame, "비밀번호 복사", lambda: self.copy_to_clipboard(self.credentials.get("pw", ""), "비밀번호"), "light").pack(side='left', padx=4, pady=10)
        self.make_button(cred_frame, "아이디 수정", lambda: self.input_credential("id", "아이디"), "secondary").pack(side='left', padx=(12, 4), pady=10)
        self.make_button(cred_frame, "비밀번호 수정", lambda: self.input_credential("pw", "비밀번호"), "secondary").pack(side='left', padx=4, pady=10)
        self.make_button(cred_frame, "KIA OTP 키 수정", lambda: self.input_credential("kia_otp_key", "KIA OTP 키"), "secondary").pack(side='left', padx=(12, 4), pady=10)
        self.make_button(cred_frame, "HND OTP 키 수정", lambda: self.input_credential("hnd_otp_key", "HND OTP 키"), "secondary").pack(side='left', padx=4, pady=10)

        otp_frame = tk.Frame(self.account_bar, bg="#f7f9fb")
        otp_frame.pack(side='right', padx=12)
        self.btn_kia_otp = self.make_button(otp_frame, "KIA OTP: ------", lambda: self.copy_otp_clipboard("kia"), "light", width=18)
        self.btn_kia_otp.pack(side='left', padx=4, pady=10)
        self.btn_hnd_otp = self.make_button(otp_frame, "HND OTP: ------", lambda: self.copy_otp_clipboard("hnd"), "light", width=18)
        self.btn_hnd_otp.pack(side='left', padx=4, pady=10)

        content_wrap = tk.Frame(self.root, bg="#eef2f6")
        content_wrap.pack(fill='both', expand=True, padx=12, pady=(0, 8))

        self.sub_notebook = DraggableNotebook(content_wrap, on_reorder=self.on_tab_reorder)
        self.sub_notebook.pack(fill='both', expand=True)
        self.sub_notebook.bind("<Button-3>", self.show_tab_context_menu)

        self.tab_context_menu = tk.Menu(self.root, tearoff=0)
        self.tab_context_menu.add_command(label="탭 이름 수정", command=self.rename_sub_tab)
        self.tab_context_menu.add_command(label="이 탭 삭제", command=self.delete_sub_tab)

        self.file_context_menu = tk.Menu(self.root, tearoff=0)
        self.file_context_menu.add_command(label="원본 열기", command=self.open_selected_file)
        self.file_context_menu.add_command(label="폴더 열기", command=self.open_selected_file_folder)
        self.file_context_menu.add_separator()
        self.file_context_menu.add_command(label="이름 변경", command=self.rename_selected_file)
        self.file_context_menu.add_command(label="삭제", command=self.delete_selected_file)

        self.image_context_menu = tk.Menu(self.root, tearoff=0)
        self.image_context_menu.add_command(label="원본 열기", command=self.open_context_image)
        self.image_context_menu.add_command(label="폴더 열기", command=self.open_context_image_folder)
        self.image_context_menu.add_separator()
        self.image_context_menu.add_command(label="이미지 설명 입력", command=self.edit_context_image_description)
        self.image_context_menu.add_command(label="이미지 교체", command=self.replace_context_image)
        self.image_context_menu.add_command(label="이미지 삭제", command=self.delete_context_image)
        self.image_context_menu.add_separator()
        self.image_context_menu.add_command(label="위로 이동", command=lambda: self.move_context_image('up'))
        self.image_context_menu.add_command(label="아래로 이동", command=lambda: self.move_context_image('down'))
        self.image_context_menu.add_command(label="맨 위로 이동", command=lambda: self.move_context_image('top'))
        self.image_context_menu.add_command(label="맨 아래로 이동", command=lambda: self.move_context_image('bottom'))

        self.status_var = tk.StringVar(value="준비")
        status_bar = tk.Label(self.root, textvariable=self.status_var, anchor='w', bg="#d9e2ec", fg="#102a43", font=("Malgun Gothic", 9), padx=12)
        status_bar.pack(side='bottom', fill='x')

    def make_button(self, master, text, command, variant="primary", width=None):
        colors = {
            "primary": ("#1f6feb", "white"),
            "secondary": ("#486581", "white"),
            "success": ("#2f9e44", "white"),
            "danger": ("#d64545", "white"),
            "accent": ("#7c3aed", "white"),
            "light": ("#ffffff", "#243b53"),
        }
        bg, fg = colors.get(variant, colors["primary"])
        btn = tk.Button(master, text=text, command=command, bg=bg, fg=fg, activebackground=bg,
                        activeforeground=fg, relief='flat', bd=0, padx=12, pady=6,
                        font=("Malgun Gothic", 9, "bold"), cursor="hand2", width=width)
        return btn

    def create_editor_tab(self, tab_name, load_existing=False):
        frame = tk.Frame(self.sub_notebook, bg="#eef2f6")
        self.tab_frames[tab_name] = frame
        self.sub_notebook.add(frame, text=tab_name)
        tab_id = self.sub_notebook.tabs()[-1]
        self.tab_ids_by_name[tab_name] = tab_id

        canvas_wrap = tk.Frame(frame, bg="#eef2f6")
        canvas_wrap.pack(fill='both', expand=True)

        main_canvas = tk.Canvas(canvas_wrap, bg="#eef2f6", highlightthickness=0, bd=0)
        main_canvas.pack(side='left', fill='both', expand=True)

        main_scroll_y = tk.Scrollbar(canvas_wrap, orient='vertical', command=main_canvas.yview)
        main_scroll_y.pack(side='right', fill='y')
        main_canvas.configure(yscrollcommand=main_scroll_y.set)

        outer = tk.Frame(main_canvas, bg="#eef2f6")
        canvas_window = main_canvas.create_window((0, 0), window=outer, anchor='nw')

        def update_scrollregion(_event=None):
            main_canvas.configure(scrollregion=main_canvas.bbox('all'))

        def resize_inner_width(event):
            main_canvas.itemconfigure(canvas_window, width=event.width)

        def bind_mousewheel(widget):
            widget.bind('<MouseWheel>', lambda e: self.on_tab_canvas_mousewheel(e, main_canvas), add='+')
            widget.bind('<Button-4>', lambda e: self.on_tab_canvas_mousewheel(e, main_canvas), add='+')
            widget.bind('<Button-5>', lambda e: self.on_tab_canvas_mousewheel(e, main_canvas), add='+')

        outer.bind('<Configure>', update_scrollregion)
        main_canvas.bind('<Configure>', resize_inner_width)
        bind_mousewheel(main_canvas)
        bind_mousewheel(outer)

        header_card = tk.Frame(outer, bg="#ffffff", bd=1, relief='solid', highlightbackground="#d9e2ec", highlightthickness=1)
        header_card.pack(fill='x', padx=8, pady=(8, 8))
        bind_mousewheel(header_card)

        left_actions = tk.Frame(header_card, bg="#ffffff")
        left_actions.pack(side='left', padx=10, pady=8)
        self.make_button(left_actions, "상용구 삽입", lambda n=tab_name: self.open_template_picker(n), "accent").pack(side='left', padx=4)
        self.make_button(left_actions, "전체 데이터 텔레그램 전송", lambda n=tab_name: self.send_to_telegram(n), "primary").pack(side='left', padx=4)

        quick_tpl_frame = tk.Frame(header_card, bg="#ffffff")
        quick_tpl_frame.pack(side='right', padx=8, pady=8)
        self.render_quick_templates(quick_tpl_frame, tab_name)

        editor_card = tk.Frame(outer, bg="#ffffff", bd=1, relief='solid', highlightbackground="#d9e2ec", highlightthickness=1)
        editor_card.pack(fill='both', expand=True, padx=8)
        bind_mousewheel(editor_card)

        text_frame = tk.Frame(editor_card, bg="#ffffff")
        text_frame.pack(fill='both', expand=True, padx=10, pady=(10, 6))

        text_scroll_y = tk.Scrollbar(text_frame)
        text_scroll_y.pack(side='right', fill='y')
        text_scroll_x = tk.Scrollbar(text_frame, orient='horizontal')
        text_scroll_x.pack(side='bottom', fill='x')

        tw = tk.Text(text_frame, wrap='word', font=("Malgun Gothic", 11), undo=False,
                     selectbackground="#cfe8ff", bd=0, relief='flat', padx=12, pady=12,
                     yscrollcommand=text_scroll_y.set, xscrollcommand=text_scroll_x.set,
                     spacing1=3, spacing2=2, spacing3=3)
        tw.pack(fill='both', expand=True)
        text_scroll_y.config(command=tw.yview)
        text_scroll_x.config(command=tw.xview)
        self.text_widgets[tab_name] = tw

        tw.bind("<Control-z>", lambda e, n=tab_name: self.perform_undo(e, n))
        tw.bind("<Control-c>", lambda e, n=tab_name: self.on_copy(e, n))
        tw.bind("<Control-v>", lambda e, n=tab_name: self.on_paste(e, n))
        tw.bind("<KeyRelease>", lambda e, n=tab_name: self.on_text_changed(e, n))
        tw.bind("<Button-1>", lambda e, w=tw: self.on_image_press(e, w), add="+")
        tw.bind("<B1-Motion>", lambda e, w=tw: self.on_image_motion(e, w), add="+")
        tw.bind("<ButtonRelease-1>", lambda e, w=tw, n=tab_name: self.on_image_release(e, w, n), add="+")
        tw.bind("<Double-Button-1>", lambda e, w=tw: self.on_image_double_click(e, w), add="+")
        tw.bind("<Button-3>", lambda e, w=tw, n=tab_name: self.on_text_right_click(e, w, n), add="+")
        tw.drop_target_register(DND_FILES)
        tw.dnd_bind('<<Drop>>', lambda e, w=tw, n=tab_name: self.handle_drop(e, w, n))

        bottom_card = tk.Frame(outer, bg="#ffffff", bd=1, relief='solid', highlightbackground="#d9e2ec", highlightthickness=1)
        bottom_card.pack(fill='x', padx=8, pady=(8, 8))
        bind_mousewheel(bottom_card)

        self.image_listboxes[tab_name] = self.create_file_panel(bottom_card, "이미지 갤러리", tab_name, 'image')
        self.pdf_listboxes[tab_name] = self.create_file_panel(bottom_card, "PDF 문서", tab_name, 'pdf')
        self.video_listboxes[tab_name] = self.create_file_panel(bottom_card, "동영상", tab_name, 'video')

        if load_existing:
            self.load_tab_content(tab_name, tw)
        self.save_undo_state(tab_name)
        self.refresh_all_lists(tab_name)
        self.sub_notebook.select(frame)
        self.root.after(50, update_scrollregion)


    def on_tab_canvas_mousewheel(self, event, canvas):
        try:
            if getattr(event, 'num', None) == 4:
                canvas.yview_scroll(-1, 'units')
            elif getattr(event, 'num', None) == 5:
                canvas.yview_scroll(1, 'units')
            else:
                delta = event.delta
                if delta == 0:
                    return 'break'
                step = -1 if delta > 0 else 1
                canvas.yview_scroll(step, 'units')
        except Exception:
            pass
        return 'break'

    def create_file_panel(self, parent, title, tab_name, mode):
        panel = tk.Frame(parent, bg="#ffffff")
        panel.pack(side='left', fill='both', expand=True, padx=6, pady=8)

        tk.Label(panel, text=title, bg="#ffffff", fg="#102a43", font=("Malgun Gothic", 10, "bold")).pack(anchor='w', padx=6, pady=(0, 4))
        listbox = tk.Listbox(panel, height=6, bd=1, relief='solid', font=("Malgun Gothic", 9), activestyle='none', selectbackground="#cfe8ff")
        listbox.pack(fill='both', expand=True, padx=6, pady=(0, 4))

        if mode == 'image':
            listbox.bind("<Double-Button-1>", lambda e, n=tab_name: self.open_selected_gallery_image(n))
            listbox.bind("<<ListboxSelect>>", lambda e, n=tab_name: self.focus_selected_gallery_image(n))
            listbox.bind("<Button-3>", lambda e, n=tab_name: self.show_file_context_menu(e, n, 'image'))
        elif mode == 'pdf':
            listbox.bind("<Double-Button-1>", lambda e, n=tab_name: self.open_listbox_file(n, 'pdf'))
            listbox.bind("<Button-3>", lambda e, n=tab_name: self.show_file_context_menu(e, n, 'pdf'))
        else:
            listbox.bind("<Double-Button-1>", lambda e, n=tab_name: self.open_listbox_file(n, 'video'))
            listbox.bind("<Button-3>", lambda e, n=tab_name: self.show_file_context_menu(e, n, 'video'))
        return listbox

    def render_quick_templates(self, master, tab_name):
        for widget in master.winfo_children():
            widget.destroy()
        tk.Label(master, text="빠른 상용구", bg="#ffffff", fg="#486581", font=("Malgun Gothic", 9, "bold")).pack(side='left', padx=(0, 8))
        for item in self.templates[:5]:
            self.make_button(master, item, lambda t=item, n=tab_name: self.insert_template_text(n, t), "light").pack(side='left', padx=3)

    def on_text_changed(self, event, tab_name):
        if event.keysym in ['Control_L', 'Control_R', 'Shift_L', 'Shift_R', 'Alt_L', 'Alt_R']:
            return
        self.save_undo_state(tab_name)
        self.request_autosave(tab_name, "자동저장 대기 중")

    def request_autosave(self, tab_name, message="자동저장 대기 중"):
        if tab_name in self.text_save_jobs:
            try:
                self.root.after_cancel(self.text_save_jobs[tab_name])
            except Exception:
                pass
        self.set_status(message, auto_clear=False)
        self.text_save_jobs[tab_name] = self.root.after(1200, lambda n=tab_name: self.perform_autosave(n))

    def perform_autosave(self, tab_name):
        self.text_save_jobs.pop(tab_name, None)
        self.save_tab_data(tab_name)
        self.save_tab_order()
        self.set_status(f"자동저장 완료: {tab_name}")

    def set_status(self, text, auto_clear=True):
        self.status_var.set(text)
        if self.status_clear_job:
            try:
                self.root.after_cancel(self.status_clear_job)
            except Exception:
                pass
            self.status_clear_job = None
        if auto_clear:
            self.status_clear_job = self.root.after(2500, lambda: self.status_var.set("준비"))

    def update_otp_loop(self):
        for brand, key, button in [("KIA", "kia_otp_key", self.btn_kia_otp), ("HND", "hnd_otp_key", self.btn_hnd_otp)]:
            secret = self.credentials.get(key, "").replace(' ', '')
            if secret:
                try:
                    otp = pyotp.TOTP(secret).now()
                    button.config(text=f"{brand} OTP: {otp}")
                except Exception:
                    button.config(text=f"{brand} OTP: 오류")
            else:
                button.config(text=f"{brand} OTP: ------")
        self.root.after(1000, self.update_otp_loop)

    def input_credential(self, key, label_text):
        current = self.credentials.get(key, "")
        new_value = simpledialog.askstring("정보 입력", f"{label_text} 입력:", initialvalue=current, parent=self.root)
        if new_value is not None:
            self.credentials[key] = new_value.strip()
            self.save_credentials()
            self.set_status(f"{label_text} 저장 완료")

    def copy_to_clipboard(self, text, name):
        if not text:
            messagebox.showwarning("안내", f"저장된 {name} 정보가 없습니다.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.set_status(f"{name} 복사 완료")

    def copy_otp_clipboard(self, brand):
        button = self.btn_kia_otp if brand == "kia" else self.btn_hnd_otp
        value = button.cget("text").split(": ")[-1]
        if value and value not in ("------", "오류"):
            self.root.clipboard_clear()
            self.root.clipboard_append(value)
            self.set_status(f"{brand.upper()} OTP 복사 완료")

    def open_template_manager(self):
        win = tk.Toplevel(self.root)
        win.title("상용구 관리")
        win.geometry("520x430")
        win.configure(bg="#f7f9fb")

        top = tk.Frame(win, bg="#f7f9fb")
        top.pack(fill='x', padx=12, pady=12)
        entry = tk.Entry(top, font=("Malgun Gothic", 10))
        entry.pack(side='left', fill='x', expand=True, ipady=4)
        self.make_button(top, "추가", lambda: add_template(), "success").pack(side='left', padx=(8, 0))

        lb = tk.Listbox(win, font=("Malgun Gothic", 10), selectbackground="#cfe8ff")
        lb.pack(fill='both', expand=True, padx=12, pady=(0, 12))

        for item in self.templates:
            lb.insert(tk.END, item)

        bottom = tk.Frame(win, bg="#f7f9fb")
        bottom.pack(fill='x', padx=12, pady=(0, 12))

        def refresh_list():
            lb.delete(0, tk.END)
            for item in self.templates:
                lb.insert(tk.END, item)
            self.save_templates()
            self.refresh_all_quick_templates()

        def add_template():
            text = entry.get().strip()
            if not text:
                return
            if text not in self.templates:
                self.templates.append(text)
            entry.delete(0, tk.END)
            refresh_list()

        def edit_template():
            try:
                idx = lb.curselection()[0]
            except Exception:
                return
            old = self.templates[idx]
            new = simpledialog.askstring("상용구 수정", "문구 입력:", initialvalue=old, parent=win)
            if new:
                self.templates[idx] = new.strip()
                refresh_list()

        def delete_template():
            try:
                idx = lb.curselection()[0]
            except Exception:
                return
            if messagebox.askyesno("삭제", "선택한 상용구를 삭제할까요?", parent=win):
                del self.templates[idx]
                refresh_list()

        self.make_button(bottom, "수정", edit_template, "secondary").pack(side='left', padx=4)
        self.make_button(bottom, "삭제", delete_template, "danger").pack(side='left', padx=4)
        self.make_button(bottom, "닫기", win.destroy, "light").pack(side='right', padx=4)

    def open_template_picker(self, tab_name):
        win = tk.Toplevel(self.root)
        win.title("상용구 삽입")
        win.geometry("420x360")
        win.configure(bg="#f7f9fb")

        tk.Label(win, text="삽입할 상용구를 선택하세요.", bg="#f7f9fb", fg="#102a43", font=("Malgun Gothic", 10, "bold")).pack(anchor='w', padx=12, pady=(12, 8))
        lb = tk.Listbox(win, font=("Malgun Gothic", 10), selectbackground="#cfe8ff")
        lb.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        for item in self.templates:
            lb.insert(tk.END, item)

        def insert_selected():
            try:
                value = lb.get(lb.curselection())
            except Exception:
                return
            self.insert_template_text(tab_name, value)
            win.destroy()

        bottom = tk.Frame(win, bg="#f7f9fb")
        bottom.pack(fill='x', padx=12, pady=(0, 12))
        self.make_button(bottom, "삽입", insert_selected, "success").pack(side='left', padx=4)
        self.make_button(bottom, "닫기", win.destroy, "light").pack(side='right', padx=4)
        lb.bind("<Double-Button-1>", lambda e: insert_selected())

    def insert_template_text(self, tab_name, text):
        tw = self.text_widgets[tab_name]
        tw.insert(tk.INSERT, text + "\n")
        tw.focus_set()
        self.save_undo_state(tab_name)
        self.request_autosave(tab_name, "상용구 삽입 후 저장 중")

    def refresh_all_quick_templates(self):
        for tab_name, frame in self.tab_frames.items():
            header_card = frame.winfo_children()[0].winfo_children()[0]
            quick_tpl_frame = header_card.winfo_children()[1]
            self.render_quick_templates(quick_tpl_frame, tab_name)

    def execute_search(self):
        query = self.search_entry.get().strip().lower()
        self.clear_search_highlight()
        self.search_results = []
        self.current_search_idx = -1
        if not query:
            self.update_search_status()
            return

        for tab_id in self.sub_notebook.tabs():
            tab_name = self.sub_notebook.tab(tab_id, "text")
            tw = self.text_widgets.get(tab_name)
            if not tw:
                continue

            if query in tab_name.lower():
                self.search_results.append({"tab": tab_name, "kind": "탭 이름", "index": None, "preview": tab_name})

            text_content = tw.get("1.0", tk.END)
            start = "1.0"
            while True:
                pos = tw.search(query, start, stopindex=tk.END, nocase=True)
                if not pos:
                    break
                end = f"{pos}+{len(query)}c"
                preview = tw.get(pos, f"{pos} lineend").strip()
                self.search_results.append({"tab": tab_name, "kind": "본문", "index": pos, "end": end, "preview": preview})
                start = end

            for image_name in tw.image_names():
                data = self.image_storage.get(image_name)
                if not data:
                    continue
                desc = data.get("description", "")
                file_name = os.path.basename(data.get("path", ""))
                if query in desc.lower():
                    self.search_results.append({"tab": tab_name, "kind": "이미지 설명", "index": tw.index(image_name), "image_name": image_name, "preview": desc})
                if query in file_name.lower():
                    self.search_results.append({"tab": tab_name, "kind": "이미지 파일명", "index": tw.index(image_name), "image_name": image_name, "preview": file_name})

            folder = self.get_tab_dir(tab_name)
            if os.path.exists(folder):
                for name in os.listdir(folder):
                    low = name.lower()
                    if query in low:
                        if low.endswith('.pdf'):
                            self.search_results.append({"tab": tab_name, "kind": "PDF 파일명", "index": None, "preview": name})
                        elif low.endswith(self.VIDEO_EXTS):
                            self.search_results.append({"tab": tab_name, "kind": "동영상 파일명", "index": None, "preview": name})

        if self.search_results:
            self.current_search_idx = 0
            self.move_to_search_result()
        else:
            self.set_status("검색 결과가 없습니다.")
            self.update_search_status()

    def update_search_status(self):
        total = len(self.search_results)
        current = self.current_search_idx + 1 if total and self.current_search_idx >= 0 else 0
        self.search_result_label.config(text=f"{current} / {total}")

    def clear_search_highlight(self):
        for tw in self.text_widgets.values():
            tw.tag_remove("search_highlight", "1.0", tk.END)

    def move_to_search_result(self):
        if not self.search_results:
            self.update_search_status()
            return
        result = self.search_results[self.current_search_idx]
        tab_name = result["tab"]
        frame = self.tab_frames.get(tab_name)
        if frame:
            self.sub_notebook.select(frame)
        tw = self.text_widgets[tab_name]
        tw.tag_remove("search_highlight", "1.0", tk.END)
        tw.tag_config("search_highlight", background="#fff3a3")

        if result.get("index"):
            idx = result["index"]
            if result.get("end"):
                tw.tag_add("search_highlight", idx, result["end"])
            tw.mark_set(tk.INSERT, idx)
            tw.see(idx)
        self.update_search_status()
        self.set_status(f"검색 결과 {self.current_search_idx + 1}/{len(self.search_results)} - {result['kind']}: {result['preview'][:60]}")

    def next_search_result(self):
        if not self.search_results:
            return
        self.current_search_idx = (self.current_search_idx + 1) % len(self.search_results)
        self.move_to_search_result()

    def prev_search_result(self):
        if not self.search_results:
            return
        self.current_search_idx = (self.current_search_idx - 1) % len(self.search_results)
        self.move_to_search_result()

    def get_tab_dir(self, tab_name):
        path = os.path.join(self.data_dir, tab_name)
        os.makedirs(path, exist_ok=True)
        return path

    def get_tab_meta_path(self, tab_name):
        return os.path.join(self.get_tab_dir(tab_name), "content.json")

    def handle_drop(self, event, tw, tab_name):
        dropped = re.findall(r'\{.*?\}|\S+', event.data)
        for raw_path in dropped:
            clean = raw_path.strip('{}')
            ext = os.path.splitext(clean)[1].lower()
            abs_path = os.path.abspath(clean)
            if not os.path.exists(abs_path):
                continue
            if ext in self.IMAGE_EXTS:
                self.insert_image_to_widget(abs_path, tw, tab_name)
            elif ext == '.pdf' or ext in self.VIDEO_EXTS:
                dest = self.get_unique_path(self.get_tab_dir(tab_name), os.path.basename(abs_path))
                shutil.copy2(abs_path, dest)
        self.refresh_all_lists(tab_name)
        self.request_autosave(tab_name, "파일 추가 후 저장 중")

    def insert_image_to_widget(self, file_path, tw, tab_name, index=tk.INSERT, description="", save_undo=True):
        dest_dir = self.get_tab_dir(tab_name)
        src_abs = os.path.abspath(file_path)
        if os.path.dirname(src_abs) != os.path.abspath(dest_dir):
            dest = self.get_unique_path(dest_dir, os.path.basename(src_abs))
            shutil.copy2(src_abs, dest)
        else:
            dest = src_abs
        try:
            img = Image.open(dest)
            img.thumbnail((220, 220))
            photo = ImageTk.PhotoImage(img)
            image_name = tw.image_create(index, image=photo)
            self.image_storage[image_name] = {
                "photo": photo,
                "path": dest,
                "description": description or "",
            }
            if save_undo:
                self.save_undo_state(tab_name)
            self.refresh_image_list(tab_name)
            return image_name
        except Exception as exc:
            messagebox.showerror("오류", f"이미지 삽입 실패\n{exc}")
            return None

    def get_image_name_at_index(self, tw, index):
        try:
            target = tw.index(index)
        except Exception:
            return None
        for name in tw.image_names():
            try:
                if tw.index(name) == target:
                    return name
            except Exception:
                continue
        return None

    def on_text_right_click(self, event, tw, tab_name):
        image_name = self.get_image_name_at_index(tw, f"@{event.x},{event.y}")
        if image_name:
            self.current_image_context = {"tab_name": tab_name, "image_name": image_name}
            self.image_context_menu.post(event.x_root, event.y_root)
            return "break"
        return None

    def on_image_press(self, event, tw):
        image_name = self.get_image_name_at_index(tw, f"@{event.x},{event.y}")
        if image_name:
            self.dragging_img_name = image_name
            self.dragging_img_source_index = tw.index(image_name)
            tw.config(cursor="fleur")
        else:
            self.dragging_img_name = None
            self.dragging_img_source_index = None

    def on_image_motion(self, event, tw):
        if self.dragging_img_name:
            tw.mark_set("insert", tw.index(f"@{event.x},{event.y}"))
            return "break"
        return None

    def on_image_release(self, event, tw, tab_name):
        if not self.dragging_img_name:
            return None
        data = self.image_storage.get(self.dragging_img_name)
        if data:
            new_index = tw.index(f"@{event.x},{event.y}")
            old_name = self.dragging_img_name
            old_data = dict(data)
            tw.delete(old_name)
            self.image_storage.pop(old_name, None)
            new_name = tw.image_create(new_index, image=old_data["photo"])
            self.image_storage[new_name] = old_data
            self.save_undo_state(tab_name)
            self.refresh_image_list(tab_name)
            self.request_autosave(tab_name, "이미지 이동 후 저장 중")
        self.dragging_img_name = None
        self.dragging_img_source_index = None
        tw.config(cursor="xterm")
        return "break"

    def on_image_double_click(self, event, tw):
        image_name = self.get_image_name_at_index(tw, f"@{event.x},{event.y}")
        if not image_name:
            return None
        data = self.image_storage.get(image_name)
        if not data:
            return None
        top = tk.Toplevel(self.root)
        top.title("이미지 보기")
        img = Image.open(data["path"])
        max_w = int(self.root.winfo_screenwidth() * 0.8)
        max_h = int(self.root.winfo_screenheight() * 0.8)
        img.thumbnail((max_w, max_h))
        photo = ImageTk.PhotoImage(img)
        label = tk.Label(top, image=photo)
        label.image = photo
        label.pack(padx=10, pady=10)
        return "break"

    def open_context_image(self):
        ctx = self.current_image_context
        if not ctx:
            return
        data = self.image_storage.get(ctx["image_name"])
        if data and os.path.exists(data["path"]):
            os.startfile(data["path"])

    def open_context_image_folder(self):
        ctx = self.current_image_context
        if not ctx:
            return
        data = self.image_storage.get(ctx["image_name"])
        if data and os.path.exists(data["path"]):
            os.startfile(os.path.dirname(data["path"]))

    def edit_context_image_description(self):
        ctx = self.current_image_context
        if not ctx:
            return
        data = self.image_storage.get(ctx["image_name"])
        if not data:
            return
        desc = simpledialog.askstring("이미지 설명", "이미지 설명 입력:", initialvalue=data.get("description", ""), parent=self.root)
        if desc is not None:
            data["description"] = desc.strip()
            self.refresh_image_list(ctx["tab_name"])
            self.request_autosave(ctx["tab_name"], "이미지 설명 저장 중")

    def replace_context_image(self):
        ctx = self.current_image_context
        if not ctx:
            return
        tab_name = ctx["tab_name"]
        image_name = ctx["image_name"]
        tw = self.text_widgets[tab_name]
        old_data = self.image_storage.get(image_name)
        if not old_data:
            return
        file_path = filedialog.askopenfilename(title="교체할 이미지 선택", filetypes=[("이미지 파일", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.heic;*.webp")])
        if not file_path:
            return
        index = tw.index(image_name)
        desc = old_data.get("description", "")
        tw.delete(image_name)
        self.image_storage.pop(image_name, None)
        self.insert_image_to_widget(file_path, tw, tab_name, index=index, description=desc, save_undo=True)
        self.request_autosave(tab_name, "이미지 교체 후 저장 중")

    def delete_context_image(self):
        ctx = self.current_image_context
        if not ctx:
            return
        tab_name = ctx["tab_name"]
        image_name = ctx["image_name"]
        tw = self.text_widgets[tab_name]
        if messagebox.askyesno("삭제", "선택한 이미지를 삭제할까요?"):
            tw.delete(image_name)
            self.image_storage.pop(image_name, None)
            self.save_undo_state(tab_name)
            self.refresh_image_list(tab_name)
            self.request_autosave(tab_name, "이미지 삭제 후 저장 중")

    def move_context_image(self, direction):
        ctx = self.current_image_context
        if not ctx:
            return
        tab_name = ctx["tab_name"]
        image_name = ctx["image_name"]
        tw = self.text_widgets[tab_name]
        data = self.image_storage.get(image_name)
        if not data:
            return
        current_idx = tw.index(image_name)
        if direction == 'up':
            target = tw.index(f"{current_idx} -1 lines")
        elif direction == 'down':
            target = tw.index(f"{current_idx} +1 lines")
        elif direction == 'top':
            target = "1.0"
        else:
            target = tk.END
        old_data = dict(data)
        tw.delete(image_name)
        self.image_storage.pop(image_name, None)
        new_name = tw.image_create(target, image=old_data["photo"])
        self.image_storage[new_name] = old_data
        self.current_image_context["image_name"] = new_name
        self.save_undo_state(tab_name)
        self.refresh_image_list(tab_name)
        self.request_autosave(tab_name, "이미지 정렬 후 저장 중")

    def refresh_all_lists(self, tab_name):
        self.refresh_image_list(tab_name)
        self.refresh_file_lists(tab_name)

    def refresh_image_list(self, tab_name):
        lb = self.image_listboxes.get(tab_name)
        tw = self.text_widgets.get(tab_name)
        if not lb or not tw:
            return
        lb.delete(0, tk.END)
        for idx, image_name in enumerate(tw.image_names(), start=1):
            data = self.image_storage.get(image_name)
            if not data:
                continue
            file_name = os.path.basename(data.get("path", ""))
            desc = data.get("description", "")
            display = f"{idx}. {file_name}"
            if desc:
                display += f" | {desc}"
            lb.insert(tk.END, display)

    def refresh_file_lists(self, tab_name):
        pdf_lb = self.pdf_listboxes.get(tab_name)
        video_lb = self.video_listboxes.get(tab_name)
        if not pdf_lb or not video_lb:
            return
        pdf_lb.delete(0, tk.END)
        video_lb.delete(0, tk.END)
        folder = self.get_tab_dir(tab_name)
        for name in sorted(os.listdir(folder)):
            low = name.lower()
            if low.endswith('.pdf'):
                pdf_lb.insert(tk.END, name)
            elif low.endswith(self.VIDEO_EXTS):
                video_lb.insert(tk.END, name)

    def focus_selected_gallery_image(self, tab_name):
        lb = self.image_listboxes.get(tab_name)
        tw = self.text_widgets.get(tab_name)
        if not lb or not tw:
            return
        try:
            idx = lb.curselection()[0]
        except Exception:
            return
        image_names = tw.image_names()
        if idx < len(image_names):
            image_name = image_names[idx]
            tw.see(tw.index(image_name))
            self.sub_notebook.select(self.tab_frames[tab_name])

    def open_selected_gallery_image(self, tab_name):
        lb = self.image_listboxes.get(tab_name)
        tw = self.text_widgets.get(tab_name)
        if not lb or not tw:
            return
        try:
            idx = lb.curselection()[0]
        except Exception:
            return
        image_names = tw.image_names()
        if idx < len(image_names):
            image_name = image_names[idx]
            data = self.image_storage.get(image_name)
            if data and os.path.exists(data["path"]):
                os.startfile(data["path"])

    def show_file_context_menu(self, event, tab_name, mode):
        listbox_map = {
            'image': self.image_listboxes,
            'pdf': self.pdf_listboxes,
            'video': self.video_listboxes,
        }
        lb = listbox_map[mode][tab_name]
        idx = lb.nearest(event.y)
        if idx < 0:
            return
        lb.selection_clear(0, tk.END)
        lb.selection_set(idx)
        self.current_active_lb = (tab_name, mode)
        if mode == 'image':
            tw = self.text_widgets[tab_name]
            image_names = tw.image_names()
            if idx < len(image_names):
                self.current_image_context = {"tab_name": tab_name, "image_name": image_names[idx]}
                self.image_context_menu.post(event.x_root, event.y_root)
        else:
            self.file_context_menu.post(event.x_root, event.y_root)

    def open_listbox_file(self, tab_name, mode):
        lb = self.pdf_listboxes[tab_name] if mode == 'pdf' else self.video_listboxes[tab_name]
        try:
            name = lb.get(lb.curselection())
        except Exception:
            return
        path = os.path.join(self.get_tab_dir(tab_name), name)
        if os.path.exists(path):
            os.startfile(path)

    def open_selected_file(self):
        if not self.current_active_lb:
            return
        tab_name, mode = self.current_active_lb
        self.open_listbox_file(tab_name, 'pdf' if mode == 'pdf' else 'video')

    def open_selected_file_folder(self):
        if not self.current_active_lb:
            return
        tab_name, mode = self.current_active_lb
        lb = self.pdf_listboxes[tab_name] if mode == 'pdf' else self.video_listboxes[tab_name]
        try:
            name = lb.get(lb.curselection())
        except Exception:
            return
        folder = self.get_tab_dir(tab_name)
        if os.path.exists(os.path.join(folder, name)):
            os.startfile(folder)

    def rename_selected_file(self):
        if not self.current_active_lb:
            return
        tab_name, mode = self.current_active_lb
        lb = self.pdf_listboxes[tab_name] if mode == 'pdf' else self.video_listboxes[tab_name]
        try:
            old_name = lb.get(lb.curselection())
        except Exception:
            return
        base, ext = os.path.splitext(old_name)
        new_base = simpledialog.askstring("이름 변경", f"새 파일명 입력 ({ext} 제외):", initialvalue=base, parent=self.root)
        if not new_base:
            return
        old_path = os.path.join(self.get_tab_dir(tab_name), old_name)
        new_path = self.get_unique_path(self.get_tab_dir(tab_name), new_base.strip() + ext)
        os.rename(old_path, new_path)
        self.refresh_file_lists(tab_name)
        self.request_autosave(tab_name, "파일 이름 변경 후 저장 중")

    def delete_selected_file(self):
        if not self.current_active_lb:
            return
        tab_name, mode = self.current_active_lb
        lb = self.pdf_listboxes[tab_name] if mode == 'pdf' else self.video_listboxes[tab_name]
        try:
            name = lb.get(lb.curselection())
        except Exception:
            return
        path = os.path.join(self.get_tab_dir(tab_name), name)
        if messagebox.askyesno("삭제", f"'{name}' 파일을 삭제할까요?"):
            if os.path.exists(path):
                os.remove(path)
            self.refresh_file_lists(tab_name)
            self.request_autosave(tab_name, "파일 삭제 후 저장 중")

    def save_undo_state(self, tab_name):
        tw = self.text_widgets.get(tab_name)
        if not tw:
            return
        data = []
        for kind, value, _index in tw.dump("1.0", tk.END, image=True, text=True):
            if kind == "text":
                data.append({"type": "text", "value": value})
            elif kind == "image":
                image_info = self.image_storage.get(value)
                if image_info:
                    data.append({
                        "type": "image",
                        "path": image_info["path"],
                        "description": image_info.get("description", ""),
                    })
        self.undo_stack.setdefault(tab_name, []).append(data)
        if len(self.undo_stack[tab_name]) > 30:
            self.undo_stack[tab_name].pop(0)

    def perform_undo(self, event, tab_name):
        history = self.undo_stack.get(tab_name, [])
        if len(history) < 2:
            return "break"
        history.pop()
        last_state = history[-1]
        tw = self.text_widgets[tab_name]
        tw.delete("1.0", tk.END)
        for image_name in list(tw.image_names()):
            self.image_storage.pop(image_name, None)
        for item in last_state:
            if item["type"] == "text":
                tw.insert(tk.END, item["value"])
            else:
                self.insert_image_to_widget(item["path"], tw, tab_name, index=tk.END,
                                            description=item.get("description", ""), save_undo=False)
        self.refresh_image_list(tab_name)
        self.request_autosave(tab_name, "되돌리기 후 저장 중")
        return "break"

    def on_copy(self, event, tab_name):
        tw = self.text_widgets[tab_name]
        try:
            sel_start, sel_end = tw.index("sel.first"), tw.index("sel.last")
        except Exception:
            return None
        self.copy_buffer = []
        for kind, value, _idx in tw.dump(sel_start, sel_end, image=True, text=True):
            if kind == "text":
                self.copy_buffer.append({"type": "text", "value": value})
            elif kind == "image" and value in self.image_storage:
                data = self.image_storage[value]
                self.copy_buffer.append({
                    "type": "image",
                    "path": data["path"],
                    "description": data.get("description", ""),
                })
        return "break"

    def on_paste(self, event, tab_name):
        tw = self.text_widgets[tab_name]
        if not self.copy_buffer:
            return None
        for item in self.copy_buffer:
            if item["type"] == "text":
                tw.insert(tk.INSERT, item["value"])
            else:
                self.insert_image_to_widget(item["path"], tw, tab_name, index=tk.INSERT,
                                            description=item.get("description", ""), save_undo=False)
        self.save_undo_state(tab_name)
        self.request_autosave(tab_name, "붙여넣기 후 저장 중")
        return "break"

    def save_tab_data(self, tab_name):
        tw = self.text_widgets.get(tab_name)
        if not tw:
            return
        data = []
        for kind, value, _index in tw.dump("1.0", tk.END, image=True, text=True):
            if kind == "text":
                data.append({"type": "text", "value": value})
            elif kind == "image":
                image_info = self.image_storage.get(value)
                if image_info:
                    data.append({
                        "type": "image",
                        "value": os.path.basename(image_info["path"]),
                        "description": image_info.get("description", ""),
                    })
        with open(self.get_tab_meta_path(tab_name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_tab_content(self, tab_name, tw):
        meta_path = self.get_tab_meta_path(tab_name)
        if not os.path.exists(meta_path):
            return
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            if item["type"] == "text":
                tw.insert(tk.END, item.get("value", ""))
            elif item["type"] == "image":
                image_path = os.path.join(self.get_tab_dir(tab_name), item.get("value", ""))
                if os.path.exists(image_path):
                    self.insert_image_to_widget(image_path, tw, tab_name, index=tk.END,
                                                description=item.get("description", ""), save_undo=False)

    def save_all_data(self):
        for tab_name in list(self.text_widgets.keys()):
            self.save_tab_data(tab_name)
        self.save_credentials()
        self.save_templates()
        self.save_tab_order()
        self.set_status("전체 저장 완료")
        messagebox.showinfo("저장 완료", "전체 저장이 완료되었습니다.")

    def load_all_tabs(self):
        saved_dirs = [d for d in os.listdir(self.data_dir) if os.path.isdir(os.path.join(self.data_dir, d))]
        order = self.load_tab_order()
        ordered_tabs = [name for name in order if name in saved_dirs]
        ordered_tabs += [name for name in sorted(saved_dirs) if name not in ordered_tabs]

        if not ordered_tabs:
            self.create_editor_tab("신규차량", load_existing=False)
            self.save_tab_order()
            return
        for tab_name in ordered_tabs:
            self.create_editor_tab(tab_name, load_existing=True)
        self.save_tab_order()

    def add_sub_tab(self):
        name = simpledialog.askstring("새 차량 탭", "차량 탭 이름 입력:", parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in self.text_widgets:
            messagebox.showwarning("중복", "이미 같은 이름의 탭이 있습니다.")
            return
        self.create_editor_tab(name, load_existing=False)
        self.save_tab_order()
        self.request_autosave(name, "새 탭 생성 후 저장 중")

    def rename_sub_tab(self):
        current = self.sub_notebook.select()
        if not current:
            return
        old_name = self.sub_notebook.tab(current, "text")
        new_name = simpledialog.askstring("탭 이름 수정", "새 차량 탭 이름:", initialvalue=old_name, parent=self.root)
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name or new_name == old_name:
            return
        if new_name in self.text_widgets:
            messagebox.showwarning("중복", "이미 같은 이름의 탭이 있습니다.")
            return
        old_dir = self.get_tab_dir(old_name)
        new_dir = os.path.join(self.data_dir, new_name)
        os.rename(old_dir, new_dir)
        self.text_widgets[new_name] = self.text_widgets.pop(old_name)
        self.pdf_listboxes[new_name] = self.pdf_listboxes.pop(old_name)
        self.video_listboxes[new_name] = self.video_listboxes.pop(old_name)
        self.image_listboxes[new_name] = self.image_listboxes.pop(old_name)
        self.undo_stack[new_name] = self.undo_stack.pop(old_name, [])
        self.tab_frames[new_name] = self.tab_frames.pop(old_name)
        self.sub_notebook.tab(current, text=new_name)
        self.tab_ids_by_name[new_name] = self.tab_ids_by_name.pop(old_name)
        self.save_tab_order()
        self.request_autosave(new_name, "탭 이름 변경 후 저장 중")

    def delete_sub_tab(self):
        current = self.sub_notebook.select()
        if not current:
            return
        tab_name = self.sub_notebook.tab(current, "text")
        if not messagebox.askyesno("탭 삭제", f"'{tab_name}' 탭과 모든 데이터를 삭제할까요?"):
            return
        folder = self.get_tab_dir(tab_name)
        if os.path.exists(folder):
            shutil.rmtree(folder)
        self.sub_notebook.forget(current)
        self.text_widgets.pop(tab_name, None)
        self.pdf_listboxes.pop(tab_name, None)
        self.video_listboxes.pop(tab_name, None)
        self.image_listboxes.pop(tab_name, None)
        self.undo_stack.pop(tab_name, None)
        self.tab_frames.pop(tab_name, None)
        self.tab_ids_by_name.pop(tab_name, None)
        self.save_tab_order()
        self.set_status(f"탭 삭제 완료: {tab_name}")
        if not self.sub_notebook.tabs():
            self.create_editor_tab("신규차량", load_existing=False)
            self.save_tab_order()

    def show_tab_context_menu(self, event):
        element = self.sub_notebook.identify(event.x, event.y)
        if "label" in element:
            try:
                index = self.sub_notebook.index(f"@{event.x},{event.y}")
                self.sub_notebook.select(index)
                self.tab_context_menu.post(event.x_root, event.y_root)
            except Exception:
                return

    def on_tab_reorder(self):
        self.save_tab_order()
        self.set_status("탭 순서 저장 완료")

    def save_tab_order(self):
        order = [self.sub_notebook.tab(tab_id, "text") for tab_id in self.sub_notebook.tabs()]
        with open(self.tab_order_path, "w", encoding="utf-8") as f:
            json.dump(order, f, ensure_ascii=False, indent=2)

    def load_tab_order(self):
        if os.path.exists(self.tab_order_path):
            try:
                with open(self.tab_order_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
            except Exception:
                return []
        return []

    def create_backup(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"차량백업_{timestamp}.zip")
        self.save_all_data_silent()
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root_dir, _, files in os.walk(self.data_dir):
                for file_name in files:
                    full_path = os.path.join(root_dir, file_name)
                    arcname = os.path.relpath(full_path, self.app_dir)
                    zf.write(full_path, arcname)
            for extra in [self.credentials_path, self.templates_path, self.tab_order_path]:
                if os.path.exists(extra):
                    zf.write(extra, os.path.relpath(extra, self.app_dir))
        self.set_status(f"백업 완료: {os.path.basename(backup_path)}")
        messagebox.showinfo("백업 완료", f"백업 파일이 생성되었습니다.\n{backup_path}")

    def restore_backup(self):
        file_path = filedialog.askopenfilename(title="복원할 백업 파일 선택", filetypes=[("ZIP 파일", "*.zip")], initialdir=self.backup_dir)
        if not file_path:
            return
        if not messagebox.askyesno("복원 확인", "현재 데이터를 덮어쓰고 백업을 복원할까요?\n복원 전 현재 데이터는 자동으로 한 번 더 백업됩니다."):
            return
        self.create_backup_quiet()
        temp_extract = os.path.join(self.app_dir, "_restore_temp")
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)
        os.makedirs(temp_extract, exist_ok=True)
        with zipfile.ZipFile(file_path, 'r') as zf:
            zf.extractall(temp_extract)

        restored_data_dir = os.path.join(temp_extract, 'vehicle_data')
        if os.path.exists(restored_data_dir):
            if os.path.exists(self.data_dir):
                shutil.rmtree(self.data_dir)
            shutil.copytree(restored_data_dir, self.data_dir)

        for rel in ['credentials.json', 'templates.json', 'tab_order.json']:
            src = os.path.join(temp_extract, rel)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(self.app_dir, rel))

        shutil.rmtree(temp_extract, ignore_errors=True)
        messagebox.showinfo("복원 완료", "백업 복원이 완료되었습니다. 프로그램을 다시 실행해 주세요.")
        self.root.destroy()

    def create_backup_quiet(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"자동백업_{timestamp}.zip")
        self.save_all_data_silent()
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root_dir, _, files in os.walk(self.data_dir):
                for file_name in files:
                    full_path = os.path.join(root_dir, file_name)
                    zf.write(full_path, os.path.relpath(full_path, self.app_dir))
            for extra in [self.credentials_path, self.templates_path, self.tab_order_path]:
                if os.path.exists(extra):
                    zf.write(extra, os.path.relpath(extra, self.app_dir))

    def save_all_data_silent(self):
        for tab_name in list(self.text_widgets.keys()):
            self.save_tab_data(tab_name)
        self.save_credentials()
        self.save_templates()
        self.save_tab_order()

    def send_to_telegram(self, tab_name):
        self.save_tab_data(tab_name)
        token = self.TELEGRAM_TOKEN.strip()
        chat_id = self.CHAT_ID.strip()
        if not token or not chat_id:
            messagebox.showwarning("안내", "텔레그램 토큰과 채팅 ID를 코드에 입력한 뒤 사용해 주세요.")
            return
        tw = self.text_widgets[tab_name]
        content = tw.get("1.0", tk.END).strip()
        image_paths = [self.image_storage[name]["path"] for name in tw.image_names() if name in self.image_storage]
        folder = self.get_tab_dir(tab_name)
        pdf_files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith('.pdf')]
        video_files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(self.VIDEO_EXTS)]

        try:
            if image_paths:
                media = []
                files = {}
                for i, path in enumerate(image_paths[:10]):
                    media.append({
                        "type": "photo",
                        "media": f"attach://p{i}",
                        "caption": f"[{tab_name}]\n{content}" if i == 0 else ""
                    })
                    files[f"p{i}"] = open(path, 'rb')
                requests.post(f"https://api.telegram.org/bot{token}/sendMediaGroup",
                              data={"chat_id": chat_id, "media": json.dumps(media, ensure_ascii=False)}, files=files, timeout=30)
                for f in files.values():
                    f.close()
            elif content:
                requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              data={"chat_id": chat_id, "text": f"[{tab_name}]\n{content}"}, timeout=30)

            for path in pdf_files:
                with open(path, 'rb') as f:
                    requests.post(f"https://api.telegram.org/bot{token}/sendDocument",
                                  data={"chat_id": chat_id}, files={"document": f}, timeout=60)
            for path in video_files:
                with open(path, 'rb') as f:
                    requests.post(f"https://api.telegram.org/bot{token}/sendVideo",
                                  data={"chat_id": chat_id}, files={"video": f}, timeout=120)
            messagebox.showinfo("전송 완료", f"'{tab_name}' 탭 데이터 전송이 완료되었습니다.")
        except Exception as exc:
            messagebox.showerror("전송 오류", str(exc))

    def load_credentials(self):
        default = {"id": "", "pw": "", "kia_otp_key": "", "hnd_otp_key": ""}
        if os.path.exists(self.credentials_path):
            try:
                with open(self.credentials_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                default.update(data)
            except Exception:
                pass
        return default

    def save_credentials(self):
        with open(self.credentials_path, "w", encoding="utf-8") as f:
            json.dump(self.credentials, f, ensure_ascii=False, indent=2)

    def load_templates(self):
        defaults = [
            "배선 마감 완료",
            "기능 테스트 완료",
            "순정 라인 손상 없이 작업 진행",
            "고객 요청 사항 반영 완료",
            "실내 라인 연결감이 자연스럽게 완성되었습니다",
        ]
        if os.path.exists(self.templates_path):
            try:
                with open(self.templates_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    return data
            except Exception:
                pass
        return defaults

    def save_templates(self):
        with open(self.templates_path, "w", encoding="utf-8") as f:
            json.dump(self.templates, f, ensure_ascii=False, indent=2)

    def get_unique_path(self, directory, file_name):
        os.makedirs(directory, exist_ok=True)
        base, ext = os.path.splitext(file_name)
        candidate = os.path.join(directory, file_name)
        count = 1
        while os.path.exists(candidate):
            candidate = os.path.join(directory, f"{base}_{count}{ext}")
            count += 1
        return candidate

    def on_closing(self):
        self.save_all_data_silent()
        self.root.destroy()


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = VehicleManagerApp(root)
    root.mainloop()

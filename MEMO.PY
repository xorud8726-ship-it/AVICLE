import sys
import os
import json
import re
import pyotp
import time
import requests
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTextEdit, QTabWidget, 
                             QWidget, QVBoxLayout, QPushButton, QHBoxLayout, 
                             QInputDialog, QLineEdit, QMessageBox, QLabel, QMenu)
from PyQt6.QtCore import QUrl, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QTextCursor, QImage, QTextDocument, QAction

class VehicleWorkNote(QTextEdit):
    file_dropped_signal = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window 
        self.setAcceptDrops(True)
        self.image_preview_width = 150 
        self.setReadOnly(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        self.setStyleSheet("""
            QTextEdit {
                padding: 25px;
                font-size: 11pt;
                line-height: 1.6;
                background-color: #ffffff;
                color: #1a1a1a;
                border: none;
            }
        """)

    def show_context_menu(self, pos):
        menu = self.createStandardContextMenu()
        if self.textCursor().hasSelection():
            menu.addSeparator()
            send_action = QAction("✈️ 선택 영역 텔레그램 전송", self)
            send_action.triggered.connect(self.send_selection_to_tg)
            menu.addAction(send_action)
        menu.exec(self.mapToGlobal(pos))

    def send_selection_to_tg(self):
        cursor = self.textCursor()
        selected_text = cursor.selection().toPlainText()
        selected_html = cursor.selection().toHtml()
        
        # 선택 영역 내의 모든 파일 경로 추출 (이미지 + PDF 등)
        file_paths = re.findall(r'href="file:///([^"]+)"', selected_html)
        file_paths = [p.replace('/', os.sep) for p in file_paths]
        
        self.main_window.process_telegram_send("선택 영역 공유", selected_text, file_paths)

    def insertFromMimeData(self, source):
        if source.hasImage():
            image = source.imageData()
            if image and not image.isNull():
                img_dir = os.path.join(self.main_window.save_dir, "images")
                os.makedirs(img_dir, exist_ok=True)
                filename = f"capture_{int(time.time() * 1000)}.png"
                save_path = os.path.join(img_dir, filename)
                image.save(save_path, "PNG")
                self.insert_embedded_file(save_path)
                self.file_dropped_signal.emit()
        else:
            super().insertFromMimeData(source)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                self.insert_embedded_file(file_path)
            event.acceptProposedAction()
            self.file_dropped_signal.emit()
        else:
            super().dropEvent(event)

    def insert_embedded_file(self, file_path):
        ext = file_path.lower().split('.')[-1]
        file_url = QUrl.fromLocalFile(file_path).toString()
        cursor = self.textCursor()
        filename = os.path.basename(file_path)
        if len(filename) > 15: filename = filename[:12] + "..."

        if ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp']:
            html = f'<a href="{file_url}"><img src="{file_url}" width="{self.image_preview_width}"></a>&nbsp;'
            cursor.insertHtml(html)
        elif ext == 'pdf':
            html = f'<a href="{file_url}" style="text-decoration:none; font-weight:bold; color:#de3618;">[📕 PDF: {filename}]</a>&nbsp;'
            cursor.insertHtml(html)
        elif ext in ['mp4', 'avi', 'mov', 'mkv']:
            html = f'<a href="{file_url}" style="text-decoration:none; color:#0052cc;">[🎬 영상: {filename}]</a>&nbsp;'
            cursor.insertHtml(html)
        else:
            html = f'<a href="{file_url}" style="text-decoration:none; color:#00875a;">[📎 {filename}]</a>&nbsp;'
            cursor.insertHtml(html)

    def mouseDoubleClickEvent(self, event):
        anchor = self.anchorAt(event.pos())
        if anchor:
            QDesktopServices.openUrl(QUrl(anchor))
            return
        super().mouseDoubleClickEvent(event)

class ShortcutButton(QPushButton):
    def __init__(self, btn_id, parent):
        super().__init__("", parent)
        self.btn_id = str(btn_id)
        self.main_window = parent
        self.setFixedWidth(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("padding: 5px; font-size: 9pt; background-color: #f0f0f0; color: #1a1a1a; border: 1px solid #ccc; border-radius: 4px;")

    def update_display(self):
        data = self.main_window.shortcut_data.get(self.btn_id, {"name": f"링크 {self.btn_id}", "url": ""})
        self.setText(data.get("name", f"링크 {self.btn_id}"))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
        elif event.button() == Qt.MouseButton.LeftButton:
            url = self.main_window.shortcut_data.get(self.btn_id, {}).get("url", "")
            if url: QDesktopServices.openUrl(QUrl(url))
            else: self.show_context_menu(event.globalPosition().toPoint())

    def show_context_menu(self, pos):
        menu = QMenu(self)
        n_act = menu.addAction("이름 변경")
        u_act = menu.addAction("링크 변경")
        action = menu.exec(pos)
        data = self.main_window.shortcut_data.get(self.btn_id, {"name": "", "url": ""})
        if action == n_act:
            new, ok = QInputDialog.getText(self, "이름", "버튼 이름:", text=data.get("name"))
            if ok: data["name"] = new
        elif action == u_act:
            new, ok = QInputDialog.getText(self, "링크", "URL:", text=data.get("url"))
            if ok: data["url"] = new if new.startswith("http") else "https://" + new
        self.main_window.shortcut_data[self.btn_id] = data
        self.update_display()
        self.main_window.save_all_tabs()

class OTPLabel(QLabel):
    def __init__(self, brand, parent):
        super().__init__(parent)
        self.brand = brand
        self.main_window = parent
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.default_style = "background-color: black; color: white; font-weight: bold; font-size: 11pt; padding: 6px 10px; border-radius: 4px;"
        self.success_style = "background-color: black; color: #00FF00; font-weight: bold; font-size: 11pt; padding: 6px 10px; border-radius: 4px;"
        self.setStyleSheet(self.default_style)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_otp)
        self.timer.start(1000)

    def update_otp(self):
        secret = self.main_window.otp_config.get(self.brand, "")
        show = self.main_window.otp_config.get("SHOW_NUMBER", False)
        try:
            totp = pyotp.TOTP(secret)
            self.setText(f"[{self.brand}] {totp.now()} ({30-(int(time.time())%30)}s)" if show else f"[{self.brand}]")
        except: self.setText(f"[{self.brand}] Error")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                totp = pyotp.TOTP(self.main_window.otp_config.get(self.brand, ""))
                QApplication.clipboard().setText(totp.now())
                self.setStyleSheet(self.success_style)
                QTimer.singleShot(400, lambda: self.setStyleSheet(self.default_style))
            except: pass
        elif event.button() == Qt.MouseButton.RightButton:
            self.main_window.show_otp_context_menu(self.brand, event.globalPosition().toPoint())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("A-VICLE Gwangju - 기술 데이터 관리")
        self.resize(1250, 850)
        self.save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "autosave")
        self.manifest_path = os.path.join(self.save_dir, "manifest.json")
        if not os.path.exists(self.save_dir): os.makedirs(self.save_dir)

        self.work_template = "■ 차량정보: \n■ 작업일자: \n■ 사전점검: \n■ 배선정보: B+( ) / ACC( ) / IG1( ) / GND( ) \n■ 특이사항: \n"
        self.otp_config = {"KIA": "", "HYUNDAI": "", "SHOW_NUMBER": False}
        self.shortcut_data = {"1": {"name": "링크 1", "url": ""}, "2": {"name": "링크 2", "url": ""}, "3": {"name": "링크 3", "url": ""}}
        self.tg_config = {"TOKEN": "", "CHAT_ID": ""}

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        ctrl = QHBoxLayout()
        self.add_tab_btn = QPushButton("+ 차종 추가")
        self.add_tab_btn.clicked.connect(lambda: self.add_new_tab())
        ctrl.addWidget(self.add_tab_btn)

        self.tpl_btn = QPushButton("📋 양식 삽입")
        self.tpl_btn.setStyleSheet("background-color: #03c75a; color: white; font-weight: bold; padding: 5px 15px; border-radius: 4px;")
        self.tpl_btn.clicked.connect(self.insert_template_text)
        self.tpl_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tpl_btn.customContextMenuRequested.connect(self.edit_template_popup)
        ctrl.addWidget(self.tpl_btn)

        self.tg_btn = QPushButton("✈️ 텔레그램 전송")
        self.tg_btn.setStyleSheet("background-color: #0088cc; color: white; font-weight: bold; padding: 5px 15px; border-radius: 4px;")
        self.tg_btn.clicked.connect(self.send_full_tab_to_tg)
        self.tg_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tg_btn.customContextMenuRequested.connect(self.show_tg_config_menu)
        ctrl.addWidget(self.tg_btn)

        ctrl.addStretch()
        self.short_btns = []
        for i in range(1, 4):
            btn = ShortcutButton(i, self)
            self.short_btns.append(btn)
            ctrl.addWidget(btn)

        self.hyundai_otp = OTPLabel("HYUNDAI", self)
        self.kia_otp = OTPLabel("KIA", self)
        ctrl.addWidget(self.hyundai_otp)
        ctrl.addWidget(self.kia_otp)
        layout.addLayout(ctrl)

        sch = QHBoxLayout()
        self.sch_in = QLineEdit()
        self.sch_in.setPlaceholderText("차량명 또는 배선 검색...")
        self.sch_in.returnPressed.connect(self.find_next)
        sch.addWidget(self.sch_in)
        btn_f = QPushButton("다음 찾기")
        btn_f.clicked.connect(self.find_next)
        sch.addWidget(btn_f)
        layout.addLayout(sch)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.remove_tab)
        self.tabs.tabBarDoubleClicked.connect(self.rename_tab)
        layout.addWidget(self.tabs)

        self.load_all_tabs()
        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self.save_all_tabs)
        self.save_timer.start(60000)

    # --- 텔레그램 전송 엔진 (PDF 파일 전송으로 수정) ---
    def process_telegram_send(self, title, text, file_paths):
        token, chat_id = self.tg_config["TOKEN"], self.tg_config["CHAT_ID"]
        if not token or not chat_id:
            QMessageBox.warning(self, "설정 필요", "텔레그램 설정을 먼저 해주세요.")
            return

        formatted_text = f"<b>[{title}]</b>\n\n{text}"
        
        # 이미지와 PDF를 구분
        img_paths = [p for p in file_paths if p.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp'))][:10]
        pdf_paths = [p for p in file_paths if p.lower().endswith('pdf')]

        try:
            # 1. 이미지(미디어 그룹) 전송
            if img_paths:
                media, files_payload, opened_files = [], {}, []
                for i, p in enumerate(img_paths):
                    file_key = f"p{i}"
                    f = open(p, 'rb')
                    opened_files.append(f)
                    files_payload[file_key] = f
                    caption = formatted_text[:1024] if i == 0 else ""
                    media.append({"type": "photo", "media": f"attach://{file_key}", "caption": caption, "parse_mode": "HTML"})
                
                requests.post(f"https://api.telegram.org/bot{token}/sendMediaGroup", 
                              data={"chat_id": chat_id, "media": json.dumps(media)}, files=files_payload)
                for f in opened_files: f.close()
            else:
                # 이미지가 없을 경우 텍스트만 전송
                requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                              data={"chat_id": chat_id, "text": formatted_text, "parse_mode": "HTML"})

            # 2. 업로드된 PDF 파일들 전송 (중요)
            for p in pdf_paths:
                if os.path.exists(p):
                    with open(p, 'rb') as f:
                        requests.post(f"https://api.telegram.org/bot{token}/sendDocument", 
                                      data={"chat_id": chat_id, "caption": f"파일: {os.path.basename(p)}"}, files={"document": f})

            QMessageBox.information(self, "전송 완료", "텍스트와 첨부 파일들이 전송되었습니다.")
        except Exception as e:
            QMessageBox.critical(self, "전송 실패", f"에러: {e}")

    def send_full_tab_to_tg(self):
        idx = self.tabs.currentIndex()
        if idx == -1: return
        editor = self.tabs.widget(idx)
        title = self.tabs.tabText(idx)
        
        # HTML에서 모든 파일 링크(이미지 + PDF) 추출
        html = editor.toHtml()
        text = editor.toPlainText()
        file_paths = re.findall(r'href="file:///([^"]+)"', html)
        file_paths = [p.replace('/', os.sep) for p in file_paths]
        
        self.process_telegram_send(title, text, file_paths)

    def show_tg_config_menu(self, pos):
        menu = QMenu(self)
        t_act = menu.addAction("토큰 수정")
        c_act = menu.addAction("채팅 ID 수정")
        action = menu.exec(self.tg_btn.mapToGlobal(pos))
        if action == t_act:
            new, ok = QInputDialog.getText(self, "TG", "TOKEN:", text=self.tg_config["TOKEN"])
            if ok: self.tg_config["TOKEN"] = new
        elif action == c_act:
            new, ok = QInputDialog.getText(self, "TG", "CHAT_ID:", text=self.tg_config["CHAT_ID"])
            if ok: self.tg_config["CHAT_ID"] = new
        self.save_all_tabs()

    def insert_template_text(self):
        editor = self.tabs.currentWidget()
        if editor:
            cursor = editor.textCursor()
            cursor.insertText(self.work_template)
            editor.setFocus()

    def edit_template_popup(self, pos):
        new_tpl, ok = QInputDialog.getMultiLineText(self, "양식", "양식 내용:", text=self.work_template)
        if ok and new_tpl:
            self.work_template = new_tpl
            self.save_all_tabs()

    def show_otp_context_menu(self, brand, pos):
        menu = QMenu(self)
        e_act = menu.addAction(f"{brand} 키 수정")
        show = self.otp_config.get("SHOW_NUMBER")
        t_act = menu.addAction("V 번호 표시" if show else "  번호 표시")
        action = menu.exec(pos)
        if action == e_act:
            key, ok = QInputDialog.getText(self, "OTP", "Key:", text=self.otp_config.get(brand, ""))
            if ok: self.otp_config[brand] = key.replace(" ","").upper()
        elif action == t_act:
            self.otp_config["SHOW_NUMBER"] = not show
        self.save_all_tabs()

    def get_safe_filename(self, title):
        return re.sub(r'[\\/*?:"<>|]', '', title).strip()

    def add_new_tab(self, title=None, content=None):
        editor = VehicleWorkNote(self)
        editor.file_dropped_signal.connect(self.save_all_tabs)
        if not title: title = f"차종 입력 {self.tabs.count() + 1}"
        idx = self.tabs.addTab(editor, title)
        if content: editor.setHtml(content)
        self.tabs.setCurrentIndex(idx)
        return editor

    def remove_tab(self, idx):
        if self.tabs.count() > 1:
            title = self.tabs.tabText(idx)
            f_path = os.path.join(self.save_dir, f"{self.get_safe_filename(title)}.html")
            if os.path.exists(f_path): os.remove(f_path)
            self.tabs.removeTab(idx)
            self.save_all_tabs()

    def rename_tab(self, idx):
        if idx == -1: return
        old = self.tabs.tabText(idx)
        new, ok = QInputDialog.getText(self, "차종", "차량명:", text=old)
        if ok and new:
            old_f = os.path.join(self.save_dir, f"{self.get_safe_filename(old)}.html")
            new_f = os.path.join(self.save_dir, f"{self.get_safe_filename(new)}.html")
            if os.path.exists(old_f): os.rename(old_f, new_f)
            self.tabs.setTabText(idx, new)
            self.save_all_tabs()

    def save_all_tabs(self):
        titles = []
        for i in range(self.tabs.count()):
            title = self.tabs.tabText(i)
            titles.append(title)
            with open(os.path.join(self.save_dir, f"{self.get_safe_filename(title)}.html"), "w", encoding="utf-8") as f:
                f.write(self.tabs.widget(i).toHtml())
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump({
                "tabs": titles, "otp": self.otp_config, 
                "shortcuts": self.shortcut_data, "template": self.work_template,
                "tg_config": self.tg_config
            }, f, ensure_ascii=False)

    def load_all_tabs(self):
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.otp_config.update(data.get("otp", {}))
                self.shortcut_data.update(data.get("shortcuts", {}))
                self.work_template = data.get("template", self.work_template)
                self.tg_config.update(data.get("tg_config", {}))
                for title in data.get("tabs", []):
                    f_path = os.path.join(self.save_dir, f"{self.get_safe_filename(title)}.html")
                    content = open(f_path, "r", encoding="utf-8").read() if os.path.exists(f_path) else ""
                    self.add_new_tab(title, content)
        else: self.add_new_tab()
        for b in self.short_btns: b.update_display()

    def find_next(self):
        txt = self.sch_in.text()
        if not txt: return
        start = self.tabs.currentIndex()
        if self.tabs.widget(start).find(txt): return
        for i in range(1, self.tabs.count()):
            idx = (start + i) % self.tabs.count()
            self.tabs.setCurrentIndex(idx)
            ed = self.tabs.widget(idx)
            cur = ed.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.Start)
            ed.setTextCursor(cur)
            if ed.find(txt): return
        QMessageBox.information(self, "검색", "정보 없음")

    def closeEvent(self, event):
        self.save_all_tabs()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

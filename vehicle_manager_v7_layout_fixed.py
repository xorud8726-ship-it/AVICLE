import sys
import os
import json
import re
import time
import shutil
import threading
import logging
import uuid
import tempfile
import html
from datetime import datetime
from urllib.parse import unquote

import pyotp
import requests

# 셀레니움 임포트
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QTabWidget,
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QInputDialog, QLineEdit, QMessageBox, QLabel, QMenu
)
from PyQt6.QtCore import QUrl, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QTextCursor, QAction

try:
    import keyring
    KEYRING_AVAILABLE = True
except Exception:
    keyring = None
    KEYRING_AVAILABLE = False


APP_SERVICE_NAME = "A-VICLE_Gwangju_TechNote"
MANIFEST_VERSION = 2


class SecretStore:
    """민감정보 저장 담당.

    우선순위:
    1. 환경변수
    2. OS 보안 저장소(keyring)
    3. 현재 실행 중 메모리 임시 저장

    keyring이 설치되어 있지 않으면 비밀번호/OTP/TG 토큰은 파일에 저장하지 않습니다.
    """

    ENV_MAP = {
        "GSW_USER_ID": "GSW_USER_ID",
        "GSW_USER_PW": "GSW_USER_PW",
        "KIA_OTP_SECRET": "GSW_KIA_OTP_SECRET",
        "HYUNDAI_OTP_SECRET": "GSW_HYUNDAI_OTP_SECRET",
        "TELEGRAM_BOT_TOKEN": "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID": "TELEGRAM_CHAT_ID",
    }

    def __init__(self):
        self._session_only = {}

    @property
    def is_persistent(self):
        return KEYRING_AVAILABLE

    def get_secret(self, key):
        env_key = self.ENV_MAP.get(key)
        if env_key and os.getenv(env_key):
            return os.getenv(env_key)

        if KEYRING_AVAILABLE:
            try:
                return keyring.get_password(APP_SERVICE_NAME, key) or ""
            except Exception as e:
                logging.exception("keyring get 실패: %s", e)

        return self._session_only.get(key, "")

    def set_secret(self, key, value):
        value = (value or "").strip()

        if not value:
            self.delete_secret(key)
            return KEYRING_AVAILABLE

        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(APP_SERVICE_NAME, key, value)
                self._session_only.pop(key, None)
                return True
            except Exception as e:
                logging.exception("keyring set 실패: %s", e)

        self._session_only[key] = value
        return False

    def delete_secret(self, key):
        self._session_only.pop(key, None)
        if KEYRING_AVAILABLE:
            try:
                keyring.delete_password(APP_SERVICE_NAME, key)
            except Exception:
                pass


class VehicleWorkNote(QTextEdit):
    file_dropped_signal = pyqtSignal()

    def __init__(self, main_window, tab_id=None):
        super().__init__()
        self.main_window = main_window
        self.tab_id = tab_id or uuid.uuid4().hex
        self.image_preview_width = 150
        self.setAcceptDrops(True)
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
        file_paths = self.main_window.extract_file_paths_from_html(selected_html)
        self.main_window.process_telegram_send("선택 영역 공유", selected_text, file_paths)

    def insertFromMimeData(self, source):
        if source.hasImage():
            image = source.imageData()
            if image and not image.isNull():
                img_dir = os.path.join(self.main_window.save_dir, "images")
                os.makedirs(img_dir, exist_ok=True)
                filename = f"capture_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.png"
                save_path = os.path.join(img_dir, filename)
                image.save(save_path, "PNG")
                self.insert_embedded_file(save_path)
                self.file_dropped_signal.emit()
        else:
            super().insertFromMimeData(source)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path:
                    stored_path = self.main_window.import_file_to_storage(file_path)
                    self.insert_embedded_file(stored_path)
            event.acceptProposedAction()
            self.file_dropped_signal.emit()
        else:
            super().dropEvent(event)

    def insert_embedded_file(self, file_path):
        ext = file_path.lower().split('.')[-1]
        file_url = QUrl.fromLocalFile(file_path).toString()
        cursor = self.textCursor()
        filename = os.path.basename(file_path)
        short_name = filename if len(filename) <= 15 else filename[:12] + "..."

        if ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
            html_code = f'<a href="{file_url}"><img src="{file_url}" width="{self.image_preview_width}"></a>&nbsp;'
        elif ext == 'pdf':
            html_code = f'<a href="{file_url}" style="text-decoration:none; font-weight:bold; color:#de3618;">[📕 PDF: {html.escape(short_name)}]</a>&nbsp;'
        elif ext in ['mp4', 'avi', 'mov', 'mkv']:
            html_code = f'<a href="{file_url}" style="text-decoration:none; color:#0052cc;">[🎬 영상: {html.escape(short_name)}]</a>&nbsp;'
        else:
            html_code = f'<a href="{file_url}" style="text-decoration:none; color:#00875a;">[📎 {html.escape(short_name)}]</a>&nbsp;'

        cursor.insertHtml(html_code)

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
        self.setStyleSheet(
            "padding: 5px; font-size: 9pt; background-color: #f0f0f0; "
            "color: #1a1a1a; border: 1px solid #ccc; border-radius: 4px;"
        )

    def update_display(self):
        data = self.main_window.shortcut_data.get(
            self.btn_id, {"name": f"링크 {self.btn_id}", "url": ""}
        )
        self.setText(data.get("name", f"링크 {self.btn_id}"))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
        elif event.button() == Qt.MouseButton.LeftButton:
            if self.btn_id == "1":
                self.main_window.run_gsw_auto_login("KIA")
                return
            if self.btn_id == "2":
                self.main_window.run_gsw_auto_login("HYUNDAI")
                return

            url = self.main_window.shortcut_data.get(self.btn_id, {}).get("url", "")
            if url:
                QDesktopServices.openUrl(QUrl(url))
            else:
                self.show_context_menu(event.globalPosition().toPoint())

    def show_context_menu(self, pos):
        menu = QMenu(self)
        n_act = menu.addAction("이름 변경")
        u_act = menu.addAction("링크 변경")
        action = menu.exec(pos)
        data = self.main_window.shortcut_data.get(self.btn_id, {"name": "", "url": ""})

        if action == n_act:
            new, ok = QInputDialog.getText(self, "이름", "버튼 이름:", text=data.get("name", ""))
            if ok:
                data["name"] = new
        elif action == u_act:
            new, ok = QInputDialog.getText(self, "링크", "URL:", text=data.get("url", ""))
            if ok:
                new = new.strip()
                data["url"] = new if not new or new.startswith("http") else "https://" + new

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
        self.error_style = "background-color: black; color: #ffb000; font-weight: bold; font-size: 11pt; padding: 6px 10px; border-radius: 4px;"
        self.setStyleSheet(self.default_style)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_otp)
        self.timer.start(1000)
        self.update_otp()

    def _secret_key(self):
        return f"{self.brand}_OTP_SECRET"

    def update_otp(self):
        secret = self.main_window.secret_store.get_secret(self._secret_key())
        show = self.main_window.otp_config.get("SHOW_NUMBER", False)

        if not secret:
            self.setText(f"[{self.brand}] 미설정")
            self.setStyleSheet(self.error_style)
            return

        try:
            totp = pyotp.TOTP(secret)
            remain = 30 - (int(time.time()) % 30)
            self.setText(f"[{self.brand}] {totp.now()} ({remain}s)" if show else f"[{self.brand}]")
            self.setStyleSheet(self.default_style)
        except Exception:
            self.setText(f"[{self.brand}] Error")
            self.setStyleSheet(self.error_style)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                secret = self.main_window.secret_store.get_secret(self._secret_key())
                if not secret:
                    QMessageBox.warning(self, "OTP 미설정", f"{self.brand} OTP 키를 먼저 설정해주세요.")
                    return
                totp = pyotp.TOTP(secret)
                QApplication.clipboard().setText(totp.now())
                self.setStyleSheet(self.success_style)
                QTimer.singleShot(400, self.update_otp)
            except Exception as e:
                QMessageBox.critical(self, "OTP 오류", f"OTP 생성 실패: {e}")
        elif event.button() == Qt.MouseButton.RightButton:
            self.main_window.show_otp_context_menu(self.brand, event.globalPosition().toPoint())


class MainWindow(QMainWindow):
    telegram_result_signal = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("A-VICLE Gwangju - 기술 데이터 관리")
        self.resize(1250, 850)

        self.save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "autosave")
        self.tabs_dir = os.path.join(self.save_dir, "tabs")
        self.images_dir = os.path.join(self.save_dir, "images")
        self.files_dir = os.path.join(self.save_dir, "files")
        self.manifest_path = os.path.join(self.save_dir, "manifest.json")

        os.makedirs(self.save_dir, exist_ok=True)
        os.makedirs(self.tabs_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.files_dir, exist_ok=True)

        logging.basicConfig(
            filename=os.path.join(self.save_dir, "app.log"),
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            encoding="utf-8"
        )

        self.secret_store = SecretStore()
        self.pending_warnings = []
        self.driver_path = None
        self.driver_lock = threading.Lock()
        threading.Thread(target=self.preload_driver, daemon=True).start()

        self.work_template = "■ 차량정보: \n■ 작업일자: \n■ 사전점검: \n■ 배선정보: B+( ) / ACC( ) / IG1( ) / GND( ) \n■ 특이사항: \n"

        self.otp_config = {"SHOW_NUMBER": False}
        self.shortcut_data = {
            "1": {"name": "기아 GSW", "url": ""},
            "2": {"name": "현대 GSW", "url": ""},
            "3": {"name": "링크 3", "url": ""}
        }

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

        self.account_btn = QPushButton("🔐 GSW 계정")
        self.account_btn.setStyleSheet("background-color: #333333; color: white; font-weight: bold; padding: 5px 15px; border-radius: 4px;")
        self.account_btn.clicked.connect(self.edit_gsw_account)
        ctrl.addWidget(self.account_btn)

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

        self.telegram_result_signal.connect(self.on_telegram_result)

        self.load_all_tabs()

        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self.save_all_tabs)
        self.save_timer.start(60000)

        if self.pending_warnings:
            QTimer.singleShot(500, self.show_pending_warnings)

    # -------------------- 공통 유틸 --------------------

    def write_text_atomic(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", delete=False, dir=os.path.dirname(path), encoding="utf-8"
            ) as tmp:
                tmp.write(text)
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp_path = tmp.name
            os.replace(tmp_path, path)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def read_json_safe(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            logging.exception("manifest 읽기 실패: %s", e)
            broken_path = path + f".broken_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                shutil.copy2(path, broken_path)
            except Exception:
                pass
            self.pending_warnings.append(
                "manifest.json 파일이 손상되어 복구 모드로 실행했습니다. 기존 파일은 .broken 파일로 백업했습니다."
            )
            return None

    def get_safe_filename(self, title):
        safe = re.sub(r'[\\/*?:"<>|]', '', title).strip()
        return safe or "untitled"

    def get_tab_file_path(self, tab_id):
        return os.path.join(self.tabs_dir, f"{tab_id}.html")

    def extract_file_paths_from_html(self, html_text):
        urls = re.findall(r'href=["\'](file:[^"\']+)["\']', html_text)
        paths = []
        for url in urls:
            local = QUrl(url).toLocalFile()
            if not local:
                # 예전 방식으로 들어간 URL을 대비한 보조 처리
                local = unquote(url.replace("file:///", "")).replace('/', os.sep)
            if local:
                paths.append(local)
        return paths

    def normalize_path(self, path):
        return os.path.normcase(os.path.abspath(path))

    def import_file_to_storage(self, file_path):
        """드래그한 파일을 autosave 내부로 복사해 링크 깨짐을 줄입니다."""
        try:
            if not os.path.exists(file_path):
                return file_path

            abs_path = self.normalize_path(file_path)
            if abs_path.startswith(self.normalize_path(self.save_dir)):
                return file_path

            ext = os.path.splitext(file_path)[1].lower()
            target_dir = self.images_dir if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"] else self.files_dir
            os.makedirs(target_dir, exist_ok=True)

            base = self.get_safe_filename(os.path.splitext(os.path.basename(file_path))[0])
            new_name = f"{base}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}{ext}"
            target_path = os.path.join(target_dir, new_name)
            shutil.copy2(file_path, target_path)
            return target_path
        except Exception as e:
            logging.exception("파일 내부 복사 실패: %s", e)
            return file_path

    def show_pending_warnings(self):
        if self.pending_warnings:
            QMessageBox.warning(self, "확인 필요", "\n\n".join(self.pending_warnings))
            self.pending_warnings.clear()

    # -------------------- 드라이버 / 로그인 --------------------

    def preload_driver(self):
        try:
            path = ChromeDriverManager().install()
            with self.driver_lock:
                self.driver_path = path
            logging.info("크롬 드라이버 사전 준비 완료")
        except Exception as e:
            logging.exception("크롬 드라이버 사전 준비 실패: %s", e)

    def edit_gsw_account(self):
        current_id = self.secret_store.get_secret("GSW_USER_ID")
        user_id, ok = QInputDialog.getText(self, "GSW 계정", "GSW 아이디:", text=current_id)
        if not ok:
            return

        current_pw = self.secret_store.get_secret("GSW_USER_PW")
        user_pw, ok = QInputDialog.getText(
            self,
            "GSW 계정",
            "GSW 비밀번호:",
            echo=QLineEdit.EchoMode.Password,
            text=current_pw
        )
        if not ok:
            return

        persisted_id = self.secret_store.set_secret("GSW_USER_ID", user_id)
        persisted_pw = self.secret_store.set_secret("GSW_USER_PW", user_pw)

        if persisted_id and persisted_pw:
            QMessageBox.information(self, "저장 완료", "GSW 계정 정보를 OS 보안 저장소에 저장했습니다.")
        else:
            QMessageBox.warning(
                self,
                "임시 저장",
                "keyring이 설치되어 있지 않아 이번 실행 중에만 저장됩니다.\n\n"
                "계속 저장하려면 아래 명령으로 설치하세요.\n"
                "pip install keyring"
            )

    def get_gsw_credentials(self):
        user_id = self.secret_store.get_secret("GSW_USER_ID")
        user_pw = self.secret_store.get_secret("GSW_USER_PW")
        if user_id and user_pw:
            return user_id, user_pw

        QMessageBox.information(self, "GSW 계정 필요", "GSW 자동 로그인을 위해 계정 정보를 먼저 입력해주세요.")
        self.edit_gsw_account()
        return self.secret_store.get_secret("GSW_USER_ID"), self.secret_store.get_secret("GSW_USER_PW")

    def run_gsw_auto_login(self, brand):
        user_id, user_pw = self.get_gsw_credentials()
        if not user_id or not user_pw:
            QMessageBox.warning(self, "로그인 중단", "아이디 또는 비밀번호가 없어 자동 로그인을 중단했습니다.")
            return

        otp_secret = self.secret_store.get_secret(f"{brand}_OTP_SECRET")

        def worker():
            target_url = "https://gsw.kia.com" if brand == "KIA" else "https://gsw.hyundai.com"

            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_experimental_option("detach", True)
            options.page_load_strategy = 'eager'
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option("prefs", {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False
            })

            try:
                with self.driver_lock:
                    driver_path = self.driver_path

                service = Service(driver_path or ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)

                driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                })

                driver.get(target_url)
                fast_wait = WebDriverWait(driver, 15, poll_frequency=0.05)

                id_field = fast_wait.until(EC.element_to_be_clickable((By.ID, "Userid")))
                id_field.clear()
                id_field.send_keys(user_id)

                pw_field = driver.find_element(By.ID, "Passwd")
                pw_field.clear()
                pw_field.send_keys(user_pw)

                driver.find_element(By.ID, "LoginButton").click()

                try:
                    WebDriverWait(driver, 1).until(EC.alert_is_present())
                    driver.switch_to.alert.accept()
                except Exception:
                    pass

                if otp_secret:
                    try:
                        current_otp = pyotp.TOTP(otp_secret).now()
                        otp_input = fast_wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="OtpNum"]')))
                        auth_btn = fast_wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="OtpAuthButton"]')))
                        driver.execute_script(
                            'arguments[0].value = arguments[1]; arguments[2].click();',
                            otp_input,
                            current_otp,
                            auth_btn
                        )
                        logging.info("[%s] OTP 자동 입력 완료", brand)
                    except Exception as e:
                        logging.exception("[%s] OTP 입력 실패: %s", brand, e)
                else:
                    logging.info("[%s] OTP 키 미설정 - 로그인까지만 진행", brand)

            except Exception as e:
                logging.exception("[%s] 자동 로그인 실패: %s", brand, e)

        threading.Thread(target=worker, daemon=True).start()

    # -------------------- 텔레그램 --------------------

    def show_tg_config_menu(self, pos):
        menu = QMenu(self)
        t_act = menu.addAction("토큰 수정")
        c_act = menu.addAction("채팅 ID 수정")
        action = menu.exec(self.tg_btn.mapToGlobal(pos))

        if action == t_act:
            current = self.secret_store.get_secret("TELEGRAM_BOT_TOKEN")
            new, ok = QInputDialog.getText(self, "Telegram", "BOT TOKEN:", text=current)
            if ok:
                persisted = self.secret_store.set_secret("TELEGRAM_BOT_TOKEN", new)
                self.show_secret_save_result(persisted)
        elif action == c_act:
            current = self.secret_store.get_secret("TELEGRAM_CHAT_ID")
            new, ok = QInputDialog.getText(self, "Telegram", "CHAT_ID:", text=current)
            if ok:
                persisted = self.secret_store.set_secret("TELEGRAM_CHAT_ID", new)
                self.show_secret_save_result(persisted)

        self.save_all_tabs()

    def show_secret_save_result(self, persisted):
        if persisted:
            QMessageBox.information(self, "저장 완료", "OS 보안 저장소에 저장했습니다.")
        else:
            QMessageBox.warning(
                self,
                "임시 저장",
                "keyring이 설치되어 있지 않아 이번 실행 중에만 저장됩니다.\n\n"
                "계속 저장하려면 아래 명령으로 설치하세요.\n"
                "pip install keyring"
            )

    def telegram_post(self, method, data=None, files=None):
        token = self.secret_store.get_secret("TELEGRAM_BOT_TOKEN")
        url = f"https://api.telegram.org/bot{token}/{method}"
        res = requests.post(url, data=data, files=files, timeout=15)
        res.raise_for_status()
        try:
            payload = res.json()
        except Exception:
            payload = {}
        if payload and not payload.get("ok", False):
            raise RuntimeError(payload.get("description") or str(payload))
        return payload

    def send_telegram_text_chunks(self, chat_id, title, safe_text):
        safe_title = html.escape(title)
        chunks = [safe_text[i:i + 3500] for i in range(0, len(safe_text), 3500)] or [""]
        for i, chunk in enumerate(chunks):
            if i == 0:
                message = f"<b>[{safe_title}]</b>\n\n{chunk}"
            else:
                message = chunk
            self.telegram_post(
                "sendMessage",
                data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            )

    def process_telegram_send(self, title, text, file_paths):
        token = self.secret_store.get_secret("TELEGRAM_BOT_TOKEN")
        chat_id = self.secret_store.get_secret("TELEGRAM_CHAT_ID")

        if not token or not chat_id:
            QMessageBox.warning(self, "설정 필요", "텔레그램 토큰과 채팅 ID를 먼저 설정해주세요.\n\n텔레그램 전송 버튼을 우클릭하면 설정할 수 있습니다.")
            return

        self.tg_btn.setEnabled(False)
        self.tg_btn.setText("전송 중...")

        safe_text = html.escape(text or "")
        existing_paths = [p for p in file_paths if p and os.path.exists(p)]
        img_paths = [p for p in existing_paths if p.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'))][:10]
        doc_paths = [p for p in existing_paths if not p.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'))]

        def worker():
            opened_files = []
            try:
                if img_paths:
                    media = []
                    files_payload = {}
                    first_caption_text = safe_text
                    if len(first_caption_text) > 850:
                        first_caption_text = first_caption_text[:850] + "..."

                    for i, path in enumerate(img_paths):
                        file_key = f"p{i}"
                        f = open(path, 'rb')
                        opened_files.append(f)
                        files_payload[file_key] = f
                        caption = f"<b>[{html.escape(title)}]</b>\n\n{first_caption_text}" if i == 0 else ""
                        media.append({
                            "type": "photo",
                            "media": f"attach://{file_key}",
                            "caption": caption,
                            "parse_mode": "HTML"
                        })

                    self.telegram_post(
                        "sendMediaGroup",
                        data={"chat_id": chat_id, "media": json.dumps(media, ensure_ascii=False)},
                        files=files_payload
                    )

                    if len(safe_text) > 850:
                        self.send_telegram_text_chunks(chat_id, f"{title} 본문", safe_text)
                else:
                    self.send_telegram_text_chunks(chat_id, title, safe_text)

                for path in doc_paths:
                    with open(path, 'rb') as f:
                        self.telegram_post(
                            "sendDocument",
                            data={"chat_id": chat_id, "caption": f"파일: {os.path.basename(path)}"},
                            files={"document": f}
                        )

                self.telegram_result_signal.emit(True, "전송되었습니다.")
            except Exception as e:
                logging.exception("텔레그램 전송 실패: %s", e)
                self.telegram_result_signal.emit(False, f"전송 실패: {e}")
            finally:
                for f in opened_files:
                    try:
                        f.close()
                    except Exception:
                        pass

        threading.Thread(target=worker, daemon=True).start()

    def on_telegram_result(self, ok, message):
        self.tg_btn.setEnabled(True)
        self.tg_btn.setText("✈️ 텔레그램 전송")
        if ok:
            QMessageBox.information(self, "전송 완료", message)
        else:
            QMessageBox.critical(self, "전송 실패", message)

    def send_full_tab_to_tg(self):
        idx = self.tabs.currentIndex()
        if idx == -1:
            return
        editor = self.tabs.widget(idx)
        title = self.tabs.tabText(idx)
        html_text = editor.toHtml()
        text = editor.toPlainText()
        file_paths = self.extract_file_paths_from_html(html_text)
        self.process_telegram_send(title, text, file_paths)

    # -------------------- 메모 / 탭 --------------------

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
        show = self.otp_config.get("SHOW_NUMBER", False)
        t_act = menu.addAction("OTP 번호 숨기기" if show else "OTP 번호 표시")
        action = menu.exec(pos)

        if action == e_act:
            secret_key = f"{brand}_OTP_SECRET"
            current = self.secret_store.get_secret(secret_key)
            key, ok = QInputDialog.getText(self, "OTP", f"{brand} OTP Key:", text=current)
            if ok:
                normalized = key.replace(" ", "").upper()
                persisted = self.secret_store.set_secret(secret_key, normalized)
                self.show_secret_save_result(persisted)
        elif action == t_act:
            self.otp_config["SHOW_NUMBER"] = not show

        self.hyundai_otp.update_otp()
        self.kia_otp.update_otp()
        self.save_all_tabs()

    def add_new_tab(self, title=None, content=None, tab_id=None):
        editor = VehicleWorkNote(self, tab_id=tab_id)
        editor.file_dropped_signal.connect(self.save_all_tabs)
        if not title:
            title = f"차종 입력 {self.tabs.count() + 1}"
        idx = self.tabs.addTab(editor, title)
        if content:
            editor.setHtml(content)
        self.tabs.setCurrentIndex(idx)
        return editor

    def remove_tab(self, idx):
        if self.tabs.count() <= 1:
            QMessageBox.information(self, "삭제 불가", "최소 1개의 탭은 남겨야 합니다.")
            return

        editor = self.tabs.widget(idx)
        reply = QMessageBox.question(
            self,
            "탭 삭제",
            f"'{self.tabs.tabText(idx)}' 탭을 삭제할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        f_path = self.get_tab_file_path(editor.tab_id)
        if os.path.exists(f_path):
            try:
                os.remove(f_path)
            except Exception as e:
                logging.exception("탭 파일 삭제 실패: %s", e)

        self.tabs.removeTab(idx)
        self.save_all_tabs()

    def rename_tab(self, idx):
        if idx == -1:
            return
        old = self.tabs.tabText(idx)
        new, ok = QInputDialog.getText(self, "차종", "차량명:", text=old)
        if ok and new:
            self.tabs.setTabText(idx, new.strip())
            self.save_all_tabs()

    # -------------------- 저장 / 로드 / 백업 --------------------

    def save_all_tabs(self):
        try:
            tabs_info = []
            for i in range(self.tabs.count()):
                editor = self.tabs.widget(i)
                title = self.tabs.tabText(i)
                tab_id = getattr(editor, "tab_id", None) or uuid.uuid4().hex
                editor.tab_id = tab_id
                file_name = f"{tab_id}.html"
                file_path = self.get_tab_file_path(tab_id)

                self.write_text_atomic(file_path, editor.toHtml())
                tabs_info.append({"id": tab_id, "title": title, "file": f"tabs/{file_name}"})

            manifest = {
                "version": MANIFEST_VERSION,
                "last_saved": datetime.now().isoformat(timespec="seconds"),
                "tabs": tabs_info,
                "otp": {"SHOW_NUMBER": self.otp_config.get("SHOW_NUMBER", False)},
                "shortcuts": self.shortcut_data,
                "template": self.work_template
            }

            self.write_text_atomic(
                self.manifest_path,
                json.dumps(manifest, ensure_ascii=False, indent=2)
            )
            self.cleanup_unused_files()
        except Exception as e:
            logging.exception("저장 실패: %s", e)
            QMessageBox.critical(self, "저장 실패", f"자동 저장 중 오류가 발생했습니다.\n\n{e}")

    def migrate_old_secrets(self, data):
        old_otp = data.get("otp", {}) if isinstance(data, dict) else {}
        for brand in ["KIA", "HYUNDAI"]:
            value = old_otp.get(brand, "")
            if value:
                persisted = self.secret_store.set_secret(f"{brand}_OTP_SECRET", value)
                if not persisted:
                    self.pending_warnings.append(
                        f"기존 {brand} OTP 키를 이번 실행 중에만 임시 보관했습니다. keyring 설치 후 다시 저장해주세요."
                    )

        old_tg = data.get("tg_config", {}) if isinstance(data, dict) else {}
        if old_tg.get("TOKEN"):
            persisted = self.secret_store.set_secret("TELEGRAM_BOT_TOKEN", old_tg.get("TOKEN"))
            if not persisted:
                self.pending_warnings.append("기존 텔레그램 토큰을 이번 실행 중에만 임시 보관했습니다. keyring 설치 후 다시 저장해주세요.")
        if old_tg.get("CHAT_ID"):
            persisted = self.secret_store.set_secret("TELEGRAM_CHAT_ID", old_tg.get("CHAT_ID"))
            if not persisted:
                self.pending_warnings.append("기존 텔레그램 채팅 ID를 이번 실행 중에만 임시 보관했습니다. keyring 설치 후 다시 저장해주세요.")

    def load_all_tabs(self):
        data = self.read_json_safe(self.manifest_path)

        if data:
            self.migrate_old_secrets(data)

            old_otp = data.get("otp", {})
            self.otp_config["SHOW_NUMBER"] = old_otp.get("SHOW_NUMBER", False)

            self.shortcut_data.update(data.get("shortcuts", {}))
            self.work_template = data.get("template", self.work_template)

            tabs_data = data.get("tabs", [])

            # 새 형식: [{id, title, file}]
            if tabs_data and isinstance(tabs_data[0], dict):
                for tab in tabs_data:
                    tab_id = tab.get("id") or uuid.uuid4().hex
                    title = tab.get("title") or "복구된 탭"
                    file_rel = tab.get("file") or f"tabs/{tab_id}.html"
                    file_path = os.path.join(self.save_dir, file_rel)
                    content = ""
                    if os.path.exists(file_path):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                        except Exception as e:
                            logging.exception("탭 파일 읽기 실패: %s", e)
                    self.add_new_tab(title, content, tab_id=tab_id)

            # 예전 형식: ["탭 제목", "탭 제목"]
            elif tabs_data and isinstance(tabs_data[0], str):
                for title in tabs_data:
                    old_path = os.path.join(self.save_dir, f"{self.get_safe_filename(title)}.html")
                    content = ""
                    if os.path.exists(old_path):
                        try:
                            with open(old_path, "r", encoding="utf-8") as f:
                                content = f.read()
                        except Exception as e:
                            logging.exception("구버전 탭 파일 읽기 실패: %s", e)
                    self.add_new_tab(title, content, tab_id=uuid.uuid4().hex)
                self.pending_warnings.append("구버전 저장 형식을 새 저장 형식으로 변환했습니다.")

        if self.tabs.count() == 0:
            self.recover_tabs_without_manifest()

        if self.tabs.count() == 0:
            self.add_new_tab()

        for btn in self.short_btns:
            btn.update_display()

        self.save_all_tabs()

    def recover_tabs_without_manifest(self):
        # manifest가 없거나 손상됐을 때 tabs 폴더의 html을 최대한 복구
        html_files = []
        if os.path.exists(self.tabs_dir):
            html_files.extend([os.path.join(self.tabs_dir, f) for f in os.listdir(self.tabs_dir) if f.lower().endswith(".html")])

        # 구버전 루트 html도 복구 대상에 포함
        html_files.extend([os.path.join(self.save_dir, f) for f in os.listdir(self.save_dir) if f.lower().endswith(".html")])

        for path in sorted(set(html_files)):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                title = os.path.splitext(os.path.basename(path))[0]
                self.add_new_tab(f"복구_{title[:12]}", content, tab_id=uuid.uuid4().hex)
            except Exception as e:
                logging.exception("HTML 복구 실패: %s", e)

        if html_files:
            self.pending_warnings.append("manifest 없이 HTML 파일을 스캔해 탭을 복구했습니다. 탭 이름은 일부 변경될 수 있습니다.")

    def cleanup_unused_files(self):
        try:
            all_html = ""
            for i in range(self.tabs.count()):
                all_html += self.tabs.widget(i).toHtml()

            used_paths = {self.normalize_path(p) for p in self.extract_file_paths_from_html(all_html)}

            for folder in [self.images_dir, self.files_dir]:
                if not os.path.exists(folder):
                    continue
                for name in os.listdir(folder):
                    full_path = os.path.join(folder, name)
                    if os.path.isfile(full_path) and self.normalize_path(full_path) not in used_paths:
                        try:
                            os.remove(full_path)
                        except Exception as e:
                            logging.exception("미사용 파일 삭제 실패: %s", e)
        except Exception as e:
            logging.exception("미사용 파일 정리 실패: %s", e)

    def create_backup(self):
        try:
            backup_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
            os.makedirs(backup_root, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            backup_path = os.path.join(backup_root, timestamp)
            shutil.copytree(self.save_dir, backup_path)

            backups = sorted(
                [os.path.join(backup_root, d) for d in os.listdir(backup_root)],
                key=os.path.getmtime
            )
            while len(backups) > 10:
                shutil.rmtree(backups.pop(0))
        except Exception as e:
            logging.exception("백업 실패: %s", e)

    # -------------------- 검색 / 종료 --------------------

    def find_next(self):
        txt = self.sch_in.text()
        if not txt:
            return

        start = self.tabs.currentIndex()
        if start == -1:
            return

        if self.tabs.widget(start).find(txt):
            return

        for i in range(1, self.tabs.count()):
            idx = (start + i) % self.tabs.count()
            self.tabs.setCurrentIndex(idx)
            ed = self.tabs.widget(idx)
            cur = ed.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.Start)
            ed.setTextCursor(cur)
            if ed.find(txt):
                return

        QMessageBox.information(self, "검색", "정보 없음")

    def closeEvent(self, event):
        self.save_all_tabs()
        self.create_backup()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

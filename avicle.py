# file: order_app_tabs_all_search.py
import tkinter as tk
from tkinter import ttk, messagebox
import sys, os, time, datetime, requests, configparser, subprocess, webbrowser
from typing import Dict, List, Tuple, Optional

# Optional Pillow for JPG/PNG preview
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

CONFIG_FILE = "config.ini"
TOKEN = "7895331234:AAG9ge6GGBg0plHb7axWcwSwIgSNG9gWvuY"
CHAT_ID = "-1003315436286"

# ---------------------------------------------------------------------------
# 단일 소스: 품목 카탈로그 (품목/카테고리/이미지/가격)
# - price: 공급가(부가세 미포함) 기준 임시 설정
# ---------------------------------------------------------------------------
ITEMS: List[Dict[str, str]] = [
    # LED (RGB/무빙)
    {"id":"rgb_led_110","name":"RGB 110cm","category":"LED (RGB/무빙)","image":"led", "price": "28000"},
    {"id":"rgb_led_90","name":"RGB 90cm","category":"LED (RGB/무빙)","image":"led", "price": "25000"}, # 80cm 단가 적용
    {"id":"moving_led_110","name":"무빙 110cm","category":"LED (RGB/무빙)","image":"led", "price": "38000"},
    {"id":"moving_led_90","name":"무빙 90cm","category":"LED (RGB/무빙)","image":"led", "price": "29000"},
    {"id":"moving_led_50","name":"무빙 50cm","category":"LED (RGB/무빙)","image":"led", "price": "18000"},
    {"id":"moving_led_30","name":"무빙 30cm","category":"LED (RGB/무빙)","image":"led", "price": "15000"},
    {"id":"moving_led_15_soldout","name":"무빙 15cm(품절)","category":"LED (RGB/무빙)","image":"led", "price": "11000"},

    # 모듈 (세트,단품)
    {"id":"haodeng_bt","name":"RGB 블루투스 모듈(하우동)","category":"모듈 (세트,단품)","image":"haodeng", "price": "20000"},
    {"id":"oem_rgb_set","name":"순정연동 RGB 모듈 1개 세트","category":"모듈 (세트,단품)","image":"rgb110", "price": "175000"},
    {"id":"oem_se_set","name":"순정연동 SE 모듈 1개 세트","category":"모듈 (세트,단품)","image":"rgb110", "price": "268000"},
    {"id":"oem_v4_set","name":"순정연동 V4 모듈 1개 세트 (품절)","category":"모듈 (세트,단품)","image":"rgb110", "price": "358000"},
    {"id":"universal_se_set","name":"유니버셜 se 모듈 1개 세트","category":"모듈 (세트,단품)","image":"seset", "price": "318000"},
    {"id":"oem_rgb_single","name":"순정연동 RGB 모듈 1개 단품","category":"모듈 (세트,단품)","image":"rgb", "price": "60000"},
    {"id":"oem_se_single","name":"순정연동 SE 모듈 1개 단품","category":"모듈 (세트,단품)","image":"se", "price": "130000"},
    {"id":"oem_v4_single","name":"순정연동 V4 모듈 1개 단품 (품절)","category":"모듈 (세트,단품)","image":"v4", "price": "220000"},
    {"id":"universal_se_single","name":"순정연동 어플 1개 단품","category":"모듈 (세트,단품)","image":"uni", "price": "230000"},
    {"id":"oem_v4_pro_set","name":"순정연동 V4 PRO 모듈 1개 세트 (품절)","category":"모듈 (세트,단품)","image":"", "price": "454500"},
    {"id":"oem_se_pro_set","name":"순정연동 SE PRO 모듈 1개 세트","category":"모듈 (세트,단품)","image":"", "price": "373500"},
    {"id":"oem_v4_pro_single","name":"순정연동 V4 PRO 모듈 1개 단품 (품절)","category":"모듈 (세트,단품)","image":"v4", "price": "270000"},
    {"id":"oem_se_pro_single","name":"순정연동 SE PRO 모듈 1개 단품","category":"모듈 (세트,단품)","image":"se", "price": "180000"},

    # 아크릴 & 몰딩
    {"id":"spk_acrylic_row1","name":"스피커 아크릴 (1열) 2PCS","category":"아크릴 & 몰딩","image":"tmvlzj", "price": "10000"},
    {"id":"spk_acrylic_row1_torres","name":"(토레스)스피커 아크릴 (1열) 2PCS","category":"아크릴 & 몰딩","image":"xhfptm", "price": "10000"},
    {"id":"foot_rgb_acrylic_4pcs","name":"RGB 풋등 아크릴 1대분 4PCS","category":"아크릴 & 몰딩","image":"foot", "price": "1650"},
    {"id":"foot_moving_acrylic_4pcs","name":"무빙 풋등 아크릴 1대분 4PCS","category":"아크릴 & 몰딩","image":"foot", "price": "2200"},
    {"id":"dial_acrylic_mq4_k8_ka4p","name":"다이얼 아크릴 MQ4(페리),K8(페리),KA4페리","category":"아크릴 & 몰딩","image":"ekdldjf", "price": "11000"}, # 단가표 다이얼 아크릴 반영
    {"id":"dial_acrylic_nq5","name":"다이얼 아크릴 NQ5","category":"아크릴 & 몰딩","image":"ekdldjf", "price": "11000"},
    {"id":"dial_acrylic_old_ka4","name":"다이얼 아크릴 구형 KA4","category":"아크릴 & 몰딩","image":"ekdldjf", "price": "11000"},
    {"id":"dial_acrylic_dl3_ferry","name":"다이얼 아크릴 DL3(페리)","category":"아크릴 & 몰딩","image":"ekdldjf", "price": "11000"},
    {"id":"stinger_airvent_row1","name":"스팅어 벤풍구 아크릴 1열","category":"아크릴 & 몰딩","image":"Stinger1", "price": "10000"},
    {"id":"stinger_airvent_row2","name":"스팅어 벤풍구 아크릴 2열","category":"아크릴 & 몰딩","image":"stinger2", "price": "10000"},

    # 컵홀더 윙
    {"id":"cupholder_wing","name":"컵홀더 (날개)(LED없음)","category":"컵홀더 윙","image":"cupwing", "price": "30000"}, # 40개 세트가는 있으나 단품가 유지

    # 배선/커넥터/부자재
    {"id":"conn_4p_100","name":"4P 커넥터 100PCS (암,숫)","category":"배선/커넥터/부자재","image":"4pconnet", "price": "30000"},
    {"id":"harness_pin_ket_100","name":"하네스 핀 KET 암,숫 100PCS","category":"배선/커넥터/부자재","image":"ket", "price": "50000"},
    {"id":"harness_pin_amp_100","name":"하네스 핀 AMP 암,숫 100PCS","category":"배선/커넥터/부자재","image":"ket", "price": "100000"}, # 신규 단가 반영
    {"id":"conn_y_50","name":"Y자 커넥터 50PCS","category":"배선/커넥터/부자재","image":"4pY", "price": "50000"},
    {"id":"power_cable","name":"전원케이블","category":"배선/커넥터/부자재","image":"MAINPOWER", "price": "40000"}, # 신규 단가 반영
    {"id":"music_switch","name":"음악반응 스위치","category":"배선/커넥터/부자재","image":"MUSICBUTTON", "price": "10000"}, # 신규 단가 반영
    {"id":"tape_3m_gray","name":"3m 양면 테이프(회색)","category":"배선/커넥터/부자재","image":"3M", "price": "35000"},
    {"id":"tape_reflect","name":"반사 테이프","category":"배선/커넥터/부자재","image":"bansa", "price": "20000"},
    {"id":"tape_sookwang_5mm","name":"아크릴 전용 3M 수광 테이프(투명) 5mm","category":"배선/커넥터/부자재","image":"SOOKWANG", "price": "1500"},
    {"id":"tape_sookwang_3mm","name":"아크릴 전용 3M 수광 테이프(투명) 3mm","category":"배선/커넥터/부자재","image":"SOOKWANG", "price": "1000"},
    {"id":"foot_rgb_rollbar","name":"풋등 RGB 롤바","category":"배선/커넥터/부자재","image":"RGBRALL", "price": "25000"}, # RGB LED 5M 단가
    {"id":"foot_moving_rollbar","name":"풋등 무빙 롤바","category":"배선/커넥터/부자재","image":"MOVINGRALL", "price": "40000"}, # 네오픽셀 LED 5M 단가
    {"id":"rgb_one_shot","name":"RGB 단발 LED","category":"배선/커넥터/부자재","image":"RGBONESHOT", "price": "8000"},
    {"id":"steer_remote_5_1k","name":"핸들 리모컨 5.1K 저항","category":"배선/커넥터/부자재","image":"5.1K", "price": "1000"},
    {"id":"fuse_10a","name":"퓨즈 10A","category":"배선/커넥터/부자재","image":"FUSE10A", "price": "1500"},
    {"id":"stinger_airvent1","name":"벤풍구 1열 (스팅어)","category":"배선/커넥터/부자재","image":"STINGERAIRVENT1", "price": "120000"},
    {"id":"stinger_airvent2","name":"벤풍구 2열 (스팅어)","category":"배선/커넥터/부자재","image":"STINGERAIRVENT2", "price": "100000"},

    # 완제품 세트
    {"id":"foot_rgb_row1","name":"RGB 풋등 1열 (2개)","category":"완제품 세트","image":"rgbfoot", "price": "15000"},
    {"id":"foot_rgb_row2","name":"RGB 풋등 2열 (2개)","category":"완제품 세트","image":"rgbfoot", "price": "20000"},
    {"id":"foot_moving_row1","name":"무빙 풋등 1열 (2개)","category":"완제품 세트","image":"movingfoot", "price": "15000"},
    {"id":"foot_moving_row2","name":"무빙 풋등 2열 (2개)","category":"완제품 세트","image":"movingfoot", "price": "20000"},
    {"id":"speaker_rgb_set","name":"RGB 스피커 2개 1SET","category":"완제품 세트","image":"speaker", "price": "50000"}, # 신규 완제품 단가
    {"id":"speaker_moving_set","name":"무빙 스피커 2개 1SET","category":"완제품 세트","image":"speaker", "price": "60000"}, # 신규 완제품 단가
    {"id":"mq4_rgb_front","name":"쏘렌토MQ4 RGB 전면","category":"완제품 세트","image":"mq4center", "price": "60000"}, # 교체용 단가 반영
    {"id":"mq4_moving_front","name":"쏘렌토MQ4 무빙 전면","category":"완제품 세트","image":"mq4center", "price": "70000"}, # 교체용 단가 반영
    {"id":"palisade_rgb_front","name":"신형팰리세이드 RGB 전면","category":"완제품 세트","image":"palisadedoor", "price": "60000"}, # 몰딩 단가 반영
    {"id":"palisade_moving_front","name":"신형팰리세이드 무빙 전면","category":"완제품 세트","image":"thenewpalisade", "price": "70000"}, # 몰딩 단가 반영
    {"id":"palisade_rgb_door","name":"신형,구형 팰리세이드 RGB 도어","category":"완제품 세트","image":"palisadedoor", "price": "140000"}, # 몰딩 단가 반영
    {"id":"palisade_moving_door","name":"신형,구형 팰리세이드 무빙 도어","category":"완제품 세트","image":"palisadedoor", "price": "180000"}, # 몰딩 단가 반영
    {"id":"gn7_rgb_front","name":"그랜져GN7 RGB 전면","category":"완제품 세트","image":"gn7center", "price": "50000"}, # 교체용 단가 반영
    {"id":"gn7_moving_front","name":"그랜져GN7 무빙 전면","category":"완제품 세트","image":"gn7center", "price": "60000"}, # 교체용 단가 반영
    {"id":"gn7_rgb_door","name":"그랜져GN7 RGB 도어","category":"완제품 세트","image":"gn7door", "price": "140000"}, # 몰딩 단가 반영
    {"id":"gn7_moving_door","name":"그랜져GN7 무빙 도어","category":"완제품 세트","image":"gn7door", "price": "180000"}, # 몰딩 단가 반영
]

# 세트 구성 규칙 (id 기반) : "세트ID": [("구성ID", 개수), ...]
SET_RULES: Dict[str, List[Tuple[str, int]]] = {
    "oem_rgb_set": [
        ("oem_rgb_single", 1),
        ("rgb_led_110", 1),
        ("rgb_led_90", 4),
    ],
    "oem_se_set": [
        ("oem_se_single", 1),
        ("moving_led_110", 1),
        ("moving_led_90", 4),
    ],
    "oem_v4_set": [
        ("oem_v4_single", 1),
        ("moving_led_110", 1),
        ("moving_led_90", 4),
    ],
    "universal_se_set": [
        ("universal_se_single", 1),
        ("oem_se_single", 1),
        ("moving_led_110", 1),
        ("moving_led_90", 4),
    ],
    "oem_v4_pro_set": [
        ("oem_v4_pro_single", 1),
        ("moving_led_110", 1),
        ("moving_led_90", 4),
        ("moving_led_50", 2),
        ("moving_led_30", 2),
    ],
    "oem_se_pro_set": [
        ("oem_se_pro_single", 1),
        ("moving_led_110", 1),
        ("moving_led_90", 4),
        ("moving_led_50", 2),
        ("moving_led_30", 2),
    ],
}

dealers = {
    "에이비클 서울경기지사": {"phone": "010-5466-6888", "addr": "경기도 광명시 일직로99번길 30"},
    "천안 에이비클": {"phone": "010-3443-4866", "addr": "충남 천안시 서북구 성성 1길 109"},
    "진주 멀티게라지": {"phone": "010-2371-6964", "addr": "경남 진주시 석갑로 155번길 54"},
    "창원 카톡하우스": {"phone": "010-2720-6345", "addr": "경남 창원시 성산구 신사로 89"},
    "전주 노이즈킹": {"phone": "010-7412-1110", "addr": "전주시 완산구 문학대6길 32-1"},
    "목포 에이비클": {"phone": "010-9695-3447", "addr": "전남 목포 산정로 37"},
    "순천 악동모터스": {"phone": "010-5474-6990", "addr": "순천시 해룡면 지봉로 180"},
    "여수 카팩토리": {"phone": "010-5052-5555", "addr": "전남 여수시 쌍봉로 143"},
    "구미 디지나인 커스텀": {"phone": "010-9455-6858", "addr": "경북 구미시 송선로 476"},
    "포항 멀티게라지": {"phone": "010-4014-2805", "addr": "경북 포항시 남구 희망대로 941"},
    "경주 카뷰티": {"phone": "010-4124-2214", "addr": "경북 경주시 천북면 천북로 99 1층"},
    "부산 비바아우토": {"phone": "010-2416-3224", "addr": "부산 부산진구 중앙대로 941번길 60"},
    "부산 원픽스": {"phone": "010-6324-3322", "addr": "부산 강서구 사덕신장로 19"},
    "울산 사운드매니아": {"phone": "010-4460-5255", "addr": "울산 북구 진장 24길 60"},
    "대구 홍스": {"phone": "010-2412-3433", "addr": "대구 동구 율하서로 96 1375 1층"},
}

# ---------- 인덱스(단일 소스에서 파생) ----------
def build_indexes(items: List[Dict[str, str]]):
    by_id: Dict[str, Dict[str, str]] = {}
    by_name_to_id: Dict[str, str] = {}
    categories: Dict[str, List[str]] = {}
    for it in items:
        by_id[it["id"]] = it
        by_name_to_id[it["name"]] = it["id"]
        categories.setdefault(it["category"], []).append(it["name"])
    for k in categories:
        categories[k].sort()
    return by_id, by_name_to_id, categories

ITEMS_BY_ID, NAME_TO_ID, ITEMS_BY_CATEGORY = build_indexes(ITEMS)

# ---------- 유틸 ----------
def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_window_position():
    if not os.path.exists(CONFIG_FILE):
        return None
    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_FILE)
        return config.get("WINDOW", "geometry", fallback=None)
    except Exception:
        return None

def save_window_position(root):
    geo = root.geometry()
    config = configparser.ConfigParser()
    config["WINDOW"] = {"geometry": geo}
    with open(CONFIG_FILE, "w") as f:
        config.write(f)

def find_image_file(image_stem_or_name: Optional[str]):
    if not image_stem_or_name:
        return None
    name_wo_ext = os.path.splitext(image_stem_or_name)[0]
    image_folder = resource_path(os.path.join("avicle"))
    if not os.path.isdir(image_folder):
        return None
    for ext in (".jpg", ".jpeg", ".png", ".gif"):
        p = os.path.join(image_folder, name_wo_ext + ext)
        if os.path.exists(p):
            return p
    return None

def open_file_cross_platform(path: str):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        webbrowser.open(f"file://{os.path.abspath(path)}")

def save_order_to_txt(order_list):
    save_dir = os.path.join(os.getcwd(), "발주기록")
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    filename = f"{timestamp}_발주내역.txt"
    with open(os.path.join(save_dir, filename), "w", encoding="utf-8") as f:
        f.write("\n".join(order_list))

def send_telegram_message(text: str):
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": text},
                timeout=10
            )
            return True
        except requests.RequestException:
            if attempt < max_attempts:
                time.sleep(2)
    return False

# ---------- GUI ----------
class OrderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("협력사 발주 프로그램 (v2.0 Price System)")
        self.root.geometry("1000x750")
        self.root.minsize(900, 650)
        saved_geo = load_window_position()
        if saved_geo:
            self.root.geometry(saved_geo)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._photo_cache = None
        self._last_preview_path = None
        self.search_var = tk.StringVar()

        self.tab_listboxes: Dict[str, tk.Listbox] = {}
        self.build_style()
        self.build_topbar()
        self.build_body_with_tabs()
        self.build_cart()
        self.bind_shortcuts()

    def build_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#f7f7fa", foreground="#111827")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("TLabel", background="#ffffff", foreground="#111827", font=("Segoe UI", 11))
        style.configure("Subtle.TLabel", background="#ffffff", foreground="#6b7280", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#ffffff", foreground="#111827", font=("Segoe UI Semibold", 14))
        style.configure("Price.TLabel", background="#ffffff", foreground="#2563eb", font=("Segoe UI Bold", 12))
        style.configure("TButton", font=("Segoe UI", 11), padding=(10, 7))
        style.configure("TCombobox", fieldbackground="#ffffff")
        style.configure("Treeview",
                        background="#ffffff", fieldbackground="#ffffff", foreground="#111827",
                        rowheight=26, bordercolor="#e5e7eb", borderwidth=1)
        style.configure("Treeview.Heading",
                        background="#f3f4f6", foreground="#111827", font=("Segoe UI Semibold", 11))
        style.map("Treeview", background=[("selected", "#e0e7ff")])

    def build_topbar(self):
        top = ttk.Frame(self.root, style="Card.TFrame", padding=12)
        top.pack(side="top", fill="x", padx=14, pady=(14, 8))

        ttk.Label(top, text="협력사", style="Header.TLabel").pack(side="left")
        self.dealer_combo = ttk.Combobox(top, values=list(dealers.keys()), state="readonly", width=30)
        self.dealer_combo.pack(side="left", padx=(8, 16))

        ttk.Label(top, text="검색", style="Subtle.TLabel").pack(side="left")
        self.search_entry = ttk.Entry(top, textvariable=self.search_var, width=22)
        self.search_entry.pack(side="left", padx=(6, 8))
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_all_tabs_list())

        ttk.Button(top, text="📌 필독", command=self.show_notice).pack(side="right")
        ttk.Button(top, text="발주 보내기", command=self.submit_order).pack(side="right", padx=(0, 8))

    def build_body_with_tabs(self):
        body = ttk.Frame(self.root, style="Card.TFrame", padding=10)
        body.pack(side="top", fill="both", expand=True, padx=14, pady=(0, 8))

        self.paned = ttk.Panedwindow(body, orient="horizontal")
        self.paned.pack(fill="both", expand=True)

        left = ttk.Frame(self.paned, style="Card.TFrame", padding=6)
        ttk.Label(left, text="상품 카테고리", style="Header.TLabel").pack(anchor="w", pady=(0, 6))

        self.notebook = ttk.Notebook(left)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all_tabs_list())

        self._create_tab(self.notebook, "전체")
        for cat in sorted(ITEMS_BY_CATEGORY.keys()):
            self._create_tab(self.notebook, cat)

        right = ttk.Frame(self.paned, style="Card.TFrame", padding=10)
        header = ttk.Frame(right, style="Card.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="미리보기", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="(더블클릭: 원본)", style="Subtle.TLabel").pack(side="left", padx=(8, 0))

        self.preview = tk.Label(
            right, bg="#f3f4f6", fg="#6b7280", anchor="center",
            text="품목을 선택하세요.", font=("Segoe UI", 11), relief="flat"
        )
        self.preview.pack(fill="both", expand=True, pady=(6, 8))
        self.preview.bind("<Double-Button-1>", self.open_last_preview_file)

        # --- 가격 정보 표시 영역 ---
        self.price_card = ttk.Frame(right, style="Card.TFrame", padding=5)
        self.price_card.pack(fill="x", pady=(0, 10))
        
        self.price_info_label = ttk.Label(self.price_card, text="공급가: - | 부가세포함: -", style="Price.TLabel", anchor="center")
        self.price_info_label.pack(fill="x")

        control = ttk.Frame(right, style="Card.TFrame")
        control.pack(fill="x")
        ttk.Label(control, text="수량").pack(side="left")
        self.qty_spin = tk.Spinbox(control, from_=1, to=1000, width=6, font=("Segoe UI", 11))
        self.qty_spin.delete(0, "end"); self.qty_spin.insert(0, "1")
        self.qty_spin.pack(side="left", padx=(6, 8))
        ttk.Button(control, text="장바구니 추가", command=self.add_to_cart).pack(side="left")

        self.paned.add(left, weight=6)
        self.paned.add(right, weight=7)

        self.refresh_all_tabs_list()
        self.preview.bind("<Configure>", lambda e: self.refresh_preview_thumb())

    def _create_tab(self, notebook: ttk.Notebook, title: str):
        tab_frame = ttk.Frame(notebook, style="Card.TFrame", padding=6)
        notebook.add(tab_frame, text=title)
        list_frame = ttk.Frame(tab_frame, style="Card.TFrame")
        list_frame.pack(fill="both", expand=True)
        lb = tk.Listbox(
            list_frame, activestyle="none", selectmode="browse", exportselection=False,
            highlightthickness=0, relief="flat", font=("Segoe UI", 11), width=44
        )
        yscroll = ttk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
        lb.configure(yscrollcommand=yscroll.set)
        lb.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        
        lb.bind("<<ListboxSelect>>", self.on_product_select)
        lb.bind("<Double-Button-1>", self.on_add_by_double_click)
        lb.bind("<Up>", self.on_list_up_down)
        lb.bind("<Down>", self.on_list_up_down)
        self.tab_listboxes[title] = lb

    def build_cart(self):
        card = ttk.Frame(self.root, style="Card.TFrame", padding=10)
        card.pack(side="bottom", fill="both", padx=14, pady=(0, 14))

        header = ttk.Frame(card, style="Card.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="🛒 장바구니", style="Header.TLabel").pack(side="left")
        
        # 합계 표시용 레이블
        self.total_label = ttk.Label(header, text="총 합계: 0원 (VAT 포함: 0원)", font=("Segoe UI Bold", 12), foreground="#dc2626")
        self.total_label.pack(side="left", padx=20)

        ttk.Button(header, text="선택 항목 삭제", command=self.remove_selected).pack(side="right")

        table_frame = ttk.Frame(card, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True, pady=(6, 0))

        # 컬럼에 가격 추가
        self.cart_tree = ttk.Treeview(table_frame, columns=("item", "qty", "unit_p", "total_p"), show="headings", height=6)
        self.cart_tree.heading("item", text="품목")
        self.cart_tree.heading("qty", text="수량")
        self.cart_tree.heading("unit_p", text="단가(공급가)")
        self.cart_tree.heading("total_p", text="금액 합계")
        
        self.cart_tree.column("item", width=400, anchor="w")
        self.cart_tree.column("qty", width=60, anchor="center")
        self.cart_tree.column("unit_p", width=120, anchor="e")
        self.cart_tree.column("total_p", width=120, anchor="e")

        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=yscroll.set)

        self.cart_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        def _on_delete(event):
            self.remove_selected(silent_if_empty=True)
            return "break"
        self.cart_tree.bind("<Delete>", _on_delete)

    def bind_shortcuts(self):
        self.root.bind("<Return>", lambda e: self.add_to_cart())

    def refresh_all_tabs_list(self):
        q = self.search_var.get().strip().lower()
        lb_all = self.tab_listboxes.get("전체")
        if lb_all:
            lb_all.delete(0, "end")
            for cat in sorted(ITEMS_BY_CATEGORY.keys()):
                for name in ITEMS_BY_CATEGORY[cat]:
                    if q and q not in name.lower(): continue
                    lb_all.insert("end", f"[{cat}] {name}")
        for cat, lb in self.tab_listboxes.items():
            if cat == "전체": continue
            lb.delete(0, "end")
            for name in ITEMS_BY_CATEGORY.get(cat, []):
                if q and q not in name.lower(): continue
                lb.insert("end", name)

        active = self.active_category()
        lb_active = self.tab_listboxes.get(active)
        if lb_active and lb_active.size() > 0 and not lb_active.curselection():
            lb_active.selection_set(0)
            lb_active.activate(0)
            lb_active.see(0)
            self.on_product_select()

    def on_list_up_down(self, event):
        lb: tk.Listbox = event.widget
        size = lb.size()
        if size == 0: return "break"
        sel = lb.curselection()
        idx = sel[0] if sel else -1
        if event.keysym == "Up":
            new = max(0, (idx if idx != -1 else 0) - 1)
        else:
            new = min(size - 1, (idx if idx != -1 else -1) + 1)
        lb.selection_clear(0, "end")
        lb.selection_set(new)
        lb.activate(new)
        lb.see(new)
        self.on_product_select()
        return "break"

    def active_category(self) -> str:
        idx = self.notebook.index("current")
        return self.notebook.tab(idx, "text")

    def get_selected_product_name(self) -> Optional[str]:
        cat = self.active_category()
        lb = self.tab_listboxes[cat]
        sel = lb.curselection()
        if not sel: return None
        text = lb.get(sel[0])
        if cat == "전체":
            try: return text.split("] ", 1)[1]
            except: return text
        return text

    def on_product_select(self, event=None):
        name = self.get_selected_product_name()
        if not name: return
        self.show_preview(name)
        self.update_price_display(name)

    # --- 가격 레이블 업데이트 기능 ---
    def update_price_display(self, name: str):
        item_id = NAME_TO_ID.get(name)
        if not item_id: return
        item_data = ITEMS_BY_ID.get(item_id)
        price_val = int(item_data.get("price", 0))
        vat_val = int(price_val * 1.1)
        
        self.price_info_label.config(
            text=f"공급가: {price_val:,}원 | 부가세포함: {vat_val:,}원"
        )

    def on_add_by_double_click(self, event=None):
        self.add_to_cart()

    def refresh_preview_thumb(self):
        if not self._last_preview_path: return
        self._render_image(self._last_preview_path)

    def show_preview(self, name: str):
        item_id = NAME_TO_ID.get(name)
        if not item_id:
            self.preview.config(text="이미지 없음", image=""); self._photo_cache = None; self._last_preview_path = None
            return
        image_stem = ITEMS_BY_ID[item_id].get("image")
        path = find_image_file(image_stem)
        if not path:
            self.preview.config(text="이미지 없음", image=""); self._photo_cache = None; self._last_preview_path = None
            return
        self._last_preview_path = path
        self._render_image(path)

    def _render_image(self, path: str):
        self.preview.update_idletasks()
        w = max(self.preview.winfo_width() - 12, 200)
        h = max(self.preview.winfo_height() - 12, 200)
        if PIL_AVAILABLE:
            try:
                img = Image.open(path)
                img.thumbnail((w, h))
                self._photo_cache = ImageTk.PhotoImage(img)
                self.preview.config(image=self._photo_cache, text="")
            except:
                self.preview.config(text="이미지 로드 실패", image=""); self._photo_cache = None
        else:
            try:
                self._photo_cache = tk.PhotoImage(file=path)
                self.preview.config(image=self._photo_cache, text="")
            except:
                self.preview.config(text="미리보기 불가 (Pillow 미설치)", image=""); self._photo_cache = None

    def open_last_preview_file(self, event=None):
        if not self._last_preview_path or not os.path.exists(self._last_preview_path):
            messagebox.showinfo("이미지 없음", "열 수 있는 이미지가 없습니다.")
            return
        open_file_cross_platform(self._last_preview_path)

    def expand_set_items(self, item_id: str, qty: int) -> List[Tuple[str, int]]:
        if item_id in SET_RULES:
            expanded: List[Tuple[str, int]] = []
            for child_id, count in SET_RULES[item_id]:
                expanded.append((child_id, qty * count))
            return expanded
        return [(item_id, qty)]

    def add_to_cart(self):
        name = self.get_selected_product_name()
        if not name:
            messagebox.showwarning("오류", "상품을 선택하세요.")
            return
        try:
            qty = int(self.qty_spin.get())
            if qty <= 0: raise ValueError
        except:
            messagebox.showwarning("오류", "수량은 1 이상의 숫자로 입력하세요.")
            return

        item_id = NAME_TO_ID.get(name)
        if not item_id: return

        # 세트 상품 여부와 관계없이 개별 단가 계산을 위해 확장 처리
        for add_id, add_qty in self.expand_set_items(item_id, qty):
            target_item = ITEMS_BY_ID.get(add_id, {})
            display_name = target_item.get("name", add_id)
            unit_price = int(target_item.get("price", 0))
            self._merge_cart(display_name, add_qty, unit_price)
        
        self.update_cart_total()

    def _merge_cart(self, name: str, add_qty: int, unit_price: int):
        for iid in self.cart_tree.get_children():
            item_name, item_qty, up, tp = self.cart_tree.item(iid, "values")
            if item_name == name:
                new_qty = int(item_qty) + add_qty
                new_total = new_qty * unit_price
                self.cart_tree.item(iid, values=(name, new_qty, f"{unit_price:,}", f"{new_total:,}"))
                return
        total_price = add_qty * unit_price
        self.cart_tree.insert("", "end", values=(name, add_qty, f"{unit_price:,}", f"{total_price:,}"))

    def update_cart_total(self):
        total_supply = 0
        for iid in self.cart_tree.get_children():
            _, _, _, tp_str = self.cart_tree.item(iid, "values")
            total_supply += int(tp_str.replace(",", ""))
        
        total_vat = int(total_supply * 1.1)
        self.total_label.config(text=f"총 합계: {total_supply:,}원 (VAT 포함: {total_vat:,}원)")

    def remove_selected(self, silent_if_empty: bool = False):
        sel = self.cart_tree.selection()
        if not sel: return
        for iid in sel:
            self.cart_tree.delete(iid)
        self.update_cart_total()

    def submit_order(self):
        dealer = self.dealer_combo.get()
        if not dealer:
            messagebox.showwarning("오류", "협력사를 선택하세요.")
            return
        if not self.cart_tree.get_children():
            messagebox.showwarning("오류", "장바구니가 비어 있습니다.")
            return
        
        info = dealers[dealer]
        order_list, order_list_msg = [], ""
        total_supply = 0
        
        for iid in self.cart_tree.get_children():
            name, qty, up, tp = self.cart_tree.item(iid, "values")
            order_list.append(f"{name} ({qty}개) - {tp}원")
            order_list_msg += f"- {name} ({qty}개)\n"
            total_supply += int(tp.replace(",", ""))
        
        total_vat = int(total_supply * 1.1)
        
        msg = (
            f"📦 신규 발주 접수\n\n"
            f"🏪 협력사: {dealer}\n"
            f"📞 연락처: {info['phone']}\n"
            f"📍 주소: {info['addr']}\n\n"
            f"🛒 주문 품목:\n{order_list_msg}\n"
            f"💰 총 공급가: {total_supply:,}원\n"
            f"💳 합계(VAT포함): {total_vat:,}원"
        )
        
        ok = send_telegram_message(msg)
        if not ok:
            messagebox.showerror("전송 실패", "텔레그램 전송이 실패했습니다.")
            return
        
        messagebox.showinfo("완료", "발주가 정상적으로 전송되었습니다.")
        save_order_to_txt(order_list + [f"총 합계(VAT포함): {total_vat:,}원"])
        self.cart_tree.delete(*self.cart_tree.get_children())
        self.update_cart_total()

    def show_notice(self):
        notice_text = (
            "📌 택배사 [한진택배]\n"
            "- 아크릴 LED 제품\n"
            "- 12시 이전 발주\n"
            "- 14시 이전 입금확인건\n"
            "- 당일 발송됩니다.\n"
            "- 완제품인 경우 1~2일 이후\n"
            "- 발송 될수 있습니다\n"
        )
        win = tk.Toplevel(self.root)
        win.title("📌 필독 안내")
        win.geometry("520x360")
        win.configure(bg="#f7f7fa")
        win.grab_set()

        body = ttk.Frame(win, style="Card.TFrame", padding=12)
        body.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(body, text=notice_text, font=("Segoe UI", 11),
                 justify="left", wraplength=488, bg="#ffffff", fg="#111827").pack(fill="both", expand=True)
        ttk.Button(body, text="확인", command=win.destroy).pack(pady=8)

        self.root.update_idletasks()
        rx, ry = self.root.winfo_x(), self.root.winfo_y()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        ww, wh = 520, 360
        x = rx + (rw // 2) - (ww // 2)
        y = ry + (rh // 2) - (wh // 2)
        win.geometry(f"{ww}x{wh}+{x}+{y}")

    def on_close(self):
        save_window_position(self.root)
        self.root.destroy()

def main():
    global ITEMS_BY_ID, NAME_TO_ID, ITEMS_BY_CATEGORY
    ITEMS_BY_ID, NAME_TO_ID, ITEMS_BY_CATEGORY = build_indexes(ITEMS)
    root = tk.Tk()
    app = OrderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

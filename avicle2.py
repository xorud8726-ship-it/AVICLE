# file: order_app_vertical_partner_inputs.py
import tkinter as tk
from tkinter import ttk, messagebox
import sys, os, datetime, requests, configparser

# -------------------- 공용 경로 --------------------
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

CONFIG_FILE = "config.ini"

# -------------------- 텔레그램 --------------------
TOKEN = "7895331234:AAG9ge6GGBg0plHb7axWcwSwIgSNG9gWvuY"
CHAT_ID = "-1003315436286"

# -------------------- 단일 카탈로그 (이름 ➜ {category, image, price}) --------------------
# image: ./avicle/<image>.(jpg|jpeg|png) 자동 탐색
# price: 일반업체 공급가 (협력업체가격 +10%)
ITEM_CATALOG = {
    # 모듈 (세트,단품)
    "RGB 블루투스 모듈(하우동)": {"category": "모듈 (세트,단품)", "image": "haodeng", "price": 24200},
    "순정연동 RGB 모듈 1개 세트 (RGB 모듈, 110 1개, 90 4개)": {"category": "모듈 (세트,단품)", "image": "rgb110", "price": 202125},
    "순정연동 SE 모듈 1개 세트 (SE 모듈, 110 1개, 90 4개, 30 1개)": {"category": "모듈 (세트,단품)", "image": "se", "price": 309540},
    "유니버셜 se 모듈 1개 세트 (SE 모듈,블루투스 모듈, 110 1개, 90 4개, 30 1개)": {"category": "모듈 (세트,단품)", "image": "seset", "price": 367290},
    "순정연동 블루투스 모듈 1개 단품": {"category": "모듈 (세트,단품)", "image": "uni", "price": 57750},
    "순정연동 RGB 모듈 1개 단품": {"category": "모듈 (세트,단품)", "image": "rgbb", "price": 69300},
    "순정연동 SE 모듈 1개 단품": {"category": "모듈 (세트,단품)", "image": "see", "price": 150150},

    # LED (RGB/무빙)
    "RGB 110cm": {"category": "LED (RGB/무빙)", "image": "rgb110", "price": 32340},
    "RGB 90cm": {"category": "LED (RGB/무빙)", "image": "rgb90", "price": 28875},
    "무빙 110cm": {"category": "LED (RGB/무빙)", "image": "moving110", "price": 43890},
    "무빙 90cm": {"category": "LED (RGB/무빙)", "image": "moving90", "price": 33495},
    "무빙 50cm": {"category": "LED (RGB/무빙)", "image": "moving50", "price": 20790},
    "무빙 30cm": {"category": "LED (RGB/무빙)", "image": "moving30", "price": 17325},
    "무빙 15cm(품절)": {"category": "LED (RGB/무빙)", "image": "led", "price": 12705},

    # 컵홀더 윙
    "컵홀더 (날개)(LED없음)": {"category": "컵홀더 윙", "image": "cupwing", "price": 36300},

    # 배선/커넥터/부자재
    "4P 커넥터 100PCS (암,숫)": {"category": "배선/커넥터/부자재", "image": "4pconnet", "price": 36300},
    "하네스 핀 KET 암,숫 100PCS": {"category": "배선/커넥터/부자재", "image": "ket", "price": 60500},
    "하네스 핀 AMP 암,숫 100PCS": {"category": "배선/커넥터/부자재", "image": "ket", "price": 121000},
    "Y자 커넥터 1PCS": {"category": "배선/커넥터/부자재", "image": "4pY", "price": 1210},
    "전원케이블": {"category": "배선/커넥터/부자재", "image": "MAINPOWER", "price": 48400},
    "음악반응 스위치": {"category": "배선/커넥터/부자재", "image": "MUSICBUTTON", "price": 12100},
    "3m 양면 테이프(회색)": {"category": "배선/커넥터/부자재", "image": "3M", "price": 42350},
    "반사 테이프": {"category": "배선/커넥터/부자재", "image": "bansa", "price": 24200},
    "아크릴 전용 3M 수광 테이프(투명) 5mm": {"category": "배선/커넥터/부자재", "image": "SOOKWANG", "price": 1815},
    "아크릴 전용 3M 수광 테이프(투명) 3mm": {"category": "배선/커넥터/부자재", "image": "SOOKWANG", "price": 1210},
    "풋등 RGB 롤바": {"category": "배선/커넥터/부자재", "image": "RGBRALL", "price": 30250},
    "풋등 무빙 롤바": {"category": "배선/커넥터/부자재", "image": "MOVINGRALL", "price": 48400},
    "RGB 단발 LED": {"category": "배선/커넥터/부자재", "image": "RGBONESHOT", "price": 9680},
    "핸들 리모컨 5.1K 저항": {"category": "배선/커넥터/부자재", "image": "5.1K", "price": 1210},
    "퓨즈 10A": {"category": "배선/커넥터/부자재", "image": "FUSE10A", "price": 1815},
    "벤풍구 1열 (스팅어)": {"category": "배선/커넥터/부자재", "image": "STINGERAIRVENT1", "price": 145200},
    "벤풍구 2열 (스팅어)": {"category": "배선/커넥터/부자재", "image": "STINGERAIRVENT2", "price": 121000},

    # 완제품 세트
    "RGB 스피커 2개 1SET": {"category": "완제품 세트", "image": "speaker", "price": 60500},
    "무빙 스피커 2개 1SET": {"category": "완제품 세트", "image": "speaker", "price": 72600},
    "RGB 풋등 1열 (2개)": {"category": "완제품 세트", "image": "rgbfoot", "price": 18150},
    "RGB 풋등 2열 (2개)": {"category": "완제품 세트", "image": "rgbfoot2", "price": 24200},
    "무빙 풋등 1열 (2개)": {"category": "완제품 세트", "image": "movingfoot1", "price": 18150},
    "무빙 풋등 2열 (2개)": {"category": "완제품 세트", "image": "movingfoot2", "price": 24200},
}

# -------------------- 파생: 카테고리 목록 / 카테고리별 품목명 --------------------
# 고정 탭 순서:
TAB_ORDER = [
    "모듈 (세트,단품)",
    "LED (RGB/무빙)",
    "컵홀더 윙",
    "배선/커넥터/부자재",
    "완제품 세트",
]

# 카테고리별 품목 이름 목록
items = {}
for name, meta in ITEM_CATALOG.items():
    cat = meta.get("category", "기타")
    items.setdefault(cat, []).append(name)
for cat in items:
    items[cat].sort(key=lambda s: s)

# 최종 탭 카테고리 목록(정렬 유지)
main_categories = [c for c in TAB_ORDER if c in items] + [c for c in items if c not in TAB_ORDER]

# -------------------- 설정 저장/불러오기 --------------------
def load_window_position():
    if not os.path.exists(CONFIG_FILE):
        return None
    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_FILE)
        return config.get("WINDOW", "geometry", fallback=None)
    except Exception:
        return None

def save_window_position():
    geo = root.geometry()
    config = configparser.ConfigParser()
    config["WINDOW"] = {"geometry": geo}
    with open(CONFIG_FILE, "w") as f:
        config.write(f)

# -------------------- 이미지 파일 찾기 --------------------
def find_image_file(image_stem_or_path):
    if not image_stem_or_path:
        return None
    base = os.path.splitext(str(image_stem_or_path))[0]
    folder = resource_path(os.path.join("avicle"))
    if not os.path.isdir(folder):
        return None
    for ext in [".jpg", ".jpeg", ".png"]:
        p = os.path.join(folder, base + ext)
        if os.path.exists(p):
            return p
    return None

# -------------------- 유틸 --------------------
def format_won(n):
    try:
        return f"{int(n):,}원"
    except Exception:
        return f"{n}원"

def _catalog_price(name: str) -> int:
    base = name.replace("(품절)", "").strip()
    return int(ITEM_CATALOG.get(base, {}).get("price", 0))

def _catalog_image(name: str):
    base = name.replace("(품절)", "").strip()
    return ITEM_CATALOG.get(base, {}).get("image")

# -------------------- 로직 --------------------
def update_submenu(event=None):
    selected = main_combo.get()
    sub_combo["values"] = items.get(selected, [])
    sub_combo.set("세부 품목 선택")

def update_totals():
    # --- 택배비 자동 추가/삭제 로직 ---
    all_iids = cart_tree.get_children()
    # 택배비를 제외한 실제 품목 리스트
    actual_items = [iid for iid in all_iids if cart_tree.item(iid, "values")[0] != "택배비"]
    
    if actual_items:
        # 실제 품목이 있는데 택배비가 없으면 최상단(index 0)에 삽입
        has_shipping = any(cart_tree.item(iid, "values")[0] == "택배비" for iid in all_iids)
        if not has_shipping:
            s_price = 4000
            s_vat = 400
            s_total = 4400
            cart_tree.insert("", 0, values=("택배비", 1, "4,000", s_price, s_vat, s_total))
    else:
        # 실제 품목이 하나도 없으면 택배비 삭제
        for iid in all_iids:
            if cart_tree.item(iid, "values")[0] == "택배비":
                cart_tree.delete(iid)

    # --- 금액 합계 계산 ---
    total = 0
    total_vat = 0
    for iid in cart_tree.get_children():
        vals = cart_tree.item(iid, "values")
        amount = int(vals[3]); vat = int(vals[4])
        total += amount; total_vat += vat
    grand = total + total_vat
    lbl_total.config(text=f"총액(합계, VAT 제외): {format_won(total)}")
    lbl_vat.config(text=f"VAT 합계(10%): {format_won(total_vat)}")
    lbl_grand.config(text=f"합계(총액+VAT): {format_won(grand)}")

def add_to_cart():
    item = sub_combo.get()
    if item == "세부 품목 선택":
        messagebox.showwarning("오류", "품목을 선택하세요.")
        return
    try:
        qty = int(qty_entry.get())
        if qty <= 0:
            raise ValueError
    except ValueError:
        messagebox.showwarning("오류", "수량은 1 이상의 숫자로 입력하세요.")
        return

    # 단품 및 세트를 분해하지 않고 그대로 장바구니에 추가합니다.
    key = item.replace("(품절)", "").strip()
    to_add = [(key, qty)]

    for name, add_qty in to_add:
        unit_price = _catalog_price(name)
        amount = unit_price * add_qty
        vat = int(round(amount * 0.1))
        line_total = amount + vat

        # 병합
        for iid in cart_tree.get_children():
            vals = cart_tree.item(iid, "values")
            if vals[0] == name:
                old_qty = int(vals[1])
                new_qty = old_qty + add_qty
                new_amount = unit_price * new_qty
                new_vat = int(round(new_amount * 0.1))
                new_line_total = new_amount + new_vat
                cart_tree.item(iid, values=(name, new_qty, f"{unit_price:,}", new_amount, new_vat, new_line_total))
                break
        else:
            cart_tree.insert("", tk.END, values=(name, add_qty, f"{unit_price:,}", amount, vat, line_total))

    update_totals()

def remove_from_cart(silent_if_empty=False):
    sel = cart_tree.selection()
    if not sel:
        if silent_if_empty:
            return
        messagebox.showwarning("오류", "삭제할 항목을 선택하세요.")
        return
    for iid in sel:
        # 택배비는 직접 삭제 불가 로직
        if cart_tree.item(iid, "values")[0] == "택배비":
            continue
        cart_tree.delete(iid)
    update_totals()

def save_order_to_txt(order_lines, totals):
    save_dir = os.path.join(os.getcwd(), "발주기록")
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    filename = f"{timestamp}_발주내역.txt"
    with open(os.path.join(save_dir, filename), "w", encoding="utf-8") as f:
        f.write("\n".join(order_lines))
        f.write("\n\n")
        f.write("\n".join(totals))

def submit_order():
    dealer = entry_name.get().strip()
    phone  = entry_phone.get().strip()
    addr   = entry_addr.get().strip()
    
    # 코딩 차량 정보 수집
    car_model = entry_car_model.get().strip()
    car_fuel = combo_fuel.get().strip()
    car_year = entry_car_year.get().strip()
    car_genuine = combo_genuine.get().strip()
    
    # 차량 정보 중 하나라도 입력되었는지 확인
    has_car_info = any([car_model, car_fuel, car_year, car_genuine])

    if not dealer or not phone or not addr:
        messagebox.showwarning("오류", "업체명, 전화번호, 주소 모두 입력하세요.")
        return
        
    # 실제 주문 품목이 있는지 확인 (택배비 제외)
    has_actual = any(cart_tree.item(iid, "values")[0] != "택배비" for iid in cart_tree.get_children())
    if not has_actual:
        messagebox.showwarning("오류", "장바구니가 비어 있습니다.")
        return

    order_lines = []
    total = 0
    total_vat = 0
    for iid in cart_tree.get_children():
        name, qty, unit_price_str, amount, vat, line_total = cart_tree.item(iid, "values")
        qty = int(qty); amount = int(amount); vat = int(vat)
        total += amount; total_vat += vat
        order_lines.append(f"{name} — {qty}개 — {format_won(amount)}")
    grand_total = total + total_vat

    # 텔레그램 메시지 구성
    tg_lines = [
        "📦 신규 발주 접수", "",
        f"🏪 업체명: {dealer}",
        f"📞 전화번호: {phone}",
        f"📍 주소: {addr}", ""
    ]
    
    # 차량 정보가 입력된 경우에만 텔레그램 메시지에 추가
    if has_car_info:
        tg_lines.extend([
            "🚗 [코딩 차량 정보]",
            f"- 차종: {car_model if car_model else '미입력'}",
            f"- 연료: {car_fuel if car_fuel else '미입력'}",
            f"- 연식: {car_year if car_year else '미입력'}",
            f"- 순정: {car_genuine if car_genuine else '미입력'}", ""
        ])

    tg_lines.extend([
        "🛒 주문 품목:",
        *order_lines, "",
        f"총액(VAT별도): {format_won(total)}",
        f"VAT(10%): {format_won(total_vat)}",
        f"합계(총합): {format_won(grand_total)}",
    ])
    tg_msg = "\n".join(tg_lines)

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": tg_msg},
            timeout=10
        )
    except Exception as e:
        messagebox.showerror("전송 실패", f"텔레그램 전송에 실패했습니다.\n{e}")
        return

    # 텍스트 파일 저장 상세 구성
    save_lines = [
        "발주 상세", "",
        f"업체명: {dealer}",
        f"전화번호: {phone}",
        f"주소: {addr}", ""
    ]
    
    # 차량 정보가 입력된 경우에만 텍스트 파일에 추가
    if has_car_info:
        save_lines.extend([
            "[코딩 차량 정보]",
            f"차종: {car_model if car_model else '미입력'}",
            f"연료: {car_fuel if car_fuel else '미입력'}",
            f"연식: {car_year if car_year else '미입력'}",
            f"순정: {car_genuine if car_genuine else '미입력'}", ""
        ])

    save_lines.append("품목 | 수량 | 단가 | 금액 | VAT | 합계")
    
    for iid in cart_tree.get_children():
        name, qty, unit_price_str, amount, vat, line_total = cart_tree.item(iid, "values")
        save_lines.append(f"{name} | {qty} | {unit_price_str} | {int(amount):,} | {int(vat):,} | {int(line_total):,}")

    totals = [
        f"총액: {total:,}",
        f"VAT 합계: {total_vat:,}",
        f"합계(총액+VAT): {grand_total:,}",
    ]
    save_order_to_txt(save_lines, totals)

    messagebox.showinfo("완료", "발주가 정상적으로 전송되었습니다.")
    cart_tree.delete(*cart_tree.get_children())
    
    # 주문 완료 후 차량 정보 초기화 (선택사항)
    entry_car_model.delete(0, tk.END)
    combo_fuel.set('')
    entry_car_year.delete(0, tk.END)
    combo_genuine.set('')
    
    update_totals()

def open_item_image(event):
    sel = cart_tree.selection()
    if not sel:
        return
    name = cart_tree.item(sel[0], "values")[0]
    if name == "택배비": return # 택배비는 이미지 없음
    image_key = _catalog_image(name)
    if not image_key:
        messagebox.showinfo("이미지 없음", "이미지가 없습니다.")
        return
    filepath = find_image_file(image_key)
    if not filepath:
        messagebox.showinfo("이미지 없음", "이미지 파일을 찾을 수 없습니다.")
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(filepath)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{filepath}"')
        else:
            os.system(f'xdg-open "{filepath}"')
    except Exception as e:
        messagebox.showerror("오류", f"이미지를 열 수 없습니다.\n{e}")

# -------------------- UI --------------------
root = tk.Tk()
root.title("협력사 발주 프로그램")
root.geometry("900x900") # 세로 길이를 조금 늘렸습니다.
root.configure(bg="#f0f2f5")

saved_geo = load_window_position()
if saved_geo:
    root.geometry(saved_geo)
root.protocol("WM_DELETE_WINDOW", lambda: (save_window_position(), root.destroy()))

style = ttk.Style()
style.theme_use("clam")
style.configure("TLabel", font=("Helvetica", 12), background="#f0f2f5")
style.configure("TButton", font=("Helvetica", 12), padding=6)
style.configure("TCombobox", font=("Helvetica", 12))

# ---- 협력사 입력(세로 1열) ----
info_frame = tk.Frame(root, bg="#f0f2f5", pady=8)
info_frame.pack(fill="x", padx=20)

tk.Label(info_frame, text="업체명", bg="#f0f2f5").pack(anchor="w")
entry_name = tk.Entry(info_frame, width=60, font=("Helvetica", 12))
entry_name.pack(fill="x", padx=2, pady=(0,8))

tk.Label(info_frame, text="전화번호", bg="#f0f2f5").pack(anchor="w")
entry_phone = tk.Entry(info_frame, width=60, font=("Helvetica", 12))
entry_phone.pack(fill="x", padx=2, pady=(0,8))

tk.Label(info_frame, text="주소", bg="#f0f2f5").pack(anchor="w")
entry_addr = tk.Entry(info_frame, width=60, font=("Helvetica", 12))
entry_addr.pack(fill="x", padx=2, pady=(0,8))

# ---- 코딩 차량 정보 (선택) 추가 ----
car_info_frame = tk.LabelFrame(root, text="코딩 차량 정보 (선택 입력)", bg="#f0f2f5", font=("Helvetica", 11, "bold"), pady=10, padx=10)
car_info_frame.pack(fill="x", padx=20, pady=(0, 8))

# 1열: 차종, 2열: 연료
tk.Label(car_info_frame, text="차종(직접작성)", bg="#f0f2f5", font=("Helvetica", 11)).grid(row=0, column=0, sticky="w", padx=(0, 5), pady=5)
entry_car_model = tk.Entry(car_info_frame, width=20, font=("Helvetica", 12))
entry_car_model.grid(row=0, column=1, padx=(0, 20), pady=5)

tk.Label(car_info_frame, text="연료", bg="#f0f2f5", font=("Helvetica", 11)).grid(row=0, column=2, sticky="w", padx=(0, 5), pady=5)
combo_fuel = ttk.Combobox(car_info_frame, values=["", "LPG", "가솔린", "하이브리드", "전기차", "디젤"], width=18, state="readonly", font=("Helvetica", 12))
combo_fuel.grid(row=0, column=3, pady=5)

# 2열: 연식, 2열: 순정
tk.Label(car_info_frame, text="연식(직접작성)", bg="#f0f2f5", font=("Helvetica", 11)).grid(row=1, column=0, sticky="w", padx=(0, 5), pady=5)
entry_car_year = tk.Entry(car_info_frame, width=20, font=("Helvetica", 12))
entry_car_year.grid(row=1, column=1, padx=(0, 20), pady=5)

tk.Label(car_info_frame, text="순정 (유/무)", bg="#f0f2f5", font=("Helvetica", 11)).grid(row=1, column=2, sticky="w", padx=(0, 5), pady=5)
combo_genuine = ttk.Combobox(car_info_frame, values=["", "유", "무"], width=18, state="readonly", font=("Helvetica", 12))
combo_genuine.grid(row=1, column=3, pady=5)

# ---- 품목 선택 ----
item_frame = tk.Frame(root, bg="#f0f2f5", pady=8)
item_frame.pack(fill="x", padx=20)

widgets = [
    ("카테고리 선택", ttk.Combobox(item_frame, values=main_categories, width=42, state="readonly")),
    ("세부 품목", ttk.Combobox(item_frame, width=42, state="readonly")),
    ("수량 입력", tk.Spinbox(item_frame, from_=1, to=10000, width=8, font=("Helvetica", 12))),
]
main_combo, sub_combo, qty_entry = [w[1] for w in widgets]
qty_entry.delete(0, "end"); qty_entry.insert(0, "1")

for i, (label, widget) in enumerate(widgets):
    ttk.Label(item_frame, text=label).grid(row=i, column=0, sticky="w", pady=5)
    widget.grid(row=i, column=1, padx=10, pady=5)

main_combo.bind("<<ComboboxSelected>>", update_submenu)
ttk.Button(item_frame, text="장바구니 추가", command=add_to_cart).grid(row=2, column=2, padx=10)

# ---- 장바구니 ----
cart_frame = tk.Frame(root, bg="#f0f2f5", pady=8)
cart_frame.pack(fill="both", expand=True, padx=20, pady=10)

ttk.Label(cart_frame, text="🛒 장바구니 목록").pack(anchor="w")

table_frame = tk.Frame(cart_frame, bg="#f0f2f5")
table_frame.pack(fill="both", expand=True, pady=(4, 6))

cart_tree = ttk.Treeview(
    table_frame,
    columns=("품목", "수량", "단가", "금액", "VAT", "합계"),
    show="headings",
    height=12
)
cart_tree.heading("품목", text="품목")
cart_tree.heading("수량", text="수량")
cart_tree.heading("단가", text="단가")
cart_tree.heading("금액", text="금액")
cart_tree.heading("VAT", text="VAT(10%)")
cart_tree.heading("합계", text="합계")

cart_tree.column("품목", width=400, anchor="w")
cart_tree.column("수량", width=80, anchor="center")
cart_tree.column("단가", width=120, anchor="e")
cart_tree.column("금액", width=120, anchor="e")
cart_tree.column("VAT", width=120, anchor="e")
cart_tree.column("합계", width=140, anchor="e")

ys = ttk.Scrollbar(table_frame, orient="vertical", command=cart_tree.yview)
xs = ttk.Scrollbar(table_frame, orient="horizontal", command=cart_tree.xview)
cart_tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)

cart_tree.grid(row=0, column=0, sticky="nsew")
ys.grid(row=0, column=1, sticky="ns")
xs.grid(row=1, column=0, sticky="ew")
table_frame.rowconfigure(0, weight=1)
table_frame.columnconfigure(0, weight=1)

cart_tree.bind("<Double-1>", open_item_image)

# Delete 키 → 조용히 삭제
def _on_delete(event):
    remove_from_cart(silent_if_empty=True)
    return "break"
cart_tree.bind("<Delete>", _on_delete)

# ---- 합계 ----
total_frame = tk.Frame(root, bg="#f0f2f5")
total_frame.pack(fill="x", padx=20, pady=8)

lbl_total = tk.Label(total_frame, text="총액(합계, VAT 제외): 0원", bg="#f0f2f5", font=("Helvetica", 13))
lbl_total.pack(anchor="w")
lbl_vat = tk.Label(total_frame, text="VAT 합계(10%): 0원", bg="#f0f2f5", font=("Helvetica", 13))
lbl_vat.pack(anchor="w")
lbl_grand = tk.Label(total_frame, text="합계(총액+VAT): 0원", bg="#f0f2f5", font=("Helvetica", 14, "bold"))
lbl_grand.pack(anchor="w")

# ---- 하단 버튼 ----
btn_frame = tk.Frame(root, bg="#f0f2f5", pady=8)
btn_frame.pack(fill="x", padx=20)
ttk.Button(btn_frame, text="선택 항목 삭제", command=lambda: remove_from_cart(silent_if_empty=True)).pack(side="left")
ttk.Button(btn_frame, text="발주 보내기", command=submit_order).pack(side="right")

# 초기 상태
if main_categories:
    main_combo.set(main_categories[0])
    update_submenu()
update_totals()

root.mainloop()

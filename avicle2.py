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

# -------------------- 세트 규칙 --------------------
set_rules = {
    "순정연동 RGB 모듈 1개 세트": ["순정연동 RGB 모듈 1개 단품", "RGB 110cm", "RGB 90cm 4개"],
    "순정연동 SE 모듈 1개 세트": ["순정연동 SE 모듈 1개 단품", "무빙 110cm", "무빙 90cm 4개"],
    "순정연동 V4 모듈 1개 세트": ["순정연동 V4 모듈 1개 단품", "무빙 110cm", "무빙 90cm 4개"],
    "유니버셜 se 모듈 1개 세트": ["순정연동 SE 모듈 1개 단품", "순정연동 블루투스 모듈 1개 단품", "무빙 110cm", "무빙 90cm 4개"],
}

# -------------------- 단일 카탈로그 (이름 ➜ {category, image, price}) --------------------
# image: ./avicle/<image>.(jpg|jpeg|png) 자동 탐색
ITEM_CATALOG = {
    # 모듈 (세트,단품)
    "RGB 블루투스 모듈(하우동)": {"category": "모듈 (세트,단품)", "image": "haodeng", "price": 20000},
    "순정연동 RGB 모듈 1개 세트": {"category": "모듈 (세트,단품)", "image": "rgb110", "price": 198000},
    "순정연동 SE 모듈 1개 세트": {"category": "모듈 (세트,단품)", "image": "se", "price": 309000},
    "유니버셜 se 모듈 1개 세트": {"category": "모듈 (세트,단품)", "image": "seset", "price": 369000},
    "순정연동 블루투스 모듈 1개 단품": {"category": "모듈 (세트,단품)", "image": "uni", "price": 55000},
    "순정연동 RGB 모듈 1개 단품": {"category": "모듈 (세트,단품)", "image": "rgbb", "price": 65000},
    "순정연동 SE 모듈 1개 단품": {"category": "모듈 (세트,단품)", "image": "see", "price": 150000},

    # LED (RGB/무빙)
    "RGB 110cm": {"category": "LED (RGB/무빙)", "image": "rgb110", "price": 30000},
    "RGB 90cm": {"category": "LED (RGB/무빙)", "image": "rgb90", "price": 27000},
    "무빙 110cm": {"category": "LED (RGB/무빙)", "image": "moving110", "price": 40000},
    "무빙 90cm": {"category": "LED (RGB/무빙)", "image": "moving90", "price": 34000},
    "무빙 50cm": {"category": "LED (RGB/무빙)", "image": "moving50", "price": 20000},
    "무빙 30cm": {"category": "LED (RGB/무빙)", "image": "moving30", "price": 16500},
    "무빙 15cm(품절)": {"category": "LED (RGB/무빙)", "image": "led", "price": 12000},

    # 아크릴 & 몰딩
    "스피커 아크릴 (1열) 2PCS": {"category": "아크릴 & 몰딩", "image": "tmvlzj", "price": 15000},
    "(토레스)스피커 아크릴 (1열) 2PCS": {"category": "아크릴 & 몰딩", "image": "xhfptm", "price": 14000},
    "RGB 풋등 아크릴 1대분 4PCS": {"category": "아크릴 & 몰딩", "image": "foot", "price": 1650},
    "무빙 풋등 아크릴 1대분 4PCS": {"category": "아크릴 & 몰딩", "image": "foot", "price": 2400},
    "다이얼 아크릴 MQ4(페리),K8(페리),KA4페리": {"category": "아크릴 & 몰딩", "image": "ekdldjf", "price": 15000},
    "다이얼 아크릴 NQ5": {"category": "아크릴 & 몰딩", "image": "ekdldjf", "price": 15000},
    "다이얼 아크릴 구형 KA4": {"category": "아크릴 & 몰딩", "image": "ekdldjf", "price": 15000},
    "다이얼 아크릴 DL3(페리)": {"category": "아크릴 & 몰딩", "image": "ekdldjf", "price": 15000},

    # 컵홀더 윙
    "컵홀더 (날개)(LED없음)": {"category": "컵홀더 윙", "image": "cupwing", "price": 35000},

    # 배선/커넥터/부자재
    "4P 커넥터 100PCS (암,숫)": {"category": "배선/커넥터/부자재", "image": "4pconnet", "price": 35000},
    "하네스 핀 KET 암,숫 100PCS": {"category": "배선/커넥터/부자재", "image": "ket", "price": 60000},
    "하네스 핀 AMP 암,숫 100PCS": {"category": "배선/커넥터/부자재", "image": "ket", "price": 120000},
    "Y자 커넥터 1PCS": {"category": "배선/커넥터/부자재", "image": "4pY", "price": 3000},
    "전원케이블": {"category": "배선/커넥터/부자재", "image": "MAINPOWER", "price": 35000},
    "음악반응 스위치": {"category": "배선/커넥터/부자재", "image": "MUSICBUTTON", "price": 15000},
    "3m 양면 테이프(회색)": {"category": "배선/커넥터/부자재", "image": "3M", "price": 38000},
    "반사 테이프": {"category": "배선/커넥터/부자재", "image": "bansa", "price": 22000},
    "아크릴 전용 3M 수광 테이프(투명) 5mm": {"category": "배선/커넥터/부자재", "image": "SOOKWANG", "price": 2000},
    "아크릴 전용 3M 수광 테이프(투명) 3mm": {"category": "배선/커넥터/부자재", "image": "SOOKWANG", "price": 1500},
    "풋등 RGB 롤바": {"category": "배선/커넥터/부자재", "image": "RGBRALL", "price": 28000},
    "풋등 무빙 롤바": {"category": "배선/커넥터/부자재", "image": "MOVINGRALL", "price": 44000},
    "RGB 단발 LED": {"category": "배선/커넥터/부자재", "image": "RGBONESHOT", "price": 10000},
    "핸들 리모컨 5.1K 저항": {"category": "배선/커넥터/부자재", "image": "5.1K", "price": 1000},
    "퓨즈 10A": {"category": "배선/커넥터/부자재", "image": "FUSE10A", "price": 2000},
    "벤풍구 1열 (스팅어)": {"category": "배선/커넥터/부자재", "image": "STINGERAIRVENT1", "price": 130000},
    "벤풍구 2열 (스팅어)": {"category": "배선/커넥터/부자재", "image": "STINGERAIRVENT2", "price": 95000},

    # 완제품 세트
    "RGB 스피커 2개 1SET": {"category": "완제품 세트", "image": "speaker", "price": 55000},
    "무빙 스피커 2개 1SET": {"category": "완제품 세트", "image": "speaker", "price": 66000},
    "RGB 풋등 1열 (2개)": {"category": "완제품 세트", "image": "rgbfoot", "price": 15000},
    "RGB 풋등 2열 (2개)": {"category": "완제품 세트", "image": "rgbfoot2", "price": 20000},
    "무빙 풋등 1열 (2개)": {"category": "완제품 세트", "image": "movingfoot1", "price": 15000},
    "무빙 풋등 2열 (2개)": {"category": "완제품 세트", "image": "movingfoot2", "price": 20000},
}

# -------------------- 파생: 카테고리 목록 / 카테고리별 품목명 --------------------
# 고정 탭 순서:
TAB_ORDER = [
    "모듈 (세트,단품)",
    "LED (RGB/무빙)",
    "아크릴 & 몰딩",
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

    to_add = []
    if item in set_rules:
        for s in set_rules[item]:
            name = s.replace(" 4개", "").replace(" 2개", "").strip()
            count = 4 if "4개" in s else (2 if "2개" in s else 1)
            to_add.append((name, qty * count))
    else:
        key = item.replace("(품절)", "").strip()
        to_add.append((key, qty))

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
    if not dealer or not phone or not addr:
        messagebox.showwarning("오류", "업체명, 전화번호, 주소 모두 입력하세요.")
        return
    if not cart_tree.get_children():
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

    tg_lines = [
        "📦 신규 발주 접수", "",
        f"🏪 업체명: {dealer}",
        f"📞 전화번호: {phone}",
        f"📍 주소: {addr}", "",
        "🛒 주문 품목:",
        *order_lines, "",
        f"총액: {format_won(total)}",
        f"VAT(10%): {format_won(total_vat)}",
        f"합계: {format_won(grand_total)}",
    ]
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

    # 파일 저장(상세)
    save_lines = [
        "발주 상세", "",
        f"업체명: {dealer}",
        f"전화번호: {phone}",
        f"주소: {addr}", "",
        "품목 | 수량 | 단가 | 금액 | VAT | 합계"
    ]
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
    update_totals()

def open_item_image(event):
    sel = cart_tree.selection()
    if not sel:
        return
    name = cart_tree.item(sel[0], "values")[0]
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
root.geometry("900x860")
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


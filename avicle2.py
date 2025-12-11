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

# -------------------- 이미지 매핑 --------------------
item_images = {
    "RGB 110cm": "rgb110",
    "RGB 90cm": "rgb90",
    "무빙 110cm": "moving110",
    "무빙 90cm": "moving90",
    "순정연동 RGB 모듈 1개 세트": "rgb110.jpg",
    "순정연동 SE 모듈 1개 세트": "se",
    "순정연동 V4 모듈 1개 세트": "rgb110.jpg",
    "RGB 블루투스 모듈(하우동)": "haodeng",
    "유니버셜 se 모듈 1개 세트": "seset",
    "순정연동 블루투스 모듈 1개 단품": "uni",
    "순정연동 RGB 모듈 1개 단품": "rgbb",
    "순정연동 SE 모듈 1개 단품": "see",
    "무빙 50cm": "moving50",
    "무빙 30cm": "moving30",
    "무빙 15cm": "led",
    "스피커 아크릴 (1열) 2PCS": "tmvlzj",
    "(토레스)스피커 아크릴 (1열) 2PCS": "xhfptm",
    "RGB 풋등 아크릴 1대분 4PCS": "foot",
    "무빙 풋등 아크릴 1대분 4PCS": "foot",
    "다이얼 아크릴 MQ4(페리),K8(페리),KA4페리": "ekdldjf",
    "다이얼 아크릴 NQ5": "ekdldjf",
    "다이얼 아크릴 구형 KA4": "ekdldjf",
    "다이얼 아크릴 DL3(페리)": "ekdldjf",
    "컵홀더 (날개)(LED없음)": "cupwing",
    "4P 커넥터 100PCS (암,숫)": "4pconnet",
    "하네스 핀 KET 암,숫 100PCS": "ket",
    "하네스 핀 AMP 암,숫 100PCS": "ket",
    "Y자 커넥터 1PCS": "4pY",
    "전원케이블": "MAINPOWER",
    "음악반응 스위치": "MUSICBUTTON",
    "3m 양면 테이프(회색)": "3M",
    "반사 테이프": "bansa",
    "아크릴 전용 3M 수광 테이프(투명) 5mm": "SOOKWANG",
    "아크릴 전용 3M 수광 테이프(투명) 3mm": "SOOKWANG",
    "풋등 RGB 롤바": "RGBRALL",
    "풋등 무빙 롤바": "MOVINGRALL",
    "RGB 단발 LED": "RGBONESHOT",
    "핸들 리모컨 5.1K 저항": "5.1K",
    "퓨즈 10A": "FUSE10A",
    "벤풍구 1열 (스팅어)": "STINGERAIRVENT1",
    "벤풍구 2열 (스팅어)": "STINGERAIRVENT2",
    "RGB 스피커 2개 1SET": "speaker",
    "무빙 스피커 2개 1SET": "speaker",
    "RGB 풋등 1열 (2개)": "rgbfoot",
    "RGB 풋등 2열 (2개)": "rgbfoot2",
    "무빙 풋등 1열 (2개)": "movingfoot1",
    "무빙 풋등 2열 (2개)": "movingfoot2",
}

# -------------------- 단가표 --------------------
item_price = {
    "RGB 110cm": 30000,
    "RGB 90cm": 27000,
    "무빙 110cm": 40000,
    "무빙 90cm": 34000,
    "순정연동 RGB 모듈 1개 세트": 198000,
    "순정연동 SE 모듈 1개 세트": 309000,
    "순정연동 V4 모듈 1개 세트": 0,  # 미등록가 → 0
    "RGB 블루투스 모듈(하우동)": 20000,
    "유니버셜 se 모듈 1개 세트": 369000,
    "순정연동 블루투스 모듈 1개 단품": 55000,
    "순정연동 RGB 모듈 1개 단품": 65000,
    "순정연동 SE 모듈 1개 단품": 150000,
    "유니버셜 se 모듈 1개 단품": 200000,
    "무빙 50cm": 20000,
    "무빙 30cm": 16500,
    "무빙 15cm": 12000,
    "스피커 아크릴 (1열) 2PCS": 15000,
    "(토레스)스피커 아크릴 (1열) 2PCS": 14000,
    "RGB 풋등 아크릴 1대분 4PCS": 1650,
    "무빙 풋등 아크릴 1대분 4PCS": 2400,
    "다이얼 아크릴 MQ4(페리),K8(페리),KA4페리": 15000,
    "다이얼 아크릴 NQ5": 15000,
    "다이얼 아크릴 구형 KA4": 15000,
    "다이얼 아크릴 DL3(페리)": 15000,
    "컵홀더 (날개)(LED없음)": 35000,
    "4P 커넥터 100PCS (암,숫)": 35000,
    "하네스 핀 KET 암,숫 100PCS": 60000,
    "하네스 핀 AMP 암,숫 100PCS": 120000,
    "Y자 커넥터 1PCS": 3000,
    "전원케이블": 35000,
    "음악반응 스위치": 15000,
    "3m 양면 테이프(회색)": 38000,
    "반사 테이프": 22000,
    "아크릴 전용 3M 수광 테이프(투명) 5mm": 2000,
    "아크릴 전용 3M 수광 테이프(투명) 3mm": 1500,
    "풋등 RGB 롤바": 28000,
    "풋등 무빙 롤바": 44000,
    "RGB 단발 LED": 10000,
    "핸들 리모컨 5.1K 저항": 1000,
    "퓨즈 10A": 2000,
    "벤풍구 1열 (스팅어)": 130000,
    "벤풍구 2열 (스팅어)": 95000,
    "RGB 스피커 2개 1SET": 55000,
    "무빙 스피커 2개 1SET": 66000,
    "RGB 풋등 1열 (2개)": 15000,
    "RGB 풋등 2열 (2개)": 20000,
    "무빙 풋등 1열 (2개)": 15000,
    "무빙 풋등 2열 (2개)": 20000,
    # 누락 가능 항목 예: "카식스 무빙 블루투스 모듈" 등은 아래에서 자동 0 등록
}

# -------------------- 카테고리/세트/품목 --------------------
main_categories = [
    "모듈 (세트,단품)",
    "LED (RGB/무빙)",
    "아크릴 & 몰딩",
    "컵홀더 윙",
    "배선/커넥터/부자재",
    "완제품 세트"
]

set_rules = {
    "순정연동 RGB 모듈 1개 세트": ["순정연동 RGB 모듈 1개 단품", "RGB 110cm", "RGB 90cm 4개"],
    "순정연동 SE 모듈 1개 세트": ["순정연동 SE 모듈 1개 단품", "무빙 110cm", "무빙 90cm 4개"],
    "유니버셜 se 모듈 1개 세트": ["순정연동 SE 모듈 1개 단품", "순정연동 블루투스 모듈 1개 단품", "무빙 110cm", "무빙 90cm 4개"],
}

items = {
    "모듈 (세트,단품)": [
        "RGB 블루투스 모듈(하우동)",
        "순정연동 RGB 모듈 1개 세트",
        "순정연동 SE 모듈 1개 세트",
        "유니버셜 se 모듈 1개 세트",
        "순정연동 블루투스 모듈 1개 단품",
        "순정연동 RGB 모듈 1개 단품",
        "순정연동 SE 모듈 1개 단품",
        "카식스 무빙 블루투스 모듈",
    ],
    "LED (RGB/무빙)": [
        "RGB 110cm", "RGB 90cm", "무빙 110cm", "무빙 90cm", "무빙 50cm", "무빙 30cm", "무빙 15cm(품절)"
    ],
    "아크릴 & 몰딩": [
        "스피커 아크릴 (1열) 2PCS",
        "(토레스)스피커 아크릴 (1열) 2PCS",
        "RGB 풋등 아크릴 1대분 4PCS",
        "무빙 풋등 아크릴 1대분 4PCS",
        "다이얼 아크릴 MQ4(페리),K8(페리),KA4페리",
        "다이얼 아크릴 NQ5",
        "다이얼 아크릴 구형 KA4",
        "다이얼 아크릴 DL3(페리)",
    ],
    "컵홀더 윙": ["컵홀더 (날개)(LED없음)"],
    "배선/커넥터/부자재": [
        "4P 커넥터 100PCS (암,숫)",
        "하네스 핀 KET 암,숫 100PCS",
        "하네스 핀 AMP 암,숫 100PCS",
        "Y자 커넥터 1PCS",
        "전원케이블",
        "음악반응 스위치",
        "3m 양면 테이프(회색)",
        "반사 테이프",
        "아크릴 전용 3M 수광 테이프(투명) 5mm",
        "아크릴 전용 3M 수광 테이프(투명) 3mm",
        "풋등 RGB 롤바",
        "풋등 무빙 롤바",
        "RGB 단발 LED",
        "핸들 리모컨 5.1K 저항",
        "퓨즈 10A",
        "벤풍구 1열 (스팅어)",
        "벤풍구 2열 (스팅어)",
    ],
    "완제품 세트": [
        "RGB 풋등 1열 (2개)",
        "RGB 풋등 2열 (2개)",
        "무빙 풋등 1열 (2개)",
        "무빙 풋등 2열 (2개)",
        "RGB 스피커 2개 1SET",
        "무빙 스피커 2개 1SET",
    ],
}

# -------------------- 가격 누락 자동 보완 --------------------
def _all_item_names():
    names = set()
    for cat, lst in items.items():
        for n in lst:
            # 품절 표기 제거용 매핑(가격키와 다르면 정규화)
            if n.endswith("(품절)"):
                base = n.replace("(품절)", "").strip()
                names.add(base)
            names.add(n)
    for k, lst in set_rules.items():
        names.add(k)
        for s in lst:
            base = s.replace(" 4개", "").replace(" 2개", "").strip()
            names.add(base)
    return names

ALL_ITEM_NAMES = _all_item_names()
# 누락 키 0원으로 등록(계산은 그대로 진행)
for n in ALL_ITEM_NAMES:
    # "무빙 15cm(품절)"는 "무빙 15cm" 가격 사용
    key = n.replace("(품절)", "").strip()
    if key not in item_price:
        item_price[key] = 0  # 미등록가는 0으로
        # 콘솔 안내(조용히): print(f"[INFO] 가격 미등록 → 0원 처리: {key}")

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
def find_image_file(filename):
    base = os.path.splitext(filename)[0]
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
            name = s.replace(" 4개", "").strip()
            count = 4 if "4개" in s else 1
            to_add.append((name, qty * count))
    else:
        # 품절 표기 제거 후 가격 조회
        key = item.replace("(품절)", "").strip()
        to_add.append((key, qty))

    for name, add_qty in to_add:
        unit_price = int(item_price.get(name, 0))
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
    # 유지(카트 더블클릭 → 원본 이미지 열기)
    sel = cart_tree.selection()
    if not sel:
        return
    name = cart_tree.item(sel[0], "values")[0]
    filename = item_images.get(name)
    if not filename:
        messagebox.showinfo("이미지 없음", "이미지가 없습니다.")
        return
    filepath = find_image_file(filename)
    if not filepath:
        messagebox.showinfo("이미지 없음", "이미지 파일을 찾을 수 없습니다.")
        return
    try:
        os.startfile(filepath)
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

import tkinter as tk
from tkinter import ttk, messagebox
import sys, os, time, datetime, requests, configparser, json


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# =========================🔹 설정 및 기본 데이터 ========================= #

CONFIG_FILE = "config.ini"

# 🔹 텔레그램 정보
TOKEN = "7895331234:AAG9ge6GGBg0plHb7axWcwSwIgSNG9gWvuY"
CHAT_ID = "-1003315436286"

# 🔹 GitHub JSON (raw) URL
DATA_URL = "https://raw.githubusercontent.com/xorud8726-ship-it/AVICLE/main/data.json"


# 🔹 JSON 데이터 로드
def load_data_from_json():
    try:
        r = requests.get(DATA_URL, timeout=5)
        r.raise_for_status()
        return json.loads(r.text)
    except Exception as e:
        messagebox.showerror("데이터 로드 오류", f"data.json을 불러오지 못했습니다.\n{e}")
        sys.exit(1)


# JSON에서 항목/딜러/카테고리/세트 규칙 로드
_data = load_data_from_json()

item_images = _data["item_images"]
dealers = _data["dealers"]
main_categories = _data["main_categories"]
set_rules = _data["set_rules"]
items = _data["items"]

cart = []


# =========================🔹 저장된 창 위치 불러오기 ========================= #
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


# =========================🔹 기능 함수 ========================= #

# 🔥🔥 자동 확장자 이미지 탐색 함수 🔥🔥
def find_image_file(filename):
    # 확장자 제거
    filename_without_ext = os.path.splitext(filename)[0]

    # avicle 폴더의 절대 경로 정확히 가져오기
    image_folder = resource_path(os.path.join("avicle"))

    # exe 실행 시 실제 폴더 존재 확인
    if not os.path.isdir(image_folder):
        print("이미지 폴더 없음:", image_folder)
        return None

    possible_ext = [".jpg", ".jpeg", ".png"]

    for ext in possible_ext:
        full_path = os.path.join(image_folder, filename_without_ext + ext)

        # 디버그 출력 (문제 추적)
        print("이미지 검사:", full_path)

        if os.path.exists(full_path):
            return full_path

    return None


def update_submenu(event):
    selected = main_combo.get()
    sub_combo["values"] = items.get(selected, [])
    sub_combo.set("세부 품목 선택")


def add_to_cart():
    item = sub_combo.get()
    if item == "세부 품목 선택":
        messagebox.showwarning("오류", "품목을 선택하세요.")
        return

    try:
        qty = int(qty_entry.get())
    except ValueError:
        messagebox.showwarning("오류", "수량은 숫자로 입력하세요.")
        return

    items_to_add = []
    if item in set_rules:
        for set_item in set_rules[item]:
            name = set_item.replace(" 4개", "").strip()
            count = 4 if "4개" in set_item else 1
            items_to_add.append((name, qty * count))
    else:
        items_to_add.append((item, qty))

    for name, add_qty in items_to_add:
        for child in cart_tree.get_children():
            tree_name, tree_qty = cart_tree.item(child, "values")
            if tree_name == name:
                new_qty = int(tree_qty) + add_qty
                cart_tree.item(child, values=(name, new_qty))
                break
        else:
            cart_tree.insert("", tk.END, values=(name, add_qty))


def remove_from_cart():
    selected = cart_tree.selection()
    if not selected:
        messagebox.showwarning("오류", "삭제할 항목을 선택하세요.")
        return
    for item_id in selected:
        cart_tree.delete(item_id)


def save_order_to_txt(order_list):
    # 현재 작업 디렉토리 기준 (PY/EXE 모두 안전)
    save_dir = os.path.join(os.getcwd(), "발주기록")
    os.makedirs(save_dir, exist_ok=True)

    # 파일명에 날짜 + 시간 + 마이크로초 포함
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    filename = f"{timestamp}_발주내역.txt"
    filepath = os.path.join(save_dir, filename)

    # 발주 내용 저장
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(order_list))

    print("발주 기록 저장:", filepath)


def submit_order():
    dealer = dealer_combo.get()
    if not dealer:
        messagebox.showwarning("오류", "협력사를 선택하세요.")
        return

    if not cart_tree.get_children():
        messagebox.showwarning("오류", "장바구니가 비어 있습니다.")
        return

    info = dealers[dealer]

    order_list = []
    order_list_msg = ""
    for item in cart_tree.get_children():
        name, qty = cart_tree.item(item, "values")
        order_list.append(f"{name} ({qty}개)")
        order_list_msg += f"{name} ({qty}개)\n"

    msg = (
        f"📦 신규 발주 접수\n\n"
        f"🏪 협력사: {dealer}\n"
        f"📞 연락처: {info['phone']}\n"
        f"📍 주소: {info['addr']}\n\n"
        f"🛒 주문 품목:\n{order_list_msg}"
    )

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                data={"chat_id": CHAT_ID, "text": msg},
                timeout=10,
            )
            break  # 성공하면 루프 종료
        except requests.RequestException as e:
            if attempt == max_attempts:
                messagebox.showerror("전송 실패", f"텔레그램 전송이 실패했습니다.\n{e}")
                return
            else:
                time.sleep(2)  # 실패 시 2초 대기 후 재시도

    messagebox.showinfo("완료", "발주가 정상적으로 전송되었습니다.")

    save_order_to_txt(order_list)

    cart_tree.delete(*cart_tree.get_children())


# 🔥🔥 새로운 기능: 더블 클릭 → 이미지 실행 🔥🔥
def open_item_image(event):
    selected_item = cart_tree.selection()
    if not selected_item:
        return

    name, _ = cart_tree.item(selected_item[0], "values")

    if name not in item_images:
        messagebox.showinfo("이미지 없음", "이미지가 없습니다.")
        return

    filename = item_images[name]
    filepath = find_image_file(filename)  # 🔥 자동확장자 + avicle 폴더 검색

    if filepath is None:
        messagebox.showinfo("이미지 없음", "이미지가 없습니다.")
        return

    try:
        os.startfile(filepath)
    except Exception as e:
        messagebox.showerror("오류", f"이미지를 열 수 없습니다.\n{e}")


def show_notice():
    notice_text = (
        "📌 택배사 [한진택배]\n"
        "- 아크릴 LED 제품\n"
        "- 12시 이전 발주\n"
        "- 14시 이전 입금확인건\n"
        "- 당일 발송됩니다.\n"
        "- 완제품인 경우 1~2일 이후\n"
        "- 발송 될수 있습니다\n\n"
    )

    notice_win = tk.Toplevel(root)
    notice_win.title("📌 필독 안내")
    notice_win.geometry("550x420")

    root.update()
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    root_w = root.winfo_width()
    root_h = root.winfo_height()

    notice_w = 550
    notice_h = 420

    pos_x = root_x + (root_w // 2) - (notice_w // 2)
    pos_y = root_y + (root_h // 2) - (notice_h // 2)

    notice_win.geometry(f"{notice_w}x{notice_h}+{pos_x}+{pos_y}")
    notice_win.grab_set()

    tk.Label(
        notice_win,
        text=notice_text,
        font=("Helvetica", 12),
        justify="left",
        wraplength=520,
    ).pack(padx=10, pady=10)
    tk.Button(
        notice_win, text="확인", command=notice_win.destroy, font=("Helvetica", 12)
    ).pack(pady=10)


# =========================🔹 UI 구성 ========================= #

root = tk.Tk()
root.title("협력사 발주 프로그램")
root.geometry("700x700")
root.configure(bg="#f0f2f5")

saved_geo = load_window_position()
if saved_geo:
    root.geometry(saved_geo)

root.protocol("WM_DELETE_WINDOW", lambda: (save_window_position(), root.destroy()))

style = ttk.Style()
style.theme_use("clam")
style.configure("TLabel", font=("Helvetica", 13), background="#f0f2f5")
style.configure("TButton", font=("Helvetica", 12), padding=6)
style.configure("TCombobox", font=("Helvetica", 12))

dealer_frame = tk.Frame(root, bg="#f0f2f5", pady=10)
dealer_frame.pack(fill="x", padx=20)

ttk.Label(dealer_frame, text="협력사 선택").pack(side="left")
dealer_combo = ttk.Combobox(
    dealer_frame, values=list(dealers.keys()), width=50, state="readonly"
)
dealer_combo.pack(side="left", padx=10)

item_frame = tk.Frame(root, bg="#f0f2f5", pady=10)
item_frame.pack(fill="x", padx=20)

widgets = [
    ("카테고리 선택", ttk.Combobox(item_frame, values=main_categories, width=30, state="readonly")),
    ("세부 품목", ttk.Combobox(item_frame, width=30, state="readonly")),
    ("수량 입력", tk.Spinbox(item_frame, from_=1, to=1000, width=5, font=("Helvetica", 12))),
]

main_combo, sub_combo, qty_entry = [w[1] for w in widgets]
qty_entry.delete(0, "end")
qty_entry.insert(0, "1")

for i, (label, widget) in enumerate(widgets):
    ttk.Label(item_frame, text=label).grid(row=i, column=0, sticky="w", pady=5)
    widget.grid(row=i, column=1, padx=10, pady=5)

main_combo.bind("<<ComboboxSelected>>", update_submenu)
ttk.Button(item_frame, text="장바구니 추가", command=add_to_cart).grid(
    row=2, column=2, padx=10
)

cart_frame = tk.Frame(root, bg="#f0f2f5", pady=10)
cart_frame.pack(fill="both", expand=True, padx=20, pady=10)

ttk.Label(cart_frame, text="🛒 장바구니 목록").pack(anchor="w")

cart_tree = ttk.Treeview(
    cart_frame, columns=("품목", "수량"), show="headings", height=12
)
cart_tree.heading("품목", text="품목")
cart_tree.heading("수량", text="수량")
cart_tree.column("품목", width=400)
cart_tree.column("수량", width=100, anchor="center")
cart_tree.pack(fill="both", expand=True, pady=5)

# ---- 🔥 더블 클릭 이벤트 연결 ----
cart_tree.bind("<Double-1>", open_item_image)

btn_frame = tk.Frame(root, bg="#f0f2f5", pady=10)
btn_frame.pack(fill="x", padx=20)

ttk.Button(btn_frame, text="선택 항목 삭제", command=remove_from_cart).pack(side="left")
ttk.Button(btn_frame, text="📌 필독", command=show_notice).pack(side="left", padx=10)
ttk.Button(btn_frame, text="발주 보내기", command=submit_order).pack(side="right")

root.mainloop()

import tkinter as tk
from tkinter import ttk, messagebox
import sys, os, time, datetime, requests, configparser








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




item_images = {
    # 기존 항목
    "RGB 110cm": "led",
    "RGB 90cm": "led",
    "무빙 110cm": "led",
    "무빙 90cm": "led",
    "순정연동 RGB 모듈 1개 세트": "rgb110.jpg",
    "순정연동 SE 모듈 1개 세트": "rgb110.jpg",
    "순정연동 V4 모듈 1개 세트": "rgb110.jpg",




    # 모듈 (세트,단품)
    "RGB 블루투스 모듈(하우동)": "haodeng",
    "카식스 무빙 블루투스 모듈": "carsix",
    "유니버셜 se 모듈 1개 세트": "uni",
    "순정연동 블루투스 모듈 1개 단품": "uni",
    "순정연동 RGB 모듈 1개 단품": "rgb",
    "순정연동 SE 모듈 1개 단품": "se",
    "순정연동 V4 모듈 1개 단품": "v4",
    "유니버셜 se 모듈 1개 단품": "seset",




    # LED (RGB/무빙)
    "무빙 50cm": "led",
    "무빙 30cm": "led",
    "무빙 15cm": "led",
"무빙 90cm": "led",
"무빙 110cm": "led",
"RGB 90cm": "led",
"RGB 110cm": "led",






    # 아크릴 & 몰딩
    "스피커 아크릴 (1열) 2PCS": "tmvlzj",
    "(토레스)스피커 아크릴 (1열) 2PCS": "xhfptm",
    "RGB 풋등 아크릴 1대분 4PCS": "foot",
    "무빙 풋등 아크릴 1대분 4PCS": "foot",
    "다이얼 아크릴 MQ4(페리),K8(페리),KA4페리": "ekdldjf",
    "다이얼 아크릴 NQ5": "ekdldjf",
    "다이얼 아크릴 구형 KA4": "ekdldjf",
    "다이얼 아크릴 DL3(페리)": "ekdldjf",
    "스팅어 벤풍구 아크릴 1열": "Stinger1",
    "스팅어 벤풍구 아크릴 2열": "stinger2",




    # 컵홀더 윙
    "컵홀더 (날개)(LED없음)": "cupwing",




    # 배선/커넥터/부자재
    "4P 커넥터 100PCS (암,숫)": "4pconnet",
    "하네스 핀 KET 암,숫 100PCS": "ket",
    "하네스 핀 AMP 암,숫 100PCS": "ket",
    "Y자 커넥터 50PCS": "4pY",
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




    # 완제품 세트


    "RGB 스피커 2개 1SET": "speaker",
    "무빙 스피커 2개 1SET": "speaker",
    "쏘렌토MQ4 RGB 전면": "mq4center",
    "쏘렌토MQ4 무빙 전면": "mq4center",
    "신형팰리세이드 RGB 전면": "palisadedoor",
    "신형팰리세이드 무빙 전면": "thenewpalisade",
    "신형,구형 팰리세이드 RGB 도어": "palisadedoor",
    "신형,구형 팰리세이드 무빙 도어": "palisadedoor",
    "그랜져GN7 RGB 전면": "gn7center",
    "그랜져GN7 무빙 전면": "gn7center",
    "그랜져GN7 RGB 도어": "gn7door",
    "그랜져GN7 무빙 도어": "gn7door",
    "RGB 풋등 1열 (2개)": "rgbfoot",
    "RGB 풋등 2열 (2개)": "rgbfoot",
    "무빙 풋등 1열 (2개)": "movingfoot",
    "무빙 풋등 2열 (2개)": "movingfoot",
}








# 🔹 협력사 정보
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




# 🔹 카테고리 / 품목 / 세트 구성
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
    "순정연동 V4 모듈 1개 세트": ["순정연동 V4 모듈 1개 단품", "무빙 110cm", "무빙 90cm 4개"],
    "유니버셜 se 모듈 1개 세트": ["유니버셜 se 모듈 1개 단품", "에이비클 어플", "무빙 110cm", "무빙 90cm 4개"],
    "순정연동 V4 PRO 모듈 1개 세트": ["순정연동 V4 모듈 1개 단품", "무빙 110cm", "무빙 90cm 4개", "무빙 50CM 2개", "무빙 30CM 2개"],
    "순정연동 SE PRO 모듈 1개 세트": ["순정연동 V4 모듈 1개 단품", "무빙 110cm", "무빙 90cm 4개", "무빙 50CM 2개", "무빙 30CM 2개"],
}




items = {
    "모듈 (세트,단품)": [
        "RGB 블루투스 모듈(하우동)",
        "카식스 무빙 블루투스 모듈",
        "순정연동 RGB 모듈 1개 세트",
        "순정연동 SE 모듈 1개 세트",
        "순정연동 V4 모듈 1개 세트",
        "유니버셜 se 모듈 1개 세트",
        "순정연동 블루투스 모듈 1개 단품",
        "순정연동 RGB 모듈 1개 단품",
        "순정연동 SE 모듈 1개 단품",
        "순정연동 V4 모듈 1개 단품",
        "유니버셜 se 모듈 1개 단품",
    ],
    "LED (RGB/무빙)": ["RGB 110cm", "RGB 90cm", "무빙 110cm", "무빙 90cm", "무빙 50cm", "무빙 30cm", "무빙 15cm(품절)"],
    "아크릴 & 몰딩": [
        "스피커 아크릴 (1열) 2PCS",
        "(토레스)스피커 아크릴 (1열) 2PCS",
        "RGB 풋등 아크릴 1대분 4PCS",
        "무빙 풋등 아크릴 1대분 4PCS",
        "다이얼 아크릴 MQ4(페리),K8(페리),KA4페리",
        "다이얼 아크릴 NQ5",
        "다이얼 아크릴 구형 KA4",
        "다이얼 아크릴 DL3(페리)",
        "스팅어 벤풍구 아크릴 1열",
        "스팅어 벤풍구 아크릴 2열",
    ],
    "컵홀더 윙": ["컵홀더 (날개)(LED없음)"],
    "배선/커넥터/부자재": [
        "4P 커넥터 100PCS (암,숫)",
        "하네스 핀 KET 암,숫 100PCS",
        "하네스 핀 AMP 암,숫 100PCS",
        "Y자 커넥터 50PCS",
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
        "쏘렌토MQ4 RGB 전면",
        "쏘렌토MQ4 무빙 전면",
        "신형팰리세이드 RGB 전면",
        "신형팰리세이드 무빙 전면",
        "신형,구형 팰리세이드 RGB 도어",
        "신형,구형 팰리세이드 무빙 도어",
        "그랜져GN7 RGB 전면",
        "그랜져GN7 무빙 전면",
        "그랜져GN7 RGB 도어",
        "그랜져GN7 무빙 도어",
    ],
}






cart = []




# =========================🔹 저장된 창 위치 불러오기 ========================= #87 =
def load_window_position():
    if not os.path.exists(CONFIG_FILE):
        return None
    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_FILE)   # ← 여기 수정됨!
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


# =========================🔹 기능 함수 ========================= #




# 🔥🔥 자동 확장자 이미지 탐색 함수 추가 🔥🔥
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
    sub_combo['values'] = items.get(selected, [])
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
                timeout=10
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
    filepath = find_image_file(filename)   # 🔥 자동확장자 + avicle 폴더 검색


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




    tk.Label(notice_win, text=notice_text, font=("Helvetica", 12), justify="left", wraplength=520).pack(padx=10, pady=10)
    tk.Button(notice_win, text="확인", command=notice_win.destroy, font=("Helvetica", 12)).pack(pady=10)




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
dealer_combo = ttk.Combobox(dealer_frame, values=list(dealers.keys()), width=50, state="readonly")
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
ttk.Button(item_frame, text="장바구니 추가", command=add_to_cart).grid(row=2, column=2, padx=10)




cart_frame = tk.Frame(root, bg="#f0f2f5", pady=10)
cart_frame.pack(fill="both", expand=True, padx=20, pady=10)




ttk.Label(cart_frame, text="🛒 장바구니 목록").pack(anchor="w")




cart_tree = ttk.Treeview(cart_frame, columns=("품목", "수량"), show="headings", height=12)
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













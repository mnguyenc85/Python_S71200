'''
Đọc kết nối từ đầu cân TDA 08B
'''

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import time

class DeviceControlApp(tk.Tk):
    def __init__(self):
        # Khởi tạo cửa sổ chính (window)
        super().__init__()
        self.title("Đọc đầu cân TDA 08B")
        
        # Biến trạng thái
        self.status_var = tk.StringVar(value="Trạng thái: Chưa kết nối")
        self.connect_time_var = tk.StringVar(value="Thời gian kết nối: N/A")
        
        # Gọi phương thức để xây dựng giao diện người dùng
        self._create_widgets()

    def _create_widgets(self):
        """
        Phương thức tạo và bố trí tất cả các thành phần (widgets) của giao diện.
        """
        # Thiết lập kiểu dáng
        style = ttk.Style(self)
        style.theme_use('clam')

        # --- Hàng 1: IP, Port, Connect ---
        frame_row1 = ttk.Frame(self, padding="10")
        frame_row1.grid(row=0, column=0, sticky="ew")

        # IP
        ttk.Label(frame_row1, text="IP:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.ip_entry = ttk.Entry(frame_row1, width=15)
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5)
        self.ip_entry.insert(0, "192.168.0.3")

        # Port
        ttk.Label(frame_row1, text="Port:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.port_entry = ttk.Entry(frame_row1, width=10)
        self.port_entry.grid(row=0, column=3, padx=5, pady=5)
        self.port_entry.insert(0, "8010")

        # Nút Connect
        self.connect_button = ttk.Button(
            frame_row1, 
            text="Connect", 
            command=self.connect_device, # Gọi phương thức của Class
            width=15
        )
        self.connect_button.grid(row=0, column=4, padx=15, pady=5)
        frame_row1.columnconfigure(4, weight=1) # Đảm bảo nút Connect co dãn

        # --- Hàng 2: Text KL, Read ---
        frame_row2 = ttk.Frame(self, padding="10 10 10 0")
        frame_row2.grid(row=1, column=0, sticky="ew")

        # Text KL
        ttk.Label(frame_row2, text="Text KL:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.text_kl_entry = ttk.Label(frame_row2, width=30)
        self.text_kl_entry.grid(row=0, column=1, padx=5, pady=5)

        # Nút Read
        ttk.Button(
            frame_row2, 
            text="Read", 
            command=self.read_data, # Gọi phương thức của Class
            width=15
        ).grid(row=0, column=2, padx=15, pady=5)
        frame_row2.columnconfigure(1, weight=1)

        # --- Khu vực Trạng thái ---
        frame_status = ttk.Frame(self, padding="10 0 10 10")
        frame_status.grid(row=2, column=0, sticky="ew")

        # Label Trạng thái
        ttk.Label(
            frame_status, 
            textvariable=self.status_var, 
            font=('Arial', 10, 'bold')
        ).grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Label Thời gian kết nối
        ttk.Label(
            frame_status, 
            textvariable=self.connect_time_var, 
            font=('Arial', 10)
        ).grid(row=1, column=0, padx=5, pady=5, sticky="w")

        frame_status.columnconfigure(0, weight=1)

        # Đảm bảo cửa sổ chính co dãn theo chiều ngang
        self.grid_columnconfigure(0, weight=1)


    ## 🛠️ Phương thức xử lý sự kiện
    def connect_device(self):
        """Xử lý sự kiện Connect/Ngắt kết nối."""
        
        # Nếu đang ở trạng thái 'Ngắt kết nối', gọi hàm ngắt và thoát
        if self.connect_button['text'] == "Ngắt kết nối":
            self._disconnect_device()
            return

        # Lấy giá trị IP và Port
        ip = self.ip_entry.get()
        port = self.port_entry.get()
        
        if not ip or not port:
            self.status_var.set("Trạng thái: ⚠️ Chưa nhập IP/Port")
            self.connect_time_var.set("Thời gian kết nối: N/A")
            return

        print(f"Đang cố gắng kết nối tới {ip}:{port}...")
        
        # --- Mô phỏng quá trình kết nối thực tế ---
        # Bạn sẽ thay thế phần này bằng thư viện socket (ví dụ: client_socket.connect((ip, port)))
        time.sleep(0.5) 
        is_connected = True 

        if is_connected:
            current_time = datetime.now().strftime("%H:%M:%S")
            self.status_var.set("Trạng thái: ✅ Đã kết nối")
            self.connect_time_var.set(f"Thời gian kết nối: {current_time}")
            self.connect_button.config(text="Ngắt kết nối", command=self.connect_device)
            print("Kết nối thành công.")
        else:
            self.status_var.set("Trạng thái: ❌ Kết nối thất bại")
            self.connect_time_var.set("Thời gian kết nối: N/A")
            print("Kết nối thất bại.")
    
    def _disconnect_device(self):
        """Phương thức nội bộ để ngắt kết nối."""
        print("Đang ngắt kết nối...")
        self.status_var.set("Trạng thái: 🛑 Đã ngắt kết nối")
        self.connect_time_var.set("Thời gian kết nối: N/A")
        self.connect_button.config(text="Connect", command=self.connect_device)
        print("Ngắt kết nối thành công.")


    def read_data(self):
        """Xử lý sự kiện Đọc dữ liệu."""
        text_kl = self.text_kl_entry.get()
        
        # Kiểm tra trạng thái kết nối
        if "Đã kết nối" in self.status_var.get():
            print(f"Đang đọc dữ liệu với lệnh: {text_kl}")
            # Thêm logic gửi lệnh/đọc dữ liệu qua socket ở đây
            self.status_var.set(f"Trạng thái: ⚙️ Đã gửi lệnh '{text_kl}'")
        else:
            print("Không thể đọc. Chưa kết nối.")
            self.status_var.set("Trạng thái: ⚠️ Vui lòng kết nối trước")


# --- Khối chạy chương trình ---
if __name__ == "__main__":
    app = DeviceControlApp()
    app.mainloop()
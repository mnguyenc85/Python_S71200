'''
Đọc kết nối từ đầu cân TDA 08B
'''

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import time
import socket, crcmod

def crc16(data: bytes, sz: int):
    crc = 0xFFFF
    n = min(sz, len(data))
    for i in range(n):
        pos = data[i]
        crc ^= pos
        for _ in range(8):
            if crc & 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, "little")

class KetNoiTDA08B:
    def __init__(self):
        self.client :socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, ip, port):
        self.client.connect((ip, port))

    def disconnect(self):
        self.client.close()

    def readkl(self) -> float:
        # Modbus RTU frame: [addr][func][addr_hi][addr_lo][len_hi][len_lo][crc_lo][crc_hi]
        addr = 1
        func = 3
        len = 2
        len_hi = len >> 8
        len_lo = len % 256
        frame = bytes([addr, func, 0x00, 0x0b, len_hi, len_lo])
        frame += crc16(frame, 6)

        self.client.send(frame)

        resp = self.client.recv(1024)
        #crc = crc16(resp, 3 + len * 2)
        if resp[0] == addr and resp[1] == func:
            kl = resp[3] << 24 | resp[4] << 16 | resp[5] << 8 | resp[6]
            return kl / 1000.0

        return 0

ketnoi = KetNoiTDA08B()

class DeviceControlApp(tk.Tk):
    def __init__(self):
        # Khởi tạo cửa sổ chính (window)
        super().__init__()
        self.title("Đọc đầu cân TDA 08B")
        
        self.user_connected = 0
        # Biến trạng thái
        self.status_var = tk.StringVar(value="Trạng thái: Chưa kết nối")
        self.connect_time_var = tk.StringVar(value="Thời gian kết nối: N/A")
        self.status_kl = tk.StringVar(value="0")

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
        ttk.Label(frame_row2, text="KL:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.text_kl_entry = ttk.Label(
            frame_row2, 
            textvariable=self.status_kl, 
            width=30).grid(row=0, column=1, padx=5, pady=5)

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


    def connect_device(self):
        """Xử lý sự kiện Connect/Ngắt kết nối."""
        
        # Nếu đang ở trạng thái 'Ngắt kết nối', gọi hàm ngắt và thoát
        if self.connect_button['text'] == "Ngắt kết nối":
            self._disconnect_device()
            return

        # Lấy giá trị IP và Port
        ip = self.ip_entry.get()
        portStr = self.port_entry.get()
        port = int(portStr)
        
        if not ip or not port:
            self.status_var.set("Trạng thái: Chưa nhập IP/Port")
            self.connect_time_var.set("Thời gian kết nối: N/A")
            return

        print(f"Đang cố gắng kết nối tới {ip}:{port}...")
        
        try:
            ketnoi.connect(ip, port)

            self.status_var.set("Trạng thái: Đã kết nối")
            self.connect_button.config(text="Ngắt kết nối", command=self.connect_device)
            print("Kết nối thành công.")
            self.user_connected = 1
        except:
            self.status_var.set("Trạng thái: Kết nối thất bại")
            print("Kết nối thất bại.")
            self.user_connected = 0
    
    def _disconnect_device(self):
        try:
            ketnoi.disconnect()
            self.connect_button.config(text="Kết nối", command=self.connect_device)
            self.status_var.set("Trạng thái: Dừng kết nối")
            self.user_connected = 0
        except:
            print("Lỗi ngắt kết nối")
            self.user_connected = 0

    def read_data(self):
        if self.user_connected:
            conn_t0 = datetime.now()

            kl = ketnoi.readkl()
            self.status_kl.set(f"{kl:.3f}")

            et = (datetime.now() - conn_t0).microseconds / 1000.0;
            self.connect_time_var.set(f"Thời gian kết nối: {et:.3f} ms")

# --- Khối chạy chương trình ---
if __name__ == "__main__":
    app = DeviceControlApp()
    app.mainloop()
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Toplevel
import socket
import struct
import threading
import time
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import deque

# --- CẤU HÌNH HẰNG SỐ ---
G_CONST = 9.80665 # Gia tốc trọng trường chuẩn (g)

# --- HÀM TÍNH CRC16 (MODBUS) ---
def calculate_crc(data):
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for i in range(8):
            if (crc & 1) != 0:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, byteorder='little')

# --- QUẢN LÝ HIỆU CHUẨN (LƯU FILE JSON) ---
class CalibrationManager:
    def __init__(self, filename="calibration.json"):
        self.filename = filename
        self.offset = 0.0      # Điểm 0
        self.scale_factor = 1.0 # Hệ số tỉ lệ
        self.load_calibration()
    
    def load_calibration(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    self.offset = data.get("offset", 0.0)
                    self.scale_factor = data.get("scale_factor", 1.0)
            except: pass
    
    def save_calibration(self):
        with open(self.filename, 'w') as f:
            json.dump({"offset": self.offset, "scale_factor": self.scale_factor}, f)

    def apply(self, raw): 
        # Công thức: y = (x - offset) * scale
        return (raw - self.offset) * self.scale_factor

    def set_zero(self, raw): 
        self.offset = raw
        self.save_calibration()

    def set_span(self, raw, real_val):
        # scale = real / (raw - offset)
        if raw - self.offset != 0:
            self.scale_factor = real_val / (raw - self.offset)
            self.save_calibration()
            return True
        return False

# --- GIAO DIỆN CHÍNH ---
class TensileTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hệ thống Đo Kéo/Xé Vật Liệu (Universal Testing Machine)")
        self.root.geometry("1366x768")
        
        # --- LOGIC ---
        self.calib = CalibrationManager()
        self.sock = None
        self.is_running = False     # Trạng thái kết nối Modbus
        self.is_testing = False     # Trạng thái đang chạy phép thử
        
        # Dữ liệu
        self.data_raw = [] # [Time, Force_N, Disp_mm, Stress_MPa, Strain_Perc]
        self.start_time = None
        
        self.current_raw_kg = 0.0 # Giá trị thô từ thiết bị (chưa calib)
        self.latest_kg = 0.0      # Giá trị đã calib
        
        # Kết quả
        self.captured_modulus = {} 
        self.break_detected = False
        self.max_force = 0.0
        self.max_stress = 0.0
        self.force_tare_offset = 0.0

        self.setup_ui()
        self.update_plot_axis() # Vẽ đồ thị rỗng ban đầu

    def setup_ui(self):
        # SỬA LỖI 1: Dùng ttk.PanedWindow thay vì tk.PanedWindow
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # === PANEL TRÁI: CẤU HÌNH ===
        left_frame = ttk.Frame(main_pane, width=320)
        main_pane.add(left_frame, weight=0) # weight=0 cố định kích thước

        # 1. Kết nối
        grp_conn = ttk.LabelFrame(left_frame, text="1. Kết nối & Hiệu chuẩn")
        grp_conn.pack(fill=tk.X, padx=5, pady=5)
        
        f_conn = ttk.Frame(grp_conn)
        f_conn.pack(fill=tk.X)
        ttk.Label(f_conn, text="IP:").pack(side=tk.LEFT)
        self.ent_ip = ttk.Entry(f_conn, width=12); self.ent_ip.insert(0, "192.168.0.3"); self.ent_ip.pack(side=tk.LEFT, padx=2)
        ttk.Label(f_conn, text="Port:").pack(side=tk.LEFT)
        self.ent_port = ttk.Entry(f_conn, width=6); self.ent_port.insert(0, "8010"); self.ent_port.pack(side=tk.LEFT)
        
        self.btn_conn = ttk.Button(grp_conn, text="KẾT NỐI", command=self.toggle_connection)
        self.btn_conn.pack(fill=tk.X, pady=2)
        
        ttk.Button(grp_conn, text="⚙️ Hiệu chuẩn Cân (Calibration)", command=self.open_calib).pack(fill=tk.X, pady=2)

        # 2. Thông số mẫu
        grp_sample = ttk.LabelFrame(left_frame, text="2. Thông số Mẫu")
        grp_sample.pack(fill=tk.X, padx=5, pady=5)

        self.create_input_row(grp_sample, "Tên mẫu:", "ent_name", "Mẫu Test 01")
        
        ttk.Label(grp_sample, text="Loại thử:").pack(anchor="w")
        self.cbo_type = ttk.Combobox(grp_sample, values=["Kéo đứt (Tensile)", "Xé rách (Tear)"], state="readonly")
        self.cbo_type.current(0); self.cbo_type.pack(fill=tk.X, pady=2)

        self.create_input_row(grp_sample, "Chiều dày (mm):", "ent_thick", "2.0")
        self.create_input_row(grp_sample, "Chiều rộng (mm):", "ent_width", "6.0")
        self.create_input_row(grp_sample, "L0 (mm):", "ent_l0", "25.0")
        
        # 3. Thông số máy
        grp_machine = ttk.LabelFrame(left_frame, text="3. Điều kiện Thử")
        grp_machine.pack(fill=tk.X, padx=5, pady=5)
        
        self.create_input_row(grp_machine, "Tốc độ (mm/phút):", "ent_speed", "500")
        
        self.chk_autostop = tk.IntVar(value=1)
        ttk.Checkbutton(grp_machine, text="Tự dừng khi đứt mẫu", variable=self.chk_autostop).pack(anchor="w", pady=5)

        # 4. Điều khiển
        grp_ctrl = ttk.LabelFrame(left_frame, text="4. Điều khiển")
        grp_ctrl.pack(fill=tk.X, padx=5, pady=5)
        
        self.btn_start = ttk.Button(grp_ctrl, text="▶ BẮT ĐẦU (START)", command=self.start_test, state="disabled")
        self.btn_start.pack(fill=tk.X, pady=5, ipady=5)
        self.btn_stop = ttk.Button(grp_ctrl, text="⏹ DỪNG (STOP)", command=self.stop_test, state="disabled")
        self.btn_stop.pack(fill=tk.X, pady=2)
        
        self.btn_save = ttk.Button(grp_ctrl, text="💾 LƯU BÁO CÁO EXCEL", command=self.save_report, state="disabled")
        self.btn_save.pack(fill=tk.X, pady=5)
        
        # === PANEL GIỮA: ĐỒ THỊ ===
        center_frame = ttk.Frame(main_pane)
        main_pane.add(center_frame, weight=4) # weight=4 để ưu tiên mở rộng

        # Thanh công cụ đồ thị
        toolbar = ttk.Frame(center_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="Trục X:").pack(side=tk.LEFT)
        self.cbo_xaxis = ttk.Combobox(toolbar, values=["Thời gian (s)", "Biến dạng (%)", "Hành trình (mm)"], width=15, state="readonly")
        self.cbo_xaxis.current(1) # Default Strain
        self.cbo_xaxis.pack(side=tk.LEFT, padx=5)
        # SỬA LỖI 2: Bind đúng tên hàm update_plot_axis
        self.cbo_xaxis.bind("<<ComboboxSelected>>", self.update_plot_axis)
        
        ttk.Label(toolbar, text="Trục Y:").pack(side=tk.LEFT, padx=(10,0))
        self.cbo_yaxis = ttk.Combobox(toolbar, values=["Lực (N)", "Ứng suất (MPa)", "Khối lượng (kg)"], width=15, state="readonly")
        self.cbo_yaxis.current(1) # Default Stress
        self.cbo_yaxis.pack(side=tk.LEFT, padx=5)
        # SỬA LỖI 2: Bind đúng tên hàm update_plot_axis
        self.cbo_yaxis.bind("<<ComboboxSelected>>", self.update_plot_axis)

        # Matplotlib Area
        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.grid(True, linestyle='--', alpha=0.5)
        self.canvas = FigureCanvasTkAgg(self.fig, master=center_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # === PANEL PHẢI: KẾT QUẢ ===
        right_frame = ttk.Frame(main_pane, width=280)
        main_pane.add(right_frame, weight=0)

        grp_live = ttk.LabelFrame(right_frame, text="Live Monitor")
        grp_live.pack(fill=tk.X, padx=5, pady=5)
        
        self.lbl_force = self.create_result_row(grp_live, "Lực (N):", "0.00", "black")
        self.lbl_disp = self.create_result_row(grp_live, "Hành trình (mm):", "0.00", "black")
        self.lbl_stress = self.create_result_row(grp_live, "Ứng suất (MPa):", "0.00", "black")
        self.lbl_strain = self.create_result_row(grp_live, "Biến dạng (%):", "0.00", "black")

        grp_res = ttk.LabelFrame(right_frame, text="KẾT QUẢ")
        grp_res.pack(fill=tk.X, padx=5, pady=5)

        self.lbl_fmax = self.create_result_row(grp_res, "F_max (N):", "0.00", "red")
        self.lbl_smax = self.create_result_row(grp_res, "TS (MPa):", "0.00", "red")
        self.lbl_eb = self.create_result_row(grp_res, "Eb (%):", "0.00", "blue")
        
        ttk.Separator(grp_res, orient='horizontal').pack(fill='x', pady=5)
        self.lbl_m100 = self.create_result_row(grp_res, "Modulus 100%:", "---", "green")
        self.lbl_m200 = self.create_result_row(grp_res, "Modulus 200%:", "---", "green")
        self.lbl_m300 = self.create_result_row(grp_res, "Modulus 300%:", "---", "green")
        
        # Nhập tay điểm bất kỳ
        ttk.Label(grp_res, text="Check Ứng suất tại (%):").pack(pady=(10,0))
        self.ent_custom_x = ttk.Entry(grp_res, width=10); self.ent_custom_x.insert(0, "50")
        self.ent_custom_x.pack()
        self.lbl_custom_res = ttk.Label(grp_res, text="---", font=("Arial", 11, "bold"))
        self.lbl_custom_res.pack()

        self.lbl_area = self.create_result_row(grp_res, "Năng lượng (J/cm3):", "---", "purple")

    # --- HÀM UI HELPER ---
    def create_input_row(self, parent, label, var_name, default_val):
        ttk.Label(parent, text=label).pack(anchor="w")
        entry = ttk.Entry(parent)
        entry.insert(0, default_val)
        entry.pack(fill=tk.X, pady=(0, 5))
        setattr(self, var_name, entry)

    def create_result_row(self, parent, title, init_val, color):
        f = ttk.Frame(parent)
        f.pack(fill=tk.X, pady=2)
        ttk.Label(f, text=title).pack(side=tk.LEFT)
        lbl = ttk.Label(f, text=init_val, font=("Consolas", 11, "bold"), foreground=color)
        lbl.pack(side=tk.RIGHT)
        return lbl

    # --- KẾT NỐI MODBUS ---
    def toggle_connection(self):
        if not self.is_running:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(0.5)
                self.sock.connect((self.ent_ip.get(), int(self.ent_port.get())))
                self.is_running = True
                self.btn_conn.config(text="NGẮT KẾT NỐI", width=20)
                self.btn_start.config(state="normal")
                
                # Start Thread
                threading.Thread(target=self.polling_loop, daemon=True).start()
            except Exception as e: messagebox.showerror("Lỗi kết nối", str(e))
        else:
            self.is_running = False
            if self.sock: self.sock.close()
            self.btn_conn.config(text="KẾT NỐI")
            self.btn_start.config(state="disabled")

    # --- LOGIC TEST ---
    def start_test(self):
        try:
            self.test_speed = float(self.ent_speed.get())
            self.sample_w = float(self.ent_width.get())
            self.sample_t = float(self.ent_thick.get())
            self.sample_l0 = float(self.ent_l0.get())
            self.sample_area = self.sample_w * self.sample_t
            if self.sample_area <= 0: raise ValueError
        except:
            messagebox.showerror("Lỗi", "Kích thước mẫu không hợp lệ!")
            return

        self.data_raw = []
        self.captured_modulus = {"100": None, "200": None, "300": None, "Custom": None}
        self.max_force = 0.0
        self.max_stress = 0.0
        self.start_time = time.time()
        self.break_detected = False
        
        self.is_testing = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.btn_save.config(state="disabled")
        
        # Tare (Set 0 tương đối cho lần đo này)
        self.force_tare_offset = self.latest_kg * G_CONST

    def stop_test(self):
        self.is_testing = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.btn_save.config(state="normal")
        self.calculate_final_results()

    def polling_loop(self):
        # Frame đọc: Addr 1, Func 3, Reg 11, Len 2
        req = bytearray([1, 3, 0, 11, 0, 2])
        req += calculate_crc(req)
        
        while self.is_running:
            try:
                self.sock.sendall(req)
                res = self.sock.recv(1024)
                if len(res) > 5 and res[1] == 3:
                    raw_int = struct.unpack('>i', res[3:7])[0]
                    val_kg_raw = (raw_int / 100.0) # Chia 100 theo mặc định
                    
                    # Lưu giá trị thô để dùng cho Calib
                    self.current_raw_kg = val_kg_raw 
                    
                    # Áp dụng Calib
                    calib_kg = self.calib.apply(val_kg_raw)
                    self.latest_kg = calib_kg

                    if self.is_testing:
                        self.process_test_data(calib_kg)
                
                time.sleep(0.04) # ~25Hz
            except: time.sleep(0.1)

    def process_test_data(self, kg_val):
        t_elapsed = time.time() - self.start_time
        
        # 1. Tính Lực (N)
        force_n = (kg_val * G_CONST) - self.force_tare_offset
        if force_n < 0: force_n = 0
        
        # 2. Tính Biến dạng
        disp_mm = (self.test_speed / 60.0) * t_elapsed
        strain_pct = (disp_mm / self.sample_l0) * 100.0
        
        # 3. Tính Ứng suất
        test_type = self.cbo_type.get()
        if "Tensile" in test_type:
            stress_val = force_n / self.sample_area # MPa
        else:
            stress_val = force_n / self.sample_t # N/mm
            
        # 4. Lưu data
        row = [t_elapsed, force_n, disp_mm, stress_val, strain_pct]
        self.data_raw.append(row)
        
        # 5. Peak & Break
        if force_n > self.max_force: 
            self.max_force = force_n
            self.max_stress = stress_val
            
        if self.chk_autostop.get() == 1 and self.max_force > 5.0:
            # Nếu lực giảm quá 30% so với đỉnh -> Đứt
            if force_n < (self.max_force * 0.7):
                self.break_detected = True
                self.root.after(0, self.stop_test)

        # 6. Capture Modulus
        i_strain = int(strain_pct)
        for k in ["100", "200", "300"]:
            if i_strain == int(k) and self.captured_modulus[k] is None:
                self.captured_modulus[k] = stress_val
        
        try:
            cust = float(self.ent_custom_x.get())
            if strain_pct >= cust and self.captured_modulus["Custom"] is None:
                self.captured_modulus["Custom"] = stress_val
        except: pass

        # 7. Update UI (Throttle)
        if len(self.data_raw) % 5 == 0:
            self.root.after(0, lambda: self.update_live_ui(row))

    def update_live_ui(self, row):
        self.lbl_force.config(text=f"{row[1]:.2f}")
        self.lbl_disp.config(text=f"{row[2]:.2f}")
        self.lbl_stress.config(text=f"{row[3]:.2f}")
        self.lbl_strain.config(text=f"{row[4]:.1f}")
        
        self.lbl_fmax.config(text=f"{self.max_force:.2f}")
        self.lbl_smax.config(text=f"{self.max_stress:.2f}")
        
        for k, lbl in zip(["100", "200", "300"], [self.lbl_m100, self.lbl_m200, self.lbl_m300]):
            v = self.captured_modulus[k]
            if v: lbl.config(text=f"{v:.2f}")
            
        if self.captured_modulus["Custom"]:
            self.lbl_custom_res.config(text=f"{self.captured_modulus['Custom']:.2f} MPa")
            
        self.update_plot_axis()

    def update_plot_axis(self, event=None):
        if not self.data_raw: 
            self.ax.clear(); self.ax.grid(True); self.canvas.draw(); return
        
        arr = np.array(self.data_raw)
        # Cols: 0:T, 1:F, 2:D, 3:Stress, 4:Strain
        
        x_map = {"Thời gian (s)":0, "Biến dạng (%)":4, "Hành trình (mm)":2}
        y_map = {"Lực (N)":1, "Ứng suất (MPa)":3, "Khối lượng (kg)":-1}
        
        idx_x = x_map.get(self.cbo_xaxis.get(), 4)
        idx_y = y_map.get(self.cbo_yaxis.get(), 3)
        
        x_d = arr[:, idx_x]
        y_d = arr[:, idx_y] if idx_y != -1 else (arr[:, 1]/G_CONST)
        
        self.ax.clear()
        self.ax.plot(x_d, y_d, color='blue')
        self.ax.set_xlabel(self.cbo_xaxis.get())
        self.ax.set_ylabel(self.cbo_yaxis.get())
        self.ax.grid(True)
        self.canvas.draw()

    def calculate_final_results(self):
        if not self.data_raw: return
        arr = np.array(self.data_raw)
        
        eb = arr[-1, 4]
        self.lbl_eb.config(text=f"{eb:.1f}")
        
        # Tính Diện tích (J/cm3 = MJ/m3)
        # Area under Stress-Strain curve
        strain_dec = arr[:, 4] / 100.0
        stress_mpa = arr[:, 3]
        area = np.trapz(stress_mpa, strain_dec)
        self.lbl_area.config(text=f"{area:.3f}")
        
        messagebox.showinfo("Kết thúc", f"Đo xong!\nMax Stress: {self.max_stress:.2f} MPa\nEb: {eb:.1f} %")

    def save_report(self):
        if not self.data_raw: return
        fpath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if not fpath: return
        
        # Sheet 1
        info = {
            "Tham số": ["Tên mẫu", "Ngày", "Dày (mm)", "Rộng (mm)", "Tốc độ", "Loại"],
"Giá trị": [self.ent_name.get(), datetime.now().strftime("%Y-%m-%d"), 
                        self.sample_t, self.sample_w, self.test_speed, self.cbo_type.get()]
        }
        res = {
            "Kết quả": ["Fmax (N)", "TS (MPa)", "Eb (%)", "M100", "M300", "Energy"],
            "Giá trị": [self.max_force, self.max_stress, self.data_raw[-1][4],
                        self.captured_modulus['100'], self.captured_modulus['300'], self.lbl_area.cget("text")]
        }
        
        df_raw = pd.DataFrame(self.data_raw, columns=["Time", "Force", "Disp", "Stress", "Strain"])
        
        with pd.ExcelWriter(fpath) as writer:
            pd.DataFrame(info).to_excel(writer, sheet_name="Báo cáo", index=False, startrow=0)
            pd.DataFrame(res).to_excel(writer, sheet_name="Báo cáo", index=False, startrow=8)
            df_raw.to_excel(writer, sheet_name="Raw Data", index=False)
            
        messagebox.showinfo("OK", "Đã lưu báo cáo!")

    # --- CỬA SỔ HIỆU CHUẨN ---
    def open_calib(self):
        if not self.is_running:
            messagebox.showwarning("Lỗi", "Vui lòng kết nối trước!")
            return
            
        top = Toplevel(self.root)
        top.title("Hiệu chuẩn Cân")
        top.geometry("400x300")
        top.grab_set()
        
        lbl_cur = ttk.Label(top, text="---", font=("Consolas", 20, "bold"), foreground="blue")
        lbl_cur.pack(pady=10)
        
        # Update số liên tục
        def update_lbl():
            if top.winfo_exists():
                # Hiển thị số ĐÃ CALIB để người dùng đối chiếu
                lbl_cur.config(text=f"{self.latest_kg:.2f} kg")
                top.after(100, update_lbl)
        update_lbl()
        
        # Zero
        frm_z = ttk.LabelFrame(top, text="1. Lấy điểm 0 (Tare)")
        frm_z.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(frm_z, text="Set ZERO", command=lambda: [self.calib.set_zero(self.current_raw_kg), messagebox.showinfo("OK", "Đã set 0!")]).pack(fill=tk.X, padx=5, pady=5)
        
        # Span
        frm_s = ttk.LabelFrame(top, text="2. Hiệu chuẩn Tải")
        frm_s.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(frm_s, text="Đặt quả cân và nhập số kg:").pack()
        e_w = ttk.Entry(frm_s); e_w.pack(pady=2)
        
        def do_span():
            try:
                real = float(e_w.get())
                if self.calib.set_span(self.current_raw_kg, real):
                    messagebox.showinfo("OK", "Đã hiệu chuẩn xong!")
                else:
                    messagebox.showerror("Lỗi", "Giá trị raw trùng điểm 0!")
            except: pass
            
        ttk.Button(frm_s, text="Calibrate SPAN", command=do_span).pack(fill=tk.X, padx=5, pady=5)

if __name__ == "__main__":
    root = tk.Tk()
    app = TensileTestApp(root)
    root.mainloop()

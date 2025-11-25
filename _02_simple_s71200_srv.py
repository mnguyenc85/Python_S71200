'''
Mô phỏng PLC S7-1200: 3 vùng bộ nhớ
- Inputs: (2 bytes) = 16 Inputs
- Outputs (2 bytes) = 16 Outputs
- Memory (10 bytes)
- DB1 (10 bytes)
'''

from snap7.server import Server
from snap7.type import SrvArea
import ctypes
from datetime import datetime
import time

# Khai báo các vùng nhớ (Global) với kích thước theo PLC
PLC_IN = (ctypes.c_ubyte * 2)()
PLC_OUT = (ctypes.c_ubyte * 2)()
PLC_M = (ctypes.c_ubyte * 10)()
PLC_DB1 = (ctypes.c_ubyte * 10)()

class S71200Emu:
  def __init__(self):
    self.srv = Server()
    self.srv.set_events_callback(self.event_callback)
    self.last_delta = 0
    self.t0 = datetime.now()

    self.srv.register_area(SrvArea.PA, 0, PLC_OUT)
    self.srv.register_area(SrvArea.PE, 0, PLC_IN)
    self.srv.register_area(SrvArea.MK, 0, PLC_M)
    self.srv.register_area(SrvArea.DB, 1, PLC_DB1)

  def __del__(self):
    self.srv.destroy()

  def event_callback(self, event) -> None:
    """
    Callback để thông báo connect/disconnect
    Bỏ qua các event khác (read/write)
    """
    if event.EvtCode == 0x08:
      print(f"[{time.strftime('%H:%M:%S')}] Client CONNECTED from {event.EvtSender}")
    elif event.EvtCode == 0x80:
      print(f"[{time.strftime('%H:%M:%S')}] Client DISCONNECTED from {event.EvtSender}")
      print(f"   delta = {self.last_delta}")    

  def run(self):
    self.srv.start_to("0.0.0.0", 5102)
    print("Snap7 Server running at 0.0.0.0:5102... Press Ctrl+C to stop")

    try:
      while True:
        t = datetime.now()
        self.last_delta = (t - self.t0).total_seconds()
        self.t0 = t

        self.srv.pick_event()

        time.sleep(0.01)
    except Exception as e:
      if e: print("\nError: ", e)
      print("\nShutting down server...")
      self.srv.stop()


s7emu = S71200Emu()
s7emu.run()
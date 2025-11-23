'''
Các function để kết nối và đọc từ S7-1200
Thay đổi từ _01_read_s71200.py
'''

import sys
from snap7.client import Client
from snap7.type import Areas

def connect(ip, port, rack = 0, slot = 1):
  '''
  Kết nối S7-1200 và trả về client
  '''
  client = Client()
  client.connect(ip, rack, slot, port)
  if not client.get_connected():
    print(f"Could not connect to PLC at {ip} (rack={rack}, slot={slot})")
    return None
  return client

def disconnect(client):
  try:
    client.disconnect()
  except Exception:
    pass

def read_output(client, start_addr: int = 0, size: int = 2):
  '''
  Đọc dữ liệu đầu ra (outputs)
  '''
  try:
    # Output area: Areas.PE; db = 0
    buffer = client.read_area(Areas.PA, 0, start_addr, size)
    result_code = client.get_last_error()

    if result_code == 0:
      # Data successfully read, process the buffer
      return buffer
    else:
      print(f"Error reading output: {client.error_text(result_code)}")
  except Exception:
    pass

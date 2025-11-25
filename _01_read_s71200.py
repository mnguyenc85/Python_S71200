"""
Kết nối PLC S7-1200 và đọc dữ liệu (IO, M, DB1)
Kiểu kết nối đơn giản nhất: mở kết nối, đọc, đóng kết nối
"""
import sys
from snap7.client import Client
from snap7.type import Areas

def read_db(ip: str, port: int, db_number: int, start: int, size: int, rack = 0, slot = 1):
  '''
  Đọc dữ liệu từ 1 DB

  :param ip: địa chỉ ip của PLC
  :param port: địa chỉ cổng của PLC
  :param db_number: số db (theo chương trình PLC)
  :param start: địa chỉ bắt đầu đọc (byte trong db)
  :param size: số lượng byte đọc
  :param rack: số rack của PLC (theo cấu hình PLC)
  :param slot: số slot của PLC (theo cấu hình PLC)

  :return: mảng dữ liệu đọc được (byte[]) hoặc None nếu có lỗi
  '''
  client = Client()
  try:
    client.connect(ip, rack, slot, port)
    if not client.get_connected():
      raise ConnectionError(f"Could not connect to PLC at {ip} (rack={rack}, slot={slot})")
    data = client.db_read(db_number, start, size)
    return data
  finally:
    try:
      client.disconnect()
    except Exception:
      pass

def read_input(ip, port, start_addr: int = 0, size: int = 2, rack = 0, slot = 1):
  '''
  Đọc dữ liệu đầu vào (inputs)

  :param ip: địa chỉ ip của PLC
  :param port: địa chỉ cổng của PLC
  :param start: địa chỉ bắt đầu đọc (0 -> I0; 1 -> I1)
  :param size: số lượng byte đọc
  :param rack: số rack của PLC (theo cấu hình PLC)
  :param slot: số slot của PLC (theo cấu hình PLC)

  :return: mảng dữ liệu đọc được (byte[]) hoặc None nếu có lỗi
  '''
  client = Client()
  try:
    client.connect(ip, rack, slot, port)
    if not client.get_connected():
      raise ConnectionError(f"Could not connect to PLC at {ip} (rack={rack}, slot={slot})")
    
    # Input area: Areas.PE; db = 0
    buffer = client.read_area(Areas.PE, 0, start_addr, size)
    result_code = client.get_last_error()
    
    if result_code == 0:
        # Data successfully read, process the buffer
        return buffer
    else:
        print(f"Error reading input: {client.error_text(result_code)}")
  
  finally:
    try:
      client.disconnect()
    except Exception:
      pass

def read_output(ip, port, start_addr: int = 0, size: int = 2, rack = 0, slot = 1):
  '''
  Đọc dữ liệu đầu ra (outputs)

  :param ip: địa chỉ ip của PLC
  :param port: địa chỉ cổng của PLC
  :param start: địa chỉ bắt đầu đọc (0 -> Q0; 1 -> Q1)
  :param size: số lượng byte đọc
  :param rack: số rack của PLC (theo cấu hình PLC)
  :param slot: số slot của PLC (theo cấu hình PLC)

  :return: mảng dữ liệu đọc được (byte[]) hoặc None nếu có lỗi
  '''
  client = Client()
  try:
    client.connect(ip, rack, slot, port)
    if not client.get_connected():
      raise ConnectionError(f"Could not connect to PLC at {ip} (rack={rack}, slot={slot})")
    
    # Output area: Areas.PE; db = 0
    buffer = client.read_area(Areas.PA, 0, start_addr, size)
    result_code = client.get_last_error()

    if result_code == 0:
        # Data successfully read, process the buffer
        return buffer
    else:
        print(f"Error reading output: {client.error_text(result_code)}")
  
  finally:
    try:
      client.disconnect()
    except Exception:
      pass

def read_memory(ip, port, start_addr: int = 0, size: int = 2, rack = 0, slot = 1):
  '''
  Đọc dữ liệu từ vùng nhớ memory

  :param ip: địa chỉ ip của PLC
  :param port: địa chỉ cổng của PLC
  :param start_addr: địa chỉ bắt đầu đọc
  :param size: số lượng byte đọc
  :param rack: số rack của PLC (theo cấu hình PLC)
  :param slot: số slot của PLC (theo cấu hình PLC)

  :return: mảng dữ liệu đọc được (byte[]) hoặc None nếu có lỗi
  '''
  client = Client()
  try:
    client.connect(ip, rack, slot, port)
    if not client.get_connected():
      raise ConnectionError(f"Could not connect to PLC at {ip} (rack={rack}, slot={slot})")
    
    # Memory area: Areas.MK; db = 0
    buffer = client.read_area(Areas.MK, 0, start_addr, size)
    result_code = client.get_last_error()

    if result_code == 0:
        # Data successfully read, process the buffer
        return buffer
    else:
        print(f"Error reading memory: {client.error_text(result_code)}")
  
  finally:
    try:
      client.disconnect()
    except Exception:
      pass

def main():
  # địa chỉ mô phỏng: 127.0.0.1:5102
  
  ip = "192.168.0.2"
  port = 102
  db = 1
  start = 0
  size = 10

  try:
    data = read_db(ip, port, db, start, size)
  except Exception as e:
    print("Error:", e)
    sys.exit(2)

  print(f"Read {len(data)} bytes from DB{db} (start={start}):")
  print("Hex:", data.hex())
  print("Bytes:", list(data))

if __name__ == "__main__":
	main()
# Bloxorz Solver

Trò chơi xếp hình Bloxorz 3D viết bằng Python và Ursina. Project có 15 màn chơi, điều khiển bằng bàn phím và giao diện để chạy các thuật toán tìm kiếm.

## Yêu cầu

- Python 3.13
- Các thư viện trong `requirements.txt`

Project hiện nhắm tới Python 3.13; Python 3.14 chưa được hỗ trợ.

## Cài đặt và chạy

Mở terminal tại thư mục `source` (thư mục chứa `main.py`), sau đó làm theo hướng dẫn tương ứng với hệ điều hành và loại terminal của bạn. Các lệnh dưới đây tạo môi trường ảo, cài thư viện và chạy game.

### Windows PowerShell

Lệnh chạy game cuối cùng có thể dùng `python main.py` hoặc `py main.py`.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

### Windows Command Prompt (CMD)

Lệnh chạy game cuối cùng có thể dùng `python main.py` hoặc `py main.py`.

```bat
py -3.13 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python main.py
```

### macOS và Linux

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Nếu lệnh tạo môi trường ảo báo không tìm thấy Python 3.13, hãy cài Python 3.13 trước. Sau khi đã kích hoạt môi trường ảo, những lần chạy tiếp theo chỉ cần mở terminal tại thư mục `source`, kích hoạt lại môi trường theo hệ điều hành rồi chạy `python main.py`.

## Điều khiển

- **WASD** hoặc **phím mũi tên**: di chuyển khối
- **Space**: chuyển khối lập phương đang điều khiển sau khi khối bị tách
- **R**: chơi lại màn hiện tại
- **Esc** hoặc nút **LEVELS**: quay lại màn chọn level
- Các nút **BFS**, **DFS**, **UCS**, **A\***: chạy thuật toán giải
- **STOP**: dừng thuật toán đang chạy
- **RESTART**: chơi lại màn
- **RESULTS**: xem thống kê kết quả

Hiện tại BFS đã hoạt động. Các nút DFS, UCS và A* sẽ được mở khi những thuật toán đó hoàn thiện.

## Cấu trúc project

- `main.py`: điểm khởi chạy ứng dụng Ursina
- `core/`: bàn chơi, khối, trạng thái, luật di chuyển và bộ đọc level JSON
- `game/`: menu, điều khiển trò chơi, dựng hình, hoạt ảnh và phát lại nước đi
- `algorithms/`: các thuật toán BFS, DFS, UCS, A* và bộ đo hiệu năng
- `gui/`: giao diện dùng chung và bảng thống kê
- `levels/`: dữ liệu 15 màn chơi dạng JSON
- `assets/`: ảnh nền menu và màn chọn level

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

Cả BFS, DFS, UCS và A* đều đã được cài đặt và có thể chạy trong game.

## Chạy thực nghiệm các thuật toán

Mở terminal tại thư mục `source` và kích hoạt môi trường ảo đã tạo ở phần cài đặt. Script mặc định chạy BFS và DFS trên cả 15 level. Để tạo cả biểu đồ, cài Matplotlib rồi chạy:

```bash
python -m experiments.bfs_dfs_experiment
```

Kết quả mặc định được lưu trong `experiments/results/`, gồm CSV và biểu đồ PNG. Để chạy cả bốn thuật toán BFS, DFS, UCS và A* rồi lưu riêng vào `experiments/results_all/`, dùng:

```bash
python -m experiments.bfs_dfs_experiment --algos all --out experiments/results_all
```

Hai thư mục kết quả khác nhau ở các thuật toán được chạy:

- `experiments/results/`: BFS và DFS.
- `experiments/results_all/`: BFS, DFS, UCS và A*.

Một số tùy chọn khác:

```bash
# Đo mỗi cặp thuật toán/level 10 lần (mặc định là 5 lần)
python -m experiments.bfs_dfs_experiment --runs 10

# Chỉ xuất CSV, không vẽ biểu đồ (không cần Matplotlib)
python -m experiments.bfs_dfs_experiment --no-plot

# Chọn thuật toán và thư mục kết quả tùy ý
python -m experiments.bfs_dfs_experiment --algos BFS,UCS --out experiments/results_bfs_ucs
```

Các tên thuật toán hợp lệ là `BFS`, `DFS`, `UCS` và `A*`; phân cách nhiều tên bằng dấu phẩy. Khi không chỉ định `--out`, script ghi vào `experiments/results/`.

## Cấu trúc project

```text
source/
├── main.py                         # Điểm khởi chạy game
├── requirements.txt                # Thư viện cần cài
├── README.md                       # Hướng dẫn project
├── algorithms/                     # BFS, DFS, UCS, A* và mã dùng chung
├── assets/                          # Ảnh nền menu và màn chọn level
├── core/                            # Mô hình bàn chơi, trạng thái và luật di chuyển
├── experiments/
│   ├── bfs_dfs_experiment.py        # Chạy benchmark, xuất CSV và biểu đồ
│   ├── results/                     # Kết quả BFS/DFS
│   └── results_all/                 # Kết quả BFS/DFS/UCS/A*
├── game/                            # Menu, vòng chơi, hiển thị và phát lại nước đi
├── gui/                             # Chủ đề giao diện và bảng thống kê
└── levels/                          # Dữ liệu 15 màn chơi dạng JSON
```

`experiments/results/` và `experiments/results_all/` chứa các kết quả đã được lưu sẵn. Chạy lại script thực nghiệm có thể tạo hoặc ghi đè các file kết quả trong thư mục được chọn qua `--out`.

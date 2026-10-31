# Bloxorz Solver

Bloxorz Solver là trò chơi giải đố 3D được xây dựng bằng Python và thư viện Ursina. Chương trình gồm 15 màn chơi, hỗ trợ điều khiển thủ công và giải tự động bằng bốn thuật toán tìm kiếm: BFS, DFS, UCS và A*.

Dự án được thực hiện trong học phần CSC14003 - Nhập môn Trí tuệ nhân tạo.

## 1. Yêu cầu hệ thống

- Python 3.13
- Các thư viện được liệt kê trong `requirements.txt`
- Hệ điều hành Windows, Linux hoặc macOS có hỗ trợ Python và Ursina

Các thư viện chính:
- `ursina==8.3.0`: Xây dựng giao diện và trò chơi 3D.
- `matplotlib`: Vẽ biểu đồ so sánh kết quả thực nghiệm.

## 2. Cài đặt và chạy chương trình

Mở terminal tại thư mục `source`, nơi chứa file `main.py` và `requirements.txt`.

### 2.1. Windows PowerShell

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

### 2.2. Windows Command Prompt (CMD)

```bat
py -3.13 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python main.py
```

### 2.3. Linux và macOS

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

### 2.4. Sử dụng Conda

Nếu đã cài đặt và cấu hình môi trường Conda:

```bash
conda activate lab1AI
cd source
python -m pip install -r requirements.txt
python main.py
```

Sau khi cài đặt đầy đủ thư viện, những lần chạy tiếp theo chỉ cần kích hoạt môi trường và thực thi:

```bash
python main.py
```

## 3. Điều khiển trò chơi

| Phím / Nút | Chức năng |
|---|---|
| W, A, S, D | Di chuyển khối theo bốn hướng |
| Phím mũi tên | Di chuyển khối theo bốn hướng |
| Space | Chuyển quyền điều khiển giữa hai khối khi tách |
| R | Khởi động lại màn chơi |
| Esc | Quay về màn hình chọn level |
| LEVELS | Mở danh sách màn chơi |
| RESTART | Khởi động lại màn chơi hiện tại |
| BFS | Giải màn chơi bằng Breadth-First Search |
| DFS | Giải màn chơi bằng Depth-First Search |
| UCS | Giải màn chơi bằng Uniform-Cost Search |
| A* | Giải màn chơi bằng A* Search |
| STOP | Dừng phát lại lời giải hoặc bỏ qua kết quả tìm kiếm đang chờ |
| RESULTS | Hiển thị bảng thống kê kết quả |

Lưu ý: Nút STOP hiện chưa hỗ trợ hủy tức thời thuật toán đang thực thi trong luồng nền.

## 4. Các thuật toán tìm kiếm

Chương trình triển khai bốn thuật toán:

- **BFS (Breadth-First Search):** Tìm lời giải có số hành động ít nhất.
- **DFS (Depth-First Search):** Tìm kiếm theo chiều sâu, sử dụng tập trạng thái đã thăm để tránh chu trình.
- **UCS (Uniform-Cost Search):** Tìm lời giải có tổng chi phí nhỏ nhất.
- **A* (A-Star Search):** Kết hợp chi phí đã đi và heuristic để tìm lời giải có tổng chi phí nhỏ nhất.

### Hàm chi phí

Chương trình sử dụng quy tắc chi phí 1-2-4:

- Chi phí 4: Trạng thái sau hành động có ít nhất một ô bị chiếm là fragile.
- Chi phí 2: Không chạm fragile nhưng có thay đổi tư thế khối.
- Chi phí 1: Các trường hợp còn lại.

Các mức chi phí không cộng dồn.

BFS tối ưu số hành động, trong khi UCS và A* tối ưu tổng chi phí. DFS không bảo đảm tối ưu hai đại lượng này.

### Heuristic của A*

Đối với màn chơi không có cơ chế split, A* sử dụng heuristic dựa trên khoảng cách Manhattan đến đích và tư thế của khối.

Đối với màn chơi có split switch, heuristic được đặt bằng 0 để bảo đảm không đánh giá quá cao chi phí còn lại khi có teleport.

## 5. Chạy thực nghiệm

Chương trình sử dụng file `experiments/search_experiment.py` để thực hiện đánh giá bốn thuật toán trên cùng bộ 15 màn chơi.

Mở terminal tại thư mục `source` và kích hoạt môi trường Python đã cài đặt.

### 5.1. Chạy đầy đủ bốn thuật toán

```bash
python -m experiments.search_experiment --algos all --runs 5 --out experiments/report_results
```

Lệnh trên thực hiện:
- Chạy BFS, DFS, UCS và A* trên 15 màn chơi.
- Đo thời gian tìm kiếm với 5 lượt chạy cho mỗi cặp thuật toán và màn chơi.
- Đo bộ nhớ sử dụng.
- Ghi nhận số nút mở rộng, độ dài lời giải và tổng chi phí.
- Kiểm tra tính hợp lệ của lời giải và chi phí.
- Xuất kết quả CSV và biểu đồ PNG.

### 5.2. Các tùy chọn thực nghiệm

Chạy thực nghiệm với 10 lượt đo thời gian:

```bash
python -m experiments.search_experiment --algos all --runs 10 --out experiments/report_results
```

Chỉ xuất CSV, không tạo biểu đồ:

```bash
python -m experiments.search_experiment --algos all --runs 5 --no-plot --out experiments/report_results
```

Chạy riêng BFS và UCS:

```bash
python -m experiments.search_experiment --algos BFS,UCS --runs 5 --out experiments/report_results
```

Các thuật toán hợp lệ gồm `BFS`, `DFS`, `UCS`, `A*`. Có thể dùng `all` để chạy cả bốn thuật toán.

Lưu ý: Thực nghiệm có thể ghi đè các file kết quả cùng tên trong thư mục đầu ra. Nên sao lưu dữ liệu trước khi chạy lại nếu cần giữ bộ số liệu đã sử dụng trong báo cáo.

## 6. Kết quả thực nghiệm

Toàn bộ kết quả chính thức được lưu tại:

```text
source/experiments/report_results/
```

Các file kết quả gồm:

| File | Nội dung |
|---|---|
| bfs_dfs_ucs_astar_results.csv | Kết quả chi tiết của bốn thuật toán trên từng màn chơi |
| bfs_dfs_ucs_astar_summary.csv | Kết quả tổng hợp theo thuật toán |
| length.png | Biểu đồ so sánh độ dài lời giải |
| cost.png | Biểu đồ so sánh tổng chi phí lời giải |
| expanded.png | Biểu đồ so sánh số nút mở rộng |
| time.png | Biểu đồ so sánh thời gian tìm kiếm |
| memory.png | Biểu đồ so sánh bộ nhớ sử dụng |
| tradeoff.png | Biểu đồ thể hiện quan hệ giữa số nút mở rộng và độ dài lời giải |

Các chỉ số đánh giá chính gồm:
- Search Time (ms): Thời gian tìm kiếm.
- Memory Usage (KiB): Bộ nhớ Python đỉnh được theo dõi.
- Expanded Nodes: Số nút mở rộng.
- Solution Length: Số hành động trong lời giải.
- Solution Cost: Tổng chi phí của lời giải.

Thời gian và bộ nhớ có thể thay đổi tùy theo môi trường thực thi.

## 7. Cấu trúc mã nguồn

```text
source/
├── main.py
├── README.md
├── requirements.txt
├── algorithms/
│   ├── bfs.py
│   ├── dfs.py
│   ├── ucs.py
│   └── astar.py
├── assets/
├── core/
├── game/
├── gui/
├── levels/
│   ├── level1.json
│   ├── ...
│   └── level15.json
└── experiments/
    ├── __init__.py
    ├── search_experiment.py
    └── report_results/
        ├── bfs_dfs_ucs_astar_results.csv
        ├── bfs_dfs_ucs_astar_summary.csv
        ├── length.png
        ├── cost.png
        ├── expanded.png
        ├── time.png
        ├── memory.png
        └── tradeoff.png
```

Chức năng các thành phần:

- `main.py`: Khởi chạy trò chơi.
- `algorithms/`: Cài đặt các thuật toán BFS, DFS, UCS, A* và các thành phần hỗ trợ tìm kiếm.
- `assets/`: Chứa tài nguyên hình ảnh của giao diện.
- `core/`: Xử lý bàn chơi, trạng thái, luật di chuyển và các loại ô đặc biệt.
- `game/`: Quản lý quá trình chơi, điều khiển và phát lại lời giải.
- `gui/`: Hiển thị giao diện và bảng kết quả.
- `levels/`: Chứa dữ liệu JSON của 15 màn chơi.
- `experiments/`: Thực hiện thực nghiệm và xuất kết quả.
- `experiments/report_results/`: Lưu dữ liệu và biểu đồ phục vụ báo cáo.

## 8. Thông tin dự án

**Học phần:** CSC14003 - Nhập môn Trí tuệ nhân tạo

**Tên đồ án:** Bloxorz Solver

**Nhóm thực hiện:** Nhóm 8

**Giảng viên hướng dẫn:** Nguyễn Thanh Tình

**Mã nguồn:** https://github.com/hohuunghiem/Fundamentals-of-Artificial-Intelligence

**Video demo:** https://youtu.be/bJiol6gotSw
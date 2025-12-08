# Apps Hub

## Giới thiệu

Apps Hub là một ứng dụng desktop đơn giản được xây dựng bằng Python và PySide6, giúp quản lý và khởi chạy các ứng dụng con một cách tập trung. Nó có các tính năng chính sau:
- Hiển thị danh sách các ứng dụng từ tệp cấu hình.

## Yêu cầu cài đặt

Trước khi bắt đầu, bạn cần cài đặt các công cụ sau trên máy tính của mình:

1.  **Conda**: Miniconda (khuyên dùng) hoặc Anaconda.
2.  **Git**: Để sao chép mã nguồn (tùy chọn, bạn cũng có thể tải file ZIP).


## Hướng dẫn cài đặt môi trường

1.  **Lấy mã nguồn**:
    Mở terminal hoặc Git Bash và di chuyển đến thư mục bạn muốn lưu dự án.
    ```bash
    # git clone <URL_repository>
    # cd nova_hub
    ```
    Nếu không dùng Git, bạn có thể tải mã nguồn về và giải nén vào một thư mục.

2.  **Tạo môi trường Conda**:
    Mở Anaconda Prompt (hoặc terminal đã được cấu hình cho conda) và chạy các lệnh sau:

    ```bash
    # Tạo một môi trường mới tên là 'app-hub-env' với Python phiên bản 3.10
    conda env create -f nova_env.yaml

    # Kích hoạt môi trường vừa tạo
    conda activate nova_env
    ```

## Cấu hình và Chuẩn bị ứng dụng ban đầu

Ứng dụng này sử dụng cơ chế fallback: nó sẽ ưu tiên tìm file đã cài đặt trên máy, nếu không thấy sẽ tìm file trong thư mục `apps` của dự án.

1.  **Tạo thư mục `apps`**:
    Trong thư mục gốc của dự án (`e:\project\nova_hub\`), hãy tạo một thư mục mới có tên là `apps`.

2.  **Đặt các ứng dụng ban đầu (Tùy chọn)**:
    Nếu bạn muốn khởi chạy các ứng dụng ngay lập tức mà không cần tải về, bạn có thể đặt các file cài đặt (`.exe`) hoặc thư mục đã giải nén của chúng vào thư mục `apps`. Cấu trúc thư mục phải khớp với giá trị của trường `local_exe` trong tệp `appconfig.json`.

    Ví dụ về cấu trúc thư mục:
    ```
    nova_hub/
    ├── apps/
    │   ├── NovaPromptMaker-1.0.1-Setup.exe
    │   └── NovaCapcutTool_v1.82/
    │       └── NovaCapcutTool_v1.8.2.exe
    ├── appconfig.json
    └── main.py
    ```

3.  **Cấu hình `appconfig.json`**:
    Mở tệp `appconfig.json` và đảm bảo các trường sau được điền chính xác cho mỗi ứng dụng, đặc biệt là `download_url` để tính năng tải về hoạt động.

## Chạy ứng dụng

Sau khi hoàn tất các bước trên, bạn có thể khởi chạy Apps Hub bằng lệnh sau trong terminal (đảm bảo môi trường conda đã được kích hoạt):

```bash
python main.py
```

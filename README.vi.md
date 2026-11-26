# eyes-desktop

**Hình nền động ASCII cho Linux, có đôi mắt nhìn theo con trỏ chuột.**

Một bức chân dung được vẽ lại bằng hàng nghìn ký tự, phủ kín màn hình. Mắt nhìn theo chuột, con ngươi co giãn, mí mắt chớp, tóc bay trong gió và bị hất ra khi bạn rê chuột qua, click vào mặt nước thì gợn sóng lan ra. Chương trình chạy như một hình nền thật nằm dưới các cửa sổ, không cần trình duyệt.

[English](README.md)

![Hình nền nhìn theo con trỏ, gợn nước và tóc bay](demo/face.gif)

Cận cảnh một mắt ở kích thước thật để đọc được từng ký tự (vân mống mắt là các ký tự `\ | / (` toả ra từ con ngươi):

![Cận cảnh một mắt nhìn theo con trỏ](demo/eye-closeup.gif)

| Theme tối | Theme sáng | Cảnh `eye` |
|---|---|---|
| ![Theme tối](demo/face-dark.png) | ![Theme sáng](demo/face-light.png) | ![Cảnh một con mắt](demo/eye-scene.png) |

## Tính năng

**Cảnh `face` (mặc định):**

- **Phủ kín màn hình.** Chạy được với 16:9, 16:10, 21:9, mọi độ phân giải và nhiều màn hình.
- **Mắt nhìn theo chuột.** Mỗi nhãn cầu được vẽ lại:
  - lòng trắng có bóng đổ dưới mí;
  - mống mắt dựng từ chính mống mắt trong tranh, thêm vân sợi, vòng collarette, viền tối và hai đốm phản quang.
  - Mống mắt trượt **ra sau mí thật** và dẹt lại khi liếc ra góc, như nhãn cầu tròn. Hai mắt tính hướng nhìn riêng.
- **Con ngươi** co lại khi chuột lại gần, giãn ra khi chuột ra xa.
- **Mí mắt.** Chớp ngẫu nhiên (thỉnh thoảng chớp hai lần), chớp khi liếc xa, nheo khi chuột đặt ngay trên mắt, và hạ xuống khi mắt nhìn xuống. Mí khi khép có màu da và kéo theo hàng mi ở mép dưới.
- **Tóc.**
  - Lay theo hướng sợi mọc: đuôi tóc bay nhiều hơn chân tóc, có gió thổi từng đợt.
  - Rê chuột qua tóc sẽ hất tóc ra, rồi tóc bật về chỗ cũ.
- **Mặt nước.** Lăn tăn sóng. Click tạo vòng gợn lan ra; rê chuột trên mặt nước để lại vệt sóng.
- **Đốm sáng và ánh sáng.** Các đốm trên tóc lấp lánh, và một vùng sáng dịu đi theo con trỏ.
- **Khi chuột đứng yên,** mắt chạy một kịch bản riêng: liếc sang, đọc, nheo, chớp.

**Cảnh `eye`:** một con mắt ASCII nhìn theo chuột, lấy từ profile card GitHub của tác giả.

**Nhẹ máy.**
- Chỉ vẽ lại phần thay đổi, vẽ thẳng lên cửa sổ bằng libX11.
- Hiệu ứng theo chuột chỉ chạy khi con trỏ nằm trên chính hình nền.
- Tự tạm dừng khi có cửa sổ phóng to hoặc toàn màn hình che phía trước.

## Yêu cầu

- **X11** cho chế độ mắt nhìn theo chuột. Trên Ubuntu, chọn **"Ubuntu on Xorg"** ở biểu tượng bánh răng trên màn hình đăng nhập.
- **GNOME 46 trên Wayland** cho chế độ hình nền động tự chạy. Xem hướng dẫn cài bên dưới.
- **Python 3.8+** cùng Tk, Pillow, NumPy và python-xlib.
- Một font monospace. Dùng DejaVu Sans Mono nếu có, nếu không thì font mà `fc-match monospace` tìm được.

Cài các gói một lần.

Debian / Ubuntu:

```bash
sudo apt install python3-tk python3-pil python3-pil.imagetk python3-xlib python3-numpy
```

Fedora:

```bash
sudo dnf install python3-tkinter python3-pillow-tk python3-xlib python3-numpy
```

Arch:

```bash
sudo pacman -S tk python-pillow python-xlib python-numpy
```

Nếu dùng virtualenv: cài gói Tk của hệ điều hành như trên, rồi:

```bash
pip install -r requirements.txt
```

## Bắt đầu nhanh

### Hình nền động trên GNOME 46 Wayland

Trong thư mục dự án, chạy `./install-wayland.sh`. Lệnh này dùng Python và các
gói như chế độ X11, cùng GStreamer với `gst-launch-1.0`, `rawvideoparse`,
`vp8enc` và `webmmux`. Nếu GNOME chưa nhận tiện ích trong lần cài đầu,
hãy đăng xuất rồi đăng nhập lại bằng phiên Ubuntu Wayland.

Cảnh tự chớp mắt và đảo hướng. Ảnh vuông có hai dải số phủ tới mép màn hình.
Ảnh ngang hiển thị nguyên khung theo tỷ lệ gốc. Cùng hình nền xuất hiện ở
desktop, Tổng quan và lúc chuyển workspace. Video mặc định
1920 × 1200. Có thể đổi kích thước bằng `--width` và `--height` khi cài.
Chạy lại lệnh cài để xuất video mới sau khi đổi ảnh hoặc chủ đề.

Dùng `gnome-extensions disable eyes-desktop@local` để trở lại nền mặc định.

### Chạy thử và cài chế độ X11

```bash
git clone https://github.com/hdnng/eyes-desktop.git
```

```bash
cd eyes-desktop
```

Chạy thử trong cửa sổ 1280x720 (nhấn Esc để thoát):

```bash
python3 eyes.py --window
```

Đặt làm hình nền, bật ngay và tự chạy mỗi lần đăng nhập:

```bash
./install.sh
```

`install.sh` tạo file `~/.config/autostart/eyes-desktop.desktop` (chỉ cho tài khoản của bạn, không sửa gì toàn hệ thống) rồi bật hình nền. Sau đó đừng di chuyển thư mục, vì mục tự chạy trỏ vào đúng đường dẫn này.

Các lệnh hằng ngày:

| Lệnh | Tác dụng |
|---|---|
| `./start.sh` | bật hoặc khởi động lại hình nền, ví dụ sau khi sửa `config.json` |
| `./stop.sh` | tắt |
| `./uninstall.sh` | tắt và bỏ tự chạy |

Log nằm ở `~/.cache/eyes-desktop.log`.

## Tuỳ chỉnh

Sửa `config.json` rồi chạy `./start.sh`. Mọi khoá cũng có thể ghi đè tạm qua dòng lệnh, ví dụ `./start.sh --theme light --cell 4`.

| Khoá | Ý nghĩa | Mặc định |
|---|---|---|
| `scene` | `"face"` hoặc `"eye"` | `"face"` |
| `theme` | `"dark"` hoặc `"light"` | `"dark"` |
| `fit` | face: `"cover"` phủ kín màn hình; `"contain"` hiện trọn ảnh ở giữa | `"cover"` |
| `focus` | face, cover: điểm của ảnh đặt vào giữa màn hình, `[x, y]` từ 0 đến 1. Tăng `y` để thấy nhiều mũi và mặt nước hơn, giảm để thấy nhiều tóc hơn | `[0.5, 0.5]` |
| `cell` | face: độ rộng một ký tự (px, tính ở 1080p). Nhỏ hơn thì chi tiết hơn và tốn CPU hơn. Tự nhân theo độ phân giải | `5` |
| `hair_strength` | biên độ tóc bay | `3.5` |
| `face_size` | face, contain: kích thước ảnh so với chiều cao màn hình | `0.92` |
| `size` | cảnh eye: chiều cao con mắt so với màn hình | `0.6` |
| `position` | contain và cảnh eye: tâm hình, `[x, y]` | `[0.5, 0.5]` |
| `monitor` | `"primary"` hoặc số thứ tự màn hình (`0`, `1`, …) | `"primary"` |
| `fps` | khung hình/giây cho mắt và hiệu ứng theo chuột | `24` |
| `ambient_fps` | khung hình/giây cho tóc và nước (ít nhất 20 khi có gợn sóng) | `12` |
| `idle_after` | số giây chuột đứng yên trước khi chạy kịch bản tự động | `8.0` |
| `effects` | bật/tắt từng hiệu ứng: `water`, `ripples`, `hair`, `stars`, `glow` | tất cả bật |
| `background` | màu nền riêng, ví dụ `"#000000"` | theo theme |
| `font` | đường dẫn font monospace khác | DejaVu Sans Mono Bold |

## Dùng ảnh của bạn

Cảnh face dùng hai file:

| File | Nội dung |
|---|---|
| `assets/avatar.png` | ảnh PNG, tốt nhất là ảnh thấy rõ hai mắt |
| `assets/face.json` | hình học của ảnh, tính theo pixel của chính ảnh đó |

Các trường trong `face.json`:

| Trường | Ý nghĩa |
|---|---|
| `eyes[].upper` / `eyes[].lower` | các điểm dọc mép trên và mép dưới của khe mắt, từ khoé trong ra khoé ngoài; hai đường bắt đầu và kết thúc ở cùng hai khoé |
| `eyes[].iris` | `[x, y, bán kính]` của mống mắt |
| `eyes[].lid` | độ dày dải mi tối ngay trên khe mắt (`lash`), và lượng da phía trên dải mi mà mí dùng khi khép (`skin`) |
| `hair[]` | một hay nhiều vùng tóc: `polygon` bao vùng, `root` là chỗ sợi tóc mọc ra, `direction` là hướng về phía đuôi tóc, `reach` là độ dài sợi |
| `water.top` / `water.full` | chỗ mặt nước (nếu có) bắt đầu, và chỗ sóng chuyển động hết mức. Đặt `top` lớn hơn chiều cao ảnh nếu ảnh không có nước |
| `stars` | xuống tới đâu thì còn tìm đốm sáng để cho lấp lánh |

Cách làm:

1. Thay `assets/avatar.png` bằng ảnh của bạn.
2. Sửa các điểm trong `assets/face.json` cho khớp ảnh mới.
3. Vẽ các đường lên ảnh để kiểm tra:

   ```bash
   python3 tools/check_geometry.py
   ```

4. Mở `geometry-check.png`: mí là màu đỏ và xanh dương, mống mắt xanh lá, tóc vàng có mũi tên chỉ hướng sợi, mặt nước xanh ngọc. Chỉnh điểm và chạy lại cho đến khi khớp.
5. Xem kết quả bằng `python3 eyes.py --window`.

## Quay lại ảnh demo

`tools/record_demo.py` tạo lại các ảnh trong `demo/` trên màn hình ảo. Cần có `Xvfb` và `xdotool`:

```bash
python3 tools/record_demo.py
```

```bash
python3 tools/record_demo.py --still-only --theme light --prefix face-light
```

## Hiệu năng

Đo trên máy thử ở 1080p, tính theo phần trăm một nhân CPU:

| Trạng thái | CPU |
|---|---|
| Cảnh face đủ hiệu ứng, chuột đứng yên | khoảng 18% |
| Cảnh face đủ hiệu ứng, đang rê chuột qua tóc | khoảng 23% |
| Cảnh face chỉ có mắt (`hair` và `water` tắt) | khoảng 7% |
| Có cửa sổ phóng to hoặc toàn màn hình phía trước | khoảng 0% (tạm dừng) |

Tóc tốn nhiều nhất. Muốn nhẹ hơn, giảm `ambient_fps` (ví dụ 8), tăng `cell` (ví dụ 6), hoặc tắt `hair`.

## Xử lý sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| Mắt không nhìn theo chuột | Chạy `echo $XDG_SESSION_TYPE`. Nếu ra `wayland`, đăng nhập bằng phiên X11 (xem phần Yêu cầu). |
| Icon desktop biến mất hoặc che hình nền | Với extension icon desktop (ví dụ Desktop Icons NG của GNOME), thứ tự lớp phụ thuộc thứ tự khởi động. Chạy lại `./start.sh` sau khi đăng nhập xong. Click vào mặt nước có thể bị lớp icon nhận thay. |
| `No monospace font found` | Cài DejaVu Sans Mono (`fonts-dejavu-core` trên Debian/Ubuntu), hoặc đặt `"font"` trong `config.json`. |
| Log có `note: direct X drawing unavailable` | Màn hình không phải 24-bit TrueColor nên chương trình dùng ảnh Tk thay thế. Vẫn chạy bình thường, chỉ tốn CPU hơn. |
| Lỗi khác | Xem `~/.cache/eyes-desktop.log`. |

## Cách hoạt động

| File | Vai trò |
|---|---|
| `eyes.py` | cửa sổ hình nền (`_NET_WM_WINDOW_TYPE_DESKTOP`, nằm dưới mọi ứng dụng); đọc chuột qua Xlib, theo dõi thay đổi màn hình, tạm dừng khi bị che |
| `behaviour.py` | hướng nhìn, con ngươi, chớp mắt, kịch bản lúc chuột đứng yên |
| `scene_face.py` | mỗi khung hình lấy mẫu lại ảnh qua trường biến dạng (tóc, nước, gợn sóng), vẽ hai nhãn cầu, rồi chuyển thành ký tự |
| `ascii_render.py` | chuyển sang ASCII và vẽ lên màn hình (xem dưới) |
| `scene_eye.py` | cảnh một con mắt |

Mỗi ô chữ được chia thành 2×3 ô con. Ký tự được chọn là ký tự có hình dạng (đo từ font thật) khớp nhất với cả độ đậm lẫn hoa văn của sáu giá trị đó. Nhờ vậy các nét như hàng mi hay sợi tóc vẫn giữ được hướng.

Khung hình nằm trong một bộ đệm NumPy; mỗi lần chỉ gửi các vùng chữ nhật thay đổi lên cửa sổ bằng `XPutImage`. Nếu không được thì dùng ảnh Tk thay thế.

## Ghi công

- Con mắt ASCII của cảnh `eye` (`assets/eye.json`) và kịch bản lúc chuột đứng yên lấy từ profile card trong [hdnng/hdnng](https://github.com/hdnng/hdnng).
- `assets/avatar.png` là avatar GitHub của tác giả. Muốn hình nền là của riêng bạn, thay ảnh theo hướng dẫn ở trên.

# Smart Scan Libera

Program ini membaca pratinjau Libera Scanner dari jendelanya. Libera tetap memproses dan menyimpan hasil scan. Program ini tidak mengubah PDF atau dokumen yang dipotret.

Proyek ini merupakan pendamping tidak resmi untuk Libera Scanner. Aplikasi Libera dan driver perangkat perlu disediakan secara terpisah.

## Mulai cepat

Kebutuhan: Windows, Python 3.11, Libera Scanner, serta perangkat scan dengan pratinjau kamera yang berfungsi. Kompatibilitas dengan versi Python, Libera, dan tata letak lain perlu diuji pada perangkat yang digunakan.

Unduh atau clone kode proyek, lalu buka PowerShell di folder proyek:

```powershell
python --version
powershell -ExecutionPolicy Bypass -File .\setup.ps1
.\run_smart_scan.bat --dry-run
```

Sebelum menjalankan simulasi, buka Libera pada tab Book Scanner dan matikan auto-scan bawaannya. Periksa bidang kamera dan zona tangan pada HUD. Setelah simulasi sesuai, tutup HUD dan jalankan:

```powershell
.\run_smart_scan.bat
```

Instalasi membutuhkan internet untuk paket Python dan model MediaPipe. `--dry-run` tetap menangkap dan menganalisis pratinjau, tetapi tidak mengirim tombol atau klik untuk scan.

## Privasi dan hasil scan

Kode aplikasi menganalisis tangkapan jendela di memori dan menampilkannya pada HUD. Kode ini tidak memiliki fungsi unggah gambar atau penyimpanan hasil scan. Penyimpanan hasil dan perilaku aplikasi Libera mengikuti pengaturan Libera. Pernyataan ini tidak mencakup seluruh perilaku internal dependency atau aplikasi Libera.

Kalibrasi `C` menampilkan tangkapan seluruh jendela Libera, yang bisa memuat thumbnail atau informasi di luar bidang kamera. Gunakan halaman contoh tanpa data pribadi untuk screenshot dan rekaman demo.

Penghitung scan menunjukkan jumlah perintah yang dikirim, bukan konfirmasi hasil tersimpan. Periksa hasil di Libera saat menguji perangkat pertama kali.

## Perilaku scan

- Pada Scan Mode `Original Image` dan `Book`, seluruh pratinjau kamera Libera menjadi bidang analisis. Garis tengah pada `Book` adalah panduan posisi buku. Pemrosesan hasil tetap mengikuti pengaturan Libera.
- Pada `Select Area`, tarik kotak merah di Libera untuk menentukan bidang analisis. Kotak boleh lebih kecil dari pratinjau kamera. Scan otomatis menunggu kotak lengkap, tombol mouse dilepas, gambar stabil, dan tangan aman. Gerakan di luar kotak tidak dihitung sebagai perubahan halaman.
- Perubahan susunan di area scan, termasuk membalik halaman atau meletakkan lembar tambahan, memulai satu siklus pengamatan. Beralih ke `Original Image`, `Book`, atau `Select Area` saat Smart Scan berjalan juga memulai satu scan awal setelah kamera siap, gambar stabil, dan tangan aman. Membuat atau mengubah kotak `Select Area` memulai scan untuk pilihan baru. Acuan halaman diatur ulang saat berganti mode atau mengubah kotak. `Document` tetap mengikuti bingkai oranye Libera.
- Scan otomatis dikirim setelah susunan berubah, gerakan mereda, dan bidang kamera stabil selama waktu yang ditentukan.
- Status `SIAP` dengan `Scene: 0.0%` berarti gambar belum berbeda dari acuan (biasanya halaman terakhir yang dipindai); status ini sendiri tidak mengirim scan. Jika gerakan membalik halaman terlewat tetapi gambar akhirnya berbeda, program tetap memulai hitung stabilisasi.
- Landmark tangan boleh tetap berada di zona hijau pada tepi gambar. Tangan yang terdeteksi di luar zona menahan scan. Jari yang terlalu sedikit terlihat sering tidak dikenali model; filter warna memeriksa komponen yang masuk dari tepi dan mengabaikan bidang besar berbentuk lembaran yang dapat menyerupai warna kulit. Komponen kecil yang meluas keluar zona tetap menghasilkan status "periksa manual".
- Bila gambar jendela tidak tersedia, tampak beku, batas area pada mode yang memerlukannya tidak terdeteksi, atau detektor tangan gagal, scan otomatis ditahan. Tekan `S` pada HUD untuk scan manual setelah Anda memeriksa susunannya dan kamera siap.
- Tampilan Libera yang masih menunjukkan pesan seperti "No device found" dianggap kamera belum siap. Program menunggu gambar kamera yang berisi detail dan berubah secara normal selama satu detik sebelum mengaktifkan analisis. Scan manual `S` juga ditahan selama kamera belum siap.
- Satu siklus hanya mengirim satu metode pemicu. Nilai awal adalah `F12`; ganti ke `click` jika Libera Anda tidak memakai F12.

Lembar tambahan yang menutupi tulisan buku tidak dapat membuat tulisan di bawahnya ikut terbaca. Potret susunan buku dan dokumen tambahan secara terpisah jika keduanya perlu tersimpan.

## Menjalankan

1. Siapkan Python 3.11 atau versi kompatibel pada Windows.
2. Jalankan `powershell -ExecutionPolicy Bypass -File .\setup.ps1` satu kali. Skrip membuat `.venv`, memasang paket, dan mengambil model tangan dari [Google MediaPipe](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/index).
3. Buka Libera Scanner pada tab Book Scanner dan matikan fitur auto-scan bawaannya agar tidak ada dua pemicu terpisah.
4. Jalankan `run_smart_scan.bat --dry-run` untuk melihat status tanpa mengirim scan. Setelah posisi jendela, ROI, dan zona tangan sesuai, jalankan `run_smart_scan.bat`.

### Tombol HUD

| Tombol | Fungsi |
| --- | --- |
| `P` | Jeda atau lanjutkan scan otomatis |
| `S` | Scan manual setelah memeriksa halaman; kamera harus siap |
| `C` | Pilih ulang seluruh bidang kamera |
| `T` | Pin atau lepas pin HUD |
| `Q` / `Esc` | Tutup aplikasi |

Tombol bekerja saat jendela HUD memiliki fokus. Tombol `PIN: ON/OFF` di kanan atas HUD juga dapat diklik. Pin aktif saat program dimulai; ubah `ui.pin_on_top` menjadi `false` di `config.json` jika ingin memulai tanpa pin. Pin menjaga HUD di depan saat Libera menerima fokus untuk scan. `S` adalah pemeriksaan manual: tombol ini tidak memakai semua penahan area/tangan dari scan otomatis.

Jika gambar HUD membesar, terpotong, atau tidak dikenali, tekan `C` pada HUD. Pada tampilan tangkapan jendela Libera, tarik kotak mengelilingi **seluruh pratinjau kamera**, lalu tekan Enter. Jangan memasukkan toolbar, thumbnail, atau panel kontrol. Esc membatalkan. Pemilihan berlangsung tanpa mengirim scan dan berlaku sampai ukuran jendela Libera berubah atau program ditutup. Kamera tetap diperiksa kesiapan gambarnya; pemilihan manual tidak mengaktifkan scan pada tampilan tanpa perangkat.

Penangkapan jendela dan koordinat klik menggunakan konteks DPI piksel fisik agar ukuran bitmap sesuai pada Windows dengan skala tampilan di atas 100%.

## Penyesuaian `config.json`

Untuk menyimpan pengaturan perangkat secara lokal, salin konfigurasi bawaan dan gunakan `--config`:

```powershell
Copy-Item .\config.json .\config.local.json
.\run_smart_scan.bat --config .\config.local.json --dry-run
```

`config.local.json` dikecualikan dari Git. Path model relatif tetap dihitung dari folder aplikasi, bukan folder konfigurasi yang dipilih.

- `window.camera_layout`: perkiraan lebar sidebar dan panel kontrol serta tinggi toolbar Libera dalam piksel. Program mencari batas pratinjau kamera pada latar abu-abu Libera dan memeriksa rasio 4:3; pratinjau boleh berubah ukuran dan posisi. Jika tema, skala Windows, atau tata letak Libera berbeda, parameter ini mungkin perlu disesuaikan.
- `hands.allowed_zones`: area tepi tempat tangan boleh berada, relatif terhadap bidang analisis: seluruh kamera pada `Original Image`/`Book`, kotak merah pada `Select Area`, atau bingkai oranye pada `Document`. Zona awal mencakup strip bawah dan kedua sudut atas. Sesuaikan dengan posisi tangan yang benar-benar diperlukan; jangan sampai zona meliputi tulisan yang harus terlihat.
- `motion.scene_change_percent`: perubahan minimum susunan di luar zona tangan. Menaikkannya mengurangi pemicu karena gerakan kecil, tetapi bisa melewatkan lembar tambahan yang kecil.
- `motion.debounce_seconds`: lama keadaan tenang sebelum scan.
- `camera_readiness`: ambang tampilan seragam, tekstur, waktu pemanasan, dan deteksi gambar beku. Tampilan buku yang benar benar kosong atau sangat seragam mungkin ikut ditahan dan memerlukan kalibrasi.
- `trigger.method`: `hotkey` atau `click`. Klik memakai posisi relatif `click_position` dan dapat meleset bila tata letak Libera berubah.

Model landmark dapat luput dari jari yang hanya terlihat sebagian. Filter warna cadangan juga dapat luput atau salah mengira warna kertas sebagai tangan; saat meragukan, program menahan scan. Jangan gunakan mode otomatis tanpa pengamatan awal pada perangkat, pencahayaan, dan jenis buku yang akan dipindai. Untuk susunan berlapis atau ketika tangan menutupi isi penting, gunakan `S` setelah memastikan hasil pratinjau sesuai.

HUD menampilkan seluruh bidang kamera dengan rasio aspek tetap. Bilah status dan tombol berada di luar gambar kamera. Garis kuning menandai bidang analisis sesuai mode: seluruh kamera, kotak merah pilihan pengguna, atau bingkai oranye Libera. Perubahan halaman dibandingkan pada koordinat kamera yang tetap, di dalam area scan dan di luar zona hijau. Bagian dalam bingkai diluruskan untuk deteksi tangan, sedangkan HUD menampilkan gambar kamera asli. Bila area yang diperlukan hilang atau tidak dapat dikenali, status menjadi "AREA SCAN BELUM TERDETEKSI" dan scan otomatis menunggu. Bila pratinjau masih menunjukkan sidebar atau panel kontrol Libera, hentikan auto-scan dan periksa `window.camera_layout`.

Pada mode yang memakai bingkai oranye, kehilangan deteksi bingkai selama kurang dari tiga detik mempertahankan acuan halaman, sehingga perubahan yang selesai selama gangguan singkat masih bisa dikenali setelah bingkai kembali. Selama bingkai tidak terdeteksi, scan otomatis tetap ditahan. Jika gangguan berlangsung lebih lama, acuan diatur ulang dan halaman perlu digerakkan lagi agar dapat dikenali sebagai perubahan baru.

Jika HUD tetap hitam dengan status "KAMERA BELUM SIAP", baca keterangan kecil di tengah HUD. Keterangan ini membedakan jendela Libera yang tidak ditemukan, kegagalan `PrintWindow`, dan bidang kamera yang tidak dikenali. Tutup HUD dan jalankan ulang setelah kode diperbarui; HUD yang sudah berjalan tidak memuat perubahan Python secara otomatis.

## Troubleshooting

| Gejala | Pemeriksaan |
| --- | --- |
| Python tidak ditemukan | Pastikan `python --version` berjalan di PowerShell sebelum menjalankan setup. |
| Model tangan tidak ada | Jalankan ulang `setup.ps1`; periksa akses internet dan `hands.model_path`. |
| HUD hitam / kamera belum siap | Baca keterangan HUD, buka kembali pratinjau Libera, dan pastikan perangkat terhubung. |
| Bidang kamera terpotong | Tekan `C` dan pilih seluruh pratinjau tanpa toolbar atau thumbnail. |
| Perintah dihitung tetapi hasil tidak muncul | Periksa fokus Libera dan dukungan F12. Uji metode `click` jika diperlukan; koordinat harus cocok dengan tata letak. |
| Scan terlalu cepat atau terlalu jarang | Uji `motion.debounce_seconds`, `motion.scene_change_percent`, dan zona tangan dalam simulasi. |

Tutup dan jalankan ulang HUD setelah mengubah kode atau konfigurasi.

## Pengembangan dan uji

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tes memeriksa logika status, area, deteksi gambar, HUD, serta tangkapan DPI dengan mock. Kinerja tangkapan jendela dan model tangan perlu diuji langsung dengan Libera terbuka. Lihat [panduan kontribusi](CONTRIBUTING.md) dan [kebijakan keamanan](SECURITY.md).

## Lisensi dan publikasi

Kode proyek tersedia dengan [lisensi MIT](LICENSE). Dependency dan model memiliki ketentuan masing-masing; lihat [catatan pihak ketiga](THIRD_PARTY_NOTICES.md).

Publikasikan kode, tes, konfigurasi bawaan, dan dokumentasi. `.gitignore` mengecualikan lingkungan Python, cache, model unduhan, konfigurasi lokal, log, serta folder `scans/`, `captures/`, dan `recordings/`. Simpan hasil scan lokal di folder tersebut; file pribadi di lokasi lain tetap perlu diperiksa sebelum commit. Upload manual atau ZIP tidak otomatis menerapkan aturan `.gitignore`.

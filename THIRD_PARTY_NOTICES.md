# Komponen pihak ketiga

Lisensi MIT proyek berlaku untuk kode Smart Scan Libera. Lisensi itu tidak menggantikan ketentuan dependency, model, atau aplikasi Libera.

## Dependency langsung

Rentang versi berasal dari `requirements.txt`. Versi yang terpasang dan komponen yang dibundel dapat berbeda.

| Paket | Rentang versi | Sumber dan lisensi upstream |
| --- | --- | --- |
| NumPy | `>=1.26,<3` | [NumPy](https://numpy.org/doc/stable/license.html), BSD 3-Clause |
| opencv-contrib-python | `>=4.8,<6` | [Paket Python](https://github.com/opencv/opencv-python/blob/4.x/LICENSE.txt), MIT untuk kode packaging; [OpenCV](https://opencv.org/license/) memakai Apache 2.0 pada versi modern |
| MediaPipe | `>=0.10,<0.11` | [MediaPipe](https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE), Apache 2.0 untuk kode upstream |

Paket biner dapat membundel library dengan lisensi tambahan. Jika membagikan installer atau paket yang berisi dependency, periksa dan sertakan lisensi serta notice dari versi distribusi yang benar-benar disertakan. Tabel ini bukan daftar lengkap dependency transitif.

## Model Hand Landmarker

`setup.ps1` mengunduh model dari [Google MediaPipe model storage](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task). Dokumentasi tersedia pada [Hand Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker).

Model disimpan di `models/hand_landmarker.task` dan dikecualikan dari Git. URL menggunakan `latest`, sehingga isi unduhan dapat berubah. Ketentuan redistribusi untuk binary model tertentu belum diverifikasi di proyek ini; jangan menganggap lisensi kode MediaPipe otomatis menentukan lisensi semua model. Pertahankan pengunduhan terpisah saat membagikan kode sumber.

## Libera Scanner

Libera adalah aplikasi eksternal yang diperlukan untuk pratinjau dan penyimpanan hasil. Repository ini tidak menyertakan executable, driver, atau lisensi Libera. Nama Libera digunakan untuk menjelaskan integrasi; proyek ini merupakan pendamping tidak resmi.

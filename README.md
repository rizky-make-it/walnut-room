# Ruang — Walnut Bedroom

Website showcase dari proyek kamar Blender. Berisi render, model GLB interaktif,
perbandingan referensi, palet material, lightbox, dan unduhan berkas proyek.

## Menjalankan secara lokal

```powershell
node scripts/serve.mjs
```

Buka http://127.0.0.1:4173. Situs tidak memerlukan instalasi paket atau build.
Semua file untuk hosting berada di `dist/`. Font, penampil 3D, dan decoder model
disimpan lokal. Berkas asli Blender tetap berada di folder `output/bedroom-v3`.

Untuk membuat ulang versi GLB yang dioptimalkan, jalankan `scripts/export_web.py`
melalui Blender. Skrip ini membaca proyek asal dan tidak menyimpan perubahan ke
file `.blend` asli.

Penampil GLB menyederhanakan geometri dan material untuk browser. Render PNG
menampilkan pencahayaan akhir dari Blender. Situs ini adalah studi desain,
bukan dokumentasi bangunan yang sudah dibangun.

## Detail edition / v3

Render utama dirender langsung di Blender Cycles pada 7680 × 5416 piksel,
bukan hasil upscale. JPEG 2400/960 piksel dipakai pada halaman agar ringan.
Empat crop detail berasal dari PNG master yang sama. Unduhan PNG 8K terpisah.
PNG lossless dikirim sebagai bagian byte kecil untuk menghindari batas ukuran
aset hosting. Browser memeriksa SHA-256 setiap bagian dan menyatukannya menjadi
PNG asli dengan satu klik. JPEG 8K tersedia sebagai unduhan langsung/fallback.

Model asli memakai foto PBR walnut dan kulit, normal/roughness maps, tenunan
katun dua arah, lipatan geometri, relief bata, dan jahitan ganda ottoman.
`.blend` berisi gambar tekstur terkemas; tidak perlu memasang add-on.
GLB memiliki normal map kain/kulit/walnut dan roughness kayu/kulit tersemat,
serta mesh terkompresi Draco. Pencahayaan browser tidak identik dengan Cycles.
Cermin GLB memakai refleksi environment, bukan refleksi planar dinamis ruangan;
cermin dan kaca dalam render Blender menggunakan ray tracing.

`scripts/prepare-images.ps1` menyiapkan gambar responsif dan crop setelah render.
`node scripts/check.mjs` memeriksa aset, GLB, dan dimensi master.
`node scripts/qa.mjs` menguji desktop, mobile, modal, model 3D, dan unduhan
(jalankan server lokal terlebih dahulu).

PBR CC0: Natural Walnut Veneer, Jenelle van Heerden,
https://polyhaven.com/a/natural_walnut_veneer;
Brown Leather, Rob Tuytel, https://polyhaven.com/a/brown_leather.
Kredit dan petunjuk rebuild disertakan dalam unduhan proyek.

Model viewer: Google `<model-viewer>` 4.4.0, Apache 2.0.
Draco decoder: Google Draco 1.5.6, Apache 2.0.
Font DM Sans dan Instrument Serif: SIL Open Font License 1.1.

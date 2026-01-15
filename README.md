0. Siapkan Kopi dan pisang goreng
1. Install Python (versi 3.13)
2. Install modul yang diperlukan dari cmd: pip install -r requirements.txt
2.a. install playwright, cmd: playwright install
3. Download rawdata sebagai bahan data kirim gc cmd: python scraping_all.py
4. Lakukan pengolahan data hasil download yg ingin di kirim ke gc (misalnya filter hanya yang sudah diprofiling, aktif dan koordinatnya valid)
5. Buat file csv baru dengan tambahan kolom hasilgc, isi kode yang sesuai (kode 99 tidak ditemukan, 1 ditemukan, 3 tutup, 4 ganda)
5.a. data yang akan dikirim adalah "perusahaan_id", "latitude","longitude","hasilgc"
5.b. PENTING: pastikan kode pada hasilgc sudah sesuai dengan ketentuan GC
6. Jika data_gc_profiling sudah siap lanjut ke langkah submit ke GC
7. Submit GC: python tandaiKirim.py username password OTP_opsional barisMulai.
8. Kopinya dah dingin tuh :D

DISKLAIMER: Gunakan script ini dengan bijak, jangan sampai melanggar aturan dari GC,
diskusi dengan ketua tim, pimpinan jika sepakat, gaskeun.
Motifnya bukan untuk banyak-banyakan, tapi memudahkan pekerjaan yang berulang,
Pastikan data yang akan dikirim adalah data yang valid dan sesuai ketentuan.

Happy GC Gaes :)

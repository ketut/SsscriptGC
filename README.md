# 🚀 Panduan Penggunaan Script GC


## 📋 Langkah-Langkah Persiapan

1. **Siapkan Kopi dan Pisang Goreng** ☕🍌  
   Pastikan Anda siap dan energik!

2. **Install Python (versi 3.13)** 🐍  
   Pastikan Python versi terbaru terinstall di sistem Anda.

3. **Install Modul yang Diperlukan** 📦  
   Jalankan perintah berikut di command prompt:  
   ```
   pip install -r requirements.txt
   ```

4. **Install Playwright** 🎭  
   Jalankan perintah:  
   ```
   playwright install
   ```

5. **Download Raw Data** 📥  
   Jalankan script untuk mengunduh data:  
   ```
   python scraping_all.py
   ```

6. **Pengolahan Data** 🔄  
   Olah data hasil download sesuai kebutuhan (misalnya, filter data yang sudah diprofiling, aktif, dan koordinat valid).
   Tahap ini perlu hati-hati agar type data, format data asli tidak berubah, terutama perusahaan_id, latitute, dan longitude

8. **Tambahkan kolom `hasilgc`** 📊
   Tambahkan kolom `hasilgc` dengan kode yang sesuai:  
   - `99`: Tidak ditemukan  
   - `1`: Ditemukan  
   - `3`: Tutup  
   - `4`: Ganda
   >Cek-ricek kembali pastikan data sudah benar, isian maupun format datanya, PENTING: id_perusahaan harus persis seperti aslinya

   **Kolom yang wajib dikirim:** `"perusahaan_id"`, `"latitude"`, `"longitude"`, `"hasilgc"`  
   ⚠️ **PENTING:** Pastikan kode pada `hasilgc` sudah sesuai dengan ketentuan GC!

10. **Submit ke GC** 📤  
   Jika data sudah siap, jalankan:  
   ```
   python tandaiKirim.py username password OTP_opsional barisMulai
   ```

11. **Kopi Sudah Dingin?** 😄  
   Waktunya istirahat sejenak!

## ⚠️ Disclaimer

> Gunakan script ini dengan bijak, jangan sampai melanggar aturan dari GC. Diskusikan dengan Ketua Tim dan Pimpinan.  
> Motifnya bukan untuk banyak-banyakan, tapi memudahkan pekerjaan yang berulang, memudahkan menandai GC usaha yang sudah diprofiling pada kegiatan profiling sebelumnya dengan keyakinan bahwa ini sudah merupakan upaya terbaik.
> Pastikan data yang akan dikirim adalah data yang valid dan sesuai ketentuan.

**Happy GC Gaes! 🎉**


#### tentang script
> scraping_all.py untuk mengunduh seluruh data (menurut wilayah user) dari matchapro, baik yang sudah diprofiling maupun yang belum diprofiling (filter `history_ref_profiling_id`)
> tandaiKirim.py untuk melakukan tandai secara otomatis, terutama ditujukan pada usaha-usaha yang sudah diprofiling dan diyakini profiling yang dilakukan sudah merupakn opsi terbaik, script ini merupakan otomatisasi tandai matchapro-mobile.

#### ⚠️ Untuk menjaga integritas data, pastikan data input valid

>>Jika script gagal silakan cek kembali repo ini, siapa tahu ada update!





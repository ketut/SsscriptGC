#### Script untuk menambahkan usaha

##### cara penggunaan `python tambahaUsaha.py --csv file_input.csv username 'password' [OTP]`

1. Input yang diperlukan file csv (contoh file_input.csv) dengan kolom: lat, lon, name, address, nmdesa_gc, provinsi, kabupaten, kecamatan, desa
2. provinsi, kabupaten, kecamatan, dan desa merupakan kode wilayah versi Matchapro.
3. nmdesa_gc adalah nama desa
4. script menggunakan pengecekan similarity sederhana berdasarkan nama usaha dibandingkan dengan lists hasil pengecekan matchapro, MAX_SIMILARITY=80 (silakan disesuaikan)

##### Requirements (pip install pandas rapidfuzz argparse)
- pandas 
- rapidfuzz
- argparse

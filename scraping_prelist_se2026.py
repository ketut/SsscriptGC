import requests
import time
import pandas as pd
from tqdm import tqdm
from login import login_with_sso
import re
import csv
from urllib.parse import quote

# ------------------------------------------------------
# KONFIGURASI - URL & PAYLOAD
# ------------------------------------------------------
BASE_URL = "https://matchapro.web.bps.go.id/se2026"

# Payload base - columns dan order saja (tanpa start, length, search, _token, wilayah)
# Urutan: draw, columns, order
BASE_PAYLOAD = "draw=1" \
"&columns%5B0%5D%5Bdata%5D=idsbr&columns%5B0%5D%5Bname%5D=idsbr&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=false&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B1%5D%5Bdata%5D=nama_usaha&columns%5B1%5D%5Bname%5D=nama_usaha&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=false&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B2%5D%5Bdata%5D=alamat_usaha&columns%5B2%5D%5Bname%5D=alamat_usaha&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=false&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B3%5D%5Bdata%5D=kode_wilayah&columns%5B3%5D%5Bname%5D=kode_wilayah&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=false&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B4%5D%5Bdata%5D=&columns%5B4%5D%5Bname%5D=kegiatan_usaha&columns%5B4%5D%5Bsearchable%5D=true&columns%5B4%5D%5Borderable%5D=false&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B5%5D%5Bdata%5D=&columns%5B5%5D%5Bname%5D=kontak_usaha&columns%5B5%5D%5Bsearchable%5D=true&columns%5B5%5D%5Borderable%5D=false&columns%5B5%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B5%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B6%5D%5Bdata%5D=skala_usaha&columns%5B6%5D%5Bname%5D=skala_usaha&columns%5B6%5D%5Bsearchable%5D=true&columns%5B6%5D%5Borderable%5D=false&columns%5B6%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B6%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B7%5D%5Bdata%5D=sumber_data&columns%5B7%5D%5Bname%5D=sumber_data&columns%5B7%5D%5Bsearchable%5D=true&columns%5B7%5D%5Borderable%5D=false&columns%5B7%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B7%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B8%5D%5Bdata%5D=&columns%5B8%5D%5Bname%5D=&columns%5B8%5D%5Bsearchable%5D=true&columns%5B8%5D%5Borderable%5D=false&columns%5B8%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B8%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B9%5D%5Bdata%5D=perusahaan_id&columns%5B9%5D%5Bname%5D=perusahaan_id&columns%5B9%5D%5Bsearchable%5D=true&columns%5B9%5D%5Borderable%5D=false&columns%5B9%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B9%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B10%5D%5Bdata%5D=kbli&columns%5B10%5D%5Bname%5D=kbli&columns%5B10%5D%5Bsearchable%5D=true&columns%5B10%5D%5Borderable%5D=false&columns%5B10%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B10%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B11%5D%5Bdata%5D=kategori&columns%5B11%5D%5Bname%5D=kategori&columns%5B11%5D%5Bsearchable%5D=true&columns%5B11%5D%5Borderable%5D=false&columns%5B11%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B11%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B12%5D%5Bdata%5D=latitude&columns%5B12%5D%5Bname%5D=latitude&columns%5B12%5D%5Bsearchable%5D=true&columns%5B12%5D%5Borderable%5D=false&columns%5B12%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B12%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B13%5D%5Bdata%5D=longitude&columns%5B13%5D%5Bname%5D=longitude&columns%5B13%5D%5Bsearchable%5D=true&columns%5B13%5D%5Borderable%5D=false&columns%5B13%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B13%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B14%5D%5Bdata%5D=nomor_telepon&columns%5B14%5D%5Bname%5D=nomor_telepon&columns%5B14%5D%5Bsearchable%5D=true&columns%5B14%5D%5Borderable%5D=false&columns%5B14%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B14%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B15%5D%5Bdata%5D=nomor_hp&columns%5B15%5D%5Bname%5D=nomor_hp&columns%5B15%5D%5Bsearchable%5D=true&columns%5B15%5D%5Borderable%5D=false&columns%5B15%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B15%5D%5Bsearch%5D%5Bregex%5D=false" \
"&columns%5B16%5D%5Bdata%5D=email&columns%5B16%5D%5Bname%5D=email&columns%5B16%5D%5Bsearchable%5D=true&columns%5B16%5D%5Borderable%5D=false&columns%5B16%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B16%5D%5Bsearch%5D%5Bregex%5D=false" \
"&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=asc"

# Headers
HEADERS = {
    "Host": "matchapro.web.bps.go.id",
    "Connection": "keep-alive",
    "sec-ch-ua-platform": "\"Windows\"",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "sec-ch-ua": "\"Google Chrome\";v=\"147\", \"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"147\"",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "sec-ch-ua-mobile": "?0",
    "Origin": "https://matchapro.web.bps.go.id",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://matchapro.web.bps.go.id/se2026",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
}

OUTPUT_EXCEL = "data_prelist_se2026.xlsx"
OUTPUT_CSV_FALLBACK = "data_prelist_se2026.csv"

DELAY_BETWEEN_REQUEST = 1.3
# ------------------------------------------------------

def parse_wilayah_from_html(html_content):
    """Parse kode wilayah dari HTML response"""
    wilayah = {
        "f_provinsi": "",
        "f_kabupaten": "",
        "f_kecamatan": "",
        "f_desa": "",
    }

    # Hapus karakter newline untuk stabilitas regex
    html_clean = html_content.replace('\n', ' ').replace('\r', ' ')

    # Cari f_provinsi yang selected - pattern fleksibel untuk handle whitespace
    prov_match = re.search(r'<select[^>]*id=["\']f_provinsi["\'][^>]*>.*?<option[^>]*value=["\'](\d+)["\'][^>]*selected', html_clean, re.DOTALL | re.IGNORECASE)
    if prov_match:
        wilayah["f_provinsi"] = prov_match.group(1)

    # Cari f_kabupaten yang selected
    kab_match = re.search(r'<select[^>]*id=["\']f_kabupaten["\'][^>]*>.*?<option[^>]*value=["\'](\d+)["\'][^>]*selected', html_clean, re.DOTALL | re.IGNORECASE)
    if kab_match:
        wilayah["f_kabupaten"] = kab_match.group(1)

    # Cari f_kecamatan yang selected (jika ada)
    kec_match = re.search(r'<select[^>]*id=["\']f_kecamatan["\'][^>]*>.*?<option[^>]*value=["\'](\d+)["\'][^>]*selected', html_clean, re.DOTALL | re.IGNORECASE)
    if kec_match:
        wilayah["f_kecamatan"] = kec_match.group(1)

    # Cari f_desa yang selected (jika ada)
    desa_match = re.search(r'<select[^>]*id=["\']f_desa["\'][^>]*>.*?<option[^>]*value=["\'](\d+)["\'][^>]*selected', html_clean, re.DOTALL | re.IGNORECASE)
    if desa_match:
        wilayah["f_desa"] = desa_match.group(1)

    return wilayah

def build_payload(start, length, _token, wilayah_filter=""):
    # Urutan sesuai working request_body:
    # BASE_PAYLOAD (draw, columns, order) + start + length + search + _token + wilayah
    payload = f"{BASE_PAYLOAD}&start={start}&length={length}&search%5Bvalue%5D=&search%5Bregex%5D=false&_token={quote(_token)}"
    if wilayah_filter:
        payload = f"{payload}&{wilayah_filter}"
    return payload

def fetch_page(start, length, _token, wilayah_filter=""):
    payload = build_payload(start, length, _token, wilayah_filter)

    try:
        r = requests.post(BASE_URL, data=payload, headers=HEADERS, timeout=20)
        if r.status_code == 419:
            print(f"CSRF error (419) - _token mungkin expired, coba jalankan ulang script")
        elif r.status_code == 400:
            print(f"400 Bad Request - Response: {r.text[:200]}")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error saat mengambil data (start={start}): {e}")
        return None

def main():
    print("Melakukan login otomatis...\n")

    username = input("Masukkan username: ")
    password = input("Masukkan password: ")
    otp_code = input("Masukkan OTP (kosongkan jika tidak ada): ").strip() or None

    page, browser = login_with_sso(username, password, otp_code)

    if not page:
        print("Login gagal. Tidak dapat melanjutkan scraping.")
        return

    _token = None
    try:
        url_gc = "https://matchapro.web.bps.go.id/se2026"
        page.goto(url_gc)
        page.wait_for_load_state('networkidle')

        page.wait_for_selector('meta[name="csrf-token"]', state='attached', timeout=10000)

        token_element = page.locator('meta[name="csrf-token"]')
        if token_element.count() > 0:
            _token = token_element.get_attribute('content')
            print(f"_token diperoleh: {_token}")
        else:
            print("Gagal mendapatkan _token")
            browser.close()
            return

        # Get cookies
        cookies = page.context.cookies()
        cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
        HEADERS["Cookie"] = cookie_string
        print("Cookies diperoleh dan diset ke headers")

        # Get selected values langsung dari DOM menggunakan JavaScript
        wilayah = {
            "f_provinsi": page.evaluate("document.getElementById('f_provinsi')?.value || ''"),
            "f_kabupaten": page.evaluate("document.getElementById('f_kabupaten')?.value || ''"),
            "f_kecamatan": page.evaluate("document.getElementById('f_kecamatan')?.value || ''"),
            "f_desa": page.evaluate("document.getElementById('f_desa')?.value || ''"),
        }
        print(f"Kode provinsi: {wilayah['f_provinsi']}")
        print(f"Kode kabupaten: {wilayah['f_kabupaten']}")
        print(f"Kode kecamatan: {wilayah['f_kecamatan']}")
        print(f"Kode desa: {wilayah['f_desa']}")

        # Build wilayah filter string
        # Server expects param names without f_ prefix, and requires all params present
        wilayah_params = {
            "provinsi": wilayah['f_provinsi'],
            "kabupaten": wilayah['f_kabupaten'],
            "kecamatan": wilayah['f_kecamatan'],
            "desa": wilayah['f_desa'],
        }
        wilayah_filter = "&".join(f"{k}={v}" for k, v in wilayah_params.items())
        print(f"Wilayah filter: {wilayah_filter}")

    except Exception as e:
        print(f"Error saat login atau ekstraksi: {e}")
        browser.close()
        return

    browser.close()

    print("Login berhasil. Memulai pengambilan data...\n")

    first_response = fetch_page(0, 100, _token, wilayah_filter)
    if not first_response or "recordsTotal" not in first_response:
        print("Gagal mendapatkan informasi awal.")
        print("Periksa kembali autentikasi dan koneksi internet")
        return

    total_records = first_response["recordsTotal"]
    print(f"Total data yang tersedia : {total_records:,} record")
    print(f"Output akan disimpan ke : {OUTPUT_EXCEL} dan {OUTPUT_CSV_FALLBACK}\n")

    all_records = []
    length_per_request = 1000

    with tqdm(total=total_records, desc="Progress", unit="record") as pbar:
        start = 0
        while start < total_records:
            data = fetch_page(start, length_per_request, _token, wilayah_filter)

            if not data or "data" not in data or not isinstance(data["data"], list):
                print(f"\nGagal di posisi start={start}. Mencoba lagi setelah jeda...")
                time.sleep(6)
                continue

            page_data = data["data"]
            all_records.extend(page_data)

            fetched_this_time = len(page_data)
            pbar.update(fetched_this_time)

            start += fetched_this_time

            time.sleep(DELAY_BETWEEN_REQUEST)

    if not all_records:
        print("\nTidak ada data yang berhasil dikumpulkan.")
        return

    print(f"\nSelesai收集 {len(all_records):,} record")

    # Normalisasi: None -> '', cleanup whitespace, nomor HP sudah benar dari API
    for record in all_records:
        for key in list(record.keys()):
            val = record[key]
            if val is None:
                record[key] = ''
            elif isinstance(val, str):
                record[key] = val.replace('\n', ' ').replace('\t', ' ').replace('\r', ' ')

    # DataFrame tanpa astype(str) agar None tetap '', bukan nan
    df = pd.DataFrame(all_records)

    print(f"Jumlah kolom yang didapat: {len(df.columns)}")
    print("Nama kolom:", ", ".join(df.columns.tolist()))

    # Simpan Excel - nomor_telepon & nomor_hp sebagai format text '@' agar +62-... tidak berubah
    try:
        import xlsxwriter
        writer = pd.ExcelWriter(OUTPUT_EXCEL, engine='xlsxwriter')
        df.to_excel(writer, index=False)
        workbook = writer.book
        text_fmt = workbook.add_format({'num_format': '@'})  # format text
        for col in ['nomor_telepon', 'nomor_hp']:
            if col in df.columns:
                col_idx = df.columns.get_loc(col)
                writer.sheets['Sheet1'].set_column(col_idx, col_idx, None, text_fmt)
        writer.close()
        print(f"\nBerhasil disimpan ke: {OUTPUT_EXCEL}")
    except Exception as e:
        print(f"Gagal simpan ke Excel: {e}")
        print("Mencoba fallback ke CSV...")

        try:
            df.to_csv(OUTPUT_CSV_FALLBACK, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_ALL)
            print(f"Berhasil disimpan ke: {OUTPUT_CSV_FALLBACK}")
        except Exception as e:
            print(f"Gagal menyimpan file: {e}")

if __name__ == "__main__":
    main()
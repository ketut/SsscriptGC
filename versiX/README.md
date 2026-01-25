### Versi X 
- Support auto generate OTP
- Auto relogin
- Deteksi VPN

>> `python tandaiKirimX.py <username> <password> [SECRET_KEY]`

Untuk dapat menggunakan auto generate OTP, harus mengisi SECRET_KEY
SECRET_KEY dapat diekstrak dari QRCODE export Google Authenticator
dengan menggunakan extraxt_otp_secrets
https://github.com/scito/extract_otp_secrets/releases
> screenshot qrcode export OTP di google authenticator
> extract `.\extract_otp_secrets_2.12.0_win_x86_64.exe screenshot.jpg`


## DISCLAIMER
- Pastikan untuk tetap menjaga kerahasiaan SECRET_KEY
- Jangan pernah diposting di medsos

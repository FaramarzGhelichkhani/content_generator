import ftplib
import os
import logging

logger = logging.getLogger(__name__)

class FTPDeployer:
    def __init__(self):
        # اطلاعات دایرکت‌ادمین خود را اینجا وارد کنید
        self.ftp_host = "195.28.168.13"  # مثال: "85.20.10.10"
        self.ftp_user = "deploy@remotecyclet.ir"     # مثال: "admin" یا "deploy@domain.com"
        self.ftp_pass = "mbL7X5F58y8AqdxV"
        
        # مسیری که فایل‌ها باید در آن آپلود شوند
        self.remote_base_dir = "/public_html/"

    def upload_file(self, local_file_path: str, remote_sub_dir: str) -> bool:
        try:
            # اتصال به سرور
            ftp = ftplib.FTP(self.ftp_host)
            ftp.login(self.ftp_user, self.ftp_pass)
            
            # رفتن به پوشه اصلی سایت
            ftp.cwd(self.remote_base_dir)
            
            # ساخت تو در توی پوشه‌ها در سرور (مثلاً /honda/click/)
            folders = remote_sub_dir.strip("/").split('/')
            for folder in folders:
                if folder:
                    try:
                        ftp.cwd(folder)
                    except ftplib.error_perm:
                        # اگر پوشه وجود نداشت، آن را می‌سازد و واردش می‌شود
                        ftp.mkd(folder)
                        ftp.cwd(folder)
            
            # آپلود فایل index.html
            file_name = os.path.basename(local_file_path)
            with open(local_file_path, 'rb') as file:
                ftp.storbinary(f'STOR {file_name}', file)
            
            ftp.quit()
            logger.info("آپلود با موفقیت انجام شد: %s", remote_sub_dir)
            return True
            
        except Exception as e:
            logger.error("خطا در آپلود FTP: %s", e)
            return False
        
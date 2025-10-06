import os
import shutil
import sys
from pathlib import Path

# সব ধরনের Temp / Cache / Prefetch ফোল্ডারের লিস্ট
folders = [
    os.environ.get('TEMP') or os.environ.get('TMP'),                # User Temp
    r"C:\Windows\Temp",                                             # Windows Temp
    r"C:\Windows\Prefetch",                                         # Prefetch
    r"C:\Windows\SoftwareDistribution\Download",                    # Windows Update cache
    str(Path.home() / "AppData" / "Local" / "Temp"),                # Local Temp
    str(Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "INetCache"),  # IE/Edge Cache
    str(Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Cache"),  # Chrome Cache
]

# ডুপ্লিকেট বাদ
folders = list(set([str(Path(f).resolve()) for f in folders if f]))

def remove_file(path):
    try:
        os.unlink(path)
        return True
    except:
        return False

def remove_folder(path):
    try:
        shutil.rmtree(path)
        return True
    except:
        return False

def main(skip_confirm=False):
    if not skip_confirm:
        print("⚠️ সতর্কতা: এই স্ক্রিপ্ট সব ধরণের TEMP / CACHE / PREFETCH ফাইল স্থায়ীভাবে মুছে ফেলবে!")
        confirm = input("চালিয়ে যেতে YES লিখো: ")
        if confirm.strip() != "YES":
            print("❌ বাতিল করা হলো।")
            return

    total_deleted = 0
    total_failed = 0

    for folder in folders:
        p = Path(folder)
        if not p.exists():
            continue
        print(f"🧹 ক্লিন করা হচ্ছে: {folder}")
        for root, dirs, files in os.walk(p, topdown=False):
            for fname in files:
                fpath = Path(root) / fname
                if remove_file(fpath):
                    total_deleted += 1
                else:
                    total_failed += 1
            for dname in dirs:
                dpath = Path(root) / dname
                if remove_folder(dpath):
                    total_deleted += 1
                else:
                    total_failed += 1

    print("\n--- ✅ সারসংক্ষেপ ---")
    print(f"ডিলিট হয়েছে: {total_deleted} ফাইল/ফোল্ডার")
    print(f"⚠️ ডিলিট হয়নি (Permission/Used): {total_failed}")

if __name__ == "__main__":
    skip = "--yes" in sys.argv
    main(skip_confirm=skip)

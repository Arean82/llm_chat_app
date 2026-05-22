import urllib.request
import zipfile
import os
import shutil

url = "https://use.fontawesome.com/releases/v6.4.0/fontawesome-free-6.4.0-web.zip"
zip_path = "fa.zip"
extract_dir = "fa_temp"
target_dir = "saas/static/fontawesome"

print("Downloading FontAwesome...")
urllib.request.urlretrieve(url, zip_path)

print("Extracting...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_dir)

print("Copying to static folder...")
if not os.path.exists(target_dir):
    os.makedirs(target_dir)

source_base = os.path.join(extract_dir, "fontawesome-free-6.4.0-web")
for folder in ["css", "webfonts"]:
    src = os.path.join(source_base, folder)
    dst = os.path.join(target_dir, folder)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

print("Cleaning up...")
os.remove(zip_path)
shutil.rmtree(extract_dir)

print("Done! FontAwesome is now in saas/static/fontawesome")

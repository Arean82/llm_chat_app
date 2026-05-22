import urllib.request
import re
import os

url = "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Outfit:wght@400;500;600;700;800&display=swap"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'}

req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as response:
        css = response.read().decode('utf-8')
except Exception as e:
    print(f"Error fetching CSS: {e}")
    exit(1)

# Find all url(...) in the css
urls = re.findall(r'url\((https://[^)]+)\)', css)

font_dir = "saas/static/fonts"
if not os.path.exists(font_dir):
    os.makedirs(font_dir)

# Download each font and replace URL
for font_url in set(urls):
    filename = font_url.split('/')[-1]
    filepath = os.path.join(font_dir, filename)
    
    print(f"Downloading {filename}...")
    try:
        req_font = urllib.request.Request(font_url, headers=headers)
        with urllib.request.urlopen(req_font) as response, open(filepath, 'wb') as out_file:
            out_file.write(response.read())
    except Exception as e:
        print(f"Error downloading {font_url}: {e}")
        
    # Replace URL in CSS to point to local
    css = css.replace(font_url, f"../fonts/{filename}")

# Save the local CSS
css_path = "saas/static/css/fonts.css"
with open(css_path, "w", encoding="utf-8") as f:
    f.write(css)

print("Done! Fonts downloaded to saas/static/fonts/ and CSS saved to saas/static/css/fonts.css")

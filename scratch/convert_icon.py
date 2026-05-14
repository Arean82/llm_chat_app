
from PIL import Image
import os

png_path = r"c:\Users\user\OneDrive\Desktop\python\llm_chat_app\resources\app_icon.png"
ico_path = r"c:\Users\user\OneDrive\Desktop\python\llm_chat_app\resources\app_icon.ico"

if os.path.exists(png_path):
    img = Image.open(png_path)
    # Windows icons usually contain multiple sizes
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, sizes=icon_sizes)
    print(f"Successfully converted {png_path} to {ico_path}")
else:
    print(f"Error: {png_path} not found.")

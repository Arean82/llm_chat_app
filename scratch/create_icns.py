
import icnsutil
import os
from PIL import Image

png_path = r"c:\Users\user\OneDrive\Desktop\python\llm_chat_app\resources\app_icon.png"
icns_path = r"c:\Users\user\OneDrive\Desktop\python\llm_chat_app\resources\app_icon.icns"

def create_icns():
    if not os.path.exists(png_path):
        print(f"Error: {png_path} not found.")
        return

    img = Image.open(png_path)
    icns = icnsutil.IcnsFile()

    # Standard macOS ICNS keys and their required resolutions
    # ic07=128, ic08=256, ic09=512, ic10=1024
    sizes = {
        'ic07': 128,
        'ic08': 256,
        'ic09': 512,
        'ic10': 1024,
    }

    for key, size in sizes.items():
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        temp_png = f"temp_{size}.png"
        resized.save(temp_png)
        # Note: Must use file= keyword argument as per library source
        icns.add_media(key, file=temp_png)
        os.remove(temp_png)

    icns.write(icns_path)
    print(f"Successfully created {icns_path}")

if __name__ == "__main__":
    create_icns()

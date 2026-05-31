import os
from PIL import Image, ImageDraw

def create_squircle_mask(size, radius):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask

def process_icon():
    # Paths
    scratch_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.dirname(scratch_dir)
    resources_dir = os.path.join(target_dir, "resources")
    app_icon_path = os.path.join(resources_dir, "app_icon.png")
    
    if not os.path.exists(app_icon_path):
        print(f"Error: {app_icon_path} not found.")
        return
        
    try:
        img = Image.open(app_icon_path).convert("RGBA")
        
        # 1. Apply transparent squircle mask
        # Typically app icons have a border radius of about 22.5% of the size
        radius = int(img.size[0] * 0.225)
        mask = create_squircle_mask(img.size, radius)
        img.putalpha(mask)
        
        # Save transparent master PNG
        transparent_path = os.path.join(resources_dir, "app_icon_transparent.png")
        img.save(transparent_path, "PNG")
        print("✅ Created transparent squircle PNG (app_icon_transparent.png)")
        
        # 2. Generate multi-resolution Windows .ico
        icon_sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
        ico_path = os.path.join(resources_dir, "app_icon.ico")
        img.save(ico_path, format="ICO", sizes=icon_sizes)
        print("✅ Generated dynamic resolution Windows .ico")
        
        # 3. Generate Mac .icns (if supported by Pillow)
        try:
            icns_path = os.path.join(resources_dir, "app_icon.icns")
            img.save(icns_path, format="ICNS")
            print("✅ Generated macOS compatible .icns")
        except Exception as e:
            print(f"⚠️ Pillow doesn't support ICNS on this environment: {e}")
            
        # 4. Generate Linux .png
        linux_path = os.path.join(resources_dir, "app_icon_linux.png")
        img.resize((512, 512), Image.Resampling.LANCZOS).save(linux_path, "PNG")
        print("✅ Generated Linux .png (512x512)")
        
    except Exception as e:
        print(f"Error processing image: {e}")

if __name__ == "__main__":
    process_icon()

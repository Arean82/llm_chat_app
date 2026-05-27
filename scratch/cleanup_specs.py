import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

unwanted_specs = [
    "LLM_Chat_App_combined.spec",
    "LLM_Chat_App_full.spec",
    "LLM_Chat_App_single.spec"
]

for spec in unwanted_specs:
    spec_path = os.path.join(root_dir, spec)
    if os.path.exists(spec_path):
        os.remove(spec_path)
        print(f"🗑️ Deleted: {spec}")
    else:
        print(f"⚠️ Not found: {spec}")

print("\n✅ Verification - Current Spec Files in Root:")
for f in os.listdir(root_dir):
    if f.endswith(".spec"):
        print(f"  - {f}")

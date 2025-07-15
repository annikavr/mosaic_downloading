import os
import re
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

# === Configuration ===
base_url = "https://pds-imaging.jpl.nasa.gov/data/mars2020/mars2020_mastcamz/"
output_root = "/Users/alanaarchbold/Desktop/jezero"
valid_extensions = (".png", ".jpg", ".jpeg")

# === Step 1: Get list of available Sol folders ===
def get_sols():
    r = requests.get(base_url)
    soup = BeautifulSoup(r.text, "html.parser")
    sols = []
    for link in soup.find_all("a"):
        href = link.get("href")
        if href and href.startswith("sol"):
            sols.append(href.strip("/"))
    return sols

# === Step 2: Get image filenames from a sol ===
def get_filenames_from_sol(sol):
    url = f"{base_url}{sol}/browse/"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    filenames = []
    for link in soup.find_all("a"):
        name = link.get("href")
        if name and name.endswith(valid_extensions):
            filenames.append((url + name, name))
    return filenames

# === Step 3: Filter and group ===
def extract_info(filename):
    # Example: ZLF_0089_0674855109_239RAD_N0040048ZCAM08050_034085J03.png
    match = re.match(r"(ZL[F|R])_(\d{4})_(\d+)_\d+([A-Z]{3})_([N|T])[0-9A-Z]+(ZCAM\d+)_.*", filename)
    if not match:
        return None
    camera, sol, timestamp, product, thumbnail_flag, seq_id = match.groups()
    return {
        "camera": camera,
        "sol": f"sol{sol}",
        "timestamp": timestamp,
        "product": product,
        "thumbnail": thumbnail_flag,
        "sequence": seq_id
    }

def group_images(filenames):
    groups = {}
    for url, fname in filenames:
        info = extract_info(fname)
        if not info:
            continue
        if info["camera"] != "ZLF":
            continue
        if info["product"] != "RAD":
            continue
        if info["thumbnail"] != "N":
            continue
        sol = info["sol"]
        seq = info["sequence"]
        groups.setdefault(sol, {}).setdefault(seq, []).append((url, fname))
    return groups

# === Step 4: Download ===
def download_images(grouped_images):
    for sol, seqs in grouped_images.items():
        for seq_id, files in seqs.items():
            folder = os.path.join(output_root, sol, seq_id)
            os.makedirs(folder, exist_ok=True)
            for url, fname in tqdm(files, desc=f"Downloading {sol}/{seq_id}", leave=False):
                out_path = os.path.join(folder, fname)
                if not os.path.exists(out_path):
                    try:
                        img_data = requests.get(url, timeout=10).content
                        with open(out_path, "wb") as f:
                            f.write(img_data)
                    except Exception as e:
                        print(f"Failed to download {url}: {e}")

# === Main ===
def main():
    sols = get_sols()
    for sol in tqdm(sols, desc="Processing Sols"):
        try:
            filenames = get_filenames_from_sol(sol)
            grouped = group_images(filenames)
            download_images(grouped)
        except Exception as e:
            print(f"Error processing {sol}: {e}")

if __name__ == "__main__":
    main()

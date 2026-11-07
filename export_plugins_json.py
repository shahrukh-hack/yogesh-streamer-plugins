import os
import glob
import zipfile
import json
import re

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGINS_JSON = os.path.join(REPO_DIR, "plugins.json")

with open(PLUGINS_JSON, "r", encoding="utf-8") as f:
    plugin_manifests = json.load(f)

manifest_by_name = {}
for p in plugin_manifests:
    manifest_by_name[p.get("internalName")] = p
    manifest_by_name[p.get("name")] = p

cs3_files = glob.glob(os.path.join(REPO_DIR, "*.cs3"))
catalog = []

for cs3_path in cs3_files:
    filename = os.path.basename(cs3_path)
    base_name = filename.replace(".cs3", "")
    manifest_info = manifest_by_name.get(base_name) or {}

    entry = {
        "id": base_name,
        "name": manifest_info.get("name") or base_name,
        "internalName": base_name,
        "version": manifest_info.get("version") or 1,
        "types": manifest_info.get("tvTypes") or ["Movie", "TvSeries"],
        "iconUrl": manifest_info.get("iconUrl") or "https://raw.githubusercontent.com/shahrukh-hack/yogesh-streamer-plugins/builds/logo.jpg",
        "description": manifest_info.get("description") or f"High-speed {base_name} scraper stream provider",
        "fileSize": os.path.getsize(cs3_path),
        "cs3DownloadUrl": f"https://raw.githubusercontent.com/shahrukh-hack/yogesh-streamer-plugins/builds/{filename}",
        "manifest": {},
        "discoveredEndpoints": []
    }

    try:
        with zipfile.ZipFile(cs3_path, "r") as z:
            if "manifest.json" in z.namelist():
                m_data = json.loads(z.read("manifest.json").decode("utf-8", errors="ignore"))
                entry["manifest"] = m_data
                if "pluginClassName" in m_data:
                    entry["pluginClassName"] = m_data["pluginClassName"]
                if "version" in m_data:
                    entry["manifestVersion"] = m_data["version"]

            if "classes.dex" in z.namelist():
                dex_bytes = z.read("classes.dex")
                raw_urls = re.findall(rb'https?://[a-zA-Z0-9\.\-_/]+', dex_bytes)
                valid_urls = []
                seen = set()
                for ru in raw_urls:
                    try:
                        u = ru.decode("ascii")
                        if (len(u) > 10 and "." in u and 
                            not u.endswith(".dex") and 
                            not "schemas.android.com" in u and 
                            not "github.com" in u and 
                            not "w3.org" in u and
                            not "example.com" in u):
                            # extract origin/base URL
                            parts = u.split("/")
                            base_origin = parts[0] + "//" + parts[2]
                            if base_origin not in seen:
                                seen.add(base_origin)
                                valid_urls.append(base_origin)
                    except:
                        pass
                entry["discoveredEndpoints"] = valid_urls[:6]
    except Exception as e:
        entry["error"] = str(e)

    catalog.append(entry)

out_file = os.path.join(REPO_DIR, "plugins_catalog.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2)

print(f"Successfully generated {out_file} with {len(catalog)} reverse-engineered plugins!")

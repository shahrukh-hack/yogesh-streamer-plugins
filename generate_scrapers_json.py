import sys
sys.stdout.reconfigure(encoding='utf-8')

import zipfile
import re
import os
import json

base_dir = r'C:\Users\yoges\.gemini\antigravity\scratch\yogesh-streamer-plugins'
plugins_json_path = os.path.join(base_dir, 'plugins.json')
output_json_path = os.path.join(base_dir, 'scrapers.json')

with open(plugins_json_path, 'r', encoding='utf-8') as f:
    plugins_meta = json.load(f)

meta_map = {}
for p in plugins_meta:
    name = p.get('internalName') or p.get('name')
    if name:
        meta_map[name.lower()] = p

print(f"Loaded {len(plugins_meta)} plugins metadata from plugins.json")

def analyze_cs3(file_path):
    filename = os.path.basename(file_path)
    plugin_id = os.path.splitext(filename)[0]
    
    with zipfile.ZipFile(file_path, 'r') as z:
        manifest = {}
        if 'manifest.json' in z.namelist():
            try:
                manifest = json.loads(z.read('manifest.json').decode('utf-8'))
            except:
                pass
        
        dex_data = z.read('classes.dex')
    
    # Extract ASCII strings from DEX binary
    raw_strings = re.findall(rb'[\x20-\x7e]{4,}', dex_data)
    strings = [s.decode('latin-1', errors='ignore') for s in raw_strings]
    
    # Extract candidate URLs
    raw_urls = [s for s in strings if 'http://' in s or 'https://' in s]
    clean_urls = []
    ignore_domains = ['w3.org', 'schema.org', 'android.com', 'google.com', 'schemas.android.com', 'github.com', 'gitlab.com']
    
    for u in raw_urls:
        u = u.strip().strip('"').strip("'").strip('!').strip('$')
        if any(ign in u for ign in ignore_domains):
            continue
        if len(u) > 10 and (u.startswith('http://') or u.startswith('https://')):
            clean_urls.append(u)
    
    clean_urls = sorted(list(set(clean_urls)))
    
    # Extract potential domains
    domains = set()
    for u in clean_urls:
        m = re.search(r'https?://([^/:?#]+)', u)
        if m:
            d = m.group(1).lower()
            if not any(ign in d for ign in ignore_domains):
                domains.add(d)
                
    # Detect Stream types & capabilities
    has_m3u8 = any('.m3u8' in s.lower() for s in strings)
    has_mpd = any('.mpd' in s.lower() for s in strings)
    has_mkv = any('.mkv' in s.lower() for s in strings)
    has_clearkey = any('clearkey' in s.lower() for s in strings)
    
    meta_info = meta_map.get(plugin_id.lower(), {})
    tv_types = meta_info.get('tvTypes', [])
    
    # Key API / Scraper Endpoints
    api_endpoints = [u for u in clean_urls if any(k in u.lower() for k in ['/api/', 'playlist', '.m3u', '.json', 'search', 'graphql'])]
    
    return {
        "id": plugin_id,
        "name": manifest.get('name') or meta_info.get('name') or plugin_id,
        "internalName": plugin_id,
        "version": manifest.get('version') or meta_info.get('version') or 1,
        "pluginClass": manifest.get('pluginClassName', ''),
        "authors": meta_info.get('authors', ['Yogesh']),
        "language": meta_info.get('language', 'en'),
        "description": meta_info.get('description', ''),
        "iconUrl": meta_info.get('iconUrl', ''),
        "tvTypes": tv_types,
        "isLive": any(t in ['Live', 'LiveStream'] for t in tv_types) or any('cricket' in s.lower() or 'live' in s.lower() for s in strings[:100]),
        "streamCapabilities": {
            "hls": has_m3u8,
            "dash": has_mpd,
            "mkv": has_mkv,
            "drmClearKey": has_clearkey
        },
        "targetDomains": sorted(list(domains)),
        "apiEndpoints": api_endpoints[:10],
        "downloadUrl": meta_info.get('url', f"https://raw.githubusercontent.com/shahrukh-hack/yogesh-streamer-plugins/builds/{filename}"),
        "fileSize": os.path.getsize(file_path),
        "lastAnalyzed": "2026-11-07T22:00:00Z"
    }

scrapers = []
cs3_files = [f for f in os.listdir(base_dir) if f.endswith('.cs3')]
print(f"Analyzing {len(cs3_files)} .cs3 files ...")

for f in sorted(cs3_files):
    try:
        data = analyze_cs3(os.path.join(base_dir, f))
        scrapers.append(data)
        print(f"  * Processed: {data['name'].ljust(30)} ({len(data['targetDomains'])} domains, {len(data['apiEndpoints'])} endpoints)")
    except Exception as e:
        print(f"  ! Error on {f}: {e}")

with open(output_json_path, 'w', encoding='utf-8') as out:
    json.dump({
        "manifestVersion": 2,
        "totalScrapers": len(scrapers),
        "generatedAt": "2026-11-07T22:00:00Z",
        "scrapers": scrapers
    }, out, indent=2)

print(f"\n🎉 Successfully converted all {len(scrapers)} plugins into {output_json_path}!")

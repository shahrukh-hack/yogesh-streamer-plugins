import os, zipfile, struct, zlib, hashlib, json

def fix_dex_checksum_and_signature(dex_bytes: bytearray) -> bytearray:
    sha1 = hashlib.sha1(dex_bytes[32:]).digest()
    dex_bytes[12:32] = sha1
    adler = zlib.adler32(dex_bytes[12:]) & 0xffffffff
    dex_bytes[8:12] = struct.pack('<I', adler)
    return dex_bytes

def read_uleb128(data, p):
    result = 0
    shift = 0
    while True:
        b = data[p]
        p += 1
        result |= (b & 0x7f) << shift
        if not (b & 0x80): break
        shift += 7
    return result, p

def neutralize_dex(dex_bytes: bytearray) -> tuple:
    string_ids_size, string_ids_off = struct.unpack_from('<II', dex_bytes, 56)
    type_ids_size, type_ids_off = struct.unpack_from('<II', dex_bytes, 64)
    method_ids_size, method_ids_off = struct.unpack_from('<II', dex_bytes, 88)
    class_defs_size, class_defs_off = struct.unpack_from('<II', dex_bytes, 96)

    def get_string(idx):
        off = struct.unpack_from('<I', dex_bytes, string_ids_off + idx * 4)[0]
        p = off
        length = 0
        shift = 0
        while True:
            b = dex_bytes[p]
            p += 1
            length |= (b & 0x7f) << shift
            if not (b & 0x80): break
            shift += 7
        end = dex_bytes.find(b'\x00', p)
        return dex_bytes[p:end].decode('latin1', errors='ignore')

    def get_type(idx):
        str_idx = struct.unpack_from('<I', dex_bytes, type_ids_off + idx * 4)[0]
        return get_string(str_idx)

    def get_method(idx):
        c_idx, p_idx, n_idx = struct.unpack_from('<HHI', dex_bytes, method_ids_off + idx * 8)
        return get_type(c_idx), get_string(n_idx)

    patched_methods = 0
    for i in range(class_defs_size):
        off = class_defs_off + i * 32
        class_idx = struct.unpack_from('<I', dex_bytes, off)[0]
        class_data_off = struct.unpack_from('<I', dex_bytes, off + 24)[0]
        cname = get_type(class_idx)

        target_class = False
        target_method_names = []
        if 'Announcer' in cname and not '$' in cname:
            target_class = True
            target_method_names = ['showDialog', 'showOnHome', 'access$showDialog', 'fetchGoal']
        elif 'DonationManager' in cname and not '$' in cname:
            target_class = True
            target_method_names = ['checkAndShow', 'checkAndShow$default', 'fetchLatestMonthlyStats']

        if not target_class or class_data_off == 0:
            continue

        p = class_data_off
        sfields, p = read_uleb128(dex_bytes, p)
        ifields, p = read_uleb128(dex_bytes, p)
        dmethods, p = read_uleb128(dex_bytes, p)
        vmethods, p = read_uleb128(dex_bytes, p)
        for _ in range(sfields + ifields):
            _, p = read_uleb128(dex_bytes, p)
            _, p = read_uleb128(dex_bytes, p)

        midx = 0
        for _ in range(dmethods):
            midx_diff, p = read_uleb128(dex_bytes, p)
            midx += midx_diff
            access_flags, p = read_uleb128(dex_bytes, p)
            code_off, p = read_uleb128(dex_bytes, p)
            mclass, mname = get_method(midx)
            if mname in target_method_names and code_off != 0:
                dex_bytes[code_off + 16] = 0x0e
                dex_bytes[code_off + 17] = 0x00
                patched_methods += 1

        midx = 0
        for _ in range(vmethods):
            midx_diff, p = read_uleb128(dex_bytes, p)
            midx += midx_diff
            access_flags, p = read_uleb128(dex_bytes, p)
            code_off, p = read_uleb128(dex_bytes, p)
            mclass, mname = get_method(midx)
            if mname in target_method_names and code_off != 0:
                dex_bytes[code_off + 16] = 0x0e
                dex_bytes[code_off + 17] = 0x00
                patched_methods += 1

    replacements = [
        (b'https://allforu-goal.pages.dev/api/stats', b'http://127.0.0.1:9/null_api_stats_dummy/'),
        (b'https://allforu-goal.pages.dev', b'http://127.0.0.1:9/disable.php'),
        (b'https://supportbot.phisher2.workers.dev/', b'http://127.0.0.1:9/null_phisher_disable/'),
        (b'https://raw.githubusercontent.com/phisher98/TVVVV/main/goal.json', b'http://127.0.0.1:9/disabled_phisher_goal_offline_suppressed.json'),
        (b'https://raw.githubusercontent.com/KSHITIJ8473/raghav/master/goal.json', b'http://127.0.0.1:9/disabled_raghav_goal_offline_suppressed_dummy.json')
    ]
    for src, dst in replacements:
        if src in dex_bytes:
            dex_bytes = bytearray(bytes(dex_bytes).replace(src, dst))
            patched_methods += 1

    if patched_methods > 0:
        return fix_dex_checksum_and_signature(dex_bytes), patched_methods
    return None, 0

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return "sha256-" + h.hexdigest()

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    plugins_json_path = os.path.join(root, "plugins.json")
    
    plugins_data = []
    if os.path.exists(plugins_json_path):
        with open(plugins_json_path, "r", encoding="utf-8") as f:
            plugins_data = json.load(f)

    updated_any = False
    for f in os.listdir(root):
        if not f.endswith(".cs3"): continue
        p = os.path.join(root, f)
        
        entries = {}
        with zipfile.ZipFile(p, "r") as z:
            for item in z.infolist():
                entries[item.filename] = z.read(item.filename)
                
        if "classes.dex" not in entries: continue
        dex = bytearray(entries["classes.dex"])
        new_dex, count = neutralize_dex(dex)
        if new_dex is not None:
            entries["classes.dex"] = bytes(new_dex)
            tmp_p = p + ".tmp"
            with zipfile.ZipFile(tmp_p, "w", compression=zipfile.ZIP_DEFLATED) as z_out:
                for fname, data in entries.items():
                    z_out.writestr(fname, data)
            os.replace(tmp_p, p)
            new_hash = sha256_file(p)
            new_size = os.path.getsize(p)
            print(f"  ✓ Neutralized {f} ({count} methods/strings patched, size {new_size})")

            # Update in plugins.json
            for entry in plugins_data:
                url = entry.get("url", "")
                if url.endswith("/" + f) or entry.get("internalName") + ".cs3" == f:
                    entry["fileHash"] = new_hash
                    entry["fileSize"] = new_size
                    updated_any = True

    if updated_any:
        with open(plugins_json_path, "w", encoding="utf-8") as f:
            json.dump(plugins_data, f, indent=4, ensure_ascii=False)
        print("✅ Updated plugins.json with new hashes and sizes.")

if __name__ == "__main__":
    main()

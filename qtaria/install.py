import hashlib
import json
import os
import subprocess
import base64
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTENSION_DIR = os.path.join(PROJECT_DIR, "extension")
KEY_FILE = os.path.join(EXTENSION_DIR, "key.pem")
MANIFEST_FILE = os.path.join(EXTENSION_DIR, "manifest.json")

BROWSERS = {
    "Google Chrome":         "google-chrome",
    "Google Chrome Beta":    "google-chrome-beta",
    "Chromium":              "chromium",
    "Brave":                 "BraveSoftware/Brave-Browser",
    "Brave Beta":            "BraveSoftware/Brave-Browser-Beta",
    "Brave Nightly":         "BraveSoftware/Brave-Browser-Nightly",
    "Microsoft Edge":        "microsoft-edge",
    "Microsoft Edge Beta":   "microsoft-edge-beta",
    "Microsoft Edge Dev":    "microsoft-edge-dev",
    "Vivaldi":               "vivaldi",
    "Vivaldi Snapshot":      "vivaldi-snapshot",
    "Opera":                 "opera",
    "Opera Beta":            "opera-beta",
    "Opera Developer":       "opera-developer",
    "Yandex Browser":        "yandex-browser",
}


def _check_openssl():
    try:
        subprocess.run(["openssl", "version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Error: openssl is required. Install it with: sudo apt install openssl")
        sys.exit(1)


def _ensure_key():
    os.makedirs(EXTENSION_DIR, exist_ok=True)
    if not os.path.exists(KEY_FILE):
        subprocess.run(
            [
                "openssl", "genpkey", "-algorithm", "RSA",
                "-out", KEY_FILE, "-pkeyopt", "rsa_keygen_bits:2048",
            ],
            check=True, capture_output=True,
        )
        print("✓ Generated extension signing key")
    return KEY_FILE


def _pubkey_b64(key_file):
    r = subprocess.run(
        ["openssl", "rsa", "-pubout", "-in", key_file, "-outform", "DER"],
        check=True, capture_output=True,
    )
    return base64.b64encode(r.stdout).decode()


def _extension_id(key_file):
    r = subprocess.run(
        ["openssl", "rsa", "-pubout", "-in", key_file, "-outform", "DER"],
        check=True, capture_output=True,
    )
    digest = hashlib.sha256(r.stdout).digest()[:16]
    chars = []
    for byte in digest:
        chars.append(chr(ord("a") + (byte >> 4)))
        chars.append(chr(ord("a") + (byte & 0x0f)))
    return "".join(chars)


def _update_manifest(key_b64):
    if not os.path.exists(MANIFEST_FILE):
        print(f"Error: {MANIFEST_FILE} not found")
        sys.exit(1)
    with open(MANIFEST_FILE) as f:
        m = json.load(f)
    m["key"] = key_b64
    with open(MANIFEST_FILE, "w") as f:
        json.dump(m, f, indent=2)
    print("✓ Updated extension manifest with signing key")


def _find_browsers():
    config_dir = os.path.expanduser("~/.config")
    found = []
    for name, rel in BROWSERS.items():
        path = os.path.join(config_dir, rel)
        if os.path.isdir(path):
            nm_dir = os.path.join(path, "NativeMessagingHosts")
            os.makedirs(nm_dir, exist_ok=True)
            found.append((name, nm_dir))
    return found


def _choose_browsers(found):
    if not found:
        print("No Chromium-based browsers detected.")
        return _manual_path()

    print("Detected Chromium-based browsers:\n")
    for i, (name, _) in enumerate(found, 1):
        print(f"  [{i}] {name}")
    print("  [m] Enter path manually")
    print()
    choice = input("Select browsers (e.g. 1,3, a=all) [a]: ").strip().lower()

    selected = []
    if choice in ("", "a"):
        selected = [nm_dir for _, nm_dir in found]
    elif choice == "m":
        return _manual_path()
    else:
        indices = set()
        for part in choice.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part)
                if 1 <= idx <= len(found):
                    indices.add(idx)
        if not indices:
            print("Invalid selection. Installing to all detected browsers.")
            selected = [nm_dir for _, nm_dir in found]
        else:
            selected = [found[idx - 1][1] for idx in sorted(indices)]

    return selected


def _manual_path():
    path = input("Enter browser config directory path: ").strip()
    if not path:
        print("No path provided. Aborting.")
        sys.exit(1)
    expanded = os.path.expanduser(path)
    if not os.path.isdir(expanded):
        print(f"Directory not found: {expanded}")
        sys.exit(1)
    nm_dir = os.path.join(expanded, "NativeMessagingHosts")
    os.makedirs(nm_dir, exist_ok=True)
    return [nm_dir]


def _install_to(browsers, nm_content):
    for nm_dir in browsers:
        dest = os.path.join(nm_dir, "com.qtaria.json")
        with open(dest, "w") as f:
            f.write(nm_content)
        print(f"  ✓ {dest}")


def install_chrome(browser_names=None):
    _check_openssl()
    key_file = _ensure_key()
    ext_id = _extension_id(key_file)
    pubkey = _pubkey_b64(key_file)
    _update_manifest(pubkey)

    host_path = os.path.join(PROJECT_DIR, "qtaria", "host.py")
    nm_manifest = {
        "name": "com.qtaria",
        "description": "QtAria Download Manager Host",
        "path": host_path,
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{ext_id}/"],
    }
    nm_content = json.dumps(nm_manifest, indent=2)

    found = _find_browsers()

    if browser_names:
        selected = []
        config_base = os.path.expanduser("~/.config")
        for name in browser_names:
            name = name.strip().lower()
            matched = False
            for display, rel in BROWSERS.items():
                if (rel.lower() == name or display.lower() == name
                        or name in rel.lower() or name in display.lower()):
                    path = os.path.join(config_base, rel)
                    if os.path.isdir(path):
                        nm_dir = os.path.join(path, "NativeMessagingHosts")
                        os.makedirs(nm_dir, exist_ok=True)
                        selected.append(nm_dir)
                        matched = True
                        print(f"  ✓ {display}")
                    else:
                        print(f"  ⚠ {display} not found at {path}")
                    break
            if not matched:
                # Try as raw path
                expanded = os.path.expanduser(name)
                if os.path.isdir(expanded):
                    nm_dir = os.path.join(expanded, "NativeMessagingHosts")
                    os.makedirs(nm_dir, exist_ok=True)
                    selected.append(nm_dir)
                else:
                    print(f"  ⚠ Unknown browser or path: {name}")
        if not selected:
            print("No valid browsers selected.")
            sys.exit(1)
    else:
        selected = _choose_browsers(found)

    _install_to(selected, nm_content)

    print()
    print(f"  Extension ID: {ext_id}")
    print(f"  Extension dir: {EXTENSION_DIR}")
    print()
    print("Next steps:")
    print(f"  1. Open chrome://extensions")
    print(f"  2. Enable Developer mode (top-right)")
    print(f"  3. Click 'Load unpacked' and select: {EXTENSION_DIR}")
    print(f"  4. Right-click any link → 'Download with QtAria'")


def list_browsers():
    found = _find_browsers()
    if not found:
        print("No Chromium-based browsers detected.")
    else:
        print("Detected browsers:")
        for name, path in found:
            print(f"  {name}  ({path})")

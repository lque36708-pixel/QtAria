# QtAria

A lightweight Qt5 frontend for aria2 with Chrome right-click integration.

## Quick start

```bash
sudo apt install -y aria2 openssl
pip install --break-system-packages PyQt5
git clone https://github.com/lque36708-pixel/QtAria.git
cd QtAria
python3 -m qtaria install-chrome
```

Then open your browser's extension page:

| Browser | URL |
|---------|-----|
| Chrome | `chrome://extensions` |
| Chromium | `chrome://extensions` |
| Brave | `brave://extensions` |
| Edge | `edge://extensions` |
| Vivaldi | `vivaldi://extensions` |
| Opera | `opera://extensions` |

1. Enable **Developer mode**
2. Click **Load unpacked** → select the `extension/` folder
3. Right-click any link → **Download with QtAria**

## Usage

```bash
python3 -m qtaria                              # Launch manually
python3 -m qtaria install-chrome --list        # List detected browsers
python3 -m qtaria install-chrome --browser chrome,brave  # Non-interactive
```

Right-click a link in your browser → the app launches automatically, shows a slider for connection threads (1/4/8/16), downloads the file in a progress window, and quits when closed.

## Requirements

- Python 3.8+
- aria2 (`sudo apt install aria2`)
- PyQt5 (`pip install --break-system-packages PyQt5`)
- openssl (for extension setup)

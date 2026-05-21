# QtAria

A lightweight Qt5 frontend for aria2 with Chrome right-click integration.

## Quick start

```bash
git clone https://github.com/lque36708-pixel/QtAria.git
cd QtAria
pip install PyQt5
python -m qtaria install-chrome
```

Then:
1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `extension/` folder
4. Right-click any link → **Download with QtAria**

## Usage

```bash
python -m qtaria                              # Launch manually
python -m qtaria install-chrome --list        # List detected browsers
python -m qtaria install-chrome --browser chrome,brave  # Non-interactive
```

Right-click a link in Chrome → the app launches automatically, shows a slider for connection threads (1/4/8/16), downloads the file in a progress window, and quits when closed.

## Requirements

- Python 3.8+
- aria2 (`sudo apt install aria2`)
- PyQt5 (`pip install PyQt5`)
- openssl (for extension setup)

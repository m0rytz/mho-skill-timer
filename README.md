# MHO Skill Timer

![Architecture Diagram](https://res.cloudinary.com/dma7qzcya/image/upload/v1761424031/skill-timer-screen1_cgyuow.png)

A customizable hotkey-based timer application for tracking skill or buff cooldowns. (6 Keys Max)

## Features

- **Hotkey-based timers**: Press any configured key to start a timer
- **Overlay**: Always-on-top transparent window
- **Customizable configuration**: 
  - Set custom hotkeys and durations
  - Assign custom icons for each timer
  - Save/load configurations

## Quick Set-up

1. **Download from: **
   https://github.com/m0rytz/mho-skill-timer/releases

2. **Start the .exe**


## Python Set-up

1. **Clone repo**:
   ```bash
   git clone https://github.com/m0rytz/mho-skill-timer.git
   ```

2. **Install dependencies**:
   ```bash
   pip install keyboard pillow tkinter
   ```

3. **Run the application**:
   ```bash
   python path/to/timer.py
   ```

## Utility Controls

| Key | Action |
|-----|--------|
| `F1` | Open configuration window |
| `F2` | Toggle timer on/off |
| `F10` | Exit application |

## Configuration

### Using the GUI
1. Run MHO Timer.exe (or launch with Python). A green "X" will appear on your screen's top-left corner to indicate the timer is active - red when it's paused.
2. Press `F1` to open the configuration window
3. Modify hotkeys, durations, and icon paths
4. Click "Save" to apply changes

### Manual Configuration
Edit `timer_config.txt`:
```
[key]::[duration]
a::3.5
s::8.5
d::4.0
---ICONS---
[key]::[path/to/icon.png]
a::icons/custom_icon.png
s::icons/another_icon.png
---UTILITY_KEYS---
open_gui::f1
toggle_active::f2
exit::f10
```

## Requirements

- Python 3.6+
- `keyboard` - For global hotkey detection
- `Pillow` - For image processing
- `tkinter` - For GUI

## TODO
- Assign multiple skill or buff displays to a single key for improved tracking.
- Custom overlay position (horizontal, vertical, drag).

## License

This project is open source. Feel free to modify and distribute as needed.

## Contributing

Contributions are welcome! Please feel free to submit issues and enhancement requests.

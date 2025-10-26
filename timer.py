import os
import sys
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import keyboard
from PIL import Image, ImageTk


def resource_path(relative_path):
    """
    Get absolute path to resource, works for both development and PyInstaller executable.
    """
    try:
        # PyInstaller
        base_path = sys._MEIPASS
    except Exception:
        # When running as a .py
        base_path = os.path.abspath(".")

    # Ensure the path separator is correct for the internal structure
    return os.path.join(base_path, relative_path)


# --- 1. CONFIGURATION AND GLOBAL STATUS ---
# Define fixed constants for the application.
ICON_SIZE = (28, 28)
CONFIG_FILE = "timer_config.txt"
DEFAULT_ICON_PATH = resource_path("icons/default_icon.png")
DEFAULT_COLOR = "cyan"

# Default Utility Hotkeys
CONFIG_KEY_OPEN_GUI = "f1"
CONFIG_KEY_TOGGLE_ACTIVE = "f2"
CONFIG_KEY_EXIT = "f10"

# Default Timer Configuration: (Key, Duration)
TIMER_CONFIGS = [("q", 2.0), ("w", 3.5), ("e", 4.0), ("r", 4.5), ("t", 5.0), ("y", 5.5)]

# Icon paths, keyed by timer key.
ICON_PATHS = {
    "q": DEFAULT_ICON_PATH,
    "w": DEFAULT_ICON_PATH,
    "e": DEFAULT_ICON_PATH,
    "r": DEFAULT_ICON_PATH,
    "t": DEFAULT_ICON_PATH,
    "y": DEFAULT_ICON_PATH,
}


# Global status variables
active_timers = {}
timers_active = True
timer_lock = threading.Lock()
hotkey_listeners = []

# GUI variables
gui_root = None
timer_labels = {}
timer_icons = {}
timer_frames = {}
config_window = None

status_root = None
status_label = None


# --- CONFIGURATION FILE HANDLING ---
def load_config():
    """
    Loads timer configurations, icon paths, and utility hotkeys from the CONFIG_FILE.
    If the file is missing, it creates the default configuration using save_config().
    It updates the global variables TIMER_CONFIGS, ICON_PATHS, and utility keys.
    """
    global TIMER_CONFIGS, ICON_PATHS
    global CONFIG_KEY_OPEN_GUI, CONFIG_KEY_TOGGLE_ACTIVE, CONFIG_KEY_EXIT

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                new_configs = []
                new_icon_paths = {}
                lines = f.readlines()

                config_section = "TIMERS"

                for line in lines:
                    line = line.strip()
                    if line == "---ICONS---":
                        config_section = "ICONS"
                        continue
                    if line == "---UTILITY_KEYS---":
                        config_section = "UTILITY_KEYS"
                        continue

                    if not line:
                        continue

                    parts = line.split("::")
                    if len(parts) < 2:
                        continue

                    key, value = parts[0], parts[1]

                    if config_section == "TIMERS":
                        # Timer Configs: Key::Duration
                        try:
                            new_configs.append((key, float(value)))
                        except ValueError:
                            print(f"Skipping invalid duration: {line}")

                    elif config_section == "ICONS":
                        # Icon Paths: Key::Path
                        new_icon_paths[key] = value

                    elif config_section == "UTILITY_KEYS":
                        # Utility Keys: Name::Key
                        if key == "open_gui":
                            CONFIG_KEY_OPEN_GUI = value.lower()
                        elif key == "toggle_active":
                            CONFIG_KEY_TOGGLE_ACTIVE = value.lower()
                        elif key == "exit":
                            CONFIG_KEY_EXIT = value.lower()

                if new_configs:
                    TIMER_CONFIGS = new_configs

                # Update ICON_PATHS using the loaded config keys, falling back to default icon
                current_keys = [c[0] for c in TIMER_CONFIGS]
                ICON_PATHS = {
                    key: new_icon_paths.get(key, DEFAULT_ICON_PATH)
                    for key in current_keys
                }

                if new_configs or new_icon_paths:
                    print("--- Configuration loaded from file. ---")
        except Exception as e:
            print(f"Error loading config file: {e}")
    else:
        # Configuration file is MISSING: create the default one.
        print(f"Configuration file '{CONFIG_FILE}' not found. Creating default config.")
        save_config()


def save_config(new_configs=None, new_icon_paths=None, new_utility_keys=None):
    """
    Saves the current global configuration (or provided configurations) to the CONFIG_FILE.
    It updates the global variables TIMER_CONFIGS, ICON_PATHS, and utility keys if new values are provided.
    """
    # The fix for the SyntaxError: all globals that are *reassigned* must be declared here.
    global TIMER_CONFIGS, ICON_PATHS
    global CONFIG_KEY_OPEN_GUI, CONFIG_KEY_TOGGLE_ACTIVE, CONFIG_KEY_EXIT

    # Use globals if no new config is provided (for initial startup save)
    configs_to_save = new_configs if new_configs is not None else TIMER_CONFIGS
    paths_to_save = new_icon_paths if new_icon_paths is not None else ICON_PATHS

    # Define utility keys to save
    if new_utility_keys:
        utility_keys_to_save = new_utility_keys
    else:
        # Use existing globals if no new ones are provided
        utility_keys_to_save = {
            "open_gui": CONFIG_KEY_OPEN_GUI,
            "toggle_active": CONFIG_KEY_TOGGLE_ACTIVE,
            "exit": CONFIG_KEY_EXIT,
        }

    try:
        with open(CONFIG_FILE, "w") as f:
            # 1. Write Timer Configs section
            for key, duration in configs_to_save:
                f.write(f"{key}::{duration}\n")

            # 2. Write Separator for Icons
            f.write("---ICONS---\n")

            # 3. Write Icon Paths section
            for key, path in paths_to_save.items():
                f.write(f"{key}::{path}\n")

            # 4. Write Separator for Utility Keys
            f.write("---UTILITY_KEYS---\n")

            # 5. Write Utility Keys
            for name, key in utility_keys_to_save.items():
                f.write(f"{name}::{key}\n")

        print("--- Configuration saved to file. ---")

        # Update global variables after successful save if new configs were provided
        if new_configs is not None:
            TIMER_CONFIGS = new_configs
            ICON_PATHS = paths_to_save

        # Update global utility keys if new ones were provided
        if new_utility_keys:
            CONFIG_KEY_OPEN_GUI = new_utility_keys["open_gui"]
            CONFIG_KEY_TOGGLE_ACTIVE = new_utility_keys["toggle_active"]
            CONFIG_KEY_EXIT = new_utility_keys["exit"]

    except Exception as e:
        print(f"Error saving config file: {e}")


# Load the config immediately at startup
load_config()

# --- 2. GUI OVERLAY & STATUS WINDOW SETUP ---


def create_status_window():
    """
    Creates a small, always-on-top, transparent status indicator window
    in the top-left corner to show if timers are ACTIVE or PAUSED.
    """
    global status_root, status_label

    if status_root and status_root.winfo_exists():
        return

    status_root = tk.Toplevel(gui_root)
    status_root.title("Status")
    status_root.overrideredirect(True)
    status_root.wm_attributes("-topmost", True)
    status_root.config(bg="#010101", padx=5, pady=5)
    status_root.wm_attributes("-transparentcolor", "#010101")
    status_root.geometry("+10+10")

    # Changed indicator text to 'T' for brevity in the status window
    status_label = tk.Label(
        status_root,
        text="X",
        font=("Helvetica", 8, "bold"),
        fg="lime green",
        bg="#010101",
    )
    status_label.pack()


def update_status_indicator():
    """
    Updates the text and color of the status window based on the global `timers_active` status.
    This is called via `gui_root.after` to ensure thread-safe GUI updates.
    """
    if status_label and status_root:
        if timers_active:
            text = "X"
            color = "lime green"
        else:
            text = "X"
            color = "red"

        try:
            gui_root.after(0, lambda: status_label.config(text=text, fg=color))
        except RuntimeError:
            pass


def load_image(key, color):
    """
    Loads the icon image associated with a timer key. If the path is the default
    or the file is not found, it generates a solid-colored placeholder image.
    The image is resized and converted to a Tkinter PhotoImage object.
    """
    # Get the key-specific path
    file_path = ICON_PATHS.get(key, DEFAULT_ICON_PATH)

    try:
        # Check if the path points to the bundled default icon or is invalid
        is_default = (file_path == DEFAULT_ICON_PATH) or (not os.path.exists(file_path))

        if is_default:
            # Use the provided color for the placeholder image
            img = Image.new("RGB", ICON_SIZE, color)
        else:
            img = Image.open(file_path)
            # Use Image.Resampling.LANCZOS for better quality resizing
            img = img.resize(ICON_SIZE, Image.Resampling.LANCZOS)

        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"Error loading image {file_path}: {e}")
        # Fallback to a solid red placeholder on error
        return ImageTk.PhotoImage(Image.new("RGB", ICON_SIZE, "red"))


def create_overlay():
    """
    Initializes the main Tkinter window (the transparent overlay), sets its properties
    (always-on-top, transparent background), and creates the label/icon elements
    for all configured timers, INITIALLY SKIPPING ANY TIMER WITH DURATION <= 0.
    """
    global gui_root

    # Ensure Tk() is called only once
    if gui_root is None:
        root = tk.Tk()
        gui_root = root
    else:
        root = gui_root

    root.title("Transparent Timer Status")
    root.wm_attributes("-topmost", True)
    root.overrideredirect(True)
    root.config(bg="#010101")
    root.wm_attributes("-transparentcolor", "#010101")
    root.geometry(f"+700+880")

    main_timer_frame = tk.Frame(root, bg="#010101")
    main_timer_frame.grid(row=0, column=0, padx=5, pady=5)

    # Filter out zero/negative duration timers for display and size calculation
    valid_configs = [c for c in TIMER_CONFIGS if c[1] > 0]

    # Calculate width based on the maximum duration string length
    max_duration_digits = (
        len(f"{max(c[1] for c in valid_configs):.2f}") if valid_configs else 5
    )

    for i, (key, duration) in enumerate(TIMER_CONFIGS):

        # --- MODIFICATION: Skip if duration is 0 or less ---
        if duration <= 0:
            # Ensure any old reference to this key's frame is cleared, in case of restart
            if key in timer_frames:
                timer_frames[key].destroy()
                del timer_frames[key]
                if key in timer_labels:
                    del timer_labels[key]
                if key in timer_icons:
                    del timer_icons[key]
            continue
        # --------------------------------------------------

        # Find the correct column index among only the valid timers
        try:
            config_index = [c[0] for c in valid_configs].index(key)
        except ValueError:
            # Should not happen if the check above passed, but as a safeguard
            continue

        timer_frame = tk.Frame(main_timer_frame, bg="#010101")
        timer_frame.grid(row=0, column=config_index, padx=10, pady=5)
        timer_frames[key] = timer_frame

        # Load image for the icon label
        photo_image = load_image(key, color=DEFAULT_COLOR)

        icon_label = tk.Label(timer_frame, image=photo_image, bg="#010101")
        icon_label.grid(row=0, column=0, pady=(0, 2))
        timer_icons[key] = photo_image  # Store image reference

        number_label = tk.Label(
            timer_frame,
            text=f"{duration:.2f}",
            font=("Courier", 14, "normal"),
            fg=DEFAULT_COLOR,
            bg="#010101",
            width=max_duration_digits + 1,
        )
        number_label.grid(row=1, column=0)
        timer_labels[key] = number_label

        # Initially hide the timer
        timer_frame.grid_forget()

    if gui_root.state() != "normal" and not timer_frames:
        gui_root.withdraw()

    create_status_window()


def update_gui_text(key, text, color=None):
    """
    Thread-safe function to update the overlay text and color for a specific key's label.
    It uses `gui_root.after` to schedule the update in the main thread.
    It also ensures the timer frame is visible (gridded).
    """
    if key in timer_labels:
        # Use default color unless specified otherwise
        color = color if color else DEFAULT_COLOR

        try:
            gui_root.after(0, lambda: timer_labels[key].config(text=text, fg=color))
            # Find index by key and grid the frame

            # Use the list of currently displayed (valid) timer keys for correct column index
            valid_keys = [c[0] for c in TIMER_CONFIGS if c[1] > 0]
            config_index = valid_keys.index(key)

            gui_root.after(
                0,
                lambda: timer_frames[key].grid(
                    row=0, column=config_index, padx=10, pady=5
                ),
            )
        except RuntimeError:
            pass
        except ValueError:
            # This handles the case where key is valid but duration was set to <= 0
            # and thus the frame doesn't exist. No action needed, just skip.
            pass


# --- 3. TIMER & VISIBILITY FUNCTIONS ---


def check_visibility():
    """
    Checks if any timer thread in `active_timers` is running.
    If no timers are active, it hides the main overlay window (`gui_root.withdraw`).
    Otherwise, it ensures the window is shown (`gui_root.deiconify`).
    """
    with timer_lock:
        # Check if ANY thread in active_timers dictionary is alive
        is_any_timer_active = any(t.is_alive() for t in active_timers.values())

    try:
        if is_any_timer_active:
            gui_root.after(0, gui_root.deiconify)
        else:
            gui_root.after(0, gui_root.withdraw)
    except RuntimeError:
        pass


def run_timer(duration, key, thread_instance):
    """
    The main timer function that runs inside a separate thread.
    It updates the GUI label with the remaining time every 0.01 seconds.
    It checks a stop signal to terminate early (for restart/cleanup).
    When finished, it hides the timer element and cleans up the `active_timers` dictionary.
    """
    start_time = time.time()
    active_color = DEFAULT_COLOR

    # Initial color for a fresh timer remains yellow
    if key in timer_labels:  # Only update if the label was created (duration > 0)
        update_gui_text(key, f"{duration:.2f}", "yellow")

    while (time.time() - start_time) < duration:
        # Check if a restart/cleanup signal was sent
        if hasattr(thread_instance, "stop_signal") and thread_instance.stop_signal:
            # When stopped, reset the display to full duration in yellow
            try:
                full_duration = next(c[1] for c in TIMER_CONFIGS if c[0] == key)
                if key in timer_labels:
                    update_gui_text(key, f"{full_duration:.2f}", "yellow")
            except StopIteration:
                pass
            return

        remaining = duration - (time.time() - start_time)
        display_text = f"{remaining:.2f}"
        if key in timer_labels:  # Only update if the label was created (duration > 0)
            update_gui_text(key, display_text, active_color)
        time.sleep(0.01)

    # Timer finished: hide the element
    if key in timer_frames:  # Only try to hide if the frame was created
        try:
            gui_root.after(0, lambda: timer_frames[key].grid_forget())
        except RuntimeError:
            pass

    with timer_lock:
        if key in active_timers:
            del active_timers[key]
    check_visibility()


def start_timer(key, duration):
    """
    Stops any currently running timer for the given key and immediately starts a new timer
    thread for the full duration (RESTART functionality).
    It ensures the main overlay window is visible.

    The initial check to prevent running/displaying zero-duration timers.
    """
    # --- MODIFICATION: Check for zero/negative duration here as a final safeguard ---
    if duration <= 0:
        return
    # -------------------------------------------------------------------------------

    if not timers_active:
        return

    with timer_lock:
        if key in active_timers and active_timers[key].is_alive():
            old_thread = active_timers[key]
            old_thread.stop_signal = True
            old_thread.join(timeout=0.1)

        # Create new thread instance
        t = threading.Thread(target=run_timer, args=(duration, key, None))
        t.stop_signal = False
        t.name = f"Timer-{key.upper()}"
        t.daemon = True

        # Hack to pass the thread instance 't' to itself after creation (to check stop_signal)
        t._args = t._args[:-1] + (t,)

        active_timers[key] = t
        t.start()

    if gui_root:
        try:
            gui_root.after(0, gui_root.deiconify)

            # Find index by key and grid the frame to ensure correct order
            # Must use the list of valid keys for correct column index
            valid_keys = [c[0] for c in TIMER_CONFIGS if c[1] > 0]
            config_index = valid_keys.index(key)

            gui_root.after(
                0,
                lambda: timer_frames[key].grid(
                    row=0, column=config_index, padx=10, pady=5
                ),
            )
        except RuntimeError:
            pass


# --- 4. HOTKEY & UTILITY FUNCTIONS ---


def toggle_hotkeys():
    """
    Toggles the global `timers_active` status (ACTIVE/PAUSED).
    Prevents new timers from starting when PAUSED.
    Updates the small status indicator window.
    """
    global timers_active
    timers_active = not timers_active
    status = "ACTIVE" if timers_active else "PAUSED"
    print(f"--- Hotkeys Toggled: Currently {status} ---")
    update_status_indicator()


def exit_script():
    """
    Immediately terminates the entire Python process (daemon threads and Tkinter loop).
    """
    print("--- INSTANTLY EXITING SCRIPT (os._exit(0)) ---")
    os._exit(0)


def unbind_hotkeys():
    """
    Removes all dynamically bound timer hotkeys tracked in `hotkey_listeners`.
    """
    global hotkey_listeners
    # Note: 'keyboard' library remembers *all* hotkeys bound, only need to remove the dynamic ones.
    for key in hotkey_listeners:
        try:
            keyboard.remove_hotkey(key)
        except Exception:
            pass
    hotkey_listeners = []


def setup_hotkeys():
    """
    Removes existing hotkeys, then binds the configured utility keys (F1, F2, F10)
    and all dynamic timer keys (Q, W, E, etc.) to their respective functions.

    MODIFICATION: Skip binding if duration is 0 or less.
    """
    unbind_hotkeys()

    # Bind fixed keys using global config variables
    try:
        keyboard.add_hotkey(CONFIG_KEY_OPEN_GUI, open_config_gui, suppress=True)
        keyboard.add_hotkey(CONFIG_KEY_TOGGLE_ACTIVE, toggle_hotkeys, suppress=True)
        keyboard.add_hotkey(CONFIG_KEY_EXIT, exit_script, suppress=True)
    except Exception as e:
        # Handle cases where the configured utility key might be invalid or reserved
        print(f"Warning: Could not bind a utility key. Error: {e}")

    # Bind dynamic timer keys
    for key, duration in TIMER_CONFIGS:
        # --- MODIFICATION: Skip binding hotkey if duration is 0 or less ---
        if duration <= 0:
            print(f"Skipping hotkey bind for '{key}' (Duration: {duration:.2f}s)")
            continue
        # --------------------------------------------------------------------

        try:
            # Lambda captures current key and duration value
            keyboard.add_hotkey(key, lambda k=key, d=duration: start_timer(k, d))
            hotkey_listeners.append(key)
        except Exception as e:
            print(
                f"Warning: Could not bind timer key '{key}'. Is it reserved? Error: {e}"
            )

    print(f"--- Hotkeys Bound/Rebound. {CONFIG_KEY_OPEN_GUI.upper()} for Config. ---")


# --- 5. CONFIGURATION GUI LOGIC ---


def open_file_dialog(entry_ref):
    """
    Opens a file selection dialog to select an image file (PNG).
    If a file is selected, it updates the provided StringVar entry field with the file path.
    """
    file_path = filedialog.askopenfilename(
        title="Select Icon Image",
        filetypes=(("PNG files", "*.png"), ("All files", "*.*")),
    )
    if file_path:
        entry_ref.set(file_path)


def apply_and_restart(
    config_entries, icon_path_entries, utility_key_entries, config_window_ref
):
    """
    1. Collects and validates new configurations from the GUI entries.
    2. Saves the new configuration to the file and updates global variables.
    3. Signals all currently running timer threads to stop gracefully.
    4. Destroys the old GUI, recreates the overlay, and rebinds hotkeys in the main thread.
    """
    new_configs = []
    new_icon_paths = {}
    new_utility_keys = {}

    # 1. Collect new config data (Timer Keys & Durations)
    for i, (entry_key, entry_duration) in enumerate(config_entries):
        try:
            new_key = entry_key.get().strip().lower()
            if not new_key:
                messagebox.showerror(
                    "Error", f"Hot Key for timer {i+1} cannot be empty."
                )
                return
            new_duration = float(entry_duration.get())

            # Save the new 2-item config tuple
            new_configs.append((new_key, new_duration))

            # Collect Icon Path
            new_icon_paths[new_key] = icon_path_entries[i].get().strip()
        except ValueError:
            messagebox.showerror(
                "Error",
                f"Duration for timer {i+1} must be a number (integer or decimal).",
            )
            return
        except Exception as e:
            messagebox.showerror(
                "Error", f"Failed to read configuration for timer {i+1}: {e}"
            )
            return

    # 2. Collect new utility key data
    for name, entry in utility_key_entries.items():
        key_value = entry.get().strip().lower()
        if not key_value:
            messagebox.showerror(
                "Error",
                f"Utility key for '{name.replace('_', ' ').title()}' cannot be empty.",
            )
            return
        new_utility_keys[name] = key_value

    # 3. Save and Update Global Config (also writes to CONFIG_FILE)
    save_config(new_configs, new_icon_paths, new_utility_keys)

    # 4. Signal all running timers to stop gracefully
    with timer_lock:
        for key, t in active_timers.items():
            if t and t.is_alive():
                t.stop_signal = True

    # 5. Schedule the GUI recreation and hotkey rebind in the main thread
    def cleanup_and_recreate_in_main_thread():
        config_window_ref.destroy()

        # Clean up existing GUI elements
        for frame in timer_frames.values():
            frame.destroy()
        timer_frames.clear()
        timer_labels.clear()
        timer_icons.clear()

        # Recreate everything based on new global config values
        create_overlay()
        check_visibility()
        setup_hotkeys()

    if gui_root:
        gui_root.after(0, cleanup_and_recreate_in_main_thread)


def open_config_gui():
    """
    Creates and displays the dedicated configuration window (on F1 press).
    This window allows users to edit timer hotkeys, durations, icons, and utility hotkeys.
    It populates the input fields with current global values.
    """
    global config_window
    global icon_preview_refs

    if config_window and config_window.winfo_exists():
        config_window.lift()
        return

    config_window = tk.Toplevel(gui_root)
    config_window.title("MHO Timer Settings")
    config_window.geometry("700x530")
    config_window.attributes("-topmost", True)

    main_frame = tk.Frame(config_window, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # ----------------------------------------------------
    # Utility Keys Configuration
    # ----------------------------------------------------
    utility_frame = tk.LabelFrame(main_frame, text="Utility Hotkeys")
    utility_frame.pack(pady=10, padx=5, fill="x")

    utility_keys = {
        "open_gui": ("Open Settings Window", CONFIG_KEY_OPEN_GUI),
        "toggle_active": ("Toggle Timers", CONFIG_KEY_TOGGLE_ACTIVE),
        "exit": ("Exit Application", CONFIG_KEY_EXIT),
    }

    utility_key_entries = {}

    for i, (name, (label_text, default_key)) in enumerate(utility_keys.items()):
        row_num = i

        tk.Label(
            utility_frame, text=f"{label_text}:", font=("Helvetica", 9, "normal")
        ).grid(row=row_num, column=0, padx=10, pady=5, sticky="w")

        entry_key = tk.StringVar(value=default_key)
        key_entry = tk.Entry(utility_frame, textvariable=entry_key, width=10)
        key_entry.grid(row=row_num, column=1, padx=10, pady=5, sticky="w")

        utility_key_entries[name] = entry_key  # Store for saving

    # ----------------------------------------------------
    # Timer Configurations
    # ----------------------------------------------------
    timer_frame = tk.LabelFrame(main_frame, text="Timer Hotkeys")
    timer_frame.pack(pady=10, padx=5, fill="x")

    # Header Row (in timer_frame)
    tk.Label(timer_frame, text="Hot Key", font=("Helvetica", 10, "bold")).grid(
        row=0, column=0, padx=5, pady=5
    )
    tk.Label(timer_frame, text="Duration (s)", font=("Helvetica", 10, "bold")).grid(
        row=0, column=1, padx=5, pady=5
    )
    tk.Label(timer_frame, text="Icon Path", font=("Helvetica", 10, "bold")).grid(
        row=0, column=2, padx=5, pady=5
    )

    config_entries = []
    icon_path_entries = []
    icon_preview_refs = {}

    for i, (key, duration) in enumerate(TIMER_CONFIGS):
        row_num = i + 1

        # Key Entry (Column 0)
        entry_key = tk.StringVar(value=key)
        key_entry = tk.Entry(timer_frame, textvariable=entry_key, width=5)
        key_entry.grid(row=row_num, column=0, padx=5, pady=5)

        # Duration Entry (Column 1)
        entry_duration = tk.StringVar(value=str(duration))
        duration_entry = tk.Entry(timer_frame, textvariable=entry_duration, width=8)
        duration_entry.grid(row=row_num, column=1, padx=5, pady=5)

        # Icon Path Entry (Column 2)
        current_icon_path = ICON_PATHS.get(key, DEFAULT_ICON_PATH)
        entry_icon_path = tk.StringVar(value=current_icon_path)
        path_entry = tk.Entry(timer_frame, textvariable=entry_icon_path, width=60)
        path_entry.grid(row=row_num, column=2, padx=5, pady=5)

        # Icon Preview (Column 3)
        photo_image = load_image(key, color=DEFAULT_COLOR)
        icon_label = tk.Label(
            timer_frame, image=photo_image, width=ICON_SIZE[0], height=ICON_SIZE[1]
        )
        icon_label.grid(row=row_num, column=3, padx=5, pady=5)
        icon_preview_refs[key] = photo_image

        # Browse Button (Column 4)
        tk.Button(
            timer_frame,
            text="Browse",
            command=lambda ref=entry_icon_path: open_file_dialog(ref),
        ).grid(row=row_num, column=4, padx=5, pady=5)

        # Save the StringVar objects for applying changes
        config_entries.append((entry_key, entry_duration))
        icon_path_entries.append(entry_icon_path)

    # Save Button
    tk.Button(
        config_window,
        text="Save",
        command=lambda: apply_and_restart(
            config_entries, icon_path_entries, utility_key_entries, config_window
        ),
        font=("Helvetica", 8, "bold"),
    ).pack(pady=18)


# --- 6. MAIN EXECUTION ---
if __name__ == "__main__":

    # 1. Initialize the GUI (creates overlay and status windows)
    create_overlay()

    # 2. Setup hotkey listener in a daemon thread
    listener_thread = threading.Thread(target=setup_hotkeys, daemon=True)
    listener_thread.start()

    try:
        # 3. Initial status update
        update_status_indicator()

        # 4. Start the main GUI loop
        gui_root.mainloop()
    except Exception as e:
        print(f"\n!!! FATAL ERROR !!!\nDetails: {e}")

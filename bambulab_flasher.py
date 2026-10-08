# -*- coding: utf-8 -*-
import subprocess
import os
import sys
import re
import threading
import urllib.request
import zipfile
import io
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
import serial.tools.list_ports

# --- CONFIGURATION ---
PM3_EXE_NAME = "proxmark3.exe"
SETTINGS_FILE_NAME = "bambu_settings.ini"
DB_FILE_NAME = "RFID_Library.db"
ICON_FILE_NAME = "fuid.ico"
BAMBU_TAGS_REPO_URL = "https://github.com/queengooborg/Bambu-Lab-RFID-Library"
BAMBU_TAGS_ZIP_URL = "https://github.com/queengooborg/Bambu-Lab-RFID-Library/archive/refs/heads/main.zip"
DEFAULT_SETTINGS_CONTENT = r"COM1|0|.\Bambu-Lab-RFID-Library|.\Bambu-Lab-RFID-Library|0|.\Bambu-Lab-RFID-Library|https://github.com/queengooborg/Bambu-Lab-RFID-Library"
LIBRARY_CATEGORIES = {'PLA', 'PETG', 'ABS', 'ASA', 'PC', 'TPU', 'PA', 'Support Material'}
# ---------------------

class BambulabFlasherGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bambu Lab FUID Flasher")
        self.root.geometry("620x720")
        self.root.minsize(540, 600)
        
        # Modern Color Palette
        self.bg_color = "#f8fafc"        # Slate 50
        self.card_bg = "#ffffff"         # Pure White
        self.border_color = "#e2e8f0"    # Slate 200
        self.text_primary = "#0f172a"    # Slate 900
        self.text_secondary = "#475569"  # Slate 600
        
        self.root.configure(bg=self.bg_color)
        self.root.resizable(True, True)
        
        # Configure root grid weights for resizing
        self.root.rowconfigure(1, weight=1)  # Main container expands
        self.root.columnconfigure(0, weight=1)
        
        # Set the window icon
        self.set_window_icon()

        self.env = {}
        self.setup_environment()
        
        # UI State Variables
        self.dump_file_var = tk.StringVar()
        self.key_file_var = tk.StringVar()
        self.library_dir_var = tk.StringVar()
        self.repo_url_var = tk.StringVar(value=BAMBU_TAGS_REPO_URL)
        self.always_on_top_var = tk.BooleanVar(value=False)
        self.copy_clipboard_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready to flash or verify tags")
        self.cached_port_name = ""

        # Configure TTK Styles
        self.setup_styles()

        # --- MAIN CONTAINER ---
        main_container = tk.Frame(root, bg=self.bg_color)
        main_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(6, weight=1)  # Log container stretches vertically

        # --- HEADER & REPO (COMBINED COMPACT ROW) ---
        top_bar = tk.Frame(main_container, bg=self.bg_color)
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        top_bar.columnconfigure(1, weight=1)

        tk.Label(
            top_bar, text="Bambu Flasher", 
            font=("Segoe UI", 12, "bold"), bg=self.bg_color, fg=self.text_primary
        ).pack(side="left", padx=(0, 10))

        # Mini Repo Entry inside top bar to save vertical space
        repo_sub = tk.Frame(top_bar, bg=self.card_bg, highlightbackground=self.border_color, highlightthickness=1)
        repo_sub.pack(side="left", fill="x", expand=True)
        
        self.repo_entry = tk.Entry(
            repo_sub, textvariable=self.repo_url_var, 
            font=("Segoe UI", 8), bd=0, relief="flat"
        )
        self.repo_entry.pack(side="left", fill="x", expand=True, padx=6, ipady=2)
        self.repo_entry.bind("<KeyRelease>", lambda e: self.save_application_settings())

        tk.Button(
            repo_sub, text="Open URL", font=("Segoe UI", 7, "bold"),
            bg="#0284c7", fg="#ffffff", bd=0, relief="flat", padx=6, pady=2, cursor="hand2",
            command=self.open_repo_url
        ).pack(side="right", padx=2, pady=2)

        # --- COM PORT & SETTINGS BAR ---
        controls_frame = tk.Frame(main_container, bg=self.bg_color)
        controls_frame.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        controls_frame.columnconfigure(1, weight=1)

        port_card = self.create_card(controls_frame)
        port_card.pack(side="left", fill="both", expand=True, padx=(0, 4))
        
        port_inner = tk.Frame(port_card, bg=self.card_bg)
        port_inner.pack(fill="x", padx=8, pady=6)

        tk.Label(port_inner, text="Port:", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg=self.text_secondary).pack(side="left", padx=(0, 4))
        
        self.port_combobox = ttk.Combobox(port_inner, width=10, font=("Segoe UI", 8), state="readonly")
        self.port_combobox.pack(side="left", padx=(0, 4))
        
        tk.Button(
            port_inner, text="🔄", font=("Segoe UI", 8),
            bg="#f1f5f9", fg=self.text_primary, bd=0, relief="flat", padx=4, pady=1, cursor="hand2",
            command=self.refresh_com_ports
        ).pack(side="left")

        options_card = self.create_card(controls_frame)
        options_card.pack(side="right", fill="both", expand=True, padx=(4, 0))

        options_inner = tk.Frame(options_card, bg=self.card_bg)
        options_inner.pack(fill="x", padx=8, pady=6)

        self.chk_ontop = tk.Checkbutton(
            options_inner, text="On Top", variable=self.always_on_top_var,
            font=("Segoe UI", 8), bg=self.card_bg, fg=self.text_primary, activebackground=self.card_bg,
            command=self.toggle_always_on_top
        )
        self.chk_ontop.pack(side="left", padx=(0, 6))

        self.chk_copy = tk.Checkbutton(
            options_inner, text="Clipboard UID", variable=self.copy_clipboard_var,
            font=("Segoe UI", 8), bg=self.card_bg, fg=self.text_primary, activebackground=self.card_bg,
            command=self.save_application_settings
        )
        self.chk_copy.pack(side="left")

        # --- LIBRARY FOLDER PANEL ---
        self.lib_frame = self.create_card(main_container)
        self.lib_frame.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        lib_inner = tk.Frame(self.lib_frame, bg=self.card_bg)
        lib_inner.pack(fill="x", padx=8, pady=6)

        tk.Label(lib_inner, text="Library:", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg=self.text_secondary).pack(side="left", padx=(0, 4))

        self.lib_entry = tk.Entry(
            lib_inner, textvariable=self.library_dir_var, font=("Segoe UI", 8), bd=1, relief="solid",
            highlightthickness=1, highlightbackground=self.border_color
        )
        self.lib_entry.pack(side="left", fill="x", expand=True, padx=(0, 4), ipady=2)

        self.browse_lib_btn = tk.Button(
            lib_inner, text="Browse", font=("Segoe UI", 7, "bold"),
            bg="#e2e8f0", fg=self.text_primary, bd=0, relief="flat", padx=6, pady=3, cursor="hand2",
            command=self.browse_library_dir
        )
        self.browse_lib_btn.pack(side="left", padx=(0, 4))

        self.index_lib_btn = tk.Button(
            lib_inner, text="Index DB", font=("Segoe UI", 7, "bold"),
            bg="#7c3aed", fg="#ffffff", bd=0, relief="flat", padx=6, pady=3, cursor="hand2",
            command=self.generate_db_file
        )
        self.index_lib_btn.pack(side="right")

        self.sync_lib_btn = tk.Button(
            lib_inner, text="Sync Upstream", font=("Segoe UI", 7, "bold"),
            bg="#0284c7", fg="#ffffff", bd=0, relief="flat", padx=6, pady=3, cursor="hand2",
            command=self.start_sync_thread
        )
        self.sync_lib_btn.pack(side="right", padx=(0, 4))

        # --- FILE SELECTION PANEL ---
        self.file_frame = self.create_card(main_container)
        self.file_frame.grid(row=3, column=0, sticky="ew", pady=(0, 6))

        file_inner = tk.Frame(self.file_frame, bg=self.card_bg)
        file_inner.pack(fill="x", padx=8, pady=6)
        file_inner.columnconfigure(1, weight=1)

        # JSON Dump File Selection
        tk.Label(file_inner, text="JSON Dump:", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg=self.text_secondary).grid(row=0, column=0, sticky="w", pady=(0, 4))
        
        dump_sub = tk.Frame(file_inner, bg=self.card_bg)
        dump_sub.grid(row=0, column=1, sticky="ew", pady=(0, 4), padx=(4, 0))
        dump_sub.columnconfigure(0, weight=1)

        self.dump_entry = tk.Entry(
            dump_sub, textvariable=self.dump_file_var, font=("Segoe UI", 8), bd=1, relief="solid",
            highlightthickness=1, highlightbackground=self.border_color
        )
        self.dump_entry.pack(side="left", fill="x", expand=True, padx=(0, 4), ipady=2)

        self.browse_dump_btn = tk.Button(
            dump_sub, text="Browse", font=("Segoe UI", 7, "bold"),
            bg="#e2e8f0", fg=self.text_primary, bd=0, relief="flat", padx=6, pady=2, cursor="hand2",
            command=self.browse_dump_file
        )
        self.browse_dump_btn.pack(side="right")

        # BIN Key File Selection
        tk.Label(file_inner, text="Key File:", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg=self.text_secondary).grid(row=1, column=0, sticky="w")
        
        key_sub = tk.Frame(file_inner, bg=self.card_bg)
        key_sub.grid(row=1, column=1, sticky="ew", padx=(4, 0))
        key_sub.columnconfigure(0, weight=1)

        self.key_entry = tk.Entry(
            key_sub, textvariable=self.key_file_var, font=("Segoe UI", 8), bd=1, relief="solid",
            highlightthickness=1, highlightbackground=self.border_color
        )
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 4), ipady=2)

        self.browse_key_btn = tk.Button(
            key_sub, text="Browse", font=("Segoe UI", 7, "bold"),
            bg="#e2e8f0", fg=self.text_primary, bd=0, relief="flat", padx=6, pady=2, cursor="hand2",
            command=self.browse_key_file
        )
        self.browse_key_btn.pack(side="right")

        # Load persisted config settings
        self.load_application_settings()
        self.toggle_always_on_top()

        # --- STATUS & ACTION BUTTONS BAR ---
        status_action_frame = tk.Frame(main_container, bg=self.bg_color)
        status_action_frame.grid(row=4, column=0, sticky="ew", pady=(0, 6))
        status_action_frame.columnconfigure(0, weight=1)

        self.status_label = tk.Label(
            status_action_frame, textvariable=self.status_var, 
            font=("Segoe UI", 8, "bold"), bg="#e2e8f0", fg=self.text_primary, padx=8, pady=4, anchor="w", justify="left"
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.verify_btn = tk.Button(
            status_action_frame, text="Verify Tag", font=("Segoe UI", 8, "bold"),
            bg="#d97706", fg="#ffffff", activebackground="#b45309", activeforeground="#ffffff",
            bd=0, relief="flat", padx=10, pady=5, cursor="hand2", command=self.start_verify_thread
        )
        self.verify_btn.pack(side="right", padx=(4, 0))

        self.write_btn = tk.Button(
            status_action_frame, text="Flash to Tag", font=("Segoe UI", 8, "bold"),
            bg="#16a34a", fg="#ffffff", activebackground="#15803d", activeforeground="#ffffff",
            bd=0, relief="flat", padx=10, pady=5, cursor="hand2", command=self.start_flash_thread
        )
        self.write_btn.pack(side="right")

        # --- LOG CONSOLE PANEL ---
        log_header_frame = tk.Frame(main_container, bg=self.bg_color)
        log_header_frame.grid(row=5, column=0, sticky="ew", pady=(2, 2))
        
        tk.Label(log_header_frame, text="Proxmark3 Execution Log:", font=("Segoe UI", 8, "bold"), bg=self.bg_color, fg=self.text_primary).pack(side="left")
        
        self.reset_settings_btn = tk.Button(
            log_header_frame, text="Reset Settings", font=("Segoe UI", 7),
            bg="#fee2e2", fg="#991b1b", activebackground="#fecaca",
            bd=0, relief="flat", padx=4, pady=1, cursor="hand2",
            command=self.reset_application_settings
        )
        self.reset_settings_btn.pack(side="right")

        # Log Container Frame with border removed
        self.log_container = tk.Frame(main_container, bg="#ffffff", bd=0, relief="flat", highlightbackground=self.border_color, highlightthickness=0)
        self.log_container.grid(row=6, column=0, sticky="nsew")
        self.log_container.rowconfigure(0, weight=1)
        self.log_container.columnconfigure(0, weight=1)

        self.log_text = tk.Text(self.log_container, font=("Consolas", 8), bg="#1e293b", fg="#f8fafc", bd=0, wrap="none", insertbackground="white")
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        self.log_y_scrollbar = tk.Scrollbar(self.log_container, orient="vertical", command=self.log_text.yview)
        self.log_y_scrollbar.grid(row=0, column=1, sticky="ns")

        self.log_x_scrollbar = tk.Scrollbar(self.log_container, orient="horizontal", command=self.log_text.xview)
        self.log_x_scrollbar.grid(row=1, column=0, sticky="ew")

        self.log_corner = tk.Frame(self.log_container, bg="#f0f0f0", bd=0)
        self.log_corner.grid(row=1, column=1, sticky="nsew")

        self.log_text.config(xscrollcommand=self.log_x_scrollbar.set, yscrollcommand=self.log_y_scrollbar.set)

        self.refresh_com_ports()

    def create_card(self, parent):
        return tk.Frame(parent, bg=self.card_bg, highlightbackground=self.border_color, highlightthickness=1)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground="white", background="white", bordercolor=self.border_color)

    def set_window_icon(self):
        try:
            if getattr(sys, 'frozen', False):
                current_dir = os.path.abspath(os.path.dirname(sys.executable))
            else:
                current_dir = os.path.abspath(os.path.dirname(__file__))
            icon_path = os.path.join(current_dir, ICON_FILE_NAME)
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

    def setup_environment(self):
        if getattr(sys, 'frozen', False):
            self.current_dir = os.path.abspath(os.path.dirname(sys.executable))
        else:
            self.current_dir = os.path.abspath(os.path.dirname(__file__))
            
        self.pm3_path = os.path.join(self.current_dir, PM3_EXE_NAME)
        self.db_file_path = os.path.join(self.current_dir, DB_FILE_NAME)
        
        self.env = os.environ.copy()
        self.env["HOME"] = self.current_dir
        self.env["QT_PLUGIN_PATH"] = os.path.join(self.current_dir, "libs")
        self.env["QT_QPA_PLATFORM_PLUGIN_PATH"] = self.env["QT_PLUGIN_PATH"]
        self.env["MSYSTEM"] = "MINGW64"
        shell_libs = os.path.join(self.env["QT_PLUGIN_PATH"], "shell")
        self.env["PATH"] = f"{self.env['QT_PLUGIN_PATH']};{shell_libs};{self.env['PATH']}"

    def to_relative(self, path):
        if not path:
            return ""
        try:
            abs_path = os.path.abspath(path)
            rel = os.path.relpath(abs_path, self.current_dir)
            if rel == ".":
                return "."
            return rel if rel.startswith(".") else f".\\{rel}"
        except Exception:
            pass
        return path

    def to_absolute(self, path):
        if not path:
            return ""
        if os.path.isabs(path):
            return path
        return os.path.abspath(os.path.join(self.current_dir, path))

    def get_db_file_path(self):
        candidates = [
            self.db_file_path,
            os.path.join(os.getcwd(), DB_FILE_NAME),
            os.path.join(os.path.dirname(self.pm3_path), DB_FILE_NAME)
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return self.db_file_path

    def toggle_always_on_top(self):
        self.root.attributes("-topmost", self.always_on_top_var.get())

    def open_repo_url(self):
        url = self.repo_url_var.get().strip() or BAMBU_TAGS_REPO_URL
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open URL: {str(e)}")

    def append_log(self, text):
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)

    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()

    def update_status(self, text, is_highlighted=False):
        self.status_var.set(text)
        if is_highlighted:
            self.status_label.config(bg="#dbeafe", fg="#1e40af")
        else:
            self.status_label.config(bg="#e2e8f0", fg=self.text_primary)

    def generate_db_file(self):
        lib_root = self.to_absolute(self.library_dir_var.get().strip())
        if not lib_root or not os.path.exists(lib_root):
            messagebox.showwarning("Library Directory", "Please select a valid Bambulab library directory first!")
            return

        self.update_status(f"Generating {DB_FILE_NAME} index...")
        self.append_log(f"\n[+] Scanning library directory: {lib_root}\n")

        lines = []
        count = 0

        for root, dirs, _ in os.walk(lib_root):
            for d in dirs:
                if re.fullmatch(r"[A-Fa-f0-9]{8}", d):
                    full_path = os.path.join(root, d)
                    rel_path = self.to_relative(full_path)
                    lines.append(f"{d.upper()}|{rel_path}\n")
                    count += 1

        target_file = self.get_db_file_path()
        try:
            with open(target_file, "w", encoding="utf-8") as f:
                f.writelines(lines)
            
            rel_target = self.to_relative(target_file)
            self.append_log(f"[✔] Successfully saved {DB_FILE_NAME} with {count} indexed entries to:\n    {rel_target}\n\n")
            messagebox.showinfo("Success", f"{DB_FILE_NAME} generated with {count} indexed UIDs!")
            self.update_status("Library Indexed Successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save {DB_FILE_NAME}: {str(e)}")
            self.update_status("Indexing Failed")
        finally:
            self.set_buttons_state(True)

    def _is_uid(self, name):
        return len(name) == 8 and all(c in '0123456789ABCDEFabcdef' for c in name)

    def start_sync_thread(self):
        lib_root = self.to_absolute(self.library_dir_var.get().strip())
        if not lib_root:
            messagebox.showwarning("Library Directory", "Please select a valid Bambulab library directory first!")
            return

        self.set_buttons_state(False)
        self.update_status("Syncing library from upstream...")
        self.log_text.delete("1.0", tk.END)
        self.append_log("[+] Connecting to GitHub upstream repository...\n")

        threading.Thread(
            target=self.execute_upstream_sync,
            args=(lib_root,),
            daemon=True
        ).start()

    def execute_upstream_sync(self, lib_root):
        try:
            self.root.after(0, lambda: self.append_log("[+] Downloading repository archive...\n"))
            req = urllib.request.urlopen(BAMBU_TAGS_ZIP_URL)
            zip_data = req.read()

            self.root.after(0, lambda: self.append_log("[+] Scanning local library UIDs...\n"))
            local_uids = set()
            if os.path.exists(lib_root):
                for p in Path(lib_root).rglob('*'):
                    if p.is_dir() and self._is_uid(p.name):
                        local_uids.add(p.name.upper())

            self.root.after(0, lambda: self.append_log("[+] Parsing upstream library zip...\n"))
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                all_infos = zf.infolist()
                
                upstream_uids = {} 
                for info in all_infos:
                    parts = Path(info.filename).parts
                    if len(parts) < 5:
                        continue
                    category = parts[1] 
                    if category not in LIBRARY_CATEGORIES:
                        continue
                    uid = parts[4]
                    if not self._is_uid(uid):
                        continue
                    
                    uid_upper = uid.upper()
                    if uid_upper not in upstream_uids:
                        rel_dir_parts = parts[1:5]
                        upstream_uids[uid_upper] = {
                            'rel_dir': os.path.join(*rel_dir_parts),
                            'files': []
                        }
                    upstream_uids[uid_upper]['files'].append(info)

                new_uids = {uid: data for uid, data in upstream_uids.items() if uid not in local_uids}

                if not new_uids:
                    self.root.after(0, lambda: self.append_log("[✔] Library is already up to date with upstream!\n\n"))
                    self.root.after(0, lambda: self.update_status("Library Already Up to Date"))
                    self.root.after(0, self.generate_db_file)
                    return

                self.root.after(0, lambda: self.append_log(f"[+] Found {len(new_uids)} new UID(s) to import. Extracting...\n"))
                
                total_files = 0
                for uid, info_dict in new_uids.items():
                    target_dir = os.path.join(lib_root, info_dict['rel_dir'])
                    os.makedirs(target_dir, exist_ok=True)
                    
                    for file_info in info_dict['files']:
                        file_name = os.path.basename(file_info.filename)
                        if not file_name:
                            continue
                        dest_path = os.path.join(target_dir, file_name)
                        if not os.path.exists(dest_path):
                            with zf.open(file_info) as src, open(dest_path, "wb") as dst:
                                dst.write(src.read())
                            total_files += 1

                    self.root.after(0, lambda u=uid, p=info_dict['rel_dir']: self.append_log(f"    Imported: {p}/\n"))

                self.root.after(0, lambda: self.append_log(f"\n[✔] Successfully imported {len(new_uids)} new UID(s), {total_files} file(s) written.\n"))
                self.root.after(0, lambda: self.update_status("Sync Complete. Indexing database..."))
                self.root.after(0, self.generate_db_file)

        except Exception as e:
            self.root.after(0, lambda: self.update_status("Sync Error"))
            self.root.after(0, lambda: self.append_log(f"\n[!] Error during upstream sync: {str(e)}\n"))
            self.root.after(0, lambda: self.set_buttons_state(True))

    def lookup_material_from_db(self, target_uid):
        target_uid_clean = target_uid.upper().strip()
        db_file = self.get_db_file_path()

        if not os.path.exists(db_file):
            return None

        try:
            with open(db_file, "r", encoding="utf-8") as f:
                for line in f:
                    if "|" in line:
                        uid, path = line.strip().split("|", 1)
                        if uid.strip().upper() == target_uid_clean:
                            clean_path = os.path.normpath(path)
                            parts = clean_path.split(os.sep)

                            bambu_idx = -1
                            for idx, p in enumerate(parts):
                                if p.lower() == "bambulab":
                                    bambu_idx = idx
                                    break
                            
                            if bambu_idx != -1 and len(parts) > bambu_idx + 1:
                                rel_parts = parts[bambu_idx + 1:]
                            else:
                                rel_parts = parts

                            if rel_parts and rel_parts[-1].upper() == target_uid_clean:
                                rel_parts = rel_parts[:-1]

                            if len(rel_parts) >= 2:
                                material = rel_parts[-2]
                                color = rel_parts[-1]
                                return f"{material} - {color}"
                            elif len(rel_parts) == 1:
                                return rel_parts[0]
        except Exception as e:
            self.append_log(f"[!] Database read error: {str(e)}\n")

        return None

    def refresh_com_ports(self):
        try:
            ports = serial.tools.list_ports.comports()
            port_list = [port.device for port in ports]
            self.port_combobox['values'] = port_list

            if port_list:
                if self.cached_port_name in port_list:
                    self.port_combobox.set(self.cached_port_name)
                else:
                    self.port_combobox.current(0)
                self.update_status(f"Ready ({len(port_list)} ports found)")
            else:
                self.port_combobox.set('')
                self.update_status("No active COM ports found!")
        except Exception:
            self.update_status("Error scanning COM ports")

    def browse_library_dir(self):
        selected_dir = filedialog.askdirectory(title="Select Root Bambulab Library Folder", initialdir=self.current_dir)
        if selected_dir:
            rel_dir = self.to_relative(os.path.normpath(selected_dir))
            self.library_dir_var.set(rel_dir)
            self.save_application_settings()

    def browse_dump_file(self):
        selected_file = filedialog.askopenfilename(
            title="Select Bambulab JSON Dump File",
            initialdir=self.current_dir,
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if selected_file:
            rel_dump = self.to_relative(os.path.normpath(selected_file))
            self.dump_file_var.set(rel_dump)

            base_dir = os.path.dirname(self.to_absolute(rel_dump))
            file_name = os.path.basename(rel_dump)
            
            key_name_candidate = file_name.replace("-dump.json", "-key.bin").replace(".json", ".bin")
            key_path = os.path.join(base_dir, key_name_candidate)

            if os.path.exists(key_path):
                self.key_file_var.set(self.to_relative(os.path.normpath(key_path)))
            
            self.save_application_settings()

    def browse_key_file(self):
        selected_file = filedialog.askopenfilename(
            title="Select Bambulab Key File",
            initialdir=self.current_dir,
            filetypes=[("Binary Key Files", "*.bin"), ("All Files", "*.*")]
        )
        if selected_file:
            rel_key = self.to_relative(os.path.normpath(selected_file))
            self.key_file_var.set(rel_key)
            self.save_application_settings()

    def load_application_settings(self):
        config_path = os.path.join(self.current_dir, SETTINGS_FILE_NAME)
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    content = f.read().strip()
                if "|" in content:
                    parts = content.split("|")
                    self.cached_port_name = parts[0]
                    ports = self.port_combobox['values']
                    if self.cached_port_name in ports:
                        self.port_combobox.set(self.cached_port_name)

                    if len(parts) >= 2:
                        self.always_on_top_var.set(parts[1] == "1")
                        self.toggle_always_on_top()

                    if len(parts) >= 3 and parts[2]:
                        self.dump_file_var.set(parts[2])

                    if len(parts) >= 4 and parts[3]:
                        self.key_file_var.set(parts[3])

                    if len(parts) >= 5:
                        self.copy_clipboard_var.set(parts[4] == "1")

                    if len(parts) >= 6 and parts[5]:
                        self.library_dir_var.set(parts[5])

                    if len(parts) >= 7 and parts[6]:
                        self.repo_url_var.set(parts[6])
                else:
                    self.cached_port_name = content
            except Exception:
                pass

    def save_application_settings(self):
        config_path = os.path.join(self.current_dir, SETTINGS_FILE_NAME)
        try:
            port = self.port_combobox.get() or "COM1"
            top_bit = "1" if self.always_on_top_var.get() else "0"
            dump = self.dump_file_var.get().strip() or r".\Bambu-Lab-RFID-Library"
            key = self.key_file_var.get().strip() or r".\Bambu-Lab-RFID-Library"
            copy_bit = "1" if self.copy_clipboard_var.get() else "0"
            lib_dir = self.library_dir_var.get().strip() or r".\Bambu-Lab-RFID-Library"
            repo_url = self.repo_url_var.get().strip() or BAMBU_TAGS_REPO_URL
            packed = f"{port}|{top_bit}|{dump}|{key}|{copy_bit}|{lib_dir}|{repo_url}"
            with open(config_path, "w") as f:
                f.write(packed)
        except Exception:
            pass

    def reset_application_settings(self):
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to defaults?"):
            config_path = os.path.join(self.current_dir, SETTINGS_FILE_NAME)
            try:
                with open(config_path, "w") as f:
                    f.write(DEFAULT_SETTINGS_CONTENT)
                self.load_application_settings()
                self.update_status("Settings Reset to Default")
                messagebox.showinfo("Success", "Settings have been successfully reset to default!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reset settings: {str(e)}")

    def set_buttons_state(self, state):
        btn_state = "normal" if state else "disabled"
        self.write_btn.config(state=btn_state)
        self.verify_btn.config(state=btn_state)
        self.browse_dump_btn.config(state=btn_state)
        self.browse_key_btn.config(state=btn_state)
        self.browse_lib_btn.config(state=btn_state)
        self.index_lib_btn.config(state=btn_state)
        self.sync_lib_btn.config(state=btn_state)
        self.reset_settings_btn.config(state=btn_state)

    def start_flash_thread(self):
        chosen_port = self.port_combobox.get()
        dump_path = self.to_absolute(self.dump_file_var.get().strip())
        key_path = self.to_absolute(self.key_file_var.get().strip())

        if not chosen_port:
            messagebox.showwarning("Port Missing", "Please select an active COM port first!")
            return
        if not dump_path or not os.path.exists(dump_path):
            messagebox.showwarning("File Missing", "Please select a valid JSON dump file!")
            return
        if not key_path or not os.path.exists(key_path):
            messagebox.showwarning("File Missing", "Please select a valid BIN key file!")
            return

        self.save_application_settings()
        self.set_buttons_state(False)
        
        self.update_status("Flashing Tag...")
        self.log_text.delete("1.0", tk.END)

        threading.Thread(
            target=self.execute_restore_command, 
            args=(chosen_port, dump_path, key_path), 
            daemon=True
        ).start()

    def start_verify_thread(self):
        chosen_port = self.port_combobox.get()

        if not chosen_port:
            messagebox.showwarning("Port Missing", "Please select an active COM port first!")
            return

        self.save_application_settings()
        self.set_buttons_state(False)
        
        self.update_status("Verifying Tag (hf mf info)...")
        self.log_text.delete("1.0", tk.END)

        threading.Thread(
            target=self.execute_verify_command, 
            args=(chosen_port,), 
            daemon=True
        ).start()

    def execute_restore_command(self, active_port, dump_file, key_file):
        if not os.path.exists(self.pm3_path):
            self.root.after(0, lambda: messagebox.showerror(
                "Error", f"Could not find {PM3_EXE_NAME} inside directory:\n{os.path.dirname(self.pm3_path)}"
            ))
            self.root.after(0, lambda: self.update_status("Config Error"))
            self.root.after(0, lambda: self.set_buttons_state(True))
            return

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

        try:
            cmd_string = f"hf mf restore --force -f \"{dump_file}\" -k \"{key_file}\"; exit"
            self.root.after(0, lambda: self.append_log(f"Executing: {cmd_string}\n\n"))

            process = subprocess.Popen(
                [self.pm3_path, active_port, "-c", cmd_string],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, startupinfo=startupinfo, env=self.env
            )

            full_output_list = []
            for line in iter(process.stdout.readline, ''):
                full_output_list.append(line)
                self.root.after(0, lambda l=line: self.append_log(l))

            process.stdout.close()
            process.wait(timeout=25)

            full_output = "".join(full_output_list)

            if "is done" in full_output.lower() or "restored" in full_output.lower() or "ok" in full_output.lower():
                self.root.after(0, lambda: self.update_status("Tag Flashed Successfully!", is_highlighted=True))
            else:
                self.root.after(0, lambda: self.update_status("Flash Finished (Check Log)"))

        except Exception as e:
            self.root.after(0, lambda: self.update_status("Flash Error"))
            self.root.after(0, lambda: self.append_log(f"\n[!] Error: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.set_buttons_state(True))

    def execute_verify_command(self, active_port):
        if not os.path.exists(self.pm3_path):
            self.root.after(0, lambda: messagebox.showerror(
                "Error", f"Could not find {PM3_EXE_NAME} inside directory:\n{os.path.dirname(self.pm3_path)}"
            ))
            self.root.after(0, lambda: self.update_status("Config Error"))
            self.root.after(0, lambda: self.set_buttons_state(True))
            return

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

        try:
            cmd_string = "hf mf info; exit"
            self.root.after(0, lambda: self.append_log(f"Executing: {cmd_string}\n\n"))

            process = subprocess.Popen(
                [self.pm3_path, active_port, "-c", cmd_string],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, startupinfo=startupinfo, env=self.env
            )

            full_output_list = []
            for line in iter(process.stdout.readline, ''):
                full_output_list.append(line)
                self.root.after(0, lambda l=line: self.append_log(l))

            process.stdout.close()
            process.wait(timeout=25)

            full_output = "".join(full_output_list)

            uid_match = re.search(r"(?:UID|uid)\s*[:=]\s*([A-Fa-f0-9\s]{8,20})", full_output)
            if uid_match:
                raw_uid = uid_match.group(1).replace(" ", "").upper()
                
                if self.copy_clipboard_var.get():
                    self.root.after(0, lambda u=raw_uid: self.copy_to_clipboard(u))

                material_info = self.lookup_material_from_db(raw_uid)
                if material_info:
                    display_text = f"CUID: {raw_uid}\nMaterial: {material_info}"
                else:
                    display_text = f"CUID: {raw_uid}\nMaterial: Unknown"
                
                self.root.after(0, lambda t=display_text: self.update_status(t, is_highlighted=True))
            else:
                self.root.after(0, lambda: self.update_status("Verification Finished (UID Not Found)"))

        except Exception as e:
            self.root.after(0, lambda: self.update_status("Verification Error"))
            self.root.after(0, lambda: self.append_log(f"\n[!] Error: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.set_buttons_state(True))

if __name__ == "__main__":
    root = tk.Tk()
    app = BambulabFlasherGUI(root)
    root.mainloop()

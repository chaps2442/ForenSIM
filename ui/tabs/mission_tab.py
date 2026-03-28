import customtkinter as ctk
import os
import queue
import datetime
from core.pysim_runner import PySimRunner
from core.report_generator import generate_pdf_report
from core.smartcard_handler import auto_security_check, test_pin, unblock_pin, change_pin
import json
from tkinter import filedialog
from core.lang import LANG

class MissionTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=10)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.lbl_title = ctk.CTkLabel(self, text=LANG["FR"]["tab_mission"], font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_title.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.cfg_frame = ctk.CTkFrame(self)
        self.cfg_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.pysim_path_var = ctk.StringVar(value=self.load_config())
        
        self.lbl_pysim = ctk.CTkLabel(self.cfg_frame, text=LANG["FR"]["lbl_pysim"])
        self.lbl_pysim.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.ent_pysim = ctk.CTkEntry(self.cfg_frame, textvariable=self.pysim_path_var)
        self.ent_pysim.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.btn_browse = ctk.CTkButton(self.cfg_frame, text=LANG["FR"]["btn_browse"], width=80, command=self.browse_pysim)
        self.btn_browse.grid(row=0, column=2, padx=10, pady=10, sticky="w")

        self.column_container = ctk.CTkFrame(self.cfg_frame, fg_color="transparent")
        self.column_container.grid(row=1, column=0, columnspan=4, pady=5, sticky="ew")
        self.column_container.grid_columnconfigure(0, weight=1)

        self.sec_basic = ctk.CTkFrame(self.column_container, border_width=2, border_color="gray", fg_color="transparent")
        self.sec_basic.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.sec_basic.grid_columnconfigure((0, 1, 2), weight=1)

        self.lbl_sec_basic = ctk.CTkLabel(self.sec_basic, text=LANG["FR"]["lbl_sec_basic"], font=ctk.CTkFont(weight="bold"), text_color="#4CAF50")
        self.lbl_sec_basic.grid(row=0, column=0, columnspan=2, pady=(10, 5), sticky="e")
        
        self.led_status = ctk.CTkFrame(self.sec_basic, width=16, height=16, corner_radius=8, fg_color="gray")
        self.led_status.grid(row=0, column=2, pady=(10, 5), padx=(5, 0), sticky="w")

        try:
            from smartcard.System import readers
            r_list = readers()
            vals = [f"Lecteur {i+1} : {str(x)}" for i, x in enumerate(r_list)]
            if not vals: vals = ["Lecteur 1 (Default)"]
        except ImportError:
            vals = ["Lecteur 1 (Default)"]
            
        self.cb_reader = ctk.CTkOptionMenu(self.sec_basic, values=vals, width=350)
        self.cb_reader.grid(row=1, column=0, columnspan=3, padx=5, pady=(5, 15))
        
        self.lbl_current_pin = ctk.CTkLabel(self.sec_basic, text=LANG["FR"]["lbl_current_pin"])
        self.lbl_current_pin.grid(row=2, column=0, padx=10, pady=5, sticky="e")
        
        self.entry_pin = ctk.CTkEntry(self.sec_basic, placeholder_text=LANG["FR"]["ent_pin_placeholder"], width=150)
        self.entry_pin.grid(row=2, column=1, padx=10, pady=5)
        
        self.btn_null = ctk.CTkButton(self.sec_basic, text=LANG["FR"]["btn_null_verify"], width=150, command=self.null_verify_ui)
        self.btn_null.grid(row=2, column=2, padx=10, pady=5, sticky="w")

        self.btn_test = ctk.CTkButton(self.sec_basic, text=LANG["FR"]["btn_test_pin"], width=150, command=self.test_pin_ui)
        self.btn_test.grid(row=3, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        self.lbl_pin_status = ctk.CTkLabel(self.cfg_frame, text="", font=ctk.CTkFont(weight="bold", size=14), wraplength=400)
        self.lbl_pin_status.grid(row=2, column=0, columnspan=4, pady=10, padx=10)

        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        
        self.btn_run = ctk.CTkButton(self.action_frame, text=LANG["FR"]["btn_start"], fg_color="green", hover_color="darkgreen", command=self.start_extraction)
        self.btn_run.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_stop = ctk.CTkButton(self.action_frame, text=LANG["FR"]["btn_stop"], fg_color="red", hover_color="darkred", state="disabled", command=self.stop_extraction)
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=5)

        self.progressbar = ctk.CTkProgressBar(self.action_frame, mode="indeterminate", width=250)
        self.progressbar.pack(side="left", pady=10, padx=20)
        self.progressbar.set(0)

        self.console = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=12))
        self.console.grid(row=6, column=0, padx=20, pady=20, sticky="nsew")
        self.console.insert("0.0", LANG["FR"]["status_ready"])
        self.console.configure(state="disabled")

        self.pysim_runner = None
        self.worker_queue = queue.Queue()

        self.after(2000, self.auto_refresh_readers)

    def auto_refresh_readers(self):
        try:
            from smartcard.System import readers
            r_list = readers()
            vals = [f"Lecteur {i+1} : {str(x)}" for i, x in enumerate(r_list)]
            if not vals: vals = ["Lecteur 1 (Default)"]
        except ImportError:
            vals = ["Lecteur 1 (Default)"]
            
        current_vals = getattr(self.cb_reader, "_values", [])
        if vals != current_vals:
            current_sel = self.cb_reader.get()
            self.cb_reader.configure(values=vals)
            if current_sel not in vals and vals:
                self.cb_reader.set(vals[0])
                
        if not getattr(self, "pysim_runner", None) or not getattr(self.pysim_runner, "is_running", False):
            reader_str = self.cb_reader.get()
            if "Lecteur " in reader_str:
                try:
                    idx = int(reader_str.split("Lecteur ")[1].split(" ")[0]) - 1
                    from core.smartcard_handler import auto_security_check
                    status = auto_security_check(idx)
                    is_bad_conn = ("Error" in status or "No reader" in status or "Muette" in status or "Conn Error" in status)
                    self.led_status.configure(fg_color="red" if is_bad_conn else "green")
                except Exception:
                    pass
                    
        self.after(2000, self.auto_refresh_readers)

    def load_config(self):
        default_path = os.path.join(os.path.expanduser("~"), "pysim")
        config_file = "forensim_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                    return config.get("pysim_path", default_path)
            except Exception:
                pass
        return default_path

    def save_config(self, path):
        try:
            with open("forensim_config.json", "w") as f:
                json.dump({"pysim_path": path}, f)
        except Exception:
            pass

    def browse_pysim(self):
        folder = filedialog.askdirectory(initialdir=self.pysim_path_var.get())
        if folder:
            self.pysim_path_var.set(folder)
            self.save_config(folder)
            if hasattr(self.master, "update_config_check"):
                self.master.update_config_check()

    def test_pin_ui(self):
        reader_idx = self.cb_reader.get()
        py_reader_idx = 0
        if "Lecteur " in reader_idx:
            try:
                py_reader_idx = int(reader_idx.split("Lecteur ")[1].split(" ")[0]) - 1
            except Exception:
                pass
        pin = self.entry_pin.get().strip()
        if pin:
            self.log(f"[*] Tentative de vérification PIN : {pin}\n")
            status, color = test_pin(py_reader_idx, pin)
            self.lbl_pin_status.configure(text=status, text_color=color)
            if color == "red":
                self.log(f"[!] ÉCHEC : Code PIN incorrect. {status}\n")
            elif color == "green":
                self.log(f"[+] SUCCÈS : {status}\n")
            
            # Show diagnostic window if there's a connection/reader error 
            is_bad_conn = ("Muette" in status or "Error" in status or "No reader" in status or "Conn Error" in status)
            self.led_status.configure(fg_color="red" if is_bad_conn else "green")
            
            if color == "orange" and is_bad_conn:
                self.show_pinout_helper()
        else:
            self.lbl_pin_status.configure(text="PIN requis", text_color="orange")

    def null_verify_ui(self):
        reader_idx = self.cb_reader.get()
        py_reader_idx = 0
        if "Lecteur " in reader_idx:
            try:
                py_reader_idx = int(reader_idx.split("Lecteur ")[1].split(" ")[0]) - 1
            except Exception:
                pass
        status = auto_security_check(py_reader_idx)
        color = "green" if "UNLOCKED" in status else ("red" if "LOCKED" in status or "BLOCKED" in status else "orange")
        self.lbl_pin_status.configure(text=status, text_color=color)
        
        is_bad_conn = ("Error" in status or "No reader" in status or "Muette" in status or "Conn Error" in status)
        self.led_status.configure(fg_color="red" if is_bad_conn else "green")
        
        if color == "orange" and is_bad_conn:
            self.show_pinout_helper()

    def show_pinout_helper(self):
        if hasattr(self, 'pinout_window') and self.pinout_window is not None and self.pinout_window.winfo_exists():
            self.pinout_window.focus()
            self.pinout_window.lift()
            return
            
        self.pinout_window = ctk.CTkToplevel(self)
        self.pinout_window.title("Diagnostic Matériel - PINOUT")
        self.pinout_window.geometry("380x480")
        self.pinout_window.attributes("-topmost", True)
        
        label = ctk.CTkLabel(self.pinout_window, text="Aide au Diagnostic : \nVérifiez les contacts de la carte", font=ctk.CTkFont(weight="bold", size=14))
        label.pack(pady=10)
        
        pinout = (
            "  [C1: VCC] [C2: RST] [C3: CLK]\n"
            "  [C5: GND] [C6: VPP] [C7: I/O]\n\n"
            "     STANDARD SIM\n"
            "      ┌─────────────┐\n"
            "     ╱              │\n"
            "    │  [C1]   [C5]  │\n"
            "    │  [C2]   [C6]  │\n"
            "    │  [C3]   [C7]  │\n"
            "    │  [C4]   [C8]  │\n"
            "    └───────────────┘\n"
            "\n"
            "       MFF2 eSIM\n"
            "     ┌─•───────────┐\n"
            "     │             │\n"
            "     │ [C4]   [C8] │\n"
            "     │ [C3]   [C7] │\n"
            "     │ [C2]   [C6] │\n"
            "     │ [C1]   [C5] │\n"
            "     └─────────────┘\n"
        )
        schema = ctk.CTkTextbox(self.pinout_window, font=ctk.CTkFont(family="Consolas", size=12), width=340, height=360)
        schema.pack(pady=10)
        schema.insert("0.0", pinout)
        schema.configure(state="disabled")

    def update_lang(self, l):
        self.lbl_title.configure(text=LANG[l]["tab_mission"])
        self.lbl_pysim.configure(text=LANG[l]["lbl_pysim"])
        self.btn_browse.configure(text=LANG[l]["btn_browse"])
        
        self.lbl_sec_basic.configure(text=LANG[l]["lbl_sec_basic"])
        self.lbl_current_pin.configure(text=LANG[l]["lbl_current_pin"])
        self.entry_pin.configure(placeholder_text=LANG[l]["ent_pin_placeholder"])
        self.btn_null.configure(text=LANG[l]["btn_null_verify"])
        self.btn_test.configure(text=LANG[l]["btn_test_pin"])
        
        self.btn_run.configure(text=LANG[l]["btn_start"])
        self.btn_stop.configure(text=LANG[l]["btn_stop"])

    def log(self, text):
        self.console.configure(state="normal")
        self.console.insert("end", text)
        self.console.see("end")
        self.console.configure(state="disabled")

    def start_extraction(self):
        self.btn_run.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.console.configure(state="normal")
        self.console.delete("0.0", "end")
        self.console.insert("end", "[*] Lancement de ForenSIM V2 Parity Mode...\n")
        self.console.see("end")
        self.console.configure(state="disabled")
        
        # Start PB
        self.progressbar.start()
        
        # PRE-FLIGHT CHECK
        pin = self.entry_pin.get().strip()
        self.validated_pin = pin if pin else ""
        
        reader_str = self.cb_reader.get()
        py_reader_idx = 0
        if "Lecteur " in reader_str:
            try:
                py_reader_idx = int(reader_str.split("Lecteur ")[1].split(" ")[0]) - 1
            except Exception:
                pass
                
        self.log("[*] --- ETAPE 0 : PRE-FLIGHT CHECK ---\n")
        sec_status = "Unlocked (PIN Injected)" if self.validated_pin else auto_security_check(py_reader_idx)
        self.log(f"[*] Pre-Flight Check : {sec_status}\n\n")
        self.last_sec_status = sec_status
        self.last_pin_tested = self.validated_pin if self.validated_pin else "Non fourni"

        pysim_path = self.pysim_path_var.get()
        if not os.path.exists(pysim_path):
            self.log("[!] Warning: pySim directory not found! Extraction will fail if pySim-shell is missing.\n")
            
        ts = datetime.datetime.now().strftime('%Y.%m.%d_%H.%M.%S')
        out_dir = os.path.join(os.path.expanduser("~"), "Desktop", f"{ts}_ForenSIM_Extraction")
        self.out_dir = out_dir
        self.ts = ts

        cmds = ""
        cmds += "set exit_on_error false\n"
        if pin: cmds += f"verify_chv {pin}\n"
        
        # 1. Racine (MF = 3f00) - ICCID et Langue
        cmds += "select 3f00\n"
        cmds += "select 2fe2\nread_binary\n"
        cmds += "select 6f05\nread_binary\n" # Langue
        
        # 2. Répertoire 2G/3G (DF.GSM = 7f20)
        cmds += "select 3f00\nselect 7f20\n"
        cmds += "select 6f07\nread_binary\n" # IMSI
        cmds += "select 6f7e\nread_binary\n" # LOCI
        cmds += "select 6f7b\nread_binary\n" # FPLMN
        cmds += "select 6f46\nread_binary\n" # SPN
        cmds += "select 6f42\nread_binary\n" # SMSC
        
        # 3. Répertoire 4G/5G (ADF Actuel = 7fff)
        cmds += "select 7fff\n"
        cmds += "select 6f07\nread_binary\n" # IMSI
        cmds += "select 6f7e\nread_binary\n" # LOCI
        cmds += "select 6fe3\nread_binary\n" # EPSLOCI
        cmds += "select 6f7b\nread_binary\n" # FPLMN
        cmds += "select 6f46\nread_binary\n" # SPN
        cmds += "select 6f42\nread_binary\n" # SMSC
        
        # 4. Répertoire Telecom (DF.TELECOM = 7f10)
        cmds += "select 3f00\nselect 7f10\n"
        cmds += "select 6f3a\nread_record 1\n" # Contacts
        cmds += "select 6f3c\nread_record 1\n" # SMS
        cmds += "select 6f40\nread_record 1\n" # MSISDN
        cmds += "select 6f44\nread_record 1\n" # Calls (LND)

        # 5. Exportation Massive (File System Dump)
        # L'export sur la racine 3f00 est récursif et dumpera toute la carte trouvée
        cmds += "select 3f00\n"
        if pin: cmds += f"verify_chv {pin}\n"
        cmds += "export\n"
        cmds += "quit\n"
        
        self.pysim_runner = PySimRunner(
            pysim_path=pysim_path,
            reader_idx=py_reader_idx,
            output_dir=out_dir,
            ui_queue=self.worker_queue
        )
        self.log("[*] Mode d'extraction Logical & File System initié...\n")
        self.log("[*] Interrogation des structures de base 2FE2 / 6F07...\n")
        self.log("[*] Récupération des SMS, Contacts et Appels...\n")
        self.log("[*] Création du dump Forensic complet. Veuillez patienter (environ 1-2 minutes) sans débrancher la carte...\n")

        import threading
        t = threading.Thread(target=self.pysim_runner.run_script, args=(cmds, "raw_dump.txt"), daemon=True)
        t.start()

        self.after(100, self.check_queue)
        
    def check_queue(self):
        while not self.worker_queue.empty():
            msg = self.worker_queue.get()
            if msg == "===PROCESS_DONE===":
                self.progressbar.stop()
                self.progressbar.set(0)
                self.finalize_extraction()
                return
            else:
                # Filtrer l'affichage pour ne pas noyer la console de données brutes
                # On cache les messages normaux, on n'affiche que les erreurs critiques
                if "Error" in msg or "Exception" in msg:
                    self.log(msg)
        self.after(100, self.check_queue)

    def find_operator(self, imsi, csv_path):
        if not imsi or len(imsi) < 5: return "Inconnu"
        mcc, mnc2, mnc3 = imsi[:3], imsi[3:5], imsi[3:6]
        if not os.path.exists(csv_path): 
            return f"MCC {mcc} MNC {mnc2}"
        try:
            import csv
            with open(csv_path, mode='r', encoding='utf-8-sig', errors='ignore') as f:
                reader = csv.DictReader(f, delimiter=';')
                if not reader.fieldnames or len(reader.fieldnames) == 1:
                    f.seek(0)
                    reader = csv.DictReader(f, delimiter=',')
                for row in reader:
                    r = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                    if r.get('mcc') == mcc and (r.get('mnc') == mnc2 or r.get('mnc') == mnc3):
                        net = r.get('network') or r.get('operator') or "Opérateur Inconnu"
                        country = r.get('country') or "Pays Inconnu"
                        return f"{net} [{country}]"
        except Exception:
            pass
        return f"MCC {mcc} MNC {mnc2}"

    def find_country(self, mcc, csv_path):
        if not mcc or not os.path.exists(csv_path): return "Pays Inconnu"
        try:
            import csv
            with open(csv_path, mode='r', encoding='utf-8-sig', errors='ignore') as f:
                reader = csv.DictReader(f, delimiter=';')
                if not reader.fieldnames or len(reader.fieldnames) == 1:
                    f.seek(0)
                    reader = csv.DictReader(f, delimiter=',')
                for row in reader:
                    r = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                    if r.get('mcc') == mcc:
                        country = r.get('country')
                        if country: return country
        except Exception:
            pass
        return "Pays Inconnu"

    def extract_hex_from_dump(self, dump_str, file_id):
        file_id = file_id.lower()
        lines = dump_str.split('\n')
        
        # Dictionnaire de traduction FID -> Noms (car pySim exporte avec les noms)
        fid_to_name = {
            "2fe2": "EF.ICCID",
            "6f07": "EF.IMSI",
            "6f7e": "EF.LOCI",
            "6fe3": "EF.EPSLOCI",
            "6f7b": "EF.FPLMN"
        }
        target_name = fid_to_name.get(file_id, "")

        # Passe 1 : Chercher dans les blocs JSON (Les requêtes manuelles)
        for i, line in enumerate(lines):
            # On cherche l'ID du fichier au sein du JSON généré par pySim
            if f'"file_id": "{file_id}"' in line.lower():
                # On a trouvé le bloc. On descend jusqu'à l'accolade fermante "}"
                for j in range(i, min(i+30, len(lines))):
                    if lines[j].strip() == "}":
                        # La réponse hexadécimale est TOUJOURS la ligne juste après
                        if j + 1 < len(lines):
                            val = lines[j+1].strip()
                            # Sécurité : vérifier que c'est bien de l'hexa brut
                            if len(val) >= 4 and all(c in "0123456789abcdefABCDEF" for c in val):
                                return val
                        break

        # Passe 2 : Chercher dans la zone d'exportation avec les noms traduits (Fallback)
        if target_name:
            for i, line in enumerate(lines):
                if target_name in line.upper() and i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    if next_line.startswith("update_binary"):
                        parts = next_line.split(" ")
                        if len(parts) >= 2:
                            return parts[1]
                            
        return ""

    def decode_imsi(self, hex_str):
        if not hex_str or len(hex_str) < 18: return "Inaccessible"
        hex_str = hex_str[2:]
        swapped = "".join([hex_str[i+1] + hex_str[i] for i in range(0, len(hex_str)-1, 2) if i+1 < len(hex_str)])
        return swapped[1:].replace("f", "").replace("F", "")

    def decode_iccid(self, hex_str):
        if not hex_str: return None
        h = hex_str.replace(" ", "").replace("\n", "")
        res = "".join([h[i+1] + h[i] for i in range(0, len(h)-1, 2) if i+1 < len(h)])
        if len(h) % 2: res += h[-1]
        return res.rstrip("fF")

    def decode_msisdn(self, hex_str):
        # 1. Vérification de base
        if not hex_str or len(hex_str) < 28:
            return "Non inscrit dans la puce (Géré côté opérateur)"
            
        # 2. Si TOUT le record est vide
        if hex_str.lower().count('f') > len(hex_str) - 4:
            return "Non inscrit dans la puce (Géré côté opérateur)"
            
        try:
            # 3. Le numéro se trouve TOUJOURS à la fin du record.
            # On ignore les 2 octets finaux (Capacité/Extension) = 4 caractères hexa
            data = hex_str[:-4]
            
            # 4. On cherche l'octet TON (Type Of Number), généralement 91 (International) ou 81 (Inconnu)
            # On cherche de la FIN vers le DÉBUT pour éviter de confondre avec l'Alpha Identifier
            ton_idx = data.rfind("91")
            prefix = "+"
            
            if ton_idx == -1 or ton_idx < len(data) - 20:
                ton_idx = data.rfind("81")
                prefix = ""
                
            # 5. Si on a trouvé le TON au bon endroit (près de la fin)
            if ton_idx != -1:
                # Le BCD (Binary Coded Decimal) commence juste après le TON
                bcd_part = data[ton_idx + 2:]
                
                # Byte Swapping (Inversion des nibbles)
                swapped = "".join([bcd_part[i+1] + bcd_part[i] for i in range(0, len(bcd_part)-1, 2)])
                
                # Nettoyage des F de remplissage
                clean_number = swapped.replace("f", "").replace("F", "")
                
                import re
                # On s'assure qu'on a extrait une suite de chiffres (au moins 6)
                if re.match(r'^\d{6,}$', clean_number):
                    return prefix + clean_number
                    
            # 6. Fallback si le TON n'est pas standard : on extrait les chiffres du dernier tiers
            tail_swapped = "".join([data[i+1] + data[i] for i in range(0, len(data)-1, 2) if i+1 < len(data)])
            clean_tail = tail_swapped.replace("f", "").replace("F", "")
            import re
            match = re.search(r'\d{8,15}', clean_tail)
            if match:
                 return match.group(0)
                 
        except Exception:
            pass
            
        # Si on arrive ici, c'est qu'il y avait des données mais pas un numéro valide
        return "Illisible ou masqué"

    def decode_plmn(self, hex_str, offset):
        try:
            if not hex_str or len(hex_str) < offset + 6: return None, None
            plmn = hex_str[offset:offset+6].lower()
            if "ff" in plmn or plmn == "000000": return None, None
            
            mcc = f"{plmn[1]}{plmn[0]}{plmn[3]}"
            mnc3 = plmn[2]
            mnc = f"{plmn[5]}{plmn[4]}"
            if mnc3 != 'f': mnc += mnc3
            
            return str(mcc), str(mnc)
        except Exception:
            return None, None

    def get_roaming_network(self, mcc, mnc, csv_path):
        if not mcc or not mnc: return "Réseau Inconnu"
        fake_imsi = f"{mcc}{mnc}0000000000"
        return self.find_operator(fake_imsi, csv_path)

    def decode_language(self, hex_str):
        if not hex_str or "ffff" in hex_str.lower(): return "Non définie"
        try:
            # Convertit l'hexa en ASCII (ex: '6672' -> 'fr')
            chars = [chr(int(hex_str[i:i+2], 16)) for i in range(0, len(hex_str), 2) if int(hex_str[i:i+2], 16) >= 32]
            lang = "".join(chars).strip()
            # Nettoie les caractères bizarres et garde les 2 premières lettres
            import re
            clean = re.sub(r'[^a-zA-Z]', '', lang)
            if len(clean) >= 2:
                return clean[:2].upper()
        except: pass
        return "Inconnue"

    def decode_spn(self, hex_str):
        if not hex_str or "ffff" in hex_str.lower() or len(hex_str) < 4: 
            return "Non programmé"
        try:
            # On ignore le premier octet (ex: '00' ou '01')
            name_hex = hex_str[2:]
            # Conversion des octets hexa en caractères ASCII lisibles
            chars = [chr(int(name_hex[i:i+2], 16)) for i in range(0, len(name_hex), 2) if 32 <= int(name_hex[i:i+2], 16) <= 126]
            spn = "".join(chars).strip()
            return spn if spn else "Non programmé"
        except Exception:
            pass
        return "Illisible"

    def decode_smsc(self, hex_str):
        if not hex_str or "ffffffff" in hex_str.lower(): 
            return "Non programmé"
        try:
            # Le format standard inclut souvent '91' (Numéro International) avant le BCD
            idx = hex_str.find("91")
            if idx != -1:
                # On extrait la partie BCD (environ 14-16 caractères hexa après le 91)
                bcd_part = hex_str[idx+2 : idx+20]
                swapped = "".join([bcd_part[i+1] + bcd_part[i] for i in range(0, len(bcd_part)-1, 2) if i+1 < len(bcd_part)])
                clean_number = swapped.replace("f", "").replace("F", "")
                
                import re
                if re.match(r'^\d{6,}$', clean_number):
                    return "+" + clean_number
        except Exception:
            pass
        return "Introuvable ou format non standard"

    def parse_fplmn(self, fplmn_hex, csv_path):
        voyages = []
        if fplmn_hex and "ffffffffffff" not in fplmn_hex.lower():
            for i in range(0, len(fplmn_hex), 6):
                chunk = fplmn_hex[i:i+6]
                if len(chunk) == 6 and chunk.lower() != 'ffffff':
                    mcc_f = f"{chunk[1]}{chunk[0]}{chunk[3]}"
                    pays = self.find_country(mcc_f, csv_path)
                    voyages.append(f"-> Blocked : {pays} (MCC: {mcc_f})")
        return voyages

    def check_human_data(self, content, prefix):
        import re
        count = 0
        blocks = re.split(r'(?i)select 6f', content)
        for block in blocks:
            if block.lower().startswith(prefix.lower().replace("6f", "")):
                if prefix == "6f3c":
                    count += len(re.findall(r'"status"', block)) + len(re.findall(r'"tp_pid"', block))
                elif prefix == "6f3a":
                    count += len(re.findall(r'"alpha_id"', block))
                elif prefix == "6f44":
                    count += len(re.findall(r'"alpha_id"', block)) + len(re.findall(r'"ccm"', block))
        return f"{count} trouvés" if count > 0 else "Aucun / Vide"

    def finalize_extraction(self):
        self.progressbar.stop()
        out_dir = self.out_dir
        logical_name = f"{self.ts}_LOGICAL.txt"
        fs_name = f"{self.ts}_FILESYSTEM.txt"
        raw_fs_path = os.path.join(out_dir, "raw_dump.txt")
        
        # Post-Processing: Scellé File System (tar.gz)
        clean_data = []; log_data = []
        markers = ("INFO:", "WARNING:", "ERROR:", "EXCEPTION", "#", "Waiting", "Card", "pySim", "usage:")
        
        if os.path.exists(raw_fs_path):
            with open(raw_fs_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith(markers): log_data.append(line)
                    elif line.strip(): clean_data.append(line)
            
            logical_path = os.path.join(out_dir, logical_name)
            fs_path = os.path.join(out_dir, fs_name) # Used as the LOG_FileSystem equivalent
            
            with open(logical_path, "w", encoding="utf-8") as f: f.writelines(clean_data)
            with open(fs_path, "w", encoding="utf-8") as f: f.writelines(log_data)
            
            try:
                os.remove(raw_fs_path)
            except Exception:
                pass

        try:
            # --- LECTURE GLOBALE DES DONNÉES ---
            content = ""
            for filename in os.listdir(out_dir):
                if filename.endswith(".txt") and "RAPPORT" not in filename:
                    filepath = os.path.join(out_dir, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            content += f.read() + "\n"
                    except: pass

            csv_db = os.path.join(self.pysim_path_var.get(), "mcc-mnc.csv")

            # --- GÉNÉRATION DU RAPPORT TEXTE V1.0 ---
            report_path = os.path.join(out_dir, "RAPPORT_EXPERT.txt")
            with open(report_path, "w", encoding="utf-8") as rf:
                rf.write(f"RAPPORT D'EXPERTISE FORENSIC (V2.01)\nDate: {self.ts}\n" + "="*60 + "\n\n")
                
                rf.write("--- 0. STATUT DE SECURITE ---\n")
                rf.write(f"Vérification Matérielle : {getattr(self, 'last_sec_status', 'Unknown')}\n")
                # On affiche le PIN tapé par l'utilisateur
                pin_teste = self.entry_pin.get().strip() if self.entry_pin.get().strip() else "Aucun / None"
                rf.write(f"Code PIN injecté (Inject PIN) : {pin_teste}\n\n")

                rf.write("--- 1. IDENTITE DE LA CARTE ---\n")
                iccid_hex = self.extract_hex_from_dump(content, "2fe2")
                imsi_hex = self.extract_hex_from_dump(content, "6f07")
                msisdn_hex = self.extract_hex_from_dump(content, "6f40")
                
                imsi_clean = self.decode_imsi(imsi_hex)
                rf.write(f"ICCID : {self.decode_iccid(iccid_hex) if iccid_hex else 'Inaccessible'}\n")
                rf.write(f"IMSI  : {imsi_clean}\n")
                rf.write(f"MSISDN: {self.decode_msisdn(msisdn_hex)}\n")
                
                if imsi_clean == "Inaccessible":
                    net_str = "Inconnu (IMSI manquant)"
                    rf.write("NET   : Inconnu (IMSI manquant)\n")
                else:
                    net_str = self.find_operator(imsi_clean, csv_db)
                    rf.write(f"NET   : {net_str}\n")
                    
                lang_hex = self.extract_hex_from_dump(content, "6f05")
                rf.write(f"LANGUE: {self.decode_language(lang_hex)}\n")

                spn_hex = self.extract_hex_from_dump(content, "6f46")
                rf.write(f"SPN   : {self.decode_spn(spn_hex)}\n")
                
                smsc_hex = self.extract_hex_from_dump(content, "6f42")
                rf.write(f"SMSC  : {self.decode_smsc(smsc_hex)}\n\n")

                rf.write("--- 2. GEOLOCALISATION & TRACKING ---\n")
                epsloci_hex = self.extract_hex_from_dump(content, "6fe3")
                loci_hex = self.extract_hex_from_dump(content, "6f7e")
                
                mcc, mnc = None, None
                try:
                    res = self.decode_plmn(epsloci_hex, 24)
                    if res and len(res) >= 2: mcc, mnc = res[0], res[1]
                except Exception: pass
                
                if not mcc:
                    try:
                        res = self.decode_plmn(loci_hex, 8)
                        if res and len(res) >= 2: mcc, mnc = res[0], res[1]
                    except Exception: pass
                    
                if mcc and mnc:
                    roaming_net = self.get_roaming_network(mcc, mnc, csv_db)
                    rf.write(f"LOCI/EPSLOCI : Dernier réseau accroché -> {roaming_net} (MCC:{mcc}/MNC:{mnc})\n\n")
                else:
                    rf.write("LOCI/EPSLOCI : Inconnue / Aucune trace réseau\n\n")
                
                rf.write("FPLMN :\n")
                fplmn_hex = self.extract_hex_from_dump(content, "6f7b")
                voyages = self.parse_fplmn(fplmn_hex, csv_db)
                if voyages:
                    for v in voyages: rf.write(f"  {v}\n")
                else:
                    rf.write("  -> Aucun franchissement de frontière détecté.\n")
                rf.write("\n")

                rf.write("--- 3. DONNEES UTILISATEUR (Alerte Forensic) ---\n")
                sms_stat = self.check_human_data(content, "6f3c")
                adn_stat = self.check_human_data(content, "6f3a")
                lnd_stat = self.check_human_data(content, "6f44")
                
                rf.write(f"SMS       : {sms_stat}\n")
                rf.write(f"CONTACTS  : {adn_stat}\n")
                rf.write(f"APPELS    : {lnd_stat}\n")

            # Affichage du résumé visuel sur la console
            visual_summary = (
                f"\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  📝 RÉSUMÉ D'EXTRACTION (V2.01)\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  ▪ PIN TESTÉ    : {pin_teste}\n"
                f"  ▪ ICCID        : {self.decode_iccid(iccid_hex) if iccid_hex else 'Inaccessible'}\n"
                f"  ▪ IMSI         : {imsi_clean}\n"
                f"  ▪ MSISDN       : {self.decode_msisdn(msisdn_hex)}\n"
                f"  ▪ OPERATEUR    : {net_str}\n"
                f"  ▪ SPN          : {self.decode_spn(spn_hex)}\n"
                f"  ▪ SMSC         : {self.decode_smsc(smsc_hex)}\n"
                f"  ▪ LANGUE       : {self.decode_language(lang_hex)}\n"
                f"  ▪ CONTENU      : SMS: {sms_stat} | Contacts: {adn_stat} | Appels: {lnd_stat}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            )
            self.log(visual_summary)
            self.log(f"[+] Rapport d'Expertise généré : {report_path}\n")

            # --- 4. MISE SOUS SCELLÉ LÉGAL (.TAR.GZ) ---
            tar_name = f"SCELLE_FORENSIC_{self.ts}.tar.gz"
            tar_path = os.path.join(out_dir, tar_name)
            
            import tarfile
            with tarfile.open(tar_path, "w:gz") as tar:
                for filename in os.listdir(out_dir):
                    if filename.endswith(".txt") and filename != "CERTIFICAT_SHA256.txt":
                        filepath = os.path.join(out_dir, filename)
                        tar.add(filepath, arcname=filename)
            
            # --- 5. GÉNÉRATION DU CERTIFICAT SHA-256 ---
            import hashlib
            h = hashlib.sha256()
            with open(tar_path, "rb") as f:
                for b in iter(lambda: f.read(4096), b""): 
                    h.update(b)
                    
            cert_path = os.path.join(out_dir, "CERTIFICAT_SHA256.txt")
            with open(cert_path, "w", encoding="utf-8") as f:
                f.write(f"--- CERTIFICAT D'EMPREINTE NUMERIQUE / DIGITAL SEAL ---\n")
                f.write(f"Archive: {tar_name}\n")
                f.write(f"SHA-256: {h.hexdigest()}\n")
            
            self.log(f"[+] Scellé TAR.GZ Créé avec succès : {tar_name}\n")
            self.log(f"[+] HASH SHA-256 : {h.hexdigest()}\n")
            
            # --- DEGEL UI ET OUVERTURE DU DOSSIER ---
            def reset_ui_state():
                self.btn_run.configure(state="normal")
                self.btn_stop.configure(state="disabled")
                try:
                    os.startfile(out_dir)
                except Exception:
                    pass

            self.after(0, reset_ui_state)
                
        except Exception as e:
            self.log(f"[!] Erreur de génération du rapport : {str(e)}\n")

    def stop_extraction(self):
        if self.pysim_runner:
            self.pysim_runner.stop()
        self.log("\n[!] Process stopped by user.\n")
        self.progressbar.stop()
        self.progressbar.set(0)
        self.btn_run.configure(state="normal")
        self.btn_stop.configure(state="disabled")

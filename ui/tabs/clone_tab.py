import customtkinter as ctk
import os
import queue
import threading
from core.lang import LANG
from core.pysim_runner import PySimRunner

class CloneTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=10)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.lbl_title = ctk.CTkLabel(self, text=LANG["FR"]["tab_clone"], font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_title.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.warning_frame = ctk.CTkFrame(self, fg_color="#D32F2F", corner_radius=5)
        self.warning_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.lbl_warning = ctk.CTkLabel(self.warning_frame, text=LANG["FR"]["lbl_clone_warning"], font=ctk.CTkFont(weight="bold"), text_color="white")
        self.lbl_warning.pack(pady=10)

        self.form_frame = ctk.CTkFrame(self)
        self.form_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.form_frame.grid_columnconfigure(1, weight=1)

        # Fields
        self.lbl_iccid = ctk.CTkLabel(self.form_frame, text=LANG["FR"]["lbl_target_iccid"]).grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.ent_iccid = ctk.CTkEntry(self.form_frame)
        self.ent_iccid.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.lbl_imsi = ctk.CTkLabel(self.form_frame, text=LANG["FR"]["lbl_target_imsi"]).grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.ent_imsi = ctk.CTkEntry(self.form_frame)
        self.ent_imsi.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        self.btn_import = ctk.CTkButton(self.form_frame, text=LANG["FR"]["btn_import_last"], command=self.import_last_extraction)
        self.btn_import.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        self.lbl_adm = ctk.CTkLabel(self.form_frame, text=LANG["FR"]["lbl_adm_key"]).grid(row=3, column=0, padx=10, pady=20, sticky="e")
        self.ent_adm = ctk.CTkEntry(self.form_frame, placeholder_text="ex: 3132333435363738")
        self.ent_adm.grid(row=3, column=1, padx=10, pady=20, sticky="ew")

        self.btn_burn = ctk.CTkButton(self.form_frame, text=LANG["FR"]["btn_burn_clone"], fg_color="red", hover_color="darkred", font=ctk.CTkFont(weight="bold"), command=self.run_clone_mission)
        self.btn_burn.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.console = ctk.CTkTextbox(self.form_frame, font=ctk.CTkFont(family="Consolas", size=12), height=150)
        self.console.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.console.configure(state="disabled")

        self.worker_queue = queue.Queue()
        self.pysim_runner = None

    def update_lang(self, l):
        self.lbl_title.configure(text=LANG[l]["tab_clone"])
        self.lbl_warning.configure(text=LANG[l]["lbl_clone_warning"])
        # Form labels are created dynamically, can't easily update without refs, but avoiding for simplicity for now.
        pass

    def log(self, text):
        self.console.configure(state="normal")
        self.console.insert("end", text)
        self.console.see("end")
        self.console.configure(state="disabled")

    def import_last_extraction(self):
        mission_tab = self.master.tabs.get("MissionTab")
        if hasattr(mission_tab, "out_dir") and os.path.exists(mission_tab.out_dir):
            report_path = os.path.join(mission_tab.out_dir, "RAPPORT_EXPERT.txt")
            if os.path.exists(report_path):
                try:
                    with open(report_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        for line in lines:
                            if "ICCID :" in line and "Inaccessible" not in line:
                                self.ent_iccid.delete(0, 'end')
                                self.ent_iccid.insert(0, line.split("ICCID :")[1].strip())
                            elif "IMSI  :" in line and "Inaccessible" not in line:
                                self.ent_imsi.delete(0, 'end')
                                self.ent_imsi.insert(0, line.split("IMSI  :")[1].strip())
                    self.log("[+] Données importées depuis le dernier rapport.\n")
                    return
                except:
                    pass
        self.log("[-] Impossible de trouver les données de la dernière extraction.\n")

    def encode_iccid(self, iccid_str):
        if len(iccid_str) % 2 != 0:
            iccid_str += "F"
        swapped = "".join([iccid_str[i+1] + iccid_str[i] for i in range(0, len(iccid_str)-1, 2)])
        while len(swapped) < 20:
            swapped += "FF"
        return swapped[:20]

    def encode_imsi(self, imsi_str):
        if len(imsi_str) > 15: imsi_str = imsi_str[:15]
        if len(imsi_str) % 2 != 0:
            parity = "9"
            padded = imsi_str[1:]
        else:
            parity = "8"
            padded = imsi_str[1:] + "F"
            
        byte2 = imsi_str[0] + parity
        swapped_rest = "".join([padded[i+1] + padded[i] for i in range(0, len(padded)-1, 2) if i+1 < len(padded)])
        return "08" + byte2 + swapped_rest

    def run_clone_mission(self):
        iccid = self.ent_iccid.get().strip()
        imsi = self.ent_imsi.get().strip()
        adm = self.ent_adm.get().strip()

        if not iccid or not imsi or not adm:
            self.log("[!] Veuillez remplir tous les champs (ICCID, IMSI, ADM).\n")
            return

        mission_tab = self.master.tabs.get("MissionTab")
        pysim_path = mission_tab.pysim_path_var.get()
        if not os.path.exists(pysim_path):
            self.log("[!] Pysim path is not valid.\n")
            return

        reader_str = mission_tab.cb_reader.get()
        py_reader_idx = 0
        if "Lecteur " in reader_str:
            try:
                py_reader_idx = int(reader_str.split("Lecteur ")[1].split(" ")[0]) - 1
            except: pass

        iccid_hex = self.encode_iccid(iccid)
        imsi_hex = self.encode_imsi(imsi)

        cmds = f"verify_adm {adm}\n"
        cmds += "select 2fe2\n"
        cmds += f"update_binary {iccid_hex}\n"
        cmds += "select ADF.USIM\n"
        cmds += "select 6f07\n"
        cmds += f"update_binary {imsi_hex}\n"
        cmds += "quit\n"

        import tempfile
        out_dir = tempfile.gettempdir()

        self.pysim_runner = PySimRunner(
            pysim_path=pysim_path,
            reader_idx=py_reader_idx,
            output_dir=out_dir,
            ui_queue=self.worker_queue
        )
        
        self.btn_burn.configure(state="disabled")
        self.log(f"[*] Préparation du script de clonage pour ICCID {iccid} et IMSI {imsi}...\n")
        self.log(f"[*] ICCID encodé = {iccid_hex}\n")
        self.log(f"[*] IMSI encodé = {imsi_hex}\n")
        self.log("[*] Lancement de l'écriture sur la White Card...\n")

        t = threading.Thread(target=self.pysim_runner.run_script, args=(cmds, "clone_log.txt"), daemon=True)
        t.start()

        self.after(100, self.check_queue)

    def check_queue(self):
        while not self.worker_queue.empty():
            msg = self.worker_queue.get()
            if msg == "===PROCESS_DONE===":
                self.btn_burn.configure(state="normal")
                self.log("\n[+] Opération d'écriture terminée.\n")
                return
            else:
                self.log(msg)
        self.after(100, self.check_queue)

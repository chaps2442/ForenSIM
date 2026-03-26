import customtkinter as ctk
import os
from core.osint import decode_iccid, decode_imsi
from core.lang import LANG

class OsintTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=10)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.lbl_title = ctk.CTkLabel(self, text=LANG["FR"]["tab_osint"], font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_title.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.ent_query = ctk.CTkEntry(self.search_frame, placeholder_text=LANG["FR"]["ent_query_placeholder"], height=40)
        self.ent_query.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.btn_search = ctk.CTkButton(self.search_frame, text=LANG["FR"]["btn_search"], width=120, height=40, command=self.perform_search)
        self.btn_search.grid(row=0, column=1, padx=10, pady=10)

        self.console = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=12), text_color="#4dd2ff")
        self.console.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        self.console.insert("0.0", "Entrez IMSI / ICCID / MAC pour analyser la donnée.\n")
        self.console.configure(state="disabled")

        # Basic pysim path for csv lookup
        self.pysim_path = os.path.join(os.path.expanduser("~"), "pysim")

    def log(self, text):
        self.console.configure(state="normal")
        self.console.insert("end", text + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def perform_search(self):
        query = self.ent_query.get().strip().upper()
        if not query: return
        
        self.console.configure(state="normal")
        self.console.delete("0.0", "end")
        self.console.configure(state="disabled")
        
        self.log(f"[+] Analyze : {query}")
        self.log("-" * 40)
        
        query_digits = "".join([c for c in query if c.isdigit()])
        
        if len(query_digits) >= 18 and (query_digits.startswith("89") or "F" in query):
            self.log("[*] Format detected : ICCID")
            res = decode_iccid(query)
            for k, v in res.items(): self.log(f" -> {k.capitalize()}: {v}")
            
        elif len(query_digits) in [14, 15]:
            self.log("[*] Format detected : IMSI")
            res = decode_imsi(query_digits, self.pysim_path)
            for k, v in res.items(): self.log(f" -> {k.capitalize()}: {v}")
                
        elif ":" in query or len(query) == 12:
            self.log("[*] Format detected : MAC Address")
            self.log(" -> OUI Identification needs oui.csv configuration.")
        else:
            self.log("[!] Unknown format. Try 15 digits for IMSI, 18-20 for ICCID.")

    def update_lang(self, l):
        self.lbl_title.configure(text=LANG[l]["tab_osint"])
        self.ent_query.configure(placeholder_text=LANG[l]["ent_query_placeholder"])
        self.btn_search.configure(text=LANG[l]["btn_search"])

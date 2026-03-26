import customtkinter as ctk
import webbrowser
from core.lang import LANG

class AboutTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=10)
        self.grid_columnconfigure(0, weight=1)

        # Title
        self.lbl_title = ctk.CTkLabel(self, text=LANG["FR"]["title"], font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_title.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.lbl_desc = ctk.CTkLabel(self, text=LANG["FR"]["about_desc"], justify="center")
        self.lbl_desc.grid(row=1, column=0, padx=20, pady=5)

        # Dev Info
        self.frame_dev = ctk.CTkFrame(self)
        self.frame_dev.grid(row=2, column=0, padx=40, pady=10, sticky="ew")
        
        self.lbl_dev_title = ctk.CTkLabel(self.frame_dev, text=LANG["FR"]["about_dev"], font=ctk.CTkFont(weight="bold"))
        self.lbl_dev_title.pack(pady=5)
        ctk.CTkLabel(self.frame_dev, text="Hat Forensic Investigation\nContact : vincent.chapeau@teeltechcanada.com").pack(pady=5)

        # Explanations
        self.frame_exp = ctk.CTkFrame(self)
        self.frame_exp.grid(row=3, column=0, padx=40, pady=10, sticky="ew")
        self.lbl_exp = ctk.CTkLabel(self.frame_exp, text=LANG["FR"]["about_explanations"], justify="left", wraplength=800)
        self.lbl_exp.pack(pady=10, padx=10)

        # Links
        self.frame_links = ctk.CTkFrame(self)
        self.frame_links.grid(row=4, column=0, padx=40, pady=10, sticky="ew")
        
        self.lbl_links_title = ctk.CTkLabel(self.frame_links, text=LANG["FR"]["about_links"], font=ctk.CTkFont(weight="bold"))
        self.lbl_links_title.pack(pady=5)
        
        self.add_link(self.frame_links, "► Moteur : Osmocom pySim (Gitea Repository)", "https://gitea.osmocom.org/sim-card/pysim")
        self.add_link(self.frame_links, "► Base de données MCC/MNC (Requis : mcc-mnc.csv dans le dossier pySim)", "https://mcc-mnc.net/")
        self.add_link(self.frame_links, "► Base de données MAC/OUI (Requis : oui.csv dans le dossier pySim)", "http://standards-oui.ieee.org/oui/oui.csv")
        self.add_link(self.frame_links, "► Base de données IMEI/TAC (Requis : trouver un 'tac.csv' via OSINT Github)", "https://github.com/search?q=tac.csv&type=code")

    def add_link(self, parent, text, url):
        lbl = ctk.CTkLabel(parent, text=text, text_color="#55b3ff", cursor="hand2")
        lbl.pack(pady=2)
        lbl.bind("<Button-1>", lambda e: webbrowser.open_new(url))

    def update_lang(self, l):
        self.lbl_title.configure(text=LANG[l]["title"])
        self.lbl_desc.configure(text=LANG[l]["about_desc"])
        self.lbl_dev_title.configure(text=LANG[l]["about_dev"])
        self.lbl_links_title.configure(text=LANG[l]["about_links"])
        self.lbl_exp.configure(text=LANG[l]["about_explanations"])

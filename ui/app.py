import customtkinter as ctk
from .tabs.mission_tab import MissionTab
from .tabs.osint_tab import OsintTab
from .tabs.about_tab import AboutTab
from .tabs.clone_tab import CloneTab
from .tabs.risk_tab import RiskTab
from .tabs.euicc_tab import EuiccTab
from core.lang import LANG
import ctypes

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ForenSimApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.current_lang = "FR"
        self.check_admin()

        self.title(LANG[self.current_lang]["title"] + self.admin_suffix)
        self.geometry("1100x800")
        
        # Grid layout (1x2)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Navigation Frame
        self.nav_frame = ctk.CTkFrame(self, corner_radius=0)
        self.nav_frame.grid(row=0, column=0, sticky="nsew")
        self.nav_frame.grid_rowconfigure(6, weight=1)
        
        # Branding
        self.logo_label = ctk.CTkLabel(
            self.nav_frame, text="ForenSIM V2", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 20))
        
        # Tabs dictionary to hold content frames
        self.tabs = {}
        
        # Create Buttons for Sidebar
        self.btn_mission = ctk.CTkButton(self.nav_frame, corner_radius=0, height=40, border_spacing=10, 
                                         text=LANG[self.current_lang]["tab_mission"],
                                         fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                         anchor="w", command=lambda: self.select_tab("MissionTab"))
        self.btn_mission.grid(row=1, column=0, sticky="ew")

        self.btn_osint = ctk.CTkButton(self.nav_frame, corner_radius=0, height=40, border_spacing=10, 
                                       text=LANG[self.current_lang]["tab_osint"],
                                       fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                       anchor="w", command=lambda: self.select_tab("OsintTab"))
        self.btn_osint.grid(row=2, column=0, sticky="ew")
        
        self.btn_clone = ctk.CTkButton(self.nav_frame, corner_radius=0, height=40, border_spacing=10, 
                                       text=LANG[self.current_lang]["tab_clone"],
                                       fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                       anchor="w", command=lambda: self.select_tab("CloneTab"))
        self.btn_clone.grid(row=3, column=0, sticky="ew")

        self.btn_risk = ctk.CTkButton(self.nav_frame, corner_radius=0, height=40, border_spacing=10, 
                                       text=LANG[self.current_lang]["tab_risk"],
                                       fg_color="transparent", text_color=("red", "lightcoral"), hover_color=("gray70", "gray30"),
                                       anchor="w", command=lambda: self.select_tab("RiskTab"))
        self.btn_risk.grid(row=4, column=0, sticky="ew")

        self.btn_euicc = ctk.CTkButton(self.nav_frame, corner_radius=0, height=40, border_spacing=10,
                                       text="🛰 eUICC / eSIM",
                                       fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                       anchor="w", command=lambda: self.select_tab("EuiccTab"))
        self.btn_euicc.grid(row=5, column=0, sticky="ew")

        self.btn_about = ctk.CTkButton(self.nav_frame, corner_radius=0, height=40, border_spacing=10, 
                                       text=LANG[self.current_lang]["tab_about"],
                                       fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                       anchor="w", command=lambda: self.select_tab("AboutTab"))
        self.btn_about.grid(row=6, column=0, sticky="ew")

        # Initialize content frames
        self.tabs["MissionTab"] = MissionTab(self)
        self.tabs["OsintTab"] = OsintTab(self)
        self.tabs["CloneTab"] = CloneTab(self)
        self.tabs["RiskTab"] = RiskTab(self)
        self.tabs["EuiccTab"] = EuiccTab(self)
        self.tabs["AboutTab"] = AboutTab(self)
        
        self.btn_lang = ctk.CTkButton(self, text="🌍 EN/FR", width=100, height=30, fg_color="#333333", hover_color="#555555", command=self.toggle_lang)
        self.btn_lang.place(relx=0.98, rely=0.02, anchor="ne")

        # Configuration Check Panel
        self.cfg_check_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", border_width=1, border_color="#555555")
        self.cfg_check_frame.place(relx=0.98, rely=0.08, anchor="ne")
        
        self.lbl_cfg_title = ctk.CTkLabel(self.cfg_check_frame, text="Configuration Check", font=ctk.CTkFont(size=11, weight="bold"))
        self.lbl_cfg_title.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5))

        self.lbl_mcc = ctk.CTkLabel(self.cfg_check_frame, text="[ ? ] Base Opérateurs", font=ctk.CTkFont(size=11))
        self.lbl_mcc.grid(row=1, column=0, sticky="w", padx=10, pady=2)

        self.lbl_oui = ctk.CTkLabel(self.cfg_check_frame, text="[ ? ] Base Réseaux / OUI", font=ctk.CTkFont(size=11))
        self.lbl_oui.grid(row=2, column=0, sticky="w", padx=10, pady=(2, 10))

        # Show default tab
        self.select_tab("MissionTab")
        self.update_config_check()

    def select_tab(self, tab_name):
        # Update button colors
        self.btn_mission.configure(fg_color=("gray75", "gray25") if tab_name == "MissionTab" else "transparent")
        self.btn_osint.configure(fg_color=("gray75", "gray25") if tab_name == "OsintTab" else "transparent")
        self.btn_clone.configure(fg_color=("gray75", "gray25") if tab_name == "CloneTab" else "transparent")
        self.btn_risk.configure(fg_color=("gray75", "gray25") if tab_name == "RiskTab" else "transparent")
        self.btn_euicc.configure(fg_color=("gray75", "gray25") if tab_name == "EuiccTab" else "transparent")
        self.btn_about.configure(fg_color=("gray75", "gray25") if tab_name == "AboutTab" else "transparent")
        
        # Hide all tabs
        for name, frame in self.tabs.items():
            frame.grid_forget()
            
        # Show selected tab
        self.tabs[tab_name].grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        # Show diagnostic frame only on Mission tab
        if tab_name == "MissionTab":
            self.cfg_check_frame.place(relx=0.98, rely=0.08, anchor="ne")
        else:
            self.cfg_check_frame.place_forget()

    def check_admin(self):
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            self.admin_suffix = "" if is_admin else " [No Admin Rights]"
        except:
            self.admin_suffix = ""

    def toggle_lang(self):
        self.current_lang = "EN" if self.current_lang == "FR" else "FR"
        self.title(LANG[self.current_lang]["title"] + self.admin_suffix)
        self.btn_mission.configure(text=LANG[self.current_lang]["tab_mission"])
        self.btn_osint.configure(text=LANG[self.current_lang]["tab_osint"])
        self.btn_clone.configure(text=LANG[self.current_lang]["tab_clone"])
        self.btn_risk.configure(text=LANG[self.current_lang]["tab_risk"])
        self.btn_about.configure(text=LANG[self.current_lang]["tab_about"])
        
        # Propagate to tabs
        for tab in self.tabs.values():
            if hasattr(tab, "update_lang"):
                tab.update_lang(self.current_lang)

    def update_config_check(self):
        import os
        try:
            pysim_path = self.tabs["MissionTab"].pysim_path_var.get()
            mcc_ok = os.path.exists(os.path.join(pysim_path, "mcc-mnc.csv"))
            oui_ok = os.path.exists(os.path.join(pysim_path, "oui.csv"))

            self.lbl_mcc.configure(text="[ ✔ ] Base Opérateurs" if mcc_ok else "[ ❌ ] Base Opérateurs", text_color="#4CAF50" if mcc_ok else "#D32F2F")
            self.lbl_oui.configure(text="[ ✔ ] Base Réseaux / OUI" if oui_ok else "[ ❌ ] Base Réseaux / OUI", text_color="#4CAF50" if oui_ok else "#D32F2F")
        except Exception:
            pass

def run_app():
    app = ForenSimApp()
    app.mainloop()

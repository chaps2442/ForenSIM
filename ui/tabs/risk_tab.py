import customtkinter as ctk
from core.lang import LANG
from core.smartcard_handler import unblock_pin, change_pin, toggle_pin

class RiskTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=10)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.lbl_title = ctk.CTkLabel(self, text=LANG["FR"]["tab_risk"], font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_title.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.column_container = ctk.CTkFrame(self, fg_color="transparent")
        self.column_container.grid(row=1, column=0, pady=5, sticky="ew", padx=20)
        self.column_container.grid_columnconfigure(0, weight=1)

        self.sec_adv = ctk.CTkFrame(self.column_container, border_width=2, border_color="#D32F2F", fg_color="transparent")
        self.sec_adv.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.sec_adv.grid_columnconfigure(1, weight=1)

        self.lbl_sec_adv = ctk.CTkLabel(self.sec_adv, text=LANG["FR"]["lbl_sec_adv"], font=ctk.CTkFont(weight="bold"), text_color="#D32F2F")
        self.lbl_sec_adv.grid(row=0, column=0, columnspan=3, pady=(10, 5))
        
        # PUK
        self.lbl_puk_unlock = ctk.CTkLabel(self.sec_adv, text=LANG["FR"]["lbl_puk_unlock"])
        self.lbl_puk_unlock.grid(row=1, column=0, padx=10, pady=10, sticky="e")

        self.frame_puk_inputs = ctk.CTkFrame(self.sec_adv, fg_color="transparent")
        self.frame_puk_inputs.grid(row=1, column=1, sticky="w")
        self.ent_puk = ctk.CTkEntry(self.frame_puk_inputs, placeholder_text=LANG["FR"]["ent_puk_placeholder"], width=80)
        self.ent_puk.pack(side="left", padx=2)
        self.ent_new_pin1 = ctk.CTkEntry(self.frame_puk_inputs, placeholder_text=LANG["FR"]["ent_new_pin_placeholder"], width=80)
        self.ent_new_pin1.pack(side="left", padx=2)

        self.btn_puk = ctk.CTkButton(self.sec_adv, text=LANG["FR"]["btn_unblock_puk"], width=150, command=self.unblock_puk_ui)
        self.btn_puk.grid(row=1, column=2, padx=10, pady=10, sticky="w")

        # Change PIN
        self.lbl_change_pin = ctk.CTkLabel(self.sec_adv, text=LANG["FR"]["lbl_change_pin"])
        self.lbl_change_pin.grid(row=2, column=0, padx=10, pady=10, sticky="e")

        self.frame_change_inputs = ctk.CTkFrame(self.sec_adv, fg_color="transparent")
        self.frame_change_inputs.grid(row=2, column=1, sticky="w")
        self.ent_old_pin = ctk.CTkEntry(self.frame_change_inputs, placeholder_text=LANG["FR"]["ent_pin_placeholder"], width=80)
        self.ent_old_pin.pack(side="left", padx=2)
        self.ent_new_pin2 = ctk.CTkEntry(self.frame_change_inputs, placeholder_text=LANG["FR"]["ent_new_pin_placeholder"], width=80)
        self.ent_new_pin2.pack(side="left", padx=2)

        self.btn_change_pin = ctk.CTkButton(self.sec_adv, text=LANG["FR"]["btn_change_pin"], width=150, command=self.change_pin_ui)
        self.btn_change_pin.grid(row=2, column=2, padx=10, pady=10, sticky="w")

        # Enable / Disable PIN
        self.lbl_toggle_pin = ctk.CTkLabel(self.sec_adv, text="Activer/Désactiver PIN:")
        self.lbl_toggle_pin.grid(row=3, column=0, padx=10, pady=10, sticky="e")

        self.ent_toggle_pin = ctk.CTkEntry(self.sec_adv, placeholder_text=LANG["FR"]["ent_pin_placeholder"], width=165)
        self.ent_toggle_pin.grid(row=3, column=1, sticky="w", padx=2)
        
        self.frame_toggle_buttons = ctk.CTkFrame(self.sec_adv, fg_color="transparent")
        self.frame_toggle_buttons.grid(row=3, column=2, sticky="w", padx=10, pady=10)

        self.btn_enable_pin = ctk.CTkButton(self.frame_toggle_buttons, text="Activer", fg_color="green", hover_color="darkgreen", width=70, command=self.enable_pin_ui)
        self.btn_enable_pin.pack(side="left", padx=(0, 5))

        self.btn_disable_pin = ctk.CTkButton(self.frame_toggle_buttons, text="Désactiver", fg_color="red", hover_color="darkred", width=70, command=self.disable_pin_ui)
        self.btn_disable_pin.pack(side="left", padx=(5, 0))

        self.lbl_pin_status = ctk.CTkLabel(self.column_container, text="", font=ctk.CTkFont(weight="bold", size=14))
        self.lbl_pin_status.grid(row=1, column=0, pady=20)

    def update_lang(self, l):
        self.lbl_title.configure(text=LANG[l]["tab_risk"])
        self.lbl_sec_adv.configure(text=LANG[l]["lbl_sec_adv"])
        self.lbl_puk_unlock.configure(text=LANG[l]["lbl_puk_unlock"])
        self.ent_puk.configure(placeholder_text=LANG[l]["ent_puk_placeholder"])
        self.ent_new_pin1.configure(placeholder_text=LANG[l]["ent_new_pin_placeholder"])
        self.btn_puk.configure(text=LANG[l]["btn_unblock_puk"])
        self.lbl_change_pin.configure(text=LANG[l]["lbl_change_pin"])
        self.ent_old_pin.configure(placeholder_text=LANG[l]["ent_pin_placeholder"])
        self.ent_new_pin2.configure(placeholder_text=LANG[l]["ent_new_pin_placeholder"])
        self.btn_change_pin.configure(text=LANG[l]["btn_change_pin"])
        
        if l == "EN":
            self.lbl_toggle_pin.configure(text="Enable/Disable PIN:")
            self.btn_enable_pin.configure(text="Enable")
            self.btn_disable_pin.configure(text="Disable")
        else:
            self.lbl_toggle_pin.configure(text="Activer/Désactiver PIN:")
            self.btn_enable_pin.configure(text="Activer")
            self.btn_disable_pin.configure(text="Désactiver")
        self.ent_toggle_pin.configure(placeholder_text=LANG[l]["ent_pin_placeholder"])

    def get_reader_idx(self):
        mission_tab = self.master.tabs.get("MissionTab")
        reader_idx = mission_tab.cb_reader.get()
        py_reader_idx = 0
        if "Lecteur " in reader_idx:
            try:
                py_reader_idx = int(reader_idx.split("Lecteur ")[1].split(" ")[0]) - 1
            except: pass
        return py_reader_idx

    def unblock_puk_ui(self):
        py_reader_idx = self.get_reader_idx()
        puk = self.ent_puk.get().strip()
        new_pin = self.ent_new_pin1.get().strip()
        status, color = unblock_pin(py_reader_idx, puk, new_pin) if puk and new_pin else ("PUK et Nouveau PIN requis", "orange")
        self.lbl_pin_status.configure(text=status, text_color=color)

    def change_pin_ui(self):
        py_reader_idx = self.get_reader_idx()
        old_pin = self.ent_old_pin.get().strip()
        new_pin = self.ent_new_pin2.get().strip()
        status, color = change_pin(py_reader_idx, old_pin, new_pin) if old_pin and new_pin else ("Ancien PIN et Nouveau PIN requis", "orange")
        self.lbl_pin_status.configure(text=status, text_color=color)

    def enable_pin_ui(self):
        py_reader_idx = self.get_reader_idx()
        pin = self.ent_toggle_pin.get().strip()
        status, color = toggle_pin(py_reader_idx, pin, enable=True) if pin else ("Code PIN requis", "orange")
        self.lbl_pin_status.configure(text=status, text_color=color)

    def disable_pin_ui(self):
        py_reader_idx = self.get_reader_idx()
        pin = self.ent_toggle_pin.get().strip()
        status, color = toggle_pin(py_reader_idx, pin, enable=False) if pin else ("Code PIN requis", "orange")
        self.lbl_pin_status.configure(text=status, text_color=color)

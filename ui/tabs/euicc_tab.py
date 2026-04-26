"""eUICC / eSIM tab — extraction profils + ARA-M + détection SGP.32 IoT.

Onglet ajouté en V2.02 pour combler le gap pySIM upstream :
  - Lecture EID
  - Liste des profils installés (consumer + IoT)
  - ARA-M rules dump
  - Détection SGP.02 (M2M legacy) vs SGP.22 (consumer) vs SGP.32 (IoT)
  - Métadonnées profil (ICCID + ISD-P AID + état + opérateur)

Pertinence forensics véhicule : le TCU (Telematic Control Unit) connected
car embarque souvent un eUICC. Cet onglet permet de l'extraire de manière
non-destructive (lecture seule par défaut — enable/disable est dans
l'onglet RisqueTab pour qu'il y ait un avertissement explicite).
"""
from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core import euicc_handler as eh
from core.pysim_runner import PySimRunner


class EuiccTab(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")
        self.master_app = master
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._info = eh.EuiccInfo()
        self._ui_queue: queue.Queue[str] = queue.Queue()
        self._build()
        self._poll_queue()

    def _build(self) -> None:
        # === Header ===
        title = ctk.CTkLabel(
            self,
            text="🛰 eUICC / eSIM — extraction GSMA SGP.02 / SGP.22 / SGP.32",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))

        intro = ctk.CTkLabel(
            self,
            text=(
                "Lecture EID + profils installés + règles ARA-M sur eUICC "
                "consumer (SGP.22) ou IoT (SGP.32). Pertinent pour TCU "
                "connected car (Tesla, BMW, Mercedes me, Stellantis SOTA)."
            ),
            wraplength=900, justify="left", text_color=("gray30", "gray70"),
        )
        intro.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))

        # === Toolbar ===
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", padx=10, pady=4)

        ctk.CTkButton(
            bar, text="🔍 Identifier eUICC + EID",
            command=self._identify_euicc, width=220,
        ).grid(row=0, column=0, padx=2, pady=4)

        ctk.CTkButton(
            bar, text="📋 Lister profils",
            command=self._list_profiles, width=180,
        ).grid(row=0, column=1, padx=2, pady=4)

        ctk.CTkButton(
            bar, text="🔐 Dump ARA-M rules",
            command=self._dump_aram, width=200,
        ).grid(row=0, column=2, padx=2, pady=4)

        ctk.CTkButton(
            bar, text="📤 Exporter rapport",
            command=self._export_report, width=180,
            fg_color="#2e7d32", hover_color="#1b5e20",
        ).grid(row=0, column=3, padx=2, pady=4)

        ctk.CTkButton(
            bar, text="🧹 Reset",
            command=self._reset, width=80,
            fg_color="#666", hover_color="#444",
        ).grid(row=0, column=4, padx=2, pady=4)

        # === Info row : EID + SGP variant ===
        info_frame = ctk.CTkFrame(self, fg_color=("gray85", "gray20"))
        info_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=4)
        info_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(info_frame, text="EID :",
                     font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=8, pady=4)
        self.eid_var = tk.StringVar(value="(non récupéré)")
        ctk.CTkLabel(info_frame, textvariable=self.eid_var,
                     font=ctk.CTkFont(family="Consolas")).grid(
            row=0, column=1, sticky="w", padx=4, pady=4)

        ctk.CTkLabel(info_frame, text="GSMA :",
                     font=ctk.CTkFont(weight="bold")).grid(
            row=1, column=0, sticky="w", padx=8, pady=4)
        self.sgp_var = tk.StringVar(value="(?)")
        ctk.CTkLabel(info_frame, textvariable=self.sgp_var).grid(
            row=1, column=1, sticky="w", padx=4, pady=4)

        # === Profiles table ===
        tbl_frame = ctk.CTkFrame(self, fg_color="transparent")
        tbl_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=4)
        tbl_frame.grid_columnconfigure(0, weight=1)
        tbl_frame.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # CTk doesn't have a native table — use a textbox formatted as a list
        ctk.CTkLabel(
            tbl_frame, text="Profils installés",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w")
        self.profiles_tb = ctk.CTkTextbox(
            tbl_frame, height=180, font=ctk.CTkFont(family="Consolas"),
        )
        self.profiles_tb.pack(fill="both", expand=False, pady=(2, 4))

        # === Live log ===
        log_frame = ctk.CTkFrame(self, fg_color="transparent")
        log_frame.grid(row=5, column=0, sticky="nsew", padx=10, pady=4)
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(log_frame, text="Sortie pySim-shell live",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, sticky="w")
        self.log_tb = ctk.CTkTextbox(
            log_frame, font=ctk.CTkFont(family="Consolas", size=10),
        )
        self.log_tb.grid(row=1, column=0, sticky="nsew")

        # === Output buffer ===
        self._output_buffer = ""

    # ──────────────────────────────────────────────────────────────────
    # Actions
    # ──────────────────────────────────────────────────────────────────
    def _runner(self) -> PySimRunner | None:
        """Récupère un PySimRunner configuré comme MissionTab."""
        try:
            mission = self.master_app.tabs.get("MissionTab")
            if mission is None:
                messagebox.showerror("eUICC", "MissionTab introuvable.")
                return None
            pysim_path = (mission.pysim_var.get()
                          if hasattr(mission, "pysim_var") else "")
            reader_idx = (mission.reader_idx
                          if hasattr(mission, "reader_idx") else 0)
        except Exception as e:
            messagebox.showerror("eUICC",
                                 f"Impossible de récupérer la config "
                                 f"MissionTab : {e}")
            return None

        if not pysim_path or not os.path.isdir(pysim_path):
            messagebox.showerror("eUICC",
                                 "Chemin pySim non configuré dans MissionTab.")
            return None

        # Output dir
        out_dir = os.path.join(
            os.path.expanduser("~"), "ForenSIM_eUICC",
            datetime.now().strftime("%Y%m%d_%H%M%S"),
        )
        os.makedirs(out_dir, exist_ok=True)
        return PySimRunner(pysim_path, reader_idx, out_dir, self._ui_queue)

    def _identify_euicc(self) -> None:
        runner = self._runner()
        if runner is None:
            return
        self._output_buffer = ""
        self.log_tb.delete("1.0", "end")
        self._log("[*] Identification eUICC + EID…\n")
        threading.Thread(
            target=runner.run_script,
            args=(eh.script_get_eid(), "euicc_eid.log"),
            daemon=True,
        ).start()

    def _list_profiles(self) -> None:
        runner = self._runner()
        if runner is None:
            return
        self._log("[*] Listage des profils installés…\n")
        threading.Thread(
            target=runner.run_script,
            args=(eh.script_list_profiles(), "euicc_profiles.log"),
            daemon=True,
        ).start()

    def _dump_aram(self) -> None:
        runner = self._runner()
        if runner is None:
            return
        self._log("[*] Dump des règles ARA-M…\n")
        threading.Thread(
            target=runner.run_script,
            args=(eh.script_aram_rules(), "euicc_aram.log"),
            daemon=True,
        ).start()

    def _export_report(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=(f"euicc_report_{datetime.now():%Y%m%d_%H%M}.txt"),
            filetypes=[("Text", "*.txt")],
        )
        if not path:
            return
        report = eh.render_euicc_report(self._info, lang="FR")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(report)
            fh.write("\n\n--- RAW pySim-shell output ---\n")
            fh.write(self._output_buffer)
        messagebox.showinfo("eUICC", f"Rapport sauvegardé :\n{path}")

    def _reset(self) -> None:
        self._info = eh.EuiccInfo()
        self._output_buffer = ""
        self.eid_var.set("(non récupéré)")
        self.sgp_var.set("(?)")
        self.profiles_tb.delete("1.0", "end")
        self.log_tb.delete("1.0", "end")

    # ──────────────────────────────────────────────────────────────────
    # Live log polling
    # ──────────────────────────────────────────────────────────────────
    def _poll_queue(self) -> None:
        try:
            while True:
                line = self._ui_queue.get_nowait()
                if line == "===PROCESS_DONE===":
                    self._on_process_done()
                else:
                    self._log(line)
                    self._output_buffer += line
        except queue.Empty:
            pass
        # 100 ms cycle
        self.after(100, self._poll_queue)

    def _on_process_done(self) -> None:
        # Re-parse cumulative buffer
        eid = eh.parse_eid(self._output_buffer)
        if eid:
            self._info.eid = eid
            self.eid_var.set(eid)
        sgp = eh.detect_sgp_variant(self._output_buffer)
        if sgp != "?":
            self._info.sgp_variant = sgp
            self.sgp_var.set(eh.SGP_VARIANTS.get(sgp, sgp))
        profiles = eh.parse_profiles(self._output_buffer)
        if profiles:
            self._info.profiles = profiles
            self._refresh_profiles_view()
        self._log("\n[OK] Commande terminée.\n\n")

    def _refresh_profiles_view(self) -> None:
        self.profiles_tb.delete("1.0", "end")
        if not self._info.profiles:
            self.profiles_tb.insert("end", "(aucun profil parsé)")
            return
        for i, p in enumerate(self._info.profiles, 1):
            self.profiles_tb.insert(
                "end",
                f"#{i:>2}  ICCID={p.iccid:<22}  état={p.state:<10}  "
                f"classe={p.profile_class:<14}  MNO={p.mno_name or '—'}\n"
                f"     ISD-P AID = {p.isd_p_aid or '—'}\n",
            )

    def _log(self, text: str) -> None:
        self.log_tb.insert("end", text)
        self.log_tb.see("end")

    def update_lang(self, lang: str) -> None:
        # Hook for app.toggle_lang — minimal i18n for now
        pass

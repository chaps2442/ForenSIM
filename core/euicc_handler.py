"""eUICC / eSIM handler — wrapper léger autour de pySim-shell pour les
fonctionnalités GSMA SGP.22 (consumer eSIM) et SGP.32 (IoT eSIM).

Pertinence forensics véhicule :
  - **TCU connected car** (Tesla, BMW ConnectedDrive, Mercedes me, Stellantis
    SOTA) embarque souvent un eUICC ou un MFF2 (M2M / IoT eSIM).
  - SGP.02 (M2M legacy) → SGP.32 (IoT eSIM ratifié 2023+) est la transition
    en cours sur les véhicules connectés post-2023.
  - SGP.22 (consumer eSIM) couvre les téléphones et certains modules
    consumer-grade dans le véhicule (display SIM-tray Tesla Model S/X, par
    ex.).

L'extraction d'un eUICC livre :
  - **EID** (eUICC Identifier, 32 chars) — ID unique du chip
  - **Liste de profils** (ICCID, ISD-P AID, état enabled/disabled, MNO name)
  - **ARA-M rules** (Access Rules — applets autorisés)

Tout passe par `pySim-shell` upstream Osmocom. Ce handler ne réimplémente
pas les protocoles, il génère les scripts et parse la sortie.

Référence upstream :
  - https://gitea.osmocom.org/sim-card/pysim
  - https://downloads.osmocom.org/docs/pysim/master/html/library-esim.html
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# Identification SGP norm/version d'un eUICC depuis son ATR / capabilities
SGP_VARIANTS = {
    "consumer": "SGP.22 (Consumer eSIM, GSMA)",
    "m2m":      "SGP.02 (M2M legacy, en sortie)",
    "iot":      "SGP.32 (IoT eSIM, 2023+, recommandé véhicule)",
}


@dataclass
class EuiccProfile:
    """Représente un profil installé sur un eUICC."""
    iccid: str = ""
    isd_p_aid: str = ""
    state: str = "?"            # "enabled" | "disabled" | "deleted"
    profile_class: str = "?"    # "operational" | "test" | "provisioning"
    mno_name: str = ""
    profile_nickname: str = ""

    def to_dict(self) -> dict:
        return {
            "iccid": self.iccid,
            "isd_p_aid": self.isd_p_aid,
            "state": self.state,
            "class": self.profile_class,
            "mno_name": self.mno_name,
            "nickname": self.profile_nickname,
        }


@dataclass
class EuiccInfo:
    """Snapshot complet d'un eUICC."""
    eid: str = ""
    sgp_variant: str = "?"          # "consumer" | "m2m" | "iot"
    profiles: list[EuiccProfile] = field(default_factory=list)
    aram_rules: list[dict] = field(default_factory=list)
    raw_output: str = ""
    notes: str = ""


# ──────────────────────────────────────────────────────────────────
# Script generators (passés à PySimRunner.run_script())
# ──────────────────────────────────────────────────────────────────

def script_get_eid() -> str:
    """Script pySim-shell pour récupérer l'EID + ATR + tagged variant."""
    return (
        "# --- ForenSIM eUICC EID probe ---\n"
        "equip\n"             # info équipement
        "lchan 0\n"
        "select MF\n"
        "select ADF.ISD-R\n"  # ISD-R = Issuer Security Domain - Root (eUICC)
        "euicc get_euicc_configured_addresses\n"
        "euicc get_eid\n"
        "euicc get_euicc_challenge\n"
    )


def script_list_profiles() -> str:
    """Liste tous les profils installés (operational + test + provisioning)."""
    return (
        "# --- ForenSIM eUICC profile listing ---\n"
        "lchan 0\n"
        "select MF\n"
        "select ADF.ISD-R\n"
        "euicc get_profiles_info\n"
        "euicc list_notification\n"
    )


def script_aram_rules() -> str:
    """Liste les règles d'accès ARA-M (Access Rule Application Master).

    Ces règles déterminent quels applets peuvent être activés et par
    qui (signature, hash de l'app, etc.). Sur un eUICC OEM custom
    (Mercedes / BMW), l'ARA-M peut révéler des applets propriétaires.
    """
    return (
        "# --- ForenSIM ARA-M rule dump ---\n"
        "lchan 0\n"
        "select MF\n"
        "select ADF.ARA-M\n"
        "select EF.ARA-M\n"
        "read_binary_decoded\n"
        "aram_get_all\n"  # commande spécifique pySim
    )


def script_profile_metadata(iccid: str) -> str:
    """Récupère les métadonnées étendues d'un profil par son ICCID."""
    safe_iccid = re.sub(r"[^0-9a-fA-F]", "", iccid)[:20]
    return (
        f"# --- ForenSIM profile metadata for ICCID {safe_iccid} ---\n"
        "lchan 0\n"
        "select MF\n"
        "select ADF.ISD-R\n"
        f"euicc get_profile_metadata --iccid {safe_iccid}\n"
    )


def script_enable_profile(iccid: str) -> str:
    """ATTENTION — change l'état du profil sur la carte.

    À utiliser UNIQUEMENT en mode bench-test ou avec autorisation OPJ
    explicite (la modification d'état est une intervention destructive
    sur la pièce de preuve).
    """
    safe = re.sub(r"[^0-9a-fA-F]", "", iccid)[:20]
    return (
        f"# --- ForenSIM ENABLE profile {safe} (RISKY) ---\n"
        "lchan 0\n"
        "select MF\n"
        "select ADF.ISD-R\n"
        f"euicc enable_profile --iccid {safe} --refresh-flag 1\n"
    )


def script_disable_profile(iccid: str) -> str:
    """ATTENTION — change l'état du profil sur la carte. Voir enable."""
    safe = re.sub(r"[^0-9a-fA-F]", "", iccid)[:20]
    return (
        f"# --- ForenSIM DISABLE profile {safe} (RISKY) ---\n"
        "lchan 0\n"
        "select MF\n"
        "select ADF.ISD-R\n"
        f"euicc disable_profile --iccid {safe}\n"
    )


# ──────────────────────────────────────────────────────────────────
# Parsers — décodent la sortie textuelle de pySim-shell
# ──────────────────────────────────────────────────────────────────

EID_RE = re.compile(r"EID[:\s]+([0-9A-Fa-f]{32})", re.IGNORECASE)
ICCID_RE = re.compile(r"ICCID[:\s]+([0-9A-Fa-f]{14,20})", re.IGNORECASE)
AID_RE = re.compile(r"ISD-?P[_\s-]+AID[:\s]+([0-9A-Fa-f]{20,32})",
                    re.IGNORECASE)
STATE_RE = re.compile(r"profile[_\s-]+state[:\s]+(enabled|disabled|deleted)",
                      re.IGNORECASE)
CLASS_RE = re.compile(r"profile[_\s-]+class[:\s]+(\w+)", re.IGNORECASE)
MNO_RE = re.compile(r"(?:service[_\s-]?provider|mno|operator)[_\s-]?name[:\s]+([^\n]+)",
                    re.IGNORECASE)


def parse_eid(output: str) -> str:
    m = EID_RE.search(output)
    return m.group(1).upper() if m else ""


def parse_profiles(output: str) -> list[EuiccProfile]:
    """Découpe la sortie par 'profile_metadata' / 'ProfileInfo' blocks."""
    blocks = re.split(r"\n(?=ProfileInfo|profile_metadata|---)", output)
    out = []
    for blk in blocks:
        iccid = ICCID_RE.search(blk)
        if not iccid:
            continue
        p = EuiccProfile(iccid=iccid.group(1).upper())
        if (m := AID_RE.search(blk)):
            p.isd_p_aid = m.group(1).upper()
        if (m := STATE_RE.search(blk)):
            p.state = m.group(1).lower()
        if (m := CLASS_RE.search(blk)):
            p.profile_class = m.group(1).lower()
        if (m := MNO_RE.search(blk)):
            p.mno_name = m.group(1).strip()
        out.append(p)
    return out


def detect_sgp_variant(output: str, atr_hex: str = "") -> str:
    """Heuristique : détecte si on parle à du SGP.02 / SGP.22 / SGP.32.

    Indices :
      - SGP.32 IoT : presence "IoT Profile Package" / "eIM" / SGP.32 dans output
      - SGP.22 consumer : "ISD-R" + Consumer profile class
      - SGP.02 M2M : MFF2 form factor, "DPF" historique
    """
    out_l = output.lower()
    if "sgp.32" in out_l or "ipa " in out_l or "eim" in out_l:
        return "iot"
    if "sgp.22" in out_l or "consumer profile" in out_l:
        return "consumer"
    if "sgp.02" in out_l or "mff2" in out_l or "dpf" in out_l:
        return "m2m"
    # Fallback : si on a au moins ISD-R, c'est forcément consumer ou IoT
    if "isd-r" in out_l or "isd_r" in out_l:
        return "consumer"
    return "?"


def render_euicc_report(info: EuiccInfo, lang: str = "FR") -> str:
    """Rapport texte forensic — à intégrer dans le .txt de session."""
    fr = lang.upper().startswith("FR")
    h = ("=" * 70)
    title = "RAPPORT eUICC / eSIM" if fr else "eUICC / eSIM REPORT"
    sgp_label = SGP_VARIANTS.get(info.sgp_variant,
                                 f"Inconnue ({info.sgp_variant})")

    lines = [
        h,
        f"  {title}",
        h,
        "",
        f"  EID            : {info.eid or '(non récupéré)'}",
        f"  Norme GSMA     : {sgp_label}",
        f"  Profils trouvés: {len(info.profiles)}",
        "",
    ]
    for i, p in enumerate(info.profiles, 1):
        lines.append(f"  --- Profil #{i} ---")
        lines.append(f"    ICCID       : {p.iccid}")
        lines.append(f"    ISD-P AID   : {p.isd_p_aid or '—'}")
        lines.append(f"    État        : {p.state}")
        lines.append(f"    Classe      : {p.profile_class}")
        if p.mno_name:
            lines.append(f"    Opérateur   : {p.mno_name}")
        if p.profile_nickname:
            lines.append(f"    Nickname    : {p.profile_nickname}")
        lines.append("")

    if info.aram_rules:
        lines.append("  --- ARA-M rules ---")
        for r in info.aram_rules:
            lines.append(f"    • {r}")
        lines.append("")

    if info.notes:
        lines.append("  Notes :")
        lines.append(f"    {info.notes}")
        lines.append("")

    if info.sgp_variant == "iot":
        sentence = ("  ⚠ SGP.32 (IoT eSIM) — typique d'un TCU connected car post-2023. "
                    "Les profils peuvent inclure des credentials opérateur "
                    "machine-to-machine non visibles côté GUI véhicule.")
        lines.append(sentence)
        lines.append("")

    lines.append(h)
    return "\n".join(lines)

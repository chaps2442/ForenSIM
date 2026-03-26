import re
import os
import csv
import webbrowser
from tkinter import messagebox

LANG_FR = {
    "err_csv_title": "Avertissement : CSV Manquant",
    "err_csv_msg": "Le fichier '{csv_name}' est introuvable dans le dossier pySim.\n\nVoulez-vous ouvrir le lien pour le télécharger ?"
}

def decode_iccid(iccid: str) -> dict:
    if not iccid or len(iccid) < 18:
        return {"error": "Invalid ICCID length"}
    
    # Check if we need to swap digits (e.g. from raw hex dump)
    if 'f' in iccid.lower() or iccid[1] == '8':  # usually 89, swapped is 98
        swapped = "".join([iccid[i+1] + iccid[i] for i in range(0, len(iccid)-1, 2)])
        iccid = swapped[:-1] if swapped.lower().endswith('f') else swapped
        
    cc_map = {
        "1": "USA / Canada", "20": "Egypte", "27": "Afsud", "30": "Grece", "31": "Pays-Bas", 
        "32": "Belgique", "33": "France", "34": "Espagne", "39": "Italie", "40": "Roumanie",
        "41": "Suisse", "43": "Autriche", "44": "Royaume-Uni", "45": "Danemark", "46": "Suede",
        "47": "Norvege", "48": "Pologne", "49": "Allemagne", "51": "Perou", "52": "Mexique",
        "54": "Argentine", "55": "Bresil", "61": "Australie", "64": "N-Zelande", "81": "Japon", 
        "82": "Coree-Sud", "86": "Chine", "90": "Turquie", "91": "Inde", "92": "Pakistan",
        "212": "Maroc", "213": "Algerie", "216": "Tunisie", "225": "Cote d'Ivoire",
        "351": "Portugal", "353": "Irlande", "358": "Finlande", "971": "UAE", "972": "Israel"
    }
    
    rest = iccid[2:]
    for length in [3, 2, 1]:
        prefix = rest[:length]
        if prefix in cc_map:
            return {
                "format": "ICCID",
                "clean": iccid,
                "country": cc_map[prefix],
                "iin": rest[length:min(length+4, len(rest))]
            }
    return {"format": "ICCID", "clean": iccid, "country": "Unknown", "iin": "Unknown"}

def decode_imsi(imsi: str, pysim_path: str = None) -> dict:
    if not imsi or len(imsi) < 14:
        return {"error": "Invalid IMSI"}
        
    # Check swap
    if len(imsi) > 15 and not imsi.isdigit():
        imsi_hex = imsi[2:]
        swapped = "".join([imsi_hex[i+1] + imsi_hex[i] for i in range(0, len(imsi_hex)-1, 2)])
        imsi = swapped[1:]

    mcc = imsi[:3]
    mnc = imsi[3:5]
    mnc3 = imsi[3:6]
    
    # Try looking up in csv
    op, loc = "Unknown", f"MCC: {mcc}"
    if pysim_path:
        csv_mcc = os.path.join(pysim_path, "mcc-mnc.csv")
        if not os.path.exists(csv_mcc):
            loc += " (mcc-mnc.csv missing)"
        else:
            try:
                with open(csv_mcc, 'r', encoding='utf-8-sig', errors='ignore') as f:
                    for row in csv.DictReader(f, delimiter=';'):
                        # Normalize keys
                        row_clean = {k.strip().lower(): v for k, v in row.items() if k}
                        r_mcc = str(row_clean.get('mcc', '')).strip()
                        r_mnc = str(row_clean.get('mnc', '')).strip()
                        
                        if r_mcc == mcc and r_mnc in [mnc, mnc3]:
                            op = row_clean.get('operator') or row_clean.get('network') or "Unknown"
                            country = row_clean.get('country') or "Unknown"
                            loc = f"{country} (MCC: {mcc})"
                            break
            except Exception:
                pass
                
    return {
        "format": "IMSI",
        "clean": imsi,
        "mcc": mcc,
        "mnc": mnc,
        "operator": op,
        "location": loc
    }

def decode_imei(imei: str, pysim_path: str = None) -> dict:
    if len(imei) != 15 or not imei.isdigit():
        return {"error": "Invalid IMEI"}
    
    tac = imei[:8]
    snr = imei[8:14]
    model = "Unknown (TAC non listé)"
    
    if pysim_path:
        tac_csv = os.path.join(pysim_path, "tac.csv")
        if not os.path.exists(tac_csv):
            model = "❓ Fichier tac.csv introuvable"
        else:
            try:
                with open(tac_csv, mode='r', encoding='utf-8-sig', errors='ignore') as file:
                    for row in csv.reader(file):
                        if len(row) >= 2 and row[0].strip() == tac:
                            brand = row[2].strip() if len(row) >= 3 else row[1].strip()
                            mod = row[1].strip() if len(row) >= 3 else ""
                            model = f"{brand} {mod}".strip()
                            break
            except Exception:
                pass

    return {
        "format": "IMEI",
        "clean": imei,
        "tac": tac,
        "snr": snr,
        "luhn": imei[14],
        "model": model
    }

def decode_mac(mac: str, pysim_path: str = None) -> dict:
    # 12 hex chars
    if len(mac) == 12:
        oui = mac[:6]
        nic = mac[6:]
        formatted_mac = f"{oui[:2]}:{oui[2:4]}:{oui[4:]}:{nic[:2]}:{nic[2:4]}:{nic[4:]}"
        
        vendor = "Inconnu"
        if pysim_path:
            oui_csv = os.path.join(pysim_path, "oui.csv")
            if not os.path.exists(oui_csv):
                vendor = "❗ Fichier oui.csv introuvable"
            else:
                try:
                    with open(oui_csv, mode='r', encoding='utf-8-sig', errors='ignore') as file:
                        for row in csv.reader(file):
                            if len(row) >= 3 and row[1].strip().upper() == oui:
                                vendor = row[2].strip()
                                break
                except Exception:
                    pass
        return {
            "format": "MAC",
            "clean": formatted_mac,
            "oui": oui,
            "nic": nic,
            "vendor": vendor
        }
    return {"error": "Invalid MAC"}

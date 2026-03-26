import re

HAS_SMARTCARD = False
try:
    from smartcard.System import readers
    import smartcard.System
    import smartcard.util
    toHexString = smartcard.util.toHexString
    HAS_SMARTCARD = True
except ImportError:
    pass

def get_readers():
    if not HAS_SMARTCARD:
        return ["Error: pyscard module not installed!"]
    try:
        r = smartcard.System.readers()
        return [str(reader) for reader in r]
    except Exception as e:
        return [f"Error reading: {str(e)}"]

def analyze_atr(atr_bytes):
    if not HAS_SMARTCARD:
        return "Empty ATR"
    if not atr_bytes:
        return "Empty ATR"

    atr_hex = toHexString(atr_bytes)
    info = [f"ATR: {atr_hex}"]

    # Historical bytes extraction (similar to strings)
    ascii_hist = "".join([chr(b) if 32 <= b <= 126 else "." for b in atr_bytes])
    clean_strings = re.findall(r'[A-Za-z0-9 _\-!]{3,}', ascii_hist)
    
    if clean_strings:
        info.append(f"ASCII Hints: {' | '.join(clean_strings)}")
        
    return "\n".join(info)

def auto_security_check(reader_index=0):
    if not HAS_SMARTCARD: return "Pyscard not installed"
    try:
        r = smartcard.System.readers()
        if not r or int(reader_index) >= len(r):
            return "No reader found."
        reader_obj = r[int(reader_index)]
        conn = reader_obj.createConnection()
        conn.connect()
        try:
            # Telecom MF
            conn.transmit([0x00, 0xA4, 0x00, 0x04, 0x02, 0x3F, 0x00]) 
            # GSM DF
            conn.transmit([0x00, 0xA4, 0x00, 0x04, 0x02, 0x7F, 0x20]) 
            # EF.LOCI
            conn.transmit([0x00, 0xA4, 0x00, 0x04, 0x02, 0x6F, 0x7E]) 
            _, sw1_read, sw2_read = conn.transmit([0x00, 0xB0, 0x00, 0x00, 0x01])

            if sw1_read in [0x6E, 0x6D, 0x68]: 
                conn.transmit([0xA0, 0xA4, 0x00, 0x00, 0x02, 0x3F, 0x00])
                conn.transmit([0xA0, 0xA4, 0x00, 0x00, 0x02, 0x7F, 0x20])
                conn.transmit([0xA0, 0xA4, 0x00, 0x00, 0x02, 0x6F, 0x7E])
                _, sw1_read, sw2_read = conn.transmit([0xA0, 0xB0, 0x00, 0x00, 0x01])

            is_locked = False
            if sw1_read in [0x90, 0x91]: return "DÉVERROUILLÉ / UNLOCKED"
            elif sw1_read == 0x69 and sw2_read == 0x82: is_locked = True
            elif sw1_read == 0x98 and sw2_read == 0x04: is_locked = True
            else: is_locked = True

            if is_locked:
                _, sw1, sw2 = conn.transmit([0x00, 0x20, 0x00, 0x01, 0x00])
                if sw1 in [0x6E, 0x6D]: _, sw1, sw2 = conn.transmit([0xA0, 0x20, 0x00, 0x01, 0x00])
                    
                if sw1 == 0x63: return f"VERROUILLÉ / LOCKED ({sw2 & 0x0F} tries left)"
                elif sw1 == 0x69 and sw2 == 0x83: return "BLOQUÉ / BLOCKED (PUK Required)"
                elif sw1 == 0x98 and sw2 == 0x40: return "BLOQUÉ / BLOCKED (2G Norm)"
                elif sw1 == 0x67 and sw2 == 0x00: return "VERROUILLÉ / LOCKED (Old GSM)"
                else: return f"LOCKED (Unknown: {hex(sw1)} {hex(sw2)})"

        except Exception as e_apdu: return f"APDU Error ({str(e_apdu)})"
        finally: conn.disconnect()
    except Exception: return "Connection Error"

def pad_pin(pin_str):
    if not pin_str.isdigit() or len(pin_str) > 8: return None
    pin_bytes = [ord(c) for c in pin_str]
    while len(pin_bytes) < 8: pin_bytes.append(0xFF)
    return pin_bytes

def test_pin(reader_index, pin_str):
    if not HAS_SMARTCARD: return "Pyscard not installed", "orange"
    pin_bytes = pad_pin(pin_str)
    if not pin_bytes: return "Invalid Format", "orange"
    
    try:
        r = smartcard.System.readers()
        if not r or int(reader_index) >= len(r):
            return "No reader found.", "orange"
        reader_obj = r[int(reader_index)]
        conn = reader_obj.createConnection()
        conn.connect()
        try:
            apdu = [0x00, 0x20, 0x00, 0x01, 0x08] + pin_bytes
            _, sw1, sw2 = conn.transmit(apdu)
            if sw1 in [0x6E, 0x6D]: 
                apdu[0] = 0xA0
                _, sw1, sw2 = conn.transmit(apdu)

            if sw1 == 0x90:
                return "✅ DÉVERROUILLÉ / UNLOCKED", "green"
            elif sw1 == 0x63:
                return f"❌ WRONG PIN ({sw2 & 0x0F} tries left)", "red"
            elif sw1 == 0x69 and sw2 == 0x83:
                return "❌ BLOQUÉ / BLOCKED", "red"
            elif sw1 == 0x98 and sw2 == 0x40:
                return "❌ BLOCKED (0 tries - 2G)", "red"
            else:
                return f"Error ({hex(sw1)} {hex(sw2)})", "orange"
        finally:
            conn.disconnect()
    except Exception as e:
        return f"Conn Error: {str(e)}", "orange"

def unblock_pin(reader_index, puk_str, new_pin_str):
    if not HAS_SMARTCARD: return "Pyscard not installed", "orange"
    puk_bytes = pad_pin(puk_str)
    new_pin_bytes = pad_pin(new_pin_str)
    if not puk_bytes or not new_pin_bytes: return "Invalid Format", "orange"
    
    try:
        r = smartcard.System.readers()
        if not r or int(reader_index) >= len(r):
            return "No reader found.", "orange"
        reader_obj = r[int(reader_index)]
        conn = reader_obj.createConnection()
        conn.connect()
        try:
            # UNBLOCK CHV (0x2C)
            apdu = [0x00, 0x2C, 0x00, 0x01, 0x10] + puk_bytes + new_pin_bytes
            _, sw1, sw2 = conn.transmit(apdu)
            if sw1 in [0x6E, 0x6D]: 
                apdu[0] = 0xA0
                _, sw1, sw2 = conn.transmit(apdu)

            if sw1 == 0x90: return "✅ PUK ACCEPTÉ / PIN RESET", "green"
            elif sw1 == 0x63: return f"❌ WRONG PUK ({sw2 & 0x0F} tries left)", "red"
            elif sw1 == 0x69 and sw2 == 0x83: return "❌ CARTE DÉFINITIVEMENT BLOQUÉE", "red"
            else: return f"Error ({hex(sw1)} {hex(sw2)})", "orange"
        finally:
            conn.disconnect()
    except Exception as e: return f"Conn Error: {str(e)}", "orange"

def change_pin(reader_index, old_pin_str, new_pin_str):
    if not HAS_SMARTCARD: return "Pyscard not installed", "orange"
    old_pin_bytes = pad_pin(old_pin_str)
    new_pin_bytes = pad_pin(new_pin_str)
    if not old_pin_bytes or not new_pin_bytes: return "Invalid Format", "orange"
    
    try:
        r = smartcard.System.readers()
        if not r or int(reader_index) >= len(r):
            return "No reader found.", "orange"
        reader_obj = r[int(reader_index)]
        conn = reader_obj.createConnection()
        conn.connect()
        try:
            # CHANGE CHV (0x24)
            apdu = [0x00, 0x24, 0x00, 0x01, 0x10] + old_pin_bytes + new_pin_bytes
            _, sw1, sw2 = conn.transmit(apdu)
            if sw1 in [0x6E, 0x6D]: 
                apdu[0] = 0xA0
                _, sw1, sw2 = conn.transmit(apdu)

            if sw1 == 0x90: return "✅ PIN MODIFIÉ", "green"
            elif sw1 == 0x63: return f"❌ WRONG PIN ({sw2 & 0x0F} tries left)", "red"
            else: return f"Error ({hex(sw1)} {hex(sw2)})", "orange"
        finally:
            conn.disconnect()
    except Exception as e: return f"Conn Error: {str(e)}", "orange"

def toggle_pin(reader_index, pin_str, enable=True):
    if not HAS_SMARTCARD: return "Pyscard not installed", "orange"
    pin_bytes = pad_pin(pin_str)
    if not pin_bytes: return "Invalid Format", "orange"
    
    try:
        r = smartcard.System.readers()
        if not r or int(reader_index) >= len(r):
            return "No reader found.", "orange"
        reader_obj = r[int(reader_index)]
        conn = reader_obj.createConnection()
        conn.connect()
        try:
            # 0x28 = Enable CHV, 0x26 = Disable CHV
            ins = 0x28 if enable else 0x26
            apdu = [0x00, ins, 0x00, 0x01, 0x08] + pin_bytes
            _, sw1, sw2 = conn.transmit(apdu)
            if sw1 in [0x6E, 0x6D]: 
                apdu[0] = 0xA0
                _, sw1, sw2 = conn.transmit(apdu)

            if sw1 == 0x90: return f"✅ PIN {'ACTIVÉ' if enable else 'DÉSACTIVÉ'}", "green"
            elif sw1 == 0x63: return f"❌ WRONG PIN ({sw2 & 0x0F} tries left)", "red"
            elif sw1 == 0x98 and sw2 == 0x08: return "❌ INCOMPATIBLE (Déjà dans cet état)", "orange"
            elif sw1 == 0x94 and sw2 == 0x04: return "❌ PIN Déjà dans cet état", "orange"
            else: return f"Error ({hex(sw1)} {hex(sw2)})", "orange"
        finally:
            conn.disconnect()
    except Exception as e: return f"Conn Error: {str(e)}", "orange"

def check_is_usim(reader_index=0):
    try:
        r = smartcard.System.readers()
        if not r or int(reader_index) >= len(r):
            return False
        conn = r[int(reader_index)].createConnection()
        conn.connect()
        # Try to select USIM AID: A0 00 00 00 87 10 02
        usim_aid = [0x00, 0xA4, 0x04, 0x04, 0x07, 0xA0, 0x00, 0x00, 0x00, 0x87, 0x10, 0x02]
        _, sw1, sw2 = conn.transmit(usim_aid)
        conn.disconnect()
        return (sw1 == 0x90 or sw1 == 0x61)
    except Exception:
        return False

def scan_generic_card():
    if not HAS_SMARTCARD:
        return "Error: pyscard module not installed! Please run with the correct Python environment."
    try:
        r = smartcard.System.readers()
        if not r:
            return "No reader found."
        
        all_results = []
        for i, reader in enumerate(r, start=1):
            results = [f"--- Lecteur {i} : {reader} ---"]
            try:
                conn = reader.createConnection()
                conn.connect()
                
                atr = conn.getATR()
                atr_analysis = analyze_atr(atr)
                results.append(atr_analysis)
                
                # 1. Try to select Telecom MF (SIM)
                try:
                    _, sw1, sw2 = conn.transmit([0x00, 0xA4, 0x00, 0x04, 0x02, 0x3F, 0x00])
                    if sw1 in [0x90, 0x61, 0x9F] or sw1 == 0x6E:
                        results.append("-> Identified as Telecom SIM/USIM Profile.")
                except: pass
                    
                # 2. Try to select PPSE (Payment System Environment - EMV Bank Card)
                try:
                    ppse_apdu = [0x00, 0xA4, 0x04, 0x00, 0x0E, 0x32, 0x50, 0x41, 0x59, 0x2E, 0x53, 0x59, 0x53, 0x2E, 0x44, 0x44, 0x46, 0x30, 0x31, 0x00]
                    _, sw1, sw2 = conn.transmit(ppse_apdu)
                    if sw1 == 0x90 or sw1 == 0x61:
                        results.append("-> Identified as EMV Bank/Payment Card (PPSE Found).")
                except: pass
                    
                # 3. Try to select Calypso (Transport Cards)
                try:
                    calypso_apdu = [0x00, 0xA4, 0x04, 0x00, 0x08, 0x31, 0x54, 0x49, 0x43, 0x2E, 0x49, 0x43, 0x41, 0x00]
                    _, sw1, sw2 = conn.transmit(calypso_apdu)
                    if sw1 == 0x90 or sw1 == 0x61:
                        results.append("-> Identified as Calypso Transport Card (Metro/Bus).")
                except: pass

                conn.disconnect()
            except Exception as e:
                if "No smart card inserted" in str(e):
                    results.append("No card inserted.")
                else:
                    results.append(f"Error testing card: {str(e)}")
            
            all_results.append("\n".join(results) + "\n")
            
        return "\n".join(all_results)
    except Exception as e:
        return f"Error during scanning: {str(e)}"

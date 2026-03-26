import os
from fpdf import FPDF
import datetime

class ForensimPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 15)
        # Assuming we might want a logo here
        self.cell(0, 10, "ForenSIM V2 - Forensic Extraction Report", border=0, align="C")
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def generate_pdf_report(out_path, data: dict):
    pdf = ForensimPDF()
    pdf.add_page()
    
    # Metadata
    pdf.set_font("Helvetica", size=12)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf.cell(0, 10, f"Date of Extraction: {ts}", ln=True)
    pdf.cell(0, 10, f"SIM Card Type: {data.get('type', 'Unknown')}", ln=True)
    pdf.cell(0, 10, "-"*50, ln=True)
    
    # Identification
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "1. Identity & Network", ln=True)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, f"ICCID: {data.get('iccid', 'N/A')}", ln=True)
    pdf.cell(0, 10, f"IMSI: {data.get('imsi', 'N/A')}", ln=True)
    pdf.cell(0, 10, f"MSISDN: {data.get('msisdn', 'Unknown')}", ln=True)
    pdf.cell(0, 10, "-"*50, ln=True)
    
    # Security
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "2. Security Status", ln=True)
    pdf.set_font("Helvetica", size=12)
    sec_info = data.get('sec_status', 'Unknown')
    pdf.cell(0, 10, f"Dernier Statut (Extraction): {sec_info}", ln=True)
    pdf.cell(0, 10, "-"*50, ln=True)
    
    # OSINT
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "3. Network Evidence Decoding", ln=True)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, f"Country (MCC): {data.get('mcc', 'Unknown')}", ln=True)
    pdf.cell(0, 10, f"Network (MNC): {data.get('mnc', 'Unknown')}", ln=True)
    pdf.cell(0, 10, f"Last Connect LOCI (TMSI/LAC): {data.get('loci', 'Unknown')}", ln=True)
    pdf.cell(0, 10, f"Forbidden Networks (FPLMN): {data.get('fplmn', 'None')}", ln=True)
    pdf.cell(0, 10, "-"*50, ln=True)

    # Human Data Counters
    counters = data.get("counters", {})
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "4. Extracted Human Data (Counters)", ln=True)
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, f"SMS Found: {counters.get('sms', 0)}", ln=True)
    pdf.cell(0, 10, f"Contacts Found: {counters.get('contacts', 0)}", ln=True)
    pdf.cell(0, 10, f"Call Logs Found: {counters.get('calls', 0)}", ln=True)
    pdf.cell(0, 10, "-"*50, ln=True)
    
    # File save
    pdf.output(out_path)
    return out_path

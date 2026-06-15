import re
import os
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple

class DocumentParser:
    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        Extract raw text from a PDF file.
        Primary: pdfplumber. Fallback: PyMuPDF (fitz).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")

        text = ""
        # 1. Primary extraction with pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                page_texts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        page_texts.append(page_text)
                text = "\n".join(page_texts).strip()
        except Exception as e:
            # We fail silently to trigger the fallback
            pass

        # 2. Fallback to PyMuPDF (fitz)
        if not text:
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                page_texts = []
                for page in doc:
                    page_text = page.get_text()
                    if page_text:
                        page_texts.append(page_text)
                text = "\n".join(page_texts).strip()
            except Exception as e:
                raise RuntimeError(f"Text extraction failed using both pdfplumber and PyMuPDF fallback: {str(e)}")

        if not text:
            raise ValueError("Extracted text is empty. The PDF may be scanned (image-only) or secured.")

        return text

    @classmethod
    def parse_contract(cls, text: str) -> Tuple[Dict[str, Any], Dict[str, float], List[str]]:
        """
        Extract contract fields: vendor_name, contract_number, contract_amount, start_date, end_date.
        Returns: (fields, confidence_scores, warnings)
        """
        fields = {
            "vendor_name": "",
            "contract_number": "",
            "contract_amount": None,
            "start_date": None,
            "end_date": None
        }
        confidence = {
            "vendor_name": 0.0,
            "contract_number": 0.0,
            "contract_amount": 0.0,
            "start_date": 0.0,
            "end_date": 0.0
        }
        warnings = []

        # --- 1. Vendor Name ---
        # Look for explicit label "Vendor: Acme Corp"
        vendor_match = re.search(r'(?i)(?:vendor|supplier|contractor|seller|party\s*b)\s*(?:name)?\s*[:\-]\s*([^\n]+)', text)
        if vendor_match:
            val = vendor_match.group(1).strip()
            fields["vendor_name"] = cls._clean_text(val)
            confidence["vendor_name"] = 0.9
        else:
            # Proximity/Corporate name fallback: look for LLC, Corp, Inc, Ltd, Company
            corp_match = re.search(r'\b([A-Za-z0-9\s,&]+(?:LLC|Corp|Inc|Ltd|Company|Corporation))\b', text)
            if corp_match:
                fields["vendor_name"] = cls._clean_text(corp_match.group(1))
                confidence["vendor_name"] = 0.5
                warnings.append("Vendor name extracted using corporate suffix fallback.")
            else:
                # Use first line or placeholder
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if lines:
                    fields["vendor_name"] = lines[0][:50]
                    confidence["vendor_name"] = 0.3
                    warnings.append("Could not find explicit vendor name; fell back to document header.")
                else:
                    warnings.append("Vendor name not found.")

        # --- 2. Contract Number ---
        # Explicit search
        no_match = re.search(r'(?i)(?:contract\s*(?:number|no|ref|reference|id)?|agreement\s*(?:number|no)?)\s*[:\-]\s*([a-zA-Z0-9\-#/\s]+)', text)
        if no_match:
            fields["contract_number"] = cls._clean_text(no_match.group(1))
            confidence["contract_number"] = 0.9
        else:
            # Generic CTR search
            ctr_match = re.search(r'\b(CTR-?[0-9\-#/\s]+)\b', text)
            if ctr_match:
                fields["contract_number"] = cls._clean_text(ctr_match.group(1))
                confidence["contract_number"] = 0.6
                warnings.append("Contract number matched via generic prefix fallback.")
            else:
                warnings.append("Contract number not found.")

        # --- 3. Contract Amount ---
        amount_match = re.search(r'(?i)(?:contract\s*(?:amount|value|limit)|total\s*amount|value|amount|limit|consideration)\s*(?:of)?\s*(?:\$\s*)?([0-9,]+(?:\.[0-9]{2})?)', text)
        if amount_match:
            parsed_amt = cls._parse_amount(amount_match.group(1))
            if parsed_amt is not None:
                fields["contract_amount"] = parsed_amt
                confidence["contract_amount"] = 0.9
            else:
                warnings.append("Failed to parse matched contract amount string.")
        else:
            # Fallback to the first dollar amount
            dollar_match = re.search(r'\$\s*([0-9,]+(?:\.[0-9]{2})?)', text)
            if dollar_match:
                parsed_amt = cls._parse_amount(dollar_match.group(1))
                if parsed_amt is not None:
                    fields["contract_amount"] = parsed_amt
                    confidence["contract_amount"] = 0.4
                    warnings.append("Contract amount extracted from first dollar value found in text.")
            else:
                warnings.append("Contract amount not found.")

        # --- 4. Start Date ---
        start_match = re.search(r'(?i)(?:start|effective|commencement|commencing)\s*(?:date)?\s*[:\-]?\s*([^\n]+)', text)
        if start_match:
            dt_str = cls._parse_date(start_match.group(1))
            if dt_str:
                fields["start_date"] = dt_str
                confidence["start_date"] = 0.9
            else:
                warnings.append("Failed to parse matched start date format.")
        else:
            warnings.append("Start date not found.")

        # --- 5. End Date ---
        end_match = re.search(r'(?i)(?:end|expiration|expiry|termination|expires)\s*(?:date)?\s*[:\-]?\s*([^\n]+)', text)
        if end_match:
            dt_str = cls._parse_date(end_match.group(1))
            if dt_str:
                fields["end_date"] = dt_str
                confidence["end_date"] = 0.9
            else:
                warnings.append("Failed to parse matched end date format.")
        else:
            # Proximity fallback: search for second date found in the document
            dates_found = cls._find_all_dates(text)
            if len(dates_found) >= 2 and fields["start_date"]:
                # Pick the second date if it is after the start date
                candidate = dates_found[1]
                if candidate > fields["start_date"]:
                    fields["end_date"] = candidate
                    confidence["end_date"] = 0.5
                    warnings.append("End date fell back to the secondary date detected in document text.")
            else:
                warnings.append("End date not found.")

        return fields, confidence, warnings

    @classmethod
    def parse_invoice(cls, text: str) -> Tuple[Dict[str, Any], Dict[str, float], List[str]]:
        """
        Extract invoice fields: vendor_name, invoice_number, invoice_date, invoice_amount.
        Returns: (fields, confidence_scores, warnings)
        """
        fields = {
            "vendor_name": "",
            "invoice_number": "",
            "invoice_date": None,
            "invoice_amount": None
        }
        confidence = {
            "vendor_name": 0.0,
            "invoice_number": 0.0,
            "invoice_date": 0.0,
            "invoice_amount": 0.0
        }
        warnings = []

        # --- 1. Vendor Name ---
        vendor_match = re.search(r'(?i)(?:vendor|supplier|issuer|biller|from)\s*(?:name)?\s*[:\-]\s*([^\n]+)', text)
        if vendor_match:
            val = vendor_match.group(1).strip()
            fields["vendor_name"] = cls._clean_text(val)
            confidence["vendor_name"] = 0.9
        else:
            # Corporate suffix fallback
            corp_match = re.search(r'\b([A-Za-z0-9\s,&]+(?:LLC|Corp|Inc|Ltd|Company|Corporation))\b', text)
            if corp_match:
                fields["vendor_name"] = cls._clean_text(corp_match.group(1))
                confidence["vendor_name"] = 0.5
                warnings.append("Vendor name matched via corporate suffix fallback.")
            else:
                # Use first line
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if lines:
                    fields["vendor_name"] = lines[0][:50]
                    confidence["vendor_name"] = 0.3
                    warnings.append("Could not find explicit vendor name; fell back to header.")
                else:
                    warnings.append("Vendor name not found.")

        # --- 2. Invoice Number ---
        no_match = re.search(r'(?i)(?:invoice\s*(?:number|no|ref|reference|id)?|inv\s*(?:number|no|id)?)\s*[:\-]\s*([a-zA-Z0-9\-#/\s]+)', text)
        if no_match:
            fields["invoice_number"] = cls._clean_text(no_match.group(1))
            confidence["invoice_number"] = 0.9
        else:
            # Generic INV search
            inv_match = re.search(r'\b(INV-?[0-9\-#/\s]+)\b', text)
            if inv_match:
                fields["invoice_number"] = cls._clean_text(inv_match.group(1))
                confidence["invoice_number"] = 0.6
                warnings.append("Invoice number matched via generic prefix fallback.")
            else:
                warnings.append("Invoice number not found.")

        # --- 3. Invoice Date ---
        date_match = re.search(r'(?i)(?:invoice|billing|date|issue)\s*(?:date)?\s*[:\-]?\s*([^\n]+)', text)
        if date_match:
            dt_str = cls._parse_date(date_match.group(1))
            if dt_str:
                fields["invoice_date"] = dt_str
                confidence["invoice_date"] = 0.9
            else:
                warnings.append("Failed to parse matched invoice date.")
        else:
            # Generic date match: first date found in document
            dates = cls._find_all_dates(text)
            if dates:
                fields["invoice_date"] = dates[0]
                confidence["invoice_date"] = 0.5
                warnings.append("Invoice date fell back to the first date detected in text.")
            else:
                warnings.append("Invoice date not found.")

        # --- 4. Invoice Amount ---
        amount_match = re.search(r'(?i)(?:total\s*(?:amount|due|value|price)?|invoice\s*total|amount\s*due|grand\s*total|amount|due)\s*(?:\$\s*)?([0-9,]+(?:\.[0-9]{2})?)', text)
        if amount_match:
            parsed_amt = cls._parse_amount(amount_match.group(1))
            if parsed_amt is not None:
                fields["invoice_amount"] = parsed_amt
                confidence["invoice_amount"] = 0.9
            else:
                warnings.append("Failed to parse matched invoice amount.")
        else:
            # Check for the last dollar amount (often the total at the bottom of invoice)
            dollar_matches = re.findall(r'\$\s*([0-9,]+(?:\.[0-9]{2})?)', text)
            if dollar_matches:
                parsed_amt = cls._parse_amount(dollar_matches[-1])
                if parsed_amt is not None:
                    fields["invoice_amount"] = parsed_amt
                    confidence["invoice_amount"] = 0.5
                    warnings.append("Invoice amount fell back to the final dollar value in text.")
            else:
                warnings.append("Invoice amount not found.")

        return fields, confidence, warnings

    @staticmethod
    def _clean_text(val: str) -> str:
        # Clean quotes, trailing punctuation, brackets
        val = val.strip().strip(",").strip(".").strip().strip('"').strip("'").strip()
        # Collapse spaces
        val = re.sub(r'\s+', ' ', val)
        return val

    @staticmethod
    def _parse_amount(val_str: str) -> Optional[float]:
        val_str = val_str.replace(",", "").strip()
        match = re.search(r'([0-9]+(?:\.[0-9]{2})?)', val_str)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_date(val_str: str) -> Optional[str]:
        val_str = val_str.strip().strip(",").strip(".").strip()
        
        # 1. YYYY-MM-DD
        match = re.search(r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b', val_str)
        if match:
            y, m, d = match.groups()
            try:
                return date(int(y), int(m), int(d)).isoformat()
            except ValueError:
                pass

        # 2. DD/MM/YYYY or MM/DD/YYYY
        match = re.search(r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b', val_str)
        if match:
            p1, p2, y = match.groups()
            try:
                if int(p1) > 12:  # Must be DD/MM/YYYY
                    return date(int(y), int(p2), int(p1)).isoformat()
                else:  # Assume MM/DD/YYYY
                    return date(int(y), int(p1), int(p2)).isoformat()
            except ValueError:
                pass

        # 3. January 12, 2026 or 12 January 2026
        months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        # Month first
        match_mf = re.search(r'(?i)\b(jan[a-z]*|feb[a-z]*|mar[a-z]*|apr[a-z]*|may|jun[a-z]*|jul[a-z]*|aug[a-z]*|sep[a-z]*|oct[a-z]*|nov[a-z]*|dec[a-z]*)\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(\d{4})\b', val_str)
        if match_mf:
            m_str, d, y = match_mf.groups()
            try:
                m_idx = next(i for i, m in enumerate(months, 1) if m_str.lower().startswith(m))
                return date(int(y), m_idx, int(d)).isoformat()
            except StopIteration:
                pass
            except ValueError:
                pass

        # Day first
        match_df = re.search(r'(?i)\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan[a-z]*|feb[a-z]*|mar[a-z]*|apr[a-z]*|may|jun[a-z]*|jul[a-z]*|aug[a-z]*|sep[a-z]*|oct[a-z]*|nov[a-z]*|dec[a-z]*)\.?\s*,?\s*(\d{4})\b', val_str)
        if match_df:
            d, m_str, y = match_df.groups()
            try:
                m_idx = next(i for i, m in enumerate(months, 1) if m_str.lower().startswith(m))
                return date(int(y), m_idx, int(d)).isoformat()
            except StopIteration:
                pass
            except ValueError:
                pass

        return None

    @classmethod
    def _find_all_dates(cls, text: str) -> List[str]:
        """Utility to scan text and return a sorted list of ISO date strings."""
        iso_dates = []
        # Find all words that resemble dates
        # Regex matching YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, and textual formats
        # We can run a scan line-by-line or token-by-token
        words = re.findall(r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b', text, re.IGNORECASE)
        for w in words:
            parsed = cls._parse_date(w)
            if parsed and parsed not in iso_dates:
                iso_dates.append(parsed)
        return sorted(iso_dates)

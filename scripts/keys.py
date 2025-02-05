import google.generativeai as genai
from dotenv import load_dotenv
from ocr import get_ocr_text
import os
import re
import json
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")
text=get_ocr_text(pdf_path = "/Users/harish/Developer/deloitte/invoiz/scripts/downloads/invoice_194cc7d42395c108/sample-invoice.pdf")
def get_keys(text:str):
    prompt=f'''
    You are an intelligent document parser. Given the OCR text of an invoice, extract the following details:

    1. **Invoice Number:** Identify the invoice number, which may be labeled as "Invoice No", "Invoice Number", "Inv No", or similar variations. It usually contains a combination of letters, numbers, and sometimes hyphens (e.g., INV-2023-4567).

    2. **Vendor Name:** Identify the name of the vendor or supplier. This is typically labeled as "Vendor", "Supplier", "From", or appears prominently at the top of the invoice.

    Provide the extracted information in the following JSON format:
    ```json
    {{
    "invoice_number": "extracted_invoice_number",
    "vendor_name": "extracted_vendor_name"
    }}


    The OCR text of the invoice is: 
    {text}
    '''
    #print(prompt)
    response = model.generate_content(prompt)
    print(response.text)
    return response.text


def extract_and_validate_json(text):
    pattern = r"\{.*\}"
    matches = re.findall(pattern, text, re.DOTALL)
    
    if matches:
        json_text = matches[-1]
        try:
            json_data = json.loads(json_text)
            return json_data
        except json.JSONDecodeError:
            return "Invalid JSON format."
    else:
        return "No JSON found in the text."
print(extract_and_validate_json((get_keys(text))))
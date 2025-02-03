import fitz  # PyMuPDF
import pymupdf4llm

# Path to your PDF file
pdf_path = "/Users/toby/Projects/deloitte/sample-invoice.pdf"

# Open the PDF
pdf_document = fitz.open(pdf_path)

# Iterate through each page
for page_num in range(len(pdf_document)):
    page = pdf_document.load_page(page_num)
    
    # Extract text using OCR
    text = page.get_text("text")
    
    print(f"--- Page {page_num + 1} ---")
    print(text)
    print("\n" + "="*50 + "\n")

# Close the PDF
pdf_document.close()


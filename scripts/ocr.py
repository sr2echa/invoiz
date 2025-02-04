import fitz  # PyMuPDF
import pymupdf4llm

# Path to your PDF file
def get_ocr_text(pdf_path:str):
    # Open the PDF
    pdf_document = fitz.open(pdf_path)
    text=""
    # Iterate through each page
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        
        # Extract text using OCR
        text+= page.get_text("text")
        
    #print(text)
    # Close the PDF
    pdf_document.close()
    return text


import streamlit as st
import os
from mail import gmail_authenticate, search_and_read
from keys import get_keys, extract_and_validate_json
from ocr import get_ocr_text

def main():
    st.set_page_config(page_title="Gmail Invoice Reader", layout="wide")
    st.title("Invoiz")

    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.service = None

    if not st.session_state.authenticated:
        st.write("Please click the button below to authenticate with Gmail")
        if st.button("Login with Gmail"):
            try:
                service = gmail_authenticate()
                st.session_state.service = service
                st.session_state.authenticated = True
                st.rerun()
            except Exception as e:
                st.error(f"Authentication failed: {str(e)}")
    else:
        st.write("✅ Successfully authenticated with Gmail")
        
        # Search interface
        st.subheader("Search Emails")
        query = st.text_input("Enter your search query:", value="invoice")
        limit_choice = st.number_input("Number of emails to fetch:", min_value=1, value=5, help="Enter -1 for unlimited emails")
        
        if st.button("Search"):
            limit = None if limit_choice == -1 else int(limit_choice)
            with st.spinner("Fetching emails..."):
                emails_data = search_and_read(st.session_state.service, query, limit)
                
            st.write(f"Found {len(emails_data)} emails")
            
            for i, email in enumerate(emails_data, 1):
                with st.expander(f"Email {i}: {email['metadata'].get('subject', 'No Subject')}"):
                    st.write(f"**From:** {email['metadata'].get('from')}")
                    st.write(f"**Date:** {email['metadata'].get('date')}")
                    st.write(f"**Folder:** {email['folder']}")
                    
                    if email['content']['text']:
                        st.write("**Text Content:**")
                        for text_file in email['content']['text']:
                            with open(text_file, 'r') as f:
                                st.text(f.read())
                    
                    if email['content']['attachments']:
                        st.write(f"**Attachments ({len(email['content']['attachments'])} files):**")
                        for attachment in email['content']['attachments']:
                            st.write(f"- {attachment['filename']} ({attachment['size']})")
                            st.write(f"  Location: {attachment['path']}")
                            
                            # Process PDF attachments
                            if attachment['filename'].lower().endswith('.pdf'):
                                st.write("**PDF Analysis:**")
                                try:
                                    # Extract text using OCR
                                    ocr_text = get_ocr_text(attachment['path'])
                                    if not ocr_text.strip():
                                        st.warning("No text could be extracted from this PDF.")
                                        continue
                                    
                                    # Get key information
                                    keys_response = get_keys(ocr_text)
                                    extracted_info = extract_and_validate_json(keys_response)
                                    
                                    if isinstance(extracted_info, dict):
                                        st.write("Extracted Information:")
                                        st.json(extracted_info)
                                    else:
                                        st.warning(f"Could not extract information: {extracted_info}")
                                except Exception as e:
                                    st.warning(f"Could not process PDF: {str(e)}")
                                    st.write("Continuing with email display...")

if __name__ == "__main__":
    main()
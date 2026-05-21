import zipfile
from io import BytesIO
from PyPDF2 import PdfReader
from docx import Document
import streamlit as st

# Function to extract text from uploaded files
def extract_text_from_file(uploaded_file, file_extension = None):
    if uploaded_file is not None:
        if not file_extension:
            file_extension = uploaded_file.name.split(".")[-1].lower()
        
        if file_extension == "txt":
            return str(uploaded_file.read(), "utf-8")
        elif file_extension == "pdf":
            pdf_reader = PdfReader(uploaded_file)
            text = "".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
            return text
        elif file_extension == "docx":
            doc = Document(uploaded_file)
            return "\n".join([para.text for para in doc.paragraphs])
        else:
            st.error("Unsupported file type. Please upload a TXT, PDF, or DOCX file.")
            return None
    return None

# Function to extract resumes from a ZIP file
def extract_resumes_from_zip(uploaded_zip):
    resumes_text = {}
    resumes_binary = {}
    with zipfile.ZipFile(BytesIO(uploaded_zip.read()), 'r') as zip_ref:
        for file_name in zip_ref.namelist():
            with zip_ref.open(file_name) as file:
                file_extension = file_name.split(".")[-1].lower()
                file_data = file.read()
                if file_extension in ["pdf", "docx", "txt"]:
                    text = extract_text_from_file(BytesIO(file_data), file_extension)
                    if text:
                        resumes_text[file_name] = text
                        resumes_binary[file_name] = file_data  # Store binary file content
    return resumes_text, resumes_binary
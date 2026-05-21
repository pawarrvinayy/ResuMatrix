import base64

def create_download_link(file_bytes, file_name):
    b64 = base64.b64encode(file_bytes).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="{file_name}"><b>{file_name}</b></a>'
    return href

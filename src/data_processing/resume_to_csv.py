import pymupdf
import mammoth
import csv
from airflow.providers.google.cloud.hooks.gcs import GCSHook
import io

# Create a custom dialect
csv.register_dialect('custom',
                    quoting=csv.QUOTE_ALL,
                    doublequote=True,
                    escapechar='\\')


### THE CURRENT PROCESS DOES NOT INCLUDE KEY DEMOGRAPHIC VARIABLES - VISA STATUS, DISABILITY AND VETERAN
### BUILD A RANDOM GENERATOR FOR THESE BOOLEAN TYPE VARIABLES VISA(0.5,0.5), DISABILITY(0.1,0.9), VETERAN(0.1,0.9)
### TAG VISA WITH EDUCATION OR WORK EXPERIENCE IF NEEDED BUT
### ENFORCE VISA==(!VETERAN) cuz commonsense
### do we need to add this to the supervised model too?

def resume_pre_processing_gcs(job_id: str,
                              bucket_name: str,
                              gcp_conn_id: str = 'google_cloud_default',
                              prefix: str = 'resumes') -> str:
    """
    Reads all .pdf and .docx resumes in gs://{bucket_name}/{prefix}/{job_id}/,
    parses them, writes a single CSV back to the same GCS path,
    and returns the gs:// URI of the CSV.
    """
    # 1) open the bucket
    hook = GCSHook(gcp_conn_id=gcp_conn_id)
    client = hook.get_conn()
    bucket = client.get_bucket(bucket_name)

    # 2) list all files under the job_id folder
    folder = f"{prefix}/{job_id}/"
    blobs = bucket.list_blobs(prefix=folder)

    # 3) stream into an in‑memory CSV
    output = io.StringIO()
    writer = csv.writer(output, dialect='custom')
    writer.writerow(['job_id', 'resume_id', 'resume_text'])  # header row

    for blob in blobs:
        name = blob.name.lower()
        if name.endswith('.pdf') or name.endswith('.docx'):
            data = blob.download_as_bytes()

            if name.endswith('.pdf'):
                # open PDF from bytes
                doc = pymupdf.open(stream=data, filetype="pdf")
                page = doc[0]
                text = page.get_text()
                links = [l['uri'] for l in page.get_links()]
                text += "\nLinks: " + ", ".join(links)

            else:  # .docx
                # mammoth accepts a file-like; wrap in BytesIO
                with io.BytesIO(data) as docx_file:
                    result = mammoth.extract_raw_text(docx_file)
                    text = result.value

            resume_id = name.split('_')[0].split('/')[2]
            writer.writerow([job_id, resume_id, text])

    # 4) upload CSV back to GCS
    csv_data = output.getvalue()
    destination = f"{folder}{job_id}.csv"
    dest_blob = bucket.blob(destination)
    dest_blob.upload_from_string(csv_data, content_type='text/csv')

    return f"gs://{bucket_name}/{destination}"

#this is the code to generate the uuid, this will go into the db step, not required for now
# job_id = uuid.uuid4().__str__()
# file_path = 'C:\\NEU Courses\\IE7374_MLOps\\resumes'
# status=resume_pre_processing(job_id, file_path)
# print(status)

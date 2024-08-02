import base64
import vertexai
from vertexai.generative_models import GenerativeModel
import vertexai.preview.generative_models as generative_models
from google.cloud import storage, bigquery
import os



client = bigquery.Client(project="plucky-function-430114-f3")
    


def process_tickets_from_gcs(bucket_name):
    # Initialize Vertex AI
    vertexai.init(project="plucky-function-430114-f3", location="us-central1")
    model = GenerativeModel("gemini-1.5-flash-001")

    # Initialize GCS client and list files in the bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Iterate through files in the bucket
    blobs = bucket.list_blobs()
    for blob in blobs:
        file_name = blob.name
        content = blob.download_as_text()  # Read the file content as text

        # Define the question for sentiment analysis
        question = "I want to know if customer sentiments are positive or negative only, and also a reason in 3-4 words"

        # Generation configuration
        generation_config = {
            "max_output_tokens": 2339,
            "temperature": 1,
            "top_p": 0.95,
        }

        # Safety settings
        safety_settings = {
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        # Generate response
        response = model.generate_content([content, question], generation_config=generation_config, safety_settings=safety_settings, stream=False)

        # Extract the sentiment and reason from the response
        response_text = response.text  # Accessing the text directly
        sentiment, reason = extract_sentiment_and_reason(response_text)

        # Write to BigQuery
        write_to_bigquery(file_name, sentiment, reason)

def extract_sentiment_and_reason(response_text):
    # Assuming the response format is consistent and contains "Positive"/"Negative" and a reason.
    lines = response_text.split('\n')
    sentiment = lines[0].strip()  # First line is assumed to be the sentiment
    reason = ' '.join(lines[1:]).strip()  # The rest is the reason
    return sentiment, reason

def write_to_bigquery(file_name, sentiment, reason):
    client = bigquery.Client()
    dataset_id = 'reports'  # Replace with your dataset ID
    table_id = 'sentiments'  # Replace with your table ID

    # Prepare the row to insert
    rows_to_insert = [{
        "file_number": file_name,
        "sentiment": sentiment,
        "reason": reason
    }]

    # Insert rows into BigQuery
    errors = client.insert_rows_json(f"{dataset_id}.{table_id}", rows_to_insert)
    if errors:
        print(f"Encountered errors while inserting rows: {errors}")
    else:
        print(f"Successfully inserted rows into {dataset_id}.{table_id}")

if __name__ == "__main__":
    # Replace 'your_bucket_name' with the actual name of your GCS bucket
    bucket_name = 'customer_chat'
    process_tickets_from_gcs(bucket_name)

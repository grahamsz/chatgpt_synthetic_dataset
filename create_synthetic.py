import psycopg2
from openai import OpenAI
import time
import concurrent.futures
from dotenv import load_dotenv
import os

# Load environment variables from the .env file (not included in github repo)
load_dotenv()

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
import json

# Function to analyze text using OpenAI's GPT-3 API
def analyze_text(text):
    # Construct the prompt with the text
    prompt_text = f"Can you analyze the following news story and return a json object that ranks the content on 3 measures\n\nfearsafety : where -1 is a story that would create a fear in a typical reader but 1 would make the reader feel safe\nopinionfact: where -1 is pure opinion and 1 is factual\nemotionalrational: where -1 is loaded with emotional language and 1 is rational\ndiversityofsource: where 0 doesn't refer to any sources but 1 has a good set of sources from each side\n\nreturn a json object like\n{{\"fearsafety\":-0.43,\"opinionfact\":0.32,\"emotionalrational\":-0.33,\"diversityofsource\":0.66}}\n\nHere's the story\n{text}"

    try:
        response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system", "content": "You are a tool which analyzes news stories fro their emotional impact."},
            {"role": "user", "content": prompt_text},

        ],
        max_tokens=100,
        )
        # Extract the text from the response
        response_text = response.choices[0].message.content.strip()
        
        # Attempt to parse the JSON from the response
        try:
            json_data = json.loads(response_text)
            return json_data
        except json.JSONDecodeError:
            print("Received bad JSON: ", response_text)
            # Return a default or empty JSON object if parsing fails
            return {}
    
    except Exception as e:
        print(f"An error occurred: {e}")
        # Handle rate limit exceeded error
        if "rate_limit_exceeded" in str(e):
            print("Rate limit exceeded, retrying in 10 seconds...")
            time.sleep(10)
            return analyze_text(text)
        return None

# Function to process a record from the database, send the text to OpenAI for analysis, and update the record with the results
def process_record(record):
    text_to_analyze = record[1]
    analysis_results = analyze_text(text_to_analyze)

    # Only update the record if valid data is returned from the analysis
    if analysis_results:
        with psycopg2.connect(dsn=database_url) as conn:
            with conn.cursor() as cur:
                update_query = """
                UPDATE news_stories
                SET fear_safety = %s, 
                    opinion_fact = %s, 
                    emotional_rational = %s, 
                    diversity_of_source = %s,
                    date_processed = NOW()
                WHERE id = %s;
                """
                cur.execute(update_query, (
                    analysis_results.get('fearsafety', 0), 
                    analysis_results.get('opinionfact', 0),
                    analysis_results.get('emotionalrational', 0), 
                    analysis_results.get('diversityofsource', 0), 
                    record[0]
                ))


# Get the database URL from the environment variable
database_url = os.getenv('DATABASE_URL')

# Connect to the PostgreSQL database and fetch records
with psycopg2.connect(dsn=database_url) as conn:
    with conn.cursor() as cur:
        cur.execute("""
        SELECT id, text FROM news_stories
        WHERE excluded = FALSE AND date_processed IS NULL
        ORDER BY RANDOM()
        LIMIT 500;
        """)
        records = cur.fetchall()

count=0

# Process records in parallel using ThreadPoolExecutor
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    future_to_record = {executor.submit(process_record, record): record for record in records}

    for future in concurrent.futures.as_completed(future_to_record):
        record = future_to_record[future]
        try:
            data = future.result()

            count = count+1
        except Exception as exc:
            print(f"{count} generated an exception: {exc}")
        else:
            print(f"{count} processed.")

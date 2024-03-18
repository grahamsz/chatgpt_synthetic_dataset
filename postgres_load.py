import json
import psycopg2
from datetime import datetime

# Get the database URL from the environment variable
database_url = os.getenv('DATABASE_URL')

# Connect to the PostgreSQL database
conn = psycopg2.connect(dsn=database_url)
cur = conn.cursor()

# SQL query to insert data
insert_query = """
INSERT INTO news_stories (title, text, summary, authors, publish_date, status, url, domain, warc_date, split, processed_at, fear_safety, opinion_fact, emotional_rational, diversity_of_source)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s, %s);
"""

# Load and insert the data
with open('/path/to/realnews.jsonl', 'r') as file:
    for i, line in enumerate(file):
        if i >= 1000000:  # Stop after processing a million lines
            break

        # Inside the loop, adjust the parsing of warc_date
        try:
            data = json.loads(line)
            
            # Check and reformat warc_date if it's in the "2016052819" format
            warc_date = data.get('warc_date')
            if warc_date and len(warc_date) == 10:
                # Assuming the format is YYYYMMDDHH
                warc_date = datetime.strptime(warc_date, '%Y%m%d%H').strftime('%Y-%m-%d %H:%M:%S')
            else:
                # Handle other formats or cases as necessary
                # This is a placeholder; actual handling may vary based on your data
                warc_date = None

            # Prepare data for insertion
            record = (
                data.get('title'),
                data.get('text'),
                data.get('summary'),
                data.get('authors'),
                data.get('publish_date'),
                data.get('status'),
                data.get('url'),
                data.get('domain'),
                warc_date,  # Use the reformatted date
                data.get('split'),
                None,  # Placeholder for fear_safety
                None,  # Placeholder for opinion_fact
                None,  # Placeholder for emotional_rational
                None,  # Placeholder for diversity_of_source
            )
            # Execute the insert query
            cur.execute(insert_query, record)
        except json.JSONDecodeError:
            print(f"Failed to parse JSON on line {i}")
        except psycopg2.Error as e:
            print(f"Database error on line {i}: {e}")
            conn.rollback()  # Rollback the current transaction on error
        else:
            conn.commit()  # Commit each successful insertion

# Close the database connection
cur.close()
conn.close()

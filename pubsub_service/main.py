from google.cloud import pubsub_v1
from datetime import datetime, timedelta
from firebase_admin import firestore
import json
import time

# Pub/Sub configuration
PROJECT_ID = "rupiseva"
TOPIC_ID = "parse-gmail-topic"

db = firestore.Client()

def get_doc_ids_to_parse():
    def fetch_users_to_parse_and_update():
        before_1_hour = datetime.now() - timedelta(hours=1)
        before_24_hrs = datetime.now() - timedelta(hours=24)

        null_query = db.collection('gmail-auth') \
            .where('isValid', '==', True) \
            .where('lastParsedAt', '==', None) \
            .where('createdAt', '>', before_24_hrs) \
            .where('createdAt', '<', before_1_hour) \
            .where('hasReadScope', '==', True) \
            .order_by('createdAt') \
            .limit(50)

        docs = list(null_query.stream())
        if len(docs) > 0:
            doc_ids = [doc.id for doc in docs]
            return doc_ids

        # Removing reparsing as of now, will add later
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        null_query_old = db.collection('gmail-auth') \
            .where('isValid', '==', True) \
            .where('hasReadScope', '==', True) \
            .where('lastParsedAt', '<', today_start) \
            .order_by('lastParsedAt') \
            .limit(50)

        docs = list(null_query_old.stream())
        if len(docs) > 0:
            return [doc.id for doc in docs]

        return []

    doc_ids = fetch_users_to_parse_and_update()
    return doc_ids

def update_last_parsed_at(docs):
    # Update lastParsedAt for these documents in batch
    batch = db.batch()
    for doc in docs:
        doc_ref = db.collection('gmail-auth').document(doc)
        batch.update(doc_ref, {'lastParsedAt': firestore.SERVER_TIMESTAMP})
    batch.commit()
    

def publish_messages_to_pubsub(doc_ids):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

    # Split doc_ids into chunks of 50
    for i in range(0, len(doc_ids), 50):
        chunk = doc_ids[i:i + 50]
        message = {"docIds": chunk}

        # Publish the message
        future = publisher.publish(topic_path, json.dumps(message).encode("utf-8"))
        messageid = future.result(timeout = 5)
        print(f"Published message ID: {messageid}")
        update_last_parsed_at(chunk)

def main():
    while True:
        try:
            # Fetch docIds using the copied logic
            doc_ids = get_doc_ids_to_parse()
            if not doc_ids:
                print("No docIds to process.")
                time.sleep(60)
                continue
            # Publish messages to Pub/Sub
            publish_messages_to_pubsub(doc_ids)
        except Exception as e:
            print(f"An error occurred: {e}")
            continue

if __name__ == "__main__":
    main()
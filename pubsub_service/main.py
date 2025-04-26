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
            .limit(10)

        docs = list(null_query.stream())
        if len(docs) > 0:
            user_data = []
            for doc in docs:
                doc_dict = doc.to_dict()
                last_parsed_at = doc_dict.get('lastParsedAt')
                if last_parsed_at is None:
                    last_parsed_at = 0
                else:
                    last_parsed_at = int(last_parsed_at.timestamp())
                user_data.append({"doc_id": doc.id, 
                                  "last_parsed_at": last_parsed_at, 
                                  })
            return user_data

        # Removing reparsing as of now, will add later
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)-timedelta(hours=5, minutes=30)
        null_query_old = db.collection('gmail-auth') \
            .where('isValid', '==', True) \
            .where('hasReadScope', '==', True) \
            .where('lastParsedAt', '<', today_start) \
            .order_by('lastParsedAt') \
            .limit(10)

        docs = list(null_query_old.stream())
        if len(docs) > 0:
            user_data = []
            for doc in docs:
                doc_dict = doc.to_dict()
                last_parsed_at = doc_dict.get('lastParsedAt')
                if last_parsed_at is None:
                    last_parsed_at = 0
                else:
                    last_parsed_at = int(last_parsed_at.timestamp())
                user_data.append({
                    "doc_id": doc.id,
                    "last_parsed_at": last_parsed_at, 
                    })
            return user_data
        return []

    user_data = fetch_users_to_parse_and_update()
    return user_data

def update_last_parsed_at(docs):
    # Update lastParsedAt for these documents in batch
    batch = db.batch()
    for doc in docs:
        doc_ref = db.collection('gmail-auth').document(doc)
        batch.update(doc_ref, {'lastParsedAt': firestore.SERVER_TIMESTAMP})
    batch.commit()
    

def publish_messages_to_pubsub(docs):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

    # Split doc_ids into chunks of 50
    for i in range(0, len(docs), 50):
        chunk = docs[i:i + 50]
        message = {"docs": chunk}
        # Publish the message
        future = publisher.publish(topic_path, json.dumps(message).encode("utf-8"))
        messageid = future.result(timeout = 5)
        print(f"Published message ID: {messageid}")
        update_last_parsed_at([doc.get("doc_id") for doc in chunk])

def main():
    while True:
        try:
            # Fetch docIds using the copied logic
            docs = get_doc_ids_to_parse()
            if not docs:
                print("No docIds to process.")
                time.sleep(60)
                continue
            # Publish messages to Pub/Sub
            publish_messages_to_pubsub(docs)
        except Exception as e:
            print(f"An error occurred: {e}")
            continue

if __name__ == "__main__":
    main()
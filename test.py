import requests
import time
from datetime import datetime, timedelta
import pytz


# Your API token
API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5YTYyNGRmMC0xMmYxLTQ0OGUtYjg4NC00MzY3ODBhNWQzY2QiLCJqdGkiOiJkYTdmMjhjYTZjYzdlNzM1NTgxNTUwMDdkMTk1Y2UzNGMyYTVjZmE0NDBmN2M4NzMyMzY3MzkyY2YzOGI2NmRkNWYyMGNjYzE4MzhmOGUyNSIsImlhdCI6MTc2MTgzNjU0Ny4yMjU0MDIsIm5iZiI6MTc2MTgzNjU0Ny4yMjU0MDYsImV4cCI6MTc5MzM3MjU0Ny4yMjAyMjEsInN1YiI6IjM4NTQ4NiIsInNjb3BlcyI6WyJwYXQ6cmVhZCIsInBhdDp3cml0ZSJdfQ.kwqxEz1otrERorO6dsufsY9Yuu0r6Sw_fwdidgkp-uzwVgum1P01jkUiNrApkgFIIvW16nYFUnTVAiac75RVl-hiQE8wKrDzIyf8YslEsTEsLyr1rPYq5QVvr44Kfk4G6kky27MYP2RunuBRvsOOUQlZWCmVk3yVMGb_b8WLEtZN9dYBnOC870ptrQkkfYyiqig-6zYUAWw19uqjzsvIKhZL34zuIWzwMovza4sPvLctGnL8Uy21fGK_VmMv4eovVeySzp2krRkLLMSk2f1vpe9WKxuRpvx3A4Slpv6LSMZCVoE76uvMg7rh6ZR1XWFwpcVZo4NQnN8c7XLvIQHA9NdctKDjM1FMxBipJrq4whZY-i0cqnxs73SCKiClWevjsiQJgheH_4Yc438pEB_BjJawHodmREfnNZo7T9AE6lIGyLuhHGMSNXSTyqUGRqcpzK6-Xn-bfHcG4eyNFA3Fr1r1obrqgxXzZEt3V1L2Jx-W0iCPIEQ1YkmDKSoFE0JeH9DtlVgUq7g00Uo8jlVfwdAKavoMNzneWOHUG1D25_2ytNlndrvkUXbZIalvyX06Y846Rz5RxFUqZF-T04HUy0QMMRDRZdAKzHFagLHy_zhzca4-w7mcuJPaaPuba1s62y5AflF8dJS3ETo1SnG8DQ8OrhQAWBNrc3uC3jN_5mk"

THAILAND_TZ = pytz.timezone('Asia/Bangkok')
RUN_INTERVAL_MINUTES = 15
START_HOUR = 0   # 12:00 AM
START_MINUTE = 15
END_HOUR = 5     # 5:15 AM
END_MINUTE = 15
# ============================================================

url = "https://public.api.hospitable.com/v2/properties?per_page=100"
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json"
}

# ============================================================
# HELPERS
# ============================================================
def get_paginated_data(url, headers):
    """Helper function to handle pagination for any endpoint"""
    all_data = []
    page = 1
    while True:
        paginated_url = f"{url}&page={page}" if "?" in url else f"{url}?page={page}"
        response = requests.get(paginated_url, headers=headers)
        if response.status_code != 200:
            break
        data = response.json()
        items = data.get("data", [])
        if not items:
            break
        all_data.extend(items)
        meta = data.get("meta", {})
        if page >= meta.get("last_page", 1):
            break
        page += 1
        time.sleep(0.1)  # Rate limiting
    return all_data


def get_all_ids_for_properties(property_uuids):
    all_ids = []
    for property_uuid in property_uuids:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')

        reservations_url = f"https://public.api.hospitable.com/v2/reservations?properties[]={property_uuid}&per_page=100&include=guest&start_date={start_date}&end_date={end_date}"
        reservations = get_paginated_data(reservations_url, headers)
        for reservation in reservations:
            guest = reservation.get("guest", {})
            all_ids.append({
                'type': 'reservation',
                'id': reservation.get("id"),
                'conversation_id': reservation.get("conversation_id"),
                'guest_name': f"{guest.get('first_name', '')} {guest.get('last_name', '')}".strip(),
                'property_uuid': property_uuid
            })
        time.sleep(0.1)
        inquiries_url = f"https://public.api.hospitable.com/v2/inquiries?properties[]={property_uuid}&per_page=100&include=guest"
        inquiries = get_paginated_data(inquiries_url, headers)
        for inquiry in inquiries:
            guest = inquiry.get("guest", {})
            all_ids.append({
                'type': 'inquiry',
                'id': inquiry.get("id"),
                'conversation_id': inquiry.get("id"),
                'guest_name': f"{guest.get('first_name', '')} {guest.get('last_name', '')}".strip(),
                'property_uuid': property_uuid
            })
        time.sleep(0.2)
    return all_ids


def check_last_message_sender(reservation_id):
    """Check if last message was from guest or host"""
    messages_url = f"https://public.api.hospitable.com/v2/reservations/{reservation_id}/messages"
    try:
        response = requests.get(messages_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            messages = data.get("data", [])
            if messages:
                last_message = messages[0]
                sender_type = last_message.get("sender_type")
                created_at = last_message.get("created_at")
                if created_at:
                    utc_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    thailand_time = utc_time.astimezone(THAILAND_TZ)
                    return sender_type, thailand_time
    except Exception as e:
        print(f"Error checking message sender: {e}")
    return None, None


def run_script():
    """Your main logic (runs once per cycle)"""
    print(f"\n--- Running script at {datetime.now(THAILAND_TZ).strftime('%Y-%m-%d %H:%M:%S')} ---")

    res = requests.get(url, headers=headers)
    data = res.json()
    property_uuids = [item.get("id") for item in data.get("data", []) if "id" in item]

    all_data = get_all_ids_for_properties(property_uuids)
    filtered_ids = []

    for item in all_data:
        if item['type'] != 'null':
            last_sender, message_time = check_last_message_sender(item['id'])
            if message_time and last_sender == 'guest':
                now = datetime.now(THAILAND_TZ)
                if now - timedelta(hours=5) <= message_time <= now:
                    item['last_message_sender'] = last_sender
                    item['last_message_time'] = message_time.strftime('%Y-%m-%d %H:%M:%S')
                    filtered_ids.append(item)
                    print(f"ID: {item['id']} | Guest: {item['guest_name']} | "
                          f"Last message by: {last_sender} | "
                          f"Time: {message_time.strftime('%Y-%m-%d %H:%M:%S')}")

    payload = {
        "body": (
            "Hello. Thank you for reaching out to us. "
            "Our working hours are between 10am - 9pm. "
            "In case of emergencies, please contact or call "
            "+33(0)64546 5371 on WhatsApp. Thank you."
            "\n-----------------------------------------------------\n"
            "This is an automated message sent via a Python script."
        )
    }

    for item in filtered_ids:
        message_url = f"https://public.api.hospitable.com/v2/reservations/{item['id']}/messages"
        response = requests.post(message_url, headers=headers, json=payload)
        if response.status_code == 201:
            print(f"📨 Message sent successfully to reservation {item['id']}")
        else:
            print(f"⚠️ Failed to send message to {item['id']}: {response.status_code}, {response.text}")
        time.sleep(0.2)


print("Auto-run schedule started...")

while True:
    now = datetime.now(THAILAND_TZ)
    start_today = now.replace(hour=START_HOUR, minute=START_MINUTE, second=0, microsecond=0)
    end_today = now.replace(hour=END_HOUR, minute=END_MINUTE, second=0, microsecond=0)

    if start_today <= now <= end_today:
        run_script()
        print("Sleeping for 15 minutes...")
        time.sleep(RUN_INTERVAL_MINUTES * 60)
    else:
        tomorrow_start = (now + timedelta(days=1)).replace(hour=START_HOUR, minute=START_MINUTE, second=0, microsecond=0)
        sleep_seconds = (tomorrow_start - now).total_seconds()
        print(f"Outside schedule ({now.strftime('%H:%M')}). Sleeping until next 12:15 AM...")
        time.sleep(sleep_seconds)



''' 
payload = {
    "body": (
        "Hello. Thank you for reaching out to us. "
        "Our working hours are between 10am - 9pm. "
        "In case of emergencies, please contact or call "
        "+33(0)64546 5371 on WhatsApp. Thank you."
        "-----------------------------------------------------"
        "This is an automated message sent via a python script"
    )
}

for reservation_id in filtered_ids:
    message_url = f"https://public.api.hospitable.com/v2/reservations/{reservation_id}/messages"
    
    response = requests.post(message_url, headers=headers, json=payload)
    
    if response.status_code == 201:
        print(f"📨 Message sent successfully to reservation {reservation_id}")
    else:
        print(f"⚠️ Failed to send message to {reservation_id}: {response.status_code}, {response.text}")
    
    time.sleep(0.2)
''' 
    
''' 
HOW TO SEND A MESSAGE TO A GUESTTTT


import requests

# Your reservation details
reservation_uuid = "dad5c057-0586-47f5-9212-4197f62beea6"
bearer_token = "YOUR_BEARER_TOKEN"  # Replace with your actual token

# API endpoint
url = f"https://public.api.hospitable.com/v2/reservations/{reservation_uuid}/messages"

# Headers
headers = {
    "Authorization": f"Bearer {bearer_token}",
    "Content-Type": "application/json"
}

# Message data
data = {
    "body": "Hi there! Just checking in to see how everything is going with your stay."
}

# Send the message
response = requests.post(url, headers=headers, json=data)

if response.status_code == 202:
    result = response.json()
    print(f"Message sent! Reference ID: {result['data']['sent_reference_id']}")
else:
    print(f"Error: {response.status_code} - {response.text}")


'''
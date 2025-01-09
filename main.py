import requests
import time
import ssl
import os
import uuid
import json
from nostr.event import Event, EventKind
from nostr.relay_manager import RelayManager
from nostr.key import PrivateKey
from nostr.filter import Filter, Filters

def get_relays():
    env_relays = os.getenv('RELAYS')
    if env_relays is None:
        env_relays = "wss://relay.nostr.band"
    return env_relays.split(",")

def setup_relay_manager(relays):
    relay_manager = RelayManager()
    for relay in relays:
        print("Adding relay: " + relay)
        relay_manager.add_relay(relay)
    relay_manager.open_connections({"cert_reqs": ssl.CERT_NONE}) # NOTE: This disables ssl certificate verification
    time.sleep(1.25) # allow the connections to open
    return relay_manager

def get_private_key():
    env_private_key = os.environ.get("PRIVATE_KEY")
    if not env_private_key:
        print('The environment variable "PRIVATE_KEY" is not set.')
        exit(1)
    return PrivateKey(bytes.fromhex(env_private_key))

def get_public_key():
    private_key = get_private_key()
    return private_key.public_key.hex()

def fetch_latest_block_height():
    url = "https://blockchain.info/latestblock"
    response = requests.get(url)
    data = response.json()
    return data["height"]

def fetch_latest_bot_message(relay_manager):
    public_key = get_public_key()
    # print("Public Key: " + public_key)
    filters = Filters([Filter(authors=[public_key], kinds=[EventKind.TEXT_NOTE], limit=1)])
    # generate a random subscription id
    subscription_id = str(uuid.uuid4())
    request = [ClientMessageType.REQUEST, subscription_id]
    request.extend(filters.to_json_array())

    relay_manager.add_subscription(subscription_id, filters)

    message = json.dumps(request)
    relay_manager.publish_message(message)

    while(not relay_manager.message_pool.has_events()):
        print("Waiting for receiving latest bot message...", end="")
        time.sleep(1)
    print("done.")
    message = relay_manager.message_pool.get_event().event.content
    # print("Received latest bot message")
    return message

def fetch_latest_bot_message_height(relay_manager):
    message = fetch_latest_bot_message(relay_manager)
    return int(message.split(" ")[1])

def main():
    try:
        relays = get_relays()
        relay_manager = setup_relay_manager(relays)
        private_key = get_private_key()

        old_block_height = fetch_latest_bot_message_height(relay_manager=relay_manager)
        print("Old Block Height: " + str(old_block_height))
        while True:
            try:
                block_height = fetch_latest_block_height()

                if block_height > old_block_height:
                    message = "⚡️ " + str(block_height) + " ⚡️"
                    print(message)
                    event = Event(
                        content=str(message),
                        public_key=private_key.public_key.hex()
                    )
                    private_key.sign_event(event)
                    relay_manager.publish_event(event)
                    old_block_height = block_height
            except Exception as e:
                print(e)
                time.sleep(10)
            time.sleep(5)
    except Exception as e:
        print(e)
        relay_manager.close_connections()
        exit(1)

if __name__ == "__main__":
    main()
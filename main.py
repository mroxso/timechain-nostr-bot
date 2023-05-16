import requests
import time
import ssl
import os
from nostr.event import Event
from nostr.relay_manager import RelayManager
from nostr.message_type import ClientMessageType
from nostr.key import PrivateKey

try:
    # Read env variable and add relays
    env_relays = os.getenv('RELAYS') # None
    if env_relays is None:
        env_relays = "wss://relay.nostr.band"
    relay_manager = RelayManager()
    for relay in env_relays.split(","):
        print("Adding relay: " + relay)
        relay_manager.add_relay(relay)

    relay_manager.open_connections({"cert_reqs": ssl.CERT_NONE}) # NOTE: This disables ssl certificate verification
    time.sleep(1.25) # allow the connections to open

    env_private_key = os.environ.get("PRIVATE_KEY")
    if not env_private_key:
        print('The environment variable "PRIVATE_KEY" is not set.')
        exit(1)

    private_key = PrivateKey(bytes.fromhex(env_private_key))

    old_block_height = 0
    while True:
        url = "https://blockchain.info/latestblock"
        response = requests.get(url)
        data = response.json()
        block_height = data["height"]

        if(block_height > old_block_height):
            message = "⚡️ " + str(block_height) + " ⚡️"
            print(message)
            event = Event(
                content=str(message),
                public_key=private_key.public_key.hex()
            )
            private_key.sign_event(event)
            relay_manager.publish_event(event)
            # relay_manager.close_connections() # NEEDED?!
            old_block_height = block_height
        time.sleep(5)
except Exception as e:
    print(e)
    relay_manager.close_connections()
    exit(1)
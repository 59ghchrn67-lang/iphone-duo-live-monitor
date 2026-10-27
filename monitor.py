
import asyncio
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import websockets

# InStock Radar live UK WebSocket
WEBSOCKET_URL = "wss://instockradar.com/api/live?cc=uk&f=iphoneduo"

# Discord webhook stored securely in GitHub Actions Secrets
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]

# Only these two iPhone Duo models
PRODUCTS = {
    "MK2E4QN/A": "iPhone Duo 256GB — Night Sky",
    "MK2D4QN/A": "iPhone Duo 256GB — Star White",
}

# Only these three Apple Stores
TARGET_STORES = {
    "R393": "Bristol — Cribbs Causeway",
    "R335": "Bath — SouthGate",
    "R334": "Cardiff",
}

# Tracks active stock alerts to prevent duplicates
alerted = set()


def send_discord(message):
    payload = urllib.parse.urlencode({
        "content": message
    }).encode("utf-8")

    request = urllib.request.Request(
        WEBHOOK_URL,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "iPhoneDuoMonitor/1.0",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        print(
            f"Discord notification sent: HTTP {response.status}",
            flush=True
        )


async def monitor():
    while True:
        try:
            print("Connecting to InStock Radar...", flush=True)

            async with websockets.connect(
                WEBSOCKET_URL,
                ping_interval=30,
                ping_timeout=20,
            ) as websocket:

                print("🟢 CONNECTED — Monitoring Bristol, Bath & Cardiff", flush=True)

                async for raw in websocket:
                    if raw == "pong":
                        continue

                    try:
                        message = json.loads(raw)
                    except (ValueError, TypeError):
                        continue

                    changes = message.get("ch", [])

                    for change in changes:
                        if len(change) < 4:
                            continue

                        store, part, available, timestamp = change[:4]
                        family = change[4] if len(change) > 4 else None

                        # Ignore other product families
                        if family and family != "iphoneduo":
                            continue

                        # Ignore other models and Apple Stores
                        if part not in PRODUCTS:
                            continue

                        if store not in TARGET_STORES:
                            continue

                        key = (store, part)

                        if available:
                            # Don't send duplicate alerts
                            if key in alerted:
                                continue

                            print(
                                f"🚨 STOCK DETECTED: {TARGET_STORES[store]} "
                                f"— {PRODUCTS[part]}",
                                flush=True
                            )

                            product_url = (
                                "https://www.apple.com/uk/shop/product/"
                                + urllib.parse.quote(part, safe="/")
                            )

                            notification = (
                                "🚨 **IPHONE DUO IN STOCK!** 🚨\n\n"
                                f"📱 **{PRODUCTS[part]}**\n"
                                f"📍 **{TARGET_STORES[store]}**\n\n"
                                f"🛒 {product_url}\n\n"
                                "⚡ ACT FAST!"
                            )

                            try:
                                await asyncio.to_thread(
                                    send_discord,
                                    notification
                                )
                                alerted.add(key)

                            except Exception as error:
                                print(
                                    f"Discord notification failed: {error}",
                                    flush=True
                                )

                        else:
                            # Reset alert when stock disappears
                            alerted.discard(key)

        except Exception as error:
            print(
                f"WebSocket disconnected: {error}",
                flush=True
            )
            print("Reconnecting in 5 seconds...", flush=True)
            await asyncio.sleep(5)

if os.getenv("TEST_DISCORD") == "true":
    send_discord(
        "🧪 TEST — iPhone Duo GitHub bot\n"
        "📱 256GB Night Sky\n"
        "📍 Bristol — Cribbs Causeway\n"
        "✅ Discord notification working!\n"
        "⚠️ SIMULATED — NOT REAL STOCK"
    )

if __name__ == "__main__":
    print(
        "Starting iPhone Duo monitor:",
        datetime.now(timezone.utc).isoformat(),
        flush=True
    )

    print("Monitoring these Apple Stores:")
    for store in TARGET_STORES.values():
        print(f"  - {store}")

    print("Monitoring these models:")
    for product in PRODUCTS.values():
        print(f"  - {product}")

    asyncio.run(monitor())

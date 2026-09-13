import asyncio
import time
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.config import settings
from backend.app.database.collections import ALL_COLLECTIONS
from motor.motor_asyncio import AsyncIOMotorClient


async def verify_mongodb():
    print("=" * 60)
    print("ZeroDayAI MongoDB Direct Verification Test")
    print("=" * 60)
    
    masked_uri = settings.MONGODB_URI.split("@")[-1] if "@" in settings.MONGODB_URI else settings.MONGODB_URI
    print(f"Target Database : {settings.MONGODB_DATABASE}")
    print(f"Connection URI  : [{masked_uri}]")
    print(f"Environment     : {settings.ENVIRONMENT}")
    print("-" * 60)

    client = None
    try:
        client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
            connectTimeoutMS=settings.MONGODB_TIMEOUT_MS,
        )
        
        # 1. Ping test
        start = time.perf_counter()
        ping_res = await client.admin.command("ping")
        latency_ms = (time.perf_counter() - start) * 1000
        print(f"Ping Result     : SUCCESS (ok={ping_res.get('ok')})")
        print(f"Ping Latency    : {latency_ms:.2f} ms")
        print("MongoDB Status  : CONNECTED")

        # 2. Server Info / Topology
        try:
            hello_res = await client.admin.command("hello")
        except Exception:
            hello_res = await client.admin.command("isMaster")
            
        server_info = await client.server_info()
        version = server_info.get("version", "Unknown")
        is_replicaset = "setName" in hello_res
        server_type = f"ReplicaSet ({hello_res.get('setName')})" if is_replicaset else "Standalone"
        
        print(f"MongoDB Version : {version}")
        print(f"Server Type     : {server_type}")
        print(f"Max BSON Size   : {hello_res.get('maxBsonObjectSize', 'N/A')}")
        print(f"Read-Only       : {hello_res.get('readOnly', False)}")

        # 3. Database & Collections check
        db = client[settings.MONGODB_DATABASE]
        existing_collections = await db.list_collection_names()
        print(f"Accessible DB   : {db.name}")
        print(f"Existing Cols   : {existing_collections}")

        print("-" * 60)
        print("Checking Required Collections:")
        for col_name in ALL_COLLECTIONS:
            col = db[col_name]
            count = await col.count_documents({})
            print(f"  - {col_name:<20}: Accessible (doc count: {count})")

        print("=" * 60)
        print("RESULT: MongoDB is ACTUALLY connected and fully functional.")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"MongoDB is unreachable: {str(e)}")
        print("=" * 60)
        print("RESULT: MongoDB is OFFLINE / UNREACHABLE")
        print("=" * 60)
        return False
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    success = asyncio.run(verify_mongodb())
    sys.exit(0 if success else 1)

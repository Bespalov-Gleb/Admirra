from core.database import SessionLocal
from core import models

db = SessionLocal()
try:
    clients = db.query(models.Client).all()
    print(f"Total clients found: {len(clients)}")
    for client in clients:
        print(f"ID: {client.id}, Name: {client.name}, Owner ID: {client.owner_id}")
finally:
    db.close()

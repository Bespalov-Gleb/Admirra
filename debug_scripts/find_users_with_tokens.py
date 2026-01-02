from core.database import SessionLocal
from core.models import User, Client, Integration, IntegrationPlatform

def find_users_with_tokens():
    db = SessionLocal()
    try:
        # Join Integration -> Client -> User
        results = (
            db.query(User.email, User.username, Client.name, Integration.platform)
            .join(Client, Client.owner_id == User.id)
            .join(Integration, Integration.client_id == Client.id)
            .filter(
                Integration.platform.in_([
                    IntegrationPlatform.VK_ADS, 
                    IntegrationPlatform.YANDEX_DIRECT,
                    IntegrationPlatform.YANDEX_METRIKA
                ])
            )
            .all()
        )

        if not results:
            print("\n❌ Ҳеҷ корбаре бо токенҳои VK ё Yandex ёфт нашуд.")
            return

        print("\n✅ Корбарони дорои интегратсия (Токенҳо):")
        print("-" * 60)
        print(f"{'Email':<30} | {'Username':<15} | {'Client':<15} | {'Platform'}")
        print("-" * 60)
        
        seen_users = set()
        
        for email, username, client_name, platform in results:
            # Format output
            uname = username if username else "(no username)"
            print(f"{email:<30} | {uname:<15} | {client_name:<15} | {platform.name}")
            seen_users.add(email)

        print("-" * 60)
        print(f"\n💡 Шумо метавонед бо яке аз ин Email-ҳо ворид шавед (Паролро ман намедонам, аммо Email-ҳо инҳоянд).")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    find_users_with_tokens()

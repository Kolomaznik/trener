from app.db import get_db


def run(db) -> list[dict]:
    db["users"].create_index("email", unique=True, name="users_email_unique")
    return list(db["users"].list_indexes())


def main() -> None:
    db = get_db()
    indexes = run(db)
    print(f"Indexes on '{db['users'].name}':")
    for index in indexes:
        print(
            f"  - {index['name']}: key={dict(index['key'])} " f"unique={index.get('unique', False)}"
        )


if __name__ == "__main__":
    main()

from src.db.models.chat_memory import ChatMemory


def save_message(
    db,
    role: str,
    message: str
):

    memory = ChatMemory(
        role=role,
        message=message
    )

    db.add(memory)

    db.commit()


def get_recent_messages(
    db,
    limit: int = 10
):

    return db.query(ChatMemory)\
        .order_by(ChatMemory.id.desc())\
        .limit(limit)\
        .all()
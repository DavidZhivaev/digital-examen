from users.models import User


async def add_teachers(subject, users: list[User]):
    for u in users:
        await subject.teachers.add(u)


async def remove_teachers(subject, users: list[User]):
    for u in users:
        await subject.teachers.remove(u)
        await subject.admins.remove(u)


async def add_admins(subject, users: list[User]):
    for u in users:
        await subject.admins.add(u)
        await subject.teachers.add(u)


async def remove_admins(subject, users: list[User]):
    for u in users:
        await subject.admins.remove(u)
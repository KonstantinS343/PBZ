import database


async def check_class_existing(class_name):
    class_existing = database.get_objects(object='owl:Class')
    for i in class_existing:
        if i['subject'].split('/')[-1][:-1] == class_name:
            return True

    return False


async def get_full_info(name: str, type: str):
    query = database.get_objects(object=type)
    all_info = []
    for i in query:
        if i["subject"].split("/")[-1][:-1] == name:
            all_info.append(i)

    return all_info

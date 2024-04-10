import database
import asyncio

from typing import Dict


async def check_class_existing(class_name: str):
    class_existing = database.get_objects(object='owl:Class')
    for i in class_existing:
        if i['subject'].split('/')[-1][:-1] == class_name:
            return True

    return False


async def validate_input(args: Dict[str, str]):
    output = {
        'Class': False if 'Class' in args.keys() else True,
        'ObjectProperty': False if 'ObjectProperty' in args.keys() else True,
        'DatatypeProperty': False if 'DatatypeProperty' in args.keys() else True,
        'NamedIndividual': False if 'NamedIndividual' in args.keys() else True
    }

    for type_class, name in args.items():
        objects = database.get_objects(object='owl:' + type_class)
        for i in objects:
            if i['subject'].split('/')[-1][:-1] == name:
                output[type_class] = True
    print(output)
    return (True if all(output.values()) else False, output)


async def get_full_info(name: str, type: str):
    query = database.get_objects(object=type)
    all_info = []
    for i in query:
        if i["subject"].split("/")[-1][:-1] == name:
            all_info.append(i)
    print(*all_info, sep='\n')
    return all_info


asyncio.run(get_full_info('Антон', 'owl:NamedIndividual'))

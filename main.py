import uvicorn
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from starlette import status
from typing import Annotated

import database
from services import check_class_existing, get_full_info
from settings import HOST, APP_PORT

app = FastAPI()


@app.post("/file/upload/")
async def root(file: Annotated[UploadFile, File(description="Some description")]):
    """Функция заргузки файла."""
    await database.write_file(file)

    return JSONResponse(
        content={"filename": file.filename},
        status_code=status.HTTP_200_OK
    )

# GET


@app.get("/class/")
async def get_classes():
    """Функция возвращает все классы онтологии."""
    content = []

    query_result = database.execute_get_query(
        relation="rdf:type", object="owl:Class"
    )
    for item in query_result:
        content.append(item['subject'].split('/')[-1][:-1])

    return JSONResponse(
        content={"data": content},
        status_code=status.HTTP_200_OK
    )


@app.get("/class/subclasses/")
async def get_subclasses():
    """Функция возвращает все подклассы онтологии."""
    content = []

    query_result = database.execute_get_query(
        relation="rdfs:subClassOf"
    )

    for item in query_result:
        content.append(
            {
                "parent": item["object"].split('/')[-1][:-1],
                "subclass": item["subject"].split('/')[-1][:-1],
            }
        )

    return JSONResponse(
        content=content,
        status_code=status.HTTP_200_OK
    )


@app.get("/individuals/")
async def get_individual():
    """Функция возвращает всех индивидов онтологии."""
    content = []

    query_result = database.execute_get_individuals_query()
    for item in query_result:
        content.append(item['subject'].split('/')[-1][:-1])

    return JSONResponse(
        content={"data": content},
        status_code=status.HTTP_200_OK
    )


@app.get("/individual/{name}/")
async def get_individual_by_name(name: str):
    """Функция возвращает характеристику индивида по имени."""
    content = []

    query_result = database.execute_get_individuals_query(name=name)
    for item in query_result:
        subject = item["subject"].split('/')[-1][:-1]
        relation = item["relation"].split('/')[-1][:-1]
        if len(item["object"].split('^^')) == 2:
            try:
                object = float(item["object"].split('^^')[0][1:-1])
            except Exception:
                object = item["object"].split('^^')[0]
        else:
            object = item["object"].split('/')[-1][:-1]
        content.append([
            subject,
            relation,
            object
            ])

    return JSONResponse(
        content={"data": content},
        status_code=status.HTTP_200_OK
    )


@app.get("/object_property/")
async def get_object_property():
    """Функция возвращает все отношения между объектами в онтологии."""
    content = []

    query_result = database.execute_get_query(
        relation="rdf:type", object="owl:ObjectProperty"
    )

    for item in query_result:
        content.append(item['subject'].split('/')[-1][:-1])

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=content
    )


@app.get("/data_property/")
async def get_data_properties():
    """Функция возвращает все свойства в онтологии."""
    content = []

    query_result = database.execute_get_query(
        relation="rdf:type", object="owl:DatatypeProperty"
    )
    for item in query_result:
        content.append(item['subject'].split('/')[-1][:-1])

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=content
    )

# POST


@app.post("/data_property/create/")
async def create_data_property(data_property, domain, xs_range):
    """Функция создает свойство."""
    allows_range = ['xsd:decimal', 'xsd:int', 'xsd:string']
    if xs_range not in allows_range:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content='Check input args')
    data_property_existing = database.get_objects(object='owl:DatatypeProperty')
    for i in data_property_existing:
        if i['subject'].split('/')[-1][:-1] == data_property:
            return JSONResponse(status_code=status.HTTP_201_CREATED, content={})
    if not await check_class_existing(domain):
        return JSONResponse(content="Such class doen't exist.", status_code=status.HTTP_400_BAD_REQUEST)
    if database.execute_post_query(f"<{data_property}>", "rdf:type", "owl:DatatypeProperty") and \
       database.execute_post_query(f"<{data_property}>", "rdfs:domain", f"<{domain}>") and \
       database.execute_post_query(f"<{data_property}>", "rdfs:range", f"{xs_range}"):
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={}
        )

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={})


@app.post("/object_property/create/")
async def create_object_property(object_property, domain_1, domain_2):
    """Функция создает отношение между объектами."""
    data_property_existing = database.get_objects(object='owl:ObjectProperty')
    for i in data_property_existing:
        if i['subject'].split('/')[-1][:-1] == object_property:
            return JSONResponse(status_code=status.HTTP_201_CREATED, content={})
    if not await check_class_existing(domain_1):
        return JSONResponse(content="Such class doen't exist.", status_code=status.HTTP_400_BAD_REQUEST)
    if not await check_class_existing(domain_2):
        return JSONResponse(content="Such class doen't exist.", status_code=status.HTTP_400_BAD_REQUEST)
    if database.execute_post_query(f"<{object_property}>", "rdf:type", "owl:ObjectProperty") and \
       database.execute_post_query(f"<{object_property}>", "rdfs:domain", f"<{domain_1}>") and \
       database.execute_post_query(f"<{object_property}>", "rdfs:range", f"<{domain_2}>"):
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={}
        )

    return JSONResponse(content={}, status_code=status.HTTP_400_BAD_REQUEST)


@app.post("/subclass/create/")
async def create_subclass(classname, parent):
    """Функция создания нового подкласса."""
    parent_class = await check_class_existing(parent)
    child_class = await check_class_existing(classname) 
    if not parent_class:
        return JSONResponse(content="Such parent class doen't exist.", status_code=status.HTTP_400_BAD_REQUEST)
    if not child_class:
        database.execute_post_query(f"<{classname}>", "rdf:type", "owl:Class")
    else:
        database.execute_delete_query()
        database.execute_post_query(f"<{classname}>", "rdf:type", "owl:Class")
    if database.execute_post_query(f"<{classname}>", "rdfs:subClassOf", f"<{parent}>"):
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={}
        )

    return JSONResponse(content={}, status_code=status.HTTP_400_BAD_REQUEST)


@app.post("/classes/create/")
async def create_class(classname):
    """Функция создания нового класса."""
    if await check_class_existing(classname):
        return JSONResponse(content={}, status_code=status.HTTP_200_OK)
    if database.execute_post_query(f"<{classname}>", "rdf:type", "owl:Class"):
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={}
        )

    return JSONResponse(content={}, status_code=status.HTTP_400_BAD_REQUEST)


@app.post("/instance/create/")
async def create_instance(instance_name, instance_type):
    """Функция создания нового индивида."""
    instances = database.execute_get_individuals_query()
    for i in instances:
        if i['subject'].split('/')[-1][:-1] == instance_name:
            return JSONResponse(content="Such instance already exist.", status_code=status.HTTP_400_BAD_REQUEST)
    if not await check_class_existing(instance_type):
        return JSONResponse(content="Such class doen't exist.", status_code=status.HTTP_400_BAD_REQUEST)
    if database.execute_post_query(f"<{instance_name}>", "rdf:type", "owl:NamedIndividual"):
        database.execute_post_query(f"<{instance_name}>", "rdf:type", f"owl:{instance_type}")
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={}
        )

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={})


@app.post("/property/connect/")
async def add_property_to_class(subject, property, object_class):
    """Функция соединяет класс и свойство."""
    if database.execute_post_query(f"<{subject}>", f"<{property}>", f"<{object_class}>"):
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={}
        )

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={})


@app.post("/object_property/rename/")
async def object_property_rename(object_property_name, new_object_property_name):
    all_info = await get_full_info(object_property_name, 'owl:ObjectProperty')
    metainfo = {
        'type': 'rdf:type',
        'range': 'rdfs:range',
        'domain': 'rdfs:domain',
        'ObjectProperty': 'owl:ObjectProperty'
    }
    for i in all_info:
        if i["relation"].split("#")[1][:-1] == 'type':
            database.execute_delete_query(f'<{i["subject"].split("/")[-1][:-1]}>',
                                          metainfo[f'{i["relation"].split("#")[1][:-1]}'],
                                          metainfo[f'{i["object"].split("#")[1][:-1]}'])
            database.execute_post_query(f'<{new_object_property_name}>',
                                        metainfo[f'{i["relation"].split("#")[1][:-1]}'],
                                        metainfo[f'{i["object"].split("#")[1][:-1]}'])
        else:
            database.execute_delete_query(f'<{i["subject"].split("/")[-1][:-1]}>',
                                          metainfo[f'{i["relation"].split("#")[1][:-1]}'],
                                          f'<{i["object"].split("/")[-1][:-1]}>')
            database.execute_post_query(f'<{new_object_property_name}>',
                                        metainfo[f'{i["relation"].split("#")[1][:-1]}'],
                                        f'<{i["object"].split("/")[-1][:-1]}>')

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={})


@app.post("/class/rename/")
async def rename_class(classname, new_name):
    database.execute_delete_query(f"<{classname}>", "rdf:type", "owl:Class")
    database.execute_post_query(f"<{new_name}>", "rdf:type", "owl:Class")

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={})


@app.post("/instance/rename")
async def rename_instance(instance_name, new_name):
    database.execute_delete_query(f"<{instance_name}>", "rdf:type", "owl:NamedIndividual")
    database.execute_post_query(f"<{new_name}>", "rdf:type", "owl:NamedIndividual")

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={})

# DELETE


@app.delete("/data_property/delete/")
async def delete_data_property(data_property):
    database.execute_delete_query(f":{data_property}", "rdf:type", "owl:DatatypeProperty")

    return JSONResponse(
        content={"result": "property was deleted"},
        status_code=status.HTTP_204_NO_CONTENT
    )


@app.delete("/class/delete")
async def delete_class(subject_class):
    """delete class"""
    if database.execute_delete_query(f"<{subject_class}>", "rdf:type", "owl:Class"):
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content={}
        )

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={})


@app.delete("/subclasses/delete")
async def delete_subclass(subclass_name, parent):
    """delete class"""
    if database.execute_delete_query(f"<{subclass_name}>", "rdfs:subClassOf", f"<{parent}>"):
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content={}
        )

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={})


@app.delete("/object_property/delete/")
async def delete_object_property(object_property):
    """delete object property"""
    if database.execute_delete_query(f":{object_property}", "rdf:type", "owl:ObjectProperty"):
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content={}
        )

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={})


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=int(APP_PORT),
        lifespan="on",
    )





#@app.get("/class/individual/")
#async def get_individual_by_class():
#    """Функция возвращает индивидов класса."""
#    content = []
#
#    query_result = database.execute_get_individuals_query()
#    for item in query_result:
#        subject = item["subject"].split('/')[-1][:-1]
#        object = item["object"].split('/')[-1][:-1]
#        content.append({
#            'instance': subject,
#            })
#
#    return JSONResponse(
#        content={"data": content},
#        status_code=status.HTTP_200_OK
#    )
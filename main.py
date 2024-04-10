import uvicorn
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import JSONResponse
from starlette import status
from typing import Annotated

import database
from services import check_class_existing, get_full_info, validate_input
from settings import HOST, APP_PORT
from template import object_property_template, class_template, data_property_template, instance_template

app = FastAPI()


@app.post("/file/upload/")
async def root(file: Annotated[UploadFile, File(description="Some description")]):
    """Функция заргузки файла."""
    await database.write_file(file)

    return JSONResponse(
        content={"filename": file.filename}, status_code=status.HTTP_200_OK
    )


# GET


@app.get("/class/")
async def get_classes():
    """Функция возвращает все классы онтологии."""
    content = []

    query_result = database.execute_get_query(relation="rdf:type", object="owl:Class")
    for item in query_result:
        content.append(item["subject"].split("/")[-1][:-1])

    return JSONResponse(content={"data": content}, status_code=status.HTTP_200_OK)


@app.get("/class/subclasses/")
async def get_subclasses():
    """Функция возвращает все подклассы онтологии."""
    content = []

    query_result = database.execute_get_query(relation="rdfs:subClassOf")

    for item in query_result:
        content.append(
            {
                "parent": item["object"].split("/")[-1][:-1],
                "subclass": item["subject"].split("/")[-1][:-1],
            }
        )

    return JSONResponse(content=content, status_code=status.HTTP_200_OK)


@app.get("/individuals/")
async def get_individual():
    """Функция возвращает всех индивидов онтологии."""
    content = []

    query_result = database.execute_get_individuals_query()
    for item in query_result:
        content.append(item["subject"].split("/")[-1][:-1])

    return JSONResponse(content={"data": content}, status_code=status.HTTP_200_OK)


@app.get("/individual/{name}/")
async def get_individual_by_name(name: str):
    """Функция возвращает характеристику индивида по имени."""
    content = []

    query_result = database.execute_get_individuals_query(name=name)
    for item in query_result:
        subject = item["subject"].split("/")[-1][:-1]
        item_dict = {
            'class': subject,
        }
        relation = item["relation"].split("/")[-1][:-1]
        if len(item["object"].split("^^")) == 2:
            try:
                object = float(item["object"].split("^^")[0][1:-1])
            except Exception:
                object = item["object"].split("^^")[0]
            item_dict.update({
                'data_property': relation,
                'value': object
            })
        else:
            object = item["object"].split("/")[-1][:-1]
            item_dict.update({
                'object_property': relation,
                'other_class': object
            })
        content.append([item_dict])

    return JSONResponse(content={"data": content}, status_code=status.HTTP_200_OK)


@app.get("/object_property/")
async def get_object_property():
    """Функция возвращает все отношения между объектами в онтологии."""
    content = []

    query_result = database.execute_get_query(
        relation="rdf:type", object="owl:ObjectProperty"
    )

    for item in query_result:
        content.append(item["subject"].split("/")[-1][:-1])

    return JSONResponse(status_code=status.HTTP_200_OK, content=content)


@app.get("/data_property/")
async def get_data_properties():
    """Функция возвращает все свойства в онтологии."""
    content = []

    query_result = database.execute_get_query(
        relation="rdf:type", object="owl:DatatypeProperty"
    )
    for item in query_result:
        content.append(item["subject"].split("/")[-1][:-1])

    return JSONResponse(status_code=status.HTTP_200_OK, content=content)


# POST


@app.post("/data_property/create/")
async def create_data_property(
    data_property: str = Query(..., min_length=1),
    domain: str = Query(..., min_length=1),
    xs_range: str = Query(..., min_length=1),
):
    """Функция создает свойство."""
    allows_range = ["xsd:decimal", "xsd:int", "xsd:string"]
    if xs_range not in allows_range:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content="Check input args"
        )
    validation = await validate_input({
        'DatatypeProperty': data_property,
        'Class': domain
    })
    if not validation[0]:
        return JSONResponse(
            content="Check input args", status_code=status.HTTP_400_BAD_REQUEST
        )
    if validation[1]['DatatypeProperty']:
        return JSONResponse(
            content="Check input args", status_code=status.HTTP_400_BAD_REQUEST
        )
    if (
        database.execute_post_query(
            f"<{data_property}>", "rdf:type", "owl:DatatypeProperty"
        )
        and database.execute_post_query(
            f"<{data_property}>", "rdfs:domain", f"<{domain}>"
        )
        and database.execute_post_query(
            f"<{data_property}>", "rdfs:range", f"{xs_range}"
        )
    ):
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={})

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={})


@app.post("/object_property/create/")
async def create_object_property(
    object_property: str = Query(..., min_length=1),
    domain_1: str = Query(..., min_length=1),
    domain_2: str = Query(..., min_length=1),
):
    """Функция создает отношение между объектами."""
    validation = await validate_input({
        'ObjectProperty': object_property,
    })
    if validation[1]['ObjectProperty']:
        return JSONResponse(
            content="Check input args", status_code=status.HTTP_400_BAD_REQUEST
        )
    if not await check_class_existing(domain_1):
        return JSONResponse(
            content="Such class doen't exist.", status_code=status.HTTP_400_BAD_REQUEST
        )
    if not await check_class_existing(domain_2):
        return JSONResponse(
            content="Such class doen't exist.", status_code=status.HTTP_400_BAD_REQUEST
        )
    if (
        database.execute_post_query(
            f"<{object_property}>", "rdf:type", "owl:ObjectProperty"
        )
        and database.execute_post_query(
            f"<{object_property}>", "rdfs:domain", f"<{domain_1}>"
        )
        and database.execute_post_query(
            f"<{object_property}>", "rdfs:range", f"<{domain_2}>"
        )
    ):
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={})

    return JSONResponse(content={}, status_code=status.HTTP_400_BAD_REQUEST)


@app.post("/subclass/create/")
async def create_subclass(
    classname: str = Query(..., min_length=1), parent: str = Query(..., min_length=1)
):
    """Функция создания нового подкласса."""
    parent_class = await check_class_existing(parent)
    child_class = await check_class_existing(classname)
    if not parent_class:
        return JSONResponse(
            content="Such parent class doen't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if not child_class:
        database.execute_post_query(f"<{classname}>", "rdf:type", "owl:Class")
    else:
        database.execute_delete_query()
        database.execute_post_query(f"<{classname}>", "rdf:type", "owl:Class")
    if database.execute_post_query(f"<{classname}>", "rdfs:subClassOf", f"<{parent}>"):
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={})

    return JSONResponse(content={}, status_code=status.HTTP_400_BAD_REQUEST)


@app.post("/classes/create/")
async def create_class(classname: str = Query(..., min_length=1)):
    """Функция создания нового класса."""
    if await check_class_existing(classname):
        return JSONResponse(content={}, status_code=status.HTTP_200_OK)
    if database.execute_post_query(f"<{classname}>", "rdf:type", "owl:Class"):
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={})

    return JSONResponse(content={}, status_code=status.HTTP_400_BAD_REQUEST)


@app.post("/instance/create/")
async def create_instance(
    instance_name: str = Query(..., min_length=1),
    instance_type: str = Query(..., min_length=1),
):
    """Функция создания нового индивида."""
    validation = await validate_input({
        'NamedIndividual': instance_name,
    })
    if validation[1]['NamedIndividual']:
        return JSONResponse(
            content="Check input args", status_code=status.HTTP_400_BAD_REQUEST
        )
    if not await check_class_existing(instance_type):
        return JSONResponse(
            content="Such class doen't exist.", status_code=status.HTTP_400_BAD_REQUEST
        )
    if database.execute_post_query(
        f"<{instance_name}>", "rdf:type", "owl:NamedIndividual"
    ):
        database.execute_post_query(
            f"<{instance_name}>", "rdf:type", f"<{instance_type}>"
        )
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={})

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={})


@app.post("/property/connect/")
async def add_property_to_instance(
    value_type: str,
    type_property: str = Query(..., min_length=1),
    subject: str = Query(..., min_length=1),
    property: str = Query(..., min_length=1),
    object_class: str = Query(..., min_length=1),
):
    """Функция соединяет инстанс и свойство."""
    allows_range = ["xsd:decimal", "xsd:int", "xsd:string"]
    if value_type not in allows_range:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content="Check input args"
        )
    validation = await validate_input({
        'NamedIndividual': subject,
        type_property: property
    })
    if not validation[0]:
        return JSONResponse(
            content="Check input args", status_code=status.HTTP_400_BAD_REQUEST
        )
    if type_property == 'ObjectProperty':
        validation = await validate_input({
            'NamedIndividual': subject
        })
        if not validation[0]:
            return JSONResponse(
                content="Check input args", status_code=status.HTTP_400_BAD_REQUEST
            )
        if database.execute_post_query(
            f"<{subject}>", f"<{property}>", f"<{object_class}>"
        ):
            return JSONResponse(status_code=status.HTTP_201_CREATED, content={})
    elif type_property == 'DatatypeProperty':
        if database.execute_post_query(
            f"<{subject}>", f"<{property}>", f'"{object_class}"^^{value_type}'
        ):
            return JSONResponse(status_code=status.HTTP_201_CREATED, content={})

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content="Check input args")


@app.post("/object_property/rename/")
async def object_property_rename(
    object_property_name: str = Query(..., min_length=1),
    new_object_property_name: str = Query(..., min_length=1),
):
    """Функция изменения имени свойчтва между объектами."""
    all_info = await get_full_info(object_property_name, "owl:ObjectProperty")
    if not all_info:
        return JSONResponse(
            content="Such property doen't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    for i in all_info:
        if i["relation"].split("#")[1][:-1] == "type":
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                object_property_template[f'{i["relation"].split("#")[1][:-1]}'],
                object_property_template[f'{i["object"].split("#")[1][:-1]}'],
            )
            database.execute_post_query(
                f"<{new_object_property_name}>",
                object_property_template[f'{i["relation"].split("#")[1][:-1]}'],
                object_property_template[f'{i["object"].split("#")[1][:-1]}'],
            )
        else:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                object_property_template[f'{i["relation"].split("#")[1][:-1]}'],
                f'<{i["object"].split("/")[-1][:-1]}>',
            )
            database.execute_post_query(
                f"<{new_object_property_name}>",
                object_property_template[f'{i["relation"].split("#")[1][:-1]}'],
                f'<{i["object"].split("/")[-1][:-1]}>',
            )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={})


@app.post("/class/rename/")
async def class_rename(
    class_name: str = Query(..., min_length=1),
    new_class_name: str = Query(..., min_length=1),
):
    """Функция изменения имени класса."""
    all_info = await get_full_info(class_name, "owl:Class")
    if not all_info:
        return JSONResponse(
            content="Such class doen't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    for i in all_info:
        if i["relation"].split("#")[1][:-1] == "type":
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                class_template[f'{i["relation"].split("#")[1][:-1]}'],
                class_template[f'{i["object"].split("#")[1][:-1]}'],
            )
            database.execute_post_query(
                f"<{new_class_name}>",
                class_template[f'{i["relation"].split("#")[1][:-1]}'],
                class_template[f'{i["object"].split("#")[1][:-1]}'],
            )
        else:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                class_template[f'{i["relation"].split("#")[1][:-1]}'],
                f'<{i["object"].split("/")[-1][:-1]}>',
            )
            database.execute_post_query(
                f"<{new_class_name}>",
                class_template[f'{i["relation"].split("#")[1][:-1]}'],
                f'<{i["object"].split("/")[-1][:-1]}>',
            )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={})


@app.post("/instance/rename/")
async def instance_rename(instance_name, new_instance_name):
    all_info = await get_full_info(instance_name, "owl:NamedIndividual")
    if not all_info:
        return JSONResponse(
            content="Such class doen't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    for i in all_info:
        object = None
        relation = None
        try:
            relation = i["relation"].split("#")[1][:-1]
        except Exception:
            pass
        try:
            object = i["object"].split("#")[1][:-1]
        except Exception:
            pass
        if relation and object:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                instance_template[f'{i["relation"].split("#")[1][:-1]}'],
                instance_template[f'{i["object"].split("#")[1][:-1]}'],
            )
            database.execute_post_query(
                f"<{new_instance_name}>",
                instance_template[f'{i["relation"].split("#")[1][:-1]}'],
                instance_template[f'{i["object"].split("#")[1][:-1]}'],
            )
        elif not object and relation:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                instance_template[f'{i["relation"].split("#")[1][:-1]}'],
                f'<{i["object"].split("/")[-1][:-1]}>',
            )
            database.execute_post_query(
                f"<{new_instance_name}>",
                instance_template[f'{i["relation"].split("#")[1][:-1]}'],
                f'<{i["object"].split("/")[-1][:-1]}>',
            )
        elif not relation and object:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                f'<{i["relation"].split("/")[-1][:-1]}>',
                f'"{i["object"].split("^^")[0][1:-1]}"^^{data_property_template[i["object"].split("#")[-1][:-1]]}',
            )
            database.execute_post_query(
                f"<{new_instance_name}>",
                f'<{i["relation"].split("/")[-1][:-1]}>',
                f'"{i["object"].split("^^")[0][1:-1]}"^^{data_property_template[i["object"].split("#")[-1][:-1]]}',
            )
        else:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                f'<{i["relation"].split("/")[-1][:-1]}>',
                f'<{i["object"].split("/")[-1][:-1]}>',
            )
            database.execute_post_query(
                f"<{new_instance_name}>",
                f'<{i["relation"].split("/")[-1][:-1]}>',
                f'<{i["object"].split("/")[-1][:-1]}>',
            )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={})


@app.post("/data_property/rename/")
async def data_property_rename(data_property_name, new_data_property_name):
    """Функция изменения свойства."""
    all_info = await get_full_info(data_property_name, "owl:DatatypeProperty")
    if not all_info:
        return JSONResponse(
            content="Such property doen't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    for i in all_info:
        if (
            i["relation"].split("#")[1][:-1] == "type"
            or i["relation"].split("#")[1][:-1] == "range"
        ):
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                data_property_template[f'{i["relation"].split("#")[1][:-1]}'],
                data_property_template[f'{i["object"].split("#")[1][:-1]}'],
            )
            database.execute_post_query(
                f"<{new_data_property_name}>",
                data_property_template[f'{i["relation"].split("#")[1][:-1]}'],
                data_property_template[f'{i["object"].split("#")[1][:-1]}'],
            )
        else:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                data_property_template[f'{i["relation"].split("#")[1][:-1]}'],
                f'<{i["object"].split("/")[-1][:-1]}>',
            )
            database.execute_post_query(
                f"<{new_data_property_name}>",
                data_property_template[f'{i["relation"].split("#")[1][:-1]}'],
                f'<{i["object"].split("/")[-1][:-1]}>',
            )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={})


# DELETE


@app.delete("/data_property/delete/")
async def delete_data_property(data_property):
    """Функция удаления свойства."""
    all_info = await get_full_info(data_property, "owl:DatatypeProperty")
    if not all_info:
        return JSONResponse(
            content="Such property doen't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    for i in all_info:
        if (
            i["relation"].split("#")[1][:-1] == "type"
            or i["relation"].split("#")[1][:-1] == "range"
        ):
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                data_property_template[f'{i["relation"].split("#")[1][:-1]}'],
                data_property_template[f'{i["object"].split("#")[1][:-1]}'],
            )
        else:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                data_property_template[f'{i["relation"].split("#")[1][:-1]}'],
                f'<{i["object"].split("/")[-1][:-1]}>',
            )
    return JSONResponse(
        content={},
        status_code=status.HTTP_204_NO_CONTENT,
    )


@app.delete("/class/delete")
async def delete_class(subject_class):
    """Функция удаления класса."""
    all_info = await get_full_info(subject_class, "owl:Class")
    if not all_info:
        return JSONResponse(
            content="Such class doen't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    for i in all_info:
        if i["relation"].split("#")[1][:-1] == "type":
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                class_template[f'{i["relation"].split("#")[1][:-1]}'],
                class_template[f'{i["object"].split("#")[1][:-1]}'],
            )
        else:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                class_template[f'{i["relation"].split("#")[1][:-1]}'],
                f'<{i["object"].split("/")[-1][:-1]}>',
            )
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={})


@app.delete("/object_property/delete/")
async def delete_object_property(object_property):
    """delete object property"""
    all_info = await get_full_info(object_property, "owl:ObjectProperty")
    if not all_info:
        return JSONResponse(
            content="Such property doen't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    for i in all_info:
        if i["relation"].split("#")[1][:-1] == "type":
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                object_property_template[f'{i["relation"].split("#")[1][:-1]}'],
                object_property_template[f'{i["object"].split("#")[1][:-1]}'],
            )
        else:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                object_property_template[f'{i["relation"].split("#")[1][:-1]}'],
                f'<{i["object"].split("/")[-1][:-1]}>',
            )

    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={})


@app.delete("/instance/delete/")
async def delete_instance(instance_name):
    """Функция удаления инстанса."""
    all_info = await get_full_info(instance_name, "owl:DatatypeProperty")
    if not all_info:
        return JSONResponse(
            content="Such instance doen't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    for i in all_info:
        object = None
        relation = None
        try:
            relation = i["relation"].split("#")[1][:-1]
        except Exception:
            pass
        try:
            object = i["object"].split("#")[1][:-1]
        except Exception:
            pass
        if relation and object:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                instance_template[f'{i["relation"].split("#")[1][:-1]}'],
                instance_template[f'{i["object"].split("#")[1][:-1]}'],
            )
        elif not object and relation:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                instance_template[f'{i["relation"].split("#")[1][:-1]}'],
                f'<{i["object"].split("/")[-1][:-1]}>',
            )
        elif not relation and object:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                f'<{i["relation"].split("/")[-1][:-1]}>',
                f'"{i["object"].split("^^")[0][1:-1]}"^^{data_property_template[i["object"].split("#")[-1][:-1]]}',
            )
        else:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                f'<{i["relation"].split("/")[-1][:-1]}>',
                f'<{i["object"].split("/")[-1][:-1]}>',
            )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={})


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=int(APP_PORT),
        lifespan="on",
    )


# @app.get("/class/individual/")
# async def get_individual_by_class():
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

import uvicorn
from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import JSONResponse, Response
from starlette import status
from typing import Annotated

import database
from services import check_class_existing, get_full_info, validate_input
from settings import HOST, APP_PORT
from template import object_property_template, class_template, data_property_template, instance_template

app = FastAPI()


@app.post("/file/upload/") # Done
async def root(file: Annotated[UploadFile, File(description="Some description")]):
    """Функция заргузки файла."""
    await database.write_file(file)

    return JSONResponse(
        content={"filename": file.filename}, status_code=status.HTTP_200_OK
    )


# GET


@app.get("/class/") # Done
async def get_classes():
    """Функция возвращает все классы онтологии."""
    content = []

    query_result = database.execute_get_query(relation="rdf:type", object="owl:Class")
    for item in query_result:
        content.append(item["subject"].split("/")[-1][:-1])

    return JSONResponse(content={"data": content}, status_code=status.HTTP_200_OK)


@app.get("/class/subclasses/") # Done
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


@app.get("/individuals/") # Done
async def get_individual():
    """Функция возвращает всех индивидов онтологии."""
    content = []

    query_result = database.execute_get_individuals_query()
    for item in query_result:
        content.append(item["subject"].split("/")[-1][:-1])

    return JSONResponse(content={"data": content}, status_code=status.HTTP_200_OK)


@app.get("/individual/{name}/") # Done
async def get_individual_by_name(name: str):
    """Функция возвращает характеристику индивида по имени."""
    content = []
    validation = await validate_input({
        'NamedIndividual': name,
    })
    if not validation[0]:
        return JSONResponse(
            content="Such individual doesn't exist.", status_code=status.HTTP_400_BAD_REQUEST
        )

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
        content.append(item_dict)

    individual_class = None

    for i in database.execute_get_query():
        if i["subject"].split("/")[-1][:-1] == name and \
           not i["object"].split("/")[-1][:-1].startswith('owl') and \
           i["relation"].split("#")[1][:-1] == 'type':
            individual_class = i["object"].split("/")[-1][:-1]
            break

    for i in content:
        i['class'] = individual_class

    return JSONResponse(content={"data": content}, status_code=status.HTTP_200_OK)


@app.get("/object_property/") # Done
async def get_object_property():
    """Функция возвращает все отношения между объектами в онтологии."""
    content = []

    query_result = database.execute_get_query(
        relation="rdf:type", object="owl:ObjectProperty"
    )
    for item in query_result:
        dict_item = {}
        for i in database.execute_get_query():
            if i["subject"].split("/")[-1][:-1] == item["subject"].split("/")[-1][:-1]:
                if i["relation"].split("#")[1][:-1] == 'type':
                    dict_item['property'] = item["subject"].split("/")[-1][:-1]
                elif i["relation"].split("#")[1][:-1] == 'domain':
                    dict_item['domain'] = i["object"].split("/")[-1][:-1]
                else:
                    dict_item['range'] = i["object"].split("/")[-1][:-1]
        content.append(dict_item.copy())
        dict_item.clear()

    return JSONResponse(status_code=status.HTTP_200_OK, content=content)


@app.get("/data_property/") # Done
async def get_data_properties():
    """Функция возвращает все свойства в онтологии."""
    content = []

    query_result = database.execute_get_query(
        relation="rdf:type", object="owl:DatatypeProperty"
    )
    for item in query_result:
        dict_item = {}
        for i in database.execute_get_query():
            if i["subject"].split("/")[-1][:-1] == item["subject"].split("/")[-1][:-1]:
                if i["relation"].split("#")[1][:-1] == 'type':
                    dict_item['property'] = item["subject"].split("/")[-1][:-1]
                elif i["relation"].split("#")[1][:-1] == 'domain':
                    dict_item['domain'] = i["object"].split("/")[-1][:-1]
                else:
                    dict_item['range'] = 'xsd:' + i["object"].split("#")[1][:-1]
        content.append(dict_item.copy())
        dict_item.clear()

    return JSONResponse(status_code=status.HTTP_200_OK, content=content)


# POST


@app.post("/data_property/create/") # Done
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
    if not validation[1]['Class']:
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


@app.post("/object_property/create/") # Done
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
            content="Such class doesn't exist.", status_code=status.HTTP_400_BAD_REQUEST
        )
    if not await check_class_existing(domain_2):
        return JSONResponse(
            content="Such class doesn't exist.", status_code=status.HTTP_400_BAD_REQUEST
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


@app.post("/subclass/create/") # Done
async def create_subclass(
    classname: str = Query(..., min_length=1), parent: str = Query(..., min_length=1)
):
    """Функция создания нового подкласса."""
    parent_class = await check_class_existing(parent)
    child_class = await check_class_existing(classname)
    if not parent_class:
        return JSONResponse(
            content="Such parent class doesn't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if not child_class:
        database.execute_post_query(f"<{classname}>", "rdf:type", "owl:Class")
    else:
        await delete_class(child_class)
        database.execute_post_query(f"<{classname}>", "rdf:type", "owl:Class")
    if database.execute_post_query(f"<{classname}>", "rdfs:subClassOf", f"<{parent}>"):
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={})

    return JSONResponse(content={}, status_code=status.HTTP_400_BAD_REQUEST)


@app.post("/classes/create/") # Done
async def create_class(classname: str = Query(..., min_length=1)):
    """Функция создания нового класса."""
    if await check_class_existing(classname):
        return JSONResponse(content={}, status_code=status.HTTP_200_OK)
    if database.execute_post_query(f"<{classname}>", "rdf:type", "owl:Class"):
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={})

    return JSONResponse(content={}, status_code=status.HTTP_400_BAD_REQUEST)


@app.post("/instance/create/") # Done
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
            content="Such class doesn't exist.", status_code=status.HTTP_400_BAD_REQUEST
        )
    if database.execute_post_query(
        f"<{instance_name}>", "rdf:type", "owl:NamedIndividual"
    ):
        database.execute_post_query(
            f"<{instance_name}>", "rdf:type", f"<{instance_type}>"
        )
        return JSONResponse(status_code=status.HTTP_201_CREATED, content={})

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={})


@app.post("/property/connect/") # Done
async def add_property_to_instance(
    value_type: str = None,
    type_property: str = Query(..., min_length=1),
    subject: str = Query(..., min_length=1),
    property: str = Query(..., min_length=1),
    object_class: str = Query(..., min_length=1),
):
    """Функция соединяет инстанс и свойство."""
    allows_range = ["xsd:decimal", "xsd:int", "xsd:string"]
    if value_type not in allows_range and type_property == 'DatatypeProperty':
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
            'NamedIndividual': object_class
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


# DELETE


@app.delete("/data_property/delete/") # Done
async def delete_data_property(data_property):
    """Функция удаления свойства."""
    all_info = await get_full_info(data_property, "owl:DatatypeProperty")
    if not all_info:
        return JSONResponse(
            content="Such property doesn't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    individuals = set()
    for i in database.execute_get_query():
        if i["relation"].split("/")[-1][:-1] == data_property:
            individuals.add(i["subject"].split("/")[-1][:-1])
    for i in individuals:
        await instance_delete_data_property(data_property, i)
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
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/instance/data_property/delete/")
async def instance_delete_data_property(data_property, individual_name):
    """Функция удаления свойства у индивида."""
    all_info = await get_full_info(individual_name, "owl:NamedIndividual")
    if not all_info:
        return JSONResponse(
            content="Such individual doesn't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    validation = await validate_input({
        'DatatypeProperty': data_property,
    })
    if not validation[0]:
        return JSONResponse(
            content="Check input args", status_code=status.HTTP_400_BAD_REQUEST
        )
    for i in all_info:
        if i["relation"].split("/")[-1][:-1] == data_property:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                f'<{i["relation"].split("/")[-1][:-1]}>',
                f'"{i["object"].split("^^")[0][1:-1]}"^^{data_property_template[i["object"].split("#")[-1][:-1]]}',
            )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/class/delete") # Done
async def delete_class(subject_class):
    """Функция удаления класса."""
    all_info = await get_full_info(subject_class, "owl:Class")
    if not all_info:
        return JSONResponse(
            content="Such class doesn't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    individuals = set()
    for i in database.execute_get_query():
        if i["object"].split("/")[-1][:-1] == subject_class:
            individuals.add(i["subject"].split("/")[-1][:-1])
    for i in individuals:
        await delete_instance(i)
    for i in database.execute_get_query():
        if i["object"].split("/")[-1][:-1] == subject_class:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                class_template[f'{i["relation"].split("#")[1][:-1]}'],
                f'<{i["object"].split("/")[-1][:-1]}>',
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
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/object_property/delete/") # Done
async def delete_object_property(object_property):
    """delete object property"""
    all_info = await get_full_info(object_property, "owl:ObjectProperty")
    if not all_info:
        return JSONResponse(
            content="Such property doesn't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    individuals = set()
    for i in database.execute_get_query():
        if i["relation"].split("/")[-1][:-1] == object_property:
            individuals.add(i["subject"].split("/")[-1][:-1])
            individuals.add(i["object"].split("/")[-1][:-1])
    for i in individuals:
        await instance_delete_object_property(object_property, i)
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

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/instance/object_property/delete/") # Done
async def instance_delete_object_property(object_property, individual_name):
    """Функция удаления свойства у индивида."""
    all_info = await get_full_info(individual_name, "owl:NamedIndividual")
    if not all_info:
        return JSONResponse(
            content="Such individual doesn't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    validation = await validate_input({
        'ObjectProperty': object_property,
    })
    if not validation[0]:
        return JSONResponse(
            content="Check input args", status_code=status.HTTP_400_BAD_REQUEST
        )
    for i in all_info:
        if i["relation"].split("/")[-1][:-1] == object_property:
            database.execute_delete_query(
                f'<{i["subject"].split("/")[-1][:-1]}>',
                f'<{i["relation"].split("/")[-1][:-1]}>',
                f'<{i["object"].split("/")[-1][:-1]}>',
            )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/instance/delete/") # Done
async def delete_instance(instance_name):
    """Функция удаления инстанса."""
    all_info = await get_full_info(instance_name, "owl:NamedIndividual")
    if not all_info:
        return JSONResponse(
            content="Such instance doesn't exist.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    individuals = set()
    for i in database.execute_get_query():
        if i["object"].split("/")[-1][:-1] == instance_name:
            individuals.add((i["subject"].split("/")[-1][:-1], i["relation"].split("/")[-1][:-1]))
    for i in individuals:
        await instance_delete_object_property(i[1], i[0])
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

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/delete/all") # Done
async def delete_all():
    """Функция удаления всего."""
    database.delete_all()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=int(APP_PORT),
        lifespan="on",
    )

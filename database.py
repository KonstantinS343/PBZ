from franz.openrdf.repository import Repository
from franz.openrdf.sail import AllegroGraphServer
from fastapi import UploadFile
from typing import Optional
import settings

import re


server = AllegroGraphServer(
    host=settings.HOST,
    port=settings.PORT,
    user=settings.USER,
    password=settings.PASSWORD,
)

catalog = server.openCatalog(settings.CATALOG_NAME)

repository = catalog.getRepository(settings.REPOSITORY_NAME, Repository.ACCESS)


def add_file_to_rep(filename: str):
    with repository.getConnection() as connection:
        connection.addFile(settings.OWL_FILES_STORAGE + filename)


def handle_file(filename: str):
    with open(settings.OWL_FILES_STORAGE + filename, "r") as f:
        content = f.read()
    exception_list = ['http://www.w3.org/2001/XMLSchema#', 'https://github.com/owlcs/owlapi', "http://www.w3.org/2002/07/owl#",
                      "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "http://www.w3.org/XML/1998/namespace", "http://www.w3.org/2000/01/rdf-schema#"]
    url = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+#?', content)
    url2 = set()
    for i in url:
        if i not in exception_list:
            url2.add(i)
    url2 = sorted(list(url2), key=lambda x: len(x), reverse=True)

    for i in url2:
        content = content.replace(i, f'http://127.0.0.1:10035/repositories/{settings.REPOSITORY_NAME}/')
    with open(settings.OWL_FILES_STORAGE + filename, "w") as f:
        f.write(content)


async def write_file(file: Optional[UploadFile]) -> bool:
    if file is None:
        return False

    with open(settings.OWL_FILES_STORAGE + file.filename, "wb") as created_file:
        content = await file.read()
        created_file.write(content)
        created_file.close()
    handle_file(file.filename)
    add_file_to_rep(file.filename)

    return True


def execute_get_query(subject="?s", relation="?r", object="?o"):
    """select query for get endpoints"""
    query_string = "SELECT distinct ?s ?r ?o WHERE {%s %s %s}" % (subject, relation, object)
    result_list = []

    with repository.getConnection() as connection:
        result = connection.executeTupleQuery(query=query_string)

        with result:
            for bindung_set in result:
                result_list.append(
                    {
                        "subject": bindung_set.getValue("s").__str__(),
                        "relation": bindung_set.getValue("r").__str__(),
                        "object": bindung_set.getValue("o").__str__(),
                    }
                )

    return result_list


def get_objects(object):
    query = "SELECT distinct ?s ?r ?o WHERE {?s ?r ?o . ?s a %s}" % (object)
    result_list = []

    with repository.getConnection() as connection:
        result = connection.executeTupleQuery(query=query)

    with result:
        for bindung_set in result:
            result_list.append(
                {
                    "subject": bindung_set.getValue("s").__str__(),
                    "relation": bindung_set.getValue("r").__str__(),
                    "object": bindung_set.getValue("o").__str__(),
                }
            )

    return result_list


def execute_get_individuals_query(name=None, class_name=None):
    if name:
        query_string = """SELECT distinct ?s ?r ?o WHERE {?s ?r ?o . ?s a owl:NamedIndividual FILTER(?r != rdf:type)}"""
    elif class_name:
        query_string = """SELECT distinct ?s ?r ?o WHERE {?s ?r ?o . ?s a owl:NamedIndividual}"""
    else:
        query_string = """SELECT distinct ?s WHERE {?s ?r ?o . ?s a owl:NamedIndividual}"""
    result_list = []

    with repository.getConnection() as connection:
        result = connection.executeTupleQuery(query=query_string)
        with result:
            for bindung_set in result:
                if name or class_name:
                    request = {
                        "subject": bindung_set.getValue("s").__str__(),
                        "relation": bindung_set.getValue("r").__str__(),
                        "object": bindung_set.getValue("o").__str__(),
                    }
                else:
                    request = {"subject": bindung_set.getValue("s").__str__()}
                result_list.append(request)
    result = []
    if name:
        for i in result_list:
            if i["subject"].split("/")[-1][:-1] == name:
                result.append(i)
        result_list = result
    elif class_name:
        for i in result_list:
            if i["object"].split("/")[-1][:-1] == class_name and i["relation"].split("#")[1][:-1] == 'type':
                result.append(i)
        result_list = result
    return result_list


def execute_post_query(subject, relation, object):
    string_query = "INSERT DATA { %s %s %s}" % (subject, relation, object)

    with repository.getConnection() as connection:
        return connection.executeUpdate(query=string_query)


def execute_delete_query(subject, predicate, object):
    string_query = "DELETE DATA { %s %s %s }" % (subject, predicate, object)

    with repository.getConnection() as connection:
        return connection.executeUpdate(query=string_query)


# SELECT ?s ?p ?o WHERE {
#  ?s ?p ?o . ?s a owl:NamedIndividual
#  FILTER(?p != rdf:type)
# }
# SELECT ?s ?p WHERE {
#  ?s ?p owl:NamedIndividual .
#  FILTER(?p != rdf:type)
# }
# SELECT distinct ?s ?o WHERE {?s ?p ?o . ?s a owl:NamedIndividual}

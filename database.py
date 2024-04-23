from franz.openrdf.repository import Repository
from franz.openrdf.sail import AllegroGraphServer

import re
import os

import settings


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
    exception_list = [
        "http://www.w3.org/2001/XMLSchema#",
        "https://github.com/owlcs/owlapi",
        "http://www.w3.org/2002/07/owl#",
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "http://www.w3.org/XML/1998/namespace",
        "http://www.w3.org/2000/01/rdf-schema#",
    ]
    url = re.findall(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+#?",
        content,
    )
    url2 = set()
    for i in url:
        if i not in exception_list:
            url2.add(i)
    url2 = sorted(list(url2), key=lambda x: len(x), reverse=True)

    for i in url2:
        content = content.replace(
            i, f"http://127.0.0.1:10035/repositories/{settings.REPOSITORY_NAME}/"
        )
    with open(settings.OWL_FILES_STORAGE + filename, "w") as f:
        f.write(content)


def write_file(filename: str) -> bool:
    if os.path.isfile(
        os.path.join(settings.OWL_FILES_STORAGE, filename.split("/")[-1])
    ):
        return True
    if filename is None:
        return False

    with open(filename, "rb") as read_file:
        content = read_file.read()
    filename = filename.split("/")[-1]

    with open(settings.OWL_FILES_STORAGE + filename, "wb") as created_file:
        created_file.write(content)
        created_file.close()
    handle_file(filename)
    add_file_to_rep(filename)

    return True


def execute_get_query(subject: str="?s", relation: str="?r", object: str="?o"):
    """select query for get endpoints"""
    query_string = "SELECT distinct ?s ?r ?o WHERE {%s %s %s}" % (
        subject,
        relation,
        object,
    )
    result_list = []

    with repository.getConnection() as connection:
        result = connection.executeTupleQuery(query=query_string)

        with result:  # type: ignore
            for bindung_set in result:  # type: ignore
                result_list.append(
                    {
                        "subject": bindung_set.getValue("s").__str__(),
                        "relation": bindung_set.getValue("r").__str__(),
                        "object": bindung_set.getValue("o").__str__(),
                    }
                )

    return result_list


def get_objects(object: str):
    query = "SELECT distinct ?s ?r ?o WHERE {?s ?r ?o . ?s a %s}" % (object)
    result_list = []

    with repository.getConnection() as connection:
        result = connection.executeTupleQuery(query=query)

    with result:  # type: ignore
        for bindung_set in result:  # type: ignore
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
        query_string = (
            """SELECT distinct ?s ?r ?o WHERE {?s ?r ?o . ?s a owl:NamedIndividual}"""
        )
    else:
        query_string = (
            """SELECT distinct ?s WHERE {?s ?r ?o . ?s a owl:NamedIndividual}"""
        )
    result_list = []

    with repository.getConnection() as connection:
        result = connection.executeTupleQuery(query=query_string)
        with result:  # type: ignore
            for bindung_set in result:  # type: ignore
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
            if (
                i["object"].split("/")[-1][:-1] == class_name
                and i["relation"].split("#")[1][:-1] == "type"
            ):
                result.append(i)
        result_list = result
    return result_list


def execute_post_query(subject: str, relation: str, object: str):
    string_query = "INSERT DATA { %s %s %s}" % (subject, relation, object)

    with repository.getConnection() as connection:
        return connection.executeUpdate(query=string_query)


def execute_delete_query(subject: str, predicate: str, object: str):
    string_query = "DELETE DATA { %s %s %s }" % (subject, predicate, object)

    with repository.getConnection() as connection:
        return connection.executeUpdate(query=string_query)


def delete_all():
    string_query = "DELETE WHERE { ?s ?p ?o }"

    for i in os.listdir(settings.OWL_FILES_STORAGE):
        file_path = os.path.join(settings.OWL_FILES_STORAGE, i)
        if os.path.isfile(file_path):
            os.remove(file_path)

    with repository.getConnection() as connection:
        return connection.executeUpdate(query=string_query)


def delete_class_or_individual(name: str):
    string_query = """
        DELETE WHERE{{
          <{0}> ?p ?o .
        }};

        DELETE WHERE{{
          ?s ?p <{0}> .
        }};
    """.format(name)

    with repository.getConnection() as connection:
        return connection.executeUpdate(query=string_query)


def delete_property(property_name: str):
    string_query = """
        DELETE WHERE{{
          <{0}> ?p ?o .
        }};

        DELETE WHERE{{
          ?s <{0}> ?o .
        }};
    """.format(property_name)

    with repository.getConnection() as connection:
        return connection.executeUpdate(query=string_query)


def rename_subject_object(old_name: str, new_name: str):
    string_query = """
        DELETE {{
          <{0}> ?p ?o .
        }}
        INSERT {{
          <{1}> ?p ?o .
        }}
        WHERE {{
          <{0}> ?p ?o .
        }};

        DELETE {{
          ?s ?p <{0}> .
        }}
        INSERT {{
          ?s ?p <{1}> .
        }}
        WHERE {{
          ?s ?p <{0}> .
        }};
    """.format(
        old_name, new_name
    )

    with repository.getConnection() as connection:
        return connection.executeUpdate(query=string_query)


def rename_relation(old_name: str, new_name: str):
    string_query = """
        DELETE {{
          <{0}> ?p ?o .
        }}
        INSERT {{
          <{1}> ?p ?o .
        }}
        WHERE {{
          <{0}> ?p ?o .
        }};

        DELETE {{
          ?s <{0}> ?o .
        }}
        INSERT {{
          ?s <{1}> ?o .
        }}
        WHERE {{
          ?s <{0}> ?o .
        }};
    """.format(
        old_name, new_name
    )

    with repository.getConnection() as connection:
        return connection.executeUpdate(query=string_query)

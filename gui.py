from tkinter import Tk, CENTER, TclError
from tkinter import ttk
from tksheet import Sheet
from tkinter import filedialog
import tkinter as tk
from tkinter import messagebox

from typing import List, Dict, Any, Set
from dataclasses import dataclass

import database
from database import write_file
from services import validate_input, check_class_existing, get_full_info
from template import object_property_template, class_template, data_property_template, instance_template


@dataclass(slots=True)
class Tab:
    tab: ttk.Frame
    sheet: Sheet
    tab_name: List[str]


class OntotlogyEditor:
    def __init__(self, name: str = "Graphical Ontotlogy Editor") -> None:
        self.window = Tk()
        self.tabs = []
        self.window.resizable(False, False)
        self.notebook = ttk.Notebook(self.window, width=1080)
        self.window.title(name)
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=1)

        self.search_label = tk.Label(self.window, text="Search:")
        self.search_entry = tk.Entry(self.window)
        self.search_button = tk.Button(self.window, text="Search", command=self.find_individual)

        self.configure_menu()
        self.init_tabs()
        self.configure_window()

    def configure_menu(self):
        self.menu = tk.Menu()
        self.sub_menu = tk.Menu(self.menu, tearoff=0)
        self.sub_menu.add_command(
            label="Upload", accelerator="Ctrl+N", command=self.browse_file
        )
        self.sub_menu.add_command(
            label="Delete All", command=self.delete_all
        )
        self.window.bind('<Control-n>', self.browse_file)
        self.menu.add_cascade(menu=self.sub_menu, label="Menu")
        self.window.config(menu=self.menu)

    def browse_file(self, *args):
        filename = filedialog.askopenfilename(
            initialdir="/home/konstantin/",
            title="Select a File",
            filetypes=(("Rdf files", "*.rdf*"), ("all files", "*.*")),
        )
        if filename:
            write_file(filename)
            self.refresh_tables(self.tabs)

    def update_data_class(self):
        content = []
        query_result = database.execute_get_query(relation="rdf:type", object="owl:Class")
        for item in query_result:
            content.append(item["subject"].split("/")[-1][:-1])

        return content

    def update_data_individual(self):
        content = []
        query_result = database.execute_get_individuals_query()
        for item in query_result:
            content.append(item["subject"].split("/")[-1][:-1])

        return content

    def handle_data_in_dict_output(self, data: List[Dict[Any, Any]]):
        content = []
        for i in data:
            content.append([*i.values()])

        return content

    def update_data_object_property(self):
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

        return self.handle_data_in_dict_output(content)

    def update_data_property(self):
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

        return self.handle_data_in_dict_output(content)

    def update_subclasses(self):
        content = []

        query_result = database.execute_get_query(relation="rdfs:subClassOf")

        for item in query_result:
            content.append(
                {
                    "parent": item["object"].split("/")[-1][:-1],
                    "subclass": item["subject"].split("/")[-1][:-1],
                }
            )

        return self.handle_data_in_dict_output(content)

    def update_data(self, tab: ttk.Frame):
        if tab == self.class_tab:
            return [[i] for i in self.update_data_class()]
        elif tab == self.individual_tab:
            return [[i] for i in self.update_data_individual()]
        elif tab == self.object_property_tab:
            return self.update_data_object_property()
        elif tab == self.data_property_tab:
            return self.update_data_property()
        elif tab == self.subclass_tab:
            return self.update_subclasses()

    def update_tab_sheet(self, tab: ttk.Frame, sheet: Sheet):
        for i in self.tabs:
            if tab == i.tab:
                i.sheet = sheet
                break

    def refresh_tables(self, tabs: List[Tab]):
        for i in tabs:
            data = self.update_data(i.tab)
            if not data:
                data = ''
            sheet = Sheet(
                i.tab,
                data=data,
                height=700,
                width=1020,
                default_column_width=300,
                )
            sheet.enable_bindings()
            sheet.extra_bindings("begin_edit_cell", self.begin_edit_cell)
            sheet.edit_validation(self.validate_edits)
            sheet.grid(row=0, column=1, sticky="nswe")
            sheet.headers(i.tab_name)
            self.update_tab_sheet(i.tab, sheet)

    def init_tabs(self):
        self.class_tab = ttk.Frame(self.notebook)
        self.individual_tab = ttk.Frame(self.notebook)
        self.object_property_tab = ttk.Frame(self.notebook)
        self.data_property_tab = ttk.Frame(self.notebook)
        self.subclass_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.class_tab, text="Classes")
        self.notebook.add(self.individual_tab, text="Individuals")
        self.notebook.add(self.object_property_tab, text="Object properties")
        self.notebook.add(self.data_property_tab, text="Data properties")
        self.notebook.add(self.subclass_tab, text="Subclasses")

        self.notebook.pack(expand=1, fill="both")

    def configure_window(self) -> None:
        self.create_tab_spaces()

    def create_tab_spaces(self) -> None:
        just_tabs = {
            self.class_tab: ['Classes'],
            self.individual_tab: ['Individuals'],
            self.object_property_tab: ['Property', 'Domain', 'Range'],
            self.data_property_tab: ['Property', 'Domain', 'Range'],
            self.subclass_tab: ['Parent', 'Child'],
        }
        for i in just_tabs.keys():
            data = self.update_data(i)
            if not data:
                data = ''
            sheet = Sheet(
                i,
                data=data,
                height=700,
                width=1020,
                default_column_width=300
            )

            sheet.enable_bindings()
            sheet.extra_bindings("begin_edit_cell", self.begin_edit_cell)
            sheet.edit_validation(self.validate_edits)
            sheet.headers(just_tabs[i])
            sheet.grid(row=0, column=1, sticky="nswe")

            self.tabs.append(Tab(tab=i, sheet=sheet, tab_name=just_tabs[i]))

            self._setup_tools(self.tabs[-1])

    def begin_edit_cell(self, event=None):
        print("Here")
        return event.value

    def validate_edits(self, event):
        print("Validate")
        return event.value

    def _setup_tools(self, tab: Tab):
        tool_frame = ttk.LabelFrame(tab.tab, text="Tools")
        tool_frame.grid(row=0, column=0, sticky="nswe")

        create_button = ttk.Button(tool_frame, text="Create", command=lambda: self.create_form_window(tab.tab))
        create_button.grid(row=2, padx=5, pady=5, sticky="ew")
        if tab.tab != self.subclass_tab:
            delete_button = ttk.Button(tool_frame, text="Delete", command=lambda: self.delete(tab))
            delete_button.grid(row=3, padx=5, pady=5, sticky="ew")

        if tab.tab == self.object_property_tab or tab.tab == self.data_property_tab:
            connect_property_button = ttk.Button(tool_frame, text="Delete Individual",
                                                 command=lambda: self.delete_individual_property_form(tab.tab))
            connect_property_button.grid(row=4, padx=5, pady=5, sticky="ew")

        if tab.tab == self.individual_tab:
            individual_info = ttk.Button(tool_frame, text="Individual Info", command=self.toggle_search_window)
            individual_info.grid(row=4, padx=5, pady=5, sticky="ew")
            individual_info = ttk.Button(tool_frame, text="Connect Property", command=self.connect_property_window)
            individual_info.grid(row=5, padx=5, pady=5, sticky="ew")

    def create(self, tab: ttk.Frame, data: Dict[str, str]):
        print(data)
        if tab == self.class_tab:
            self.create_class(data)
        elif tab == self.individual_tab:
            self.create_individual(data)
        elif tab == self.object_property_tab:
            self.create_object_property(data)
        elif tab == self.data_property_tab:
            self.create_data_property(data)
        elif tab == self.subclass_tab:
            return self.create_subclass(data)

    def create_form_window(self, tab: ttk.Frame):
        self.form_window = Tk()
        self.form_window.title("Create Form")
        self.label_entry = []
        if tab == self.class_tab:
            self.form_window.geometry("500x150")
            label = ttk.Label(self.form_window, text="Class Name")
            label.place(relx=0.5, rely=0.1, anchor=CENTER)
            entry = ttk.Entry(self.form_window)
            entry.place(relx=0.5, rely=0.3, anchor=CENTER)
            self.label_entry.append((label, entry))
        elif tab == self.individual_tab:
            self.form_window.geometry("500x300")
            label = ttk.Label(self.form_window, text="Class Name")
            label.place(relx=0.5, rely=0.1, anchor=CENTER)
            entry = ttk.Entry(self.form_window)
            entry.place(relx=0.5, rely=0.25, anchor=CENTER)
            self.label_entry.append((label, entry))
            label = ttk.Label(self.form_window, text="Individual Name")
            label.place(relx=0.5, rely=0.4, anchor=CENTER)
            entry = ttk.Entry(self.form_window)
            entry.place(relx=0.5, rely=0.55, anchor=CENTER)
            self.label_entry.append((label, entry))
        elif tab == self.object_property_tab or tab == self.data_property_tab:
            self.form_window.geometry("500x400")
            label = ttk.Label(self.form_window, text="Property Name")
            label.place(relx=0.5, rely=0.1, anchor=CENTER)
            entry = ttk.Entry(self.form_window)
            entry.place(relx=0.5, rely=0.2, anchor=CENTER)
            self.label_entry.append((label, entry))
            label = ttk.Label(self.form_window, text="Domain Name 1")
            label.place(relx=0.5, rely=0.3, anchor=CENTER)
            entry = ttk.Entry(self.form_window)
            entry.place(relx=0.5, rely=0.4, anchor=CENTER)
            self.label_entry.append((label, entry))
            label = ttk.Label(self.form_window, text="Domain Name 2" if tab == self.object_property_tab else "Range")
            label.place(relx=0.5, rely=0.5, anchor=CENTER)
            entry = ttk.Entry(self.form_window)
            entry.place(relx=0.5, rely=0.6, anchor=CENTER)
            self.label_entry.append((label, entry))
        elif tab == self.subclass_tab:
            self.form_window.geometry("500x300")
            label = ttk.Label(self.form_window, text="Class Name")
            label.place(relx=0.5, rely=0.1, anchor=CENTER)
            entry = ttk.Entry(self.form_window)
            entry.place(relx=0.5, rely=0.25, anchor=CENTER)
            self.label_entry.append((label, entry))
            label = ttk.Label(self.form_window, text="Subclass Name")
            label.place(relx=0.5, rely=0.4, anchor=CENTER)
            entry = ttk.Entry(self.form_window)
            entry.place(relx=0.5, rely=0.55, anchor=CENTER)
            self.label_entry.append((label, entry))

        self.submit_button = ttk.Button(self.form_window, text="Submit", command=lambda: self.form_submit(tab))
        self.submit_button.place(relx=0.5, rely=0.8, anchor=CENTER)

    def form_submit(self, tab: ttk.Frame):
        self.form_window.destroy()
        try:
            if tab == self.class_tab:
                data = {
                    'classname': self.label_entry[0][1].get()
                }
                self.create(tab, data)
            elif tab == self.individual_tab:
                data = {
                    'instance_name': self.label_entry[1][1].get(),
                    'instance_type': self.label_entry[0][1].get()
                }
                self.create(tab, data)
            elif tab == self.object_property_tab:
                data = {
                    'object_property': self.label_entry[0][1].get(),
                    'domain_1': self.label_entry[1][1].get(),
                    'domain_2': self.label_entry[2][1].get()
                }
                self.create(tab, data)
            elif tab == self.data_property_tab:
                data = {
                    'data_property': self.label_entry[0][1].get(),
                    'domain': self.label_entry[1][1].get(),
                    'xs_range': self.label_entry[2][1].get()
                }
                self.create(tab, data)
            elif tab == self.subclass_tab:
                data = {
                    'classname': self.label_entry[1][1].get(),
                    'parent': self.label_entry[0][1].get()
                }
                self.create(tab, data)
        except TclError:
            messagebox.showwarning("Warning", "Check input args, maybe some of them are empty.")

    def create_class(self, data: Dict[str, str]):
        if check_class_existing(data['classname']):
            return
        if database.execute_post_query(f"<{data['classname']}>", "rdf:type", "owl:Class"):
            self.refresh_tables(self.tabs)

    def create_individual(self, data: Dict[str, str]):
        validation = validate_input({
            'NamedIndividual': data['instance_name'],
        })
        if validation[1]['NamedIndividual']:
            messagebox.showwarning("Warning", "Check input args.")
            return
        if not check_class_existing(data['instance_type']):
            messagebox.showwarning("Warning", "Such class doesn't exist.")
            return
        if database.execute_post_query(
            f"<{data['instance_name']}>", "rdf:type", "owl:NamedIndividual"
        ):
            database.execute_post_query(
                f"<{data['instance_name']}>", "rdf:type", f"<{data['instance_type']}>"
            )
            self.refresh_tables(self.tabs)

    def create_object_property(self, data: Dict[str, str]):
        validation = validate_input({
            'ObjectProperty': data['object_property'],
        })
        if validation[1]['ObjectProperty']:
            messagebox.showwarning("Warning", "Check input args.")
            return
        if not check_class_existing(data['domain_1']):
            messagebox.showwarning("Warning", "Such class doesn't exist.")
            return
        if not check_class_existing(data['domain_2']):
            messagebox.showwarning("Warning", "Such class doesn't exist.")
            return
        if (
            database.execute_post_query(
                f"<{data['object_property']}>", "rdf:type", "owl:ObjectProperty"
            )
            and database.execute_post_query(
                f"<{data['object_property']}>", "rdfs:domain", f"<{data['domain_1']}>"
            )
            and database.execute_post_query(
                f"<{data['object_property']}>", "rdfs:range", f"<{data['domain_2']}>"
            )
        ):
            self.refresh_tables(self.tabs)

    def create_data_property(self, data: Dict[str, str]):
        allows_range = ["xsd:decimal", "xsd:int", "xsd:string"]
        if data['xs_range'] not in allows_range:
            messagebox.showwarning("Warning", "Check input args.")
            return
        validation = validate_input({
            'DatatypeProperty': data['data_property'],
            'Class': data['domain']
        })
        if not validation[1]['Class']:
            messagebox.showwarning("Warning", "Check input args.")
            return
        if validation[1]['DatatypeProperty']:
            messagebox.showwarning("Warning", "Check input args.")
            return
        if (
            database.execute_post_query(
                f"<{data['data_property']}>", "rdf:type", "owl:DatatypeProperty"
            )
            and database.execute_post_query(
                f"<{data['data_property']}>", "rdfs:domain", f"<{data['domain']}>"
            )
            and database.execute_post_query(
                f"<{data['data_property']}>", "rdfs:range", f"{data['xs_range']}"
            )
        ):
            self.refresh_tables(self.tabs)

    def create_subclass(self, data: Dict[str, str]):
        parent_class = check_class_existing(data['parent'])
        child_class = check_class_existing(data['classname'])
        if not parent_class:
            messagebox.showwarning("Warning", "uch parent class doesn't exist.")
            return
        if not child_class:
            database.execute_post_query(f"<{data['classname']}>", "rdf:type", "owl:Class")
        else:
            self.delete_class(data['classname'])
            database.execute_post_query(f"<{data['classname']}>", "rdf:type", "owl:Class")
        if database.execute_post_query(f"<{data['classname']}>", "rdfs:subClassOf", f"<{data['parent']}>"):
            self.refresh_tables(self.tabs)

    def get_individual_info(self, individual: str):
        content = []
        validation = validate_input({
            'NamedIndividual': individual,
        })
        if not validation[0]:
            return content

        query_result = database.execute_get_individuals_query(name=individual)
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

        # individual_class = None

        # for i in database.execute_get_query():
        #     if i["subject"].split("/")[-1][:-1] == individual and \
        #        not i["object"].split("/")[-1][:-1].startswith('owl') and \
        #        i["relation"].split("#")[1][:-1] == 'type':
        #         individual_class = i["object"].split("/")[-1][:-1]
        #         break

        # for i in content:
        #     i['class'] = individual_class

        return self.handle_data_in_dict_output(content)

    def find_individual(self):
        self.search_label.pack_forget()
        self.search_entry.pack_forget()
        self.search_button.pack_forget()
        individual_window = tk.Toplevel(self.window)
        individual_window.title("Individual Info")
        data = self.get_individual_info(self.search_entry.get())

        sheet = Sheet(
            individual_window,
            data=data,
            height=700,
            width=900,
            default_column_width=300
        )

        span = sheet.span(key=['Class', 'Property', 'Value'], header=True)
        sheet.readonly(span)

        sheet.enable_bindings()
        sheet.edit_validation(self.validate_edits)
        sheet.headers(['Class', 'Property', 'Value'])
        sheet.grid(row=0, column=1, sticky="nswe")

    def toggle_search_window(self):
        if self.search_label.winfo_viewable():
            self.search_label.pack_forget()
            self.search_entry.pack_forget()
            self.search_button.pack_forget()
        else:
            self.search_label.pack(side="left")
            self.search_entry.pack(side="left")
            self.search_button.pack(side="left")

    def delete_all(self):
        database.delete_all()
        self.refresh_tables(self.tabs)

    def connect_property_window(self):
        self.connect_property_from_window = Tk()
        self.connect_property_from_window.title("Connect Property")
        self.connect_property_from_window.geometry("500x500")
        entries = []

        label = ttk.Label(self.connect_property_from_window, text="Property Type")
        label.place(relx=0.5, rely=0.05, anchor=CENTER)
        entry = ttk.Entry(self.connect_property_from_window)
        entry.place(relx=0.5, rely=0.1, anchor=CENTER)
        entries.append(entry)

        label = ttk.Label(self.connect_property_from_window, text="Object Name")
        label.place(relx=0.5, rely=0.2, anchor=CENTER)
        entry = ttk.Entry(self.connect_property_from_window)
        entry.place(relx=0.5, rely=0.25, anchor=CENTER)
        entries.append(entry)

        label = ttk.Label(self.connect_property_from_window, text="Property")
        label.place(relx=0.5, rely=0.35, anchor=CENTER)
        entry = ttk.Entry(self.connect_property_from_window)
        entry.place(relx=0.5, rely=0.4, anchor=CENTER)
        entries.append(entry)

        label = ttk.Label(self.connect_property_from_window, text="Value")
        label.place(relx=0.5, rely=0.5, anchor=CENTER)
        entry = ttk.Entry(self.connect_property_from_window)
        entry.place(relx=0.5, rely=0.55, anchor=CENTER)
        entries.append(entry)

        label = ttk.Label(self.connect_property_from_window, text="Value Type(Optional)")
        label.place(relx=0.5, rely=0.65, anchor=CENTER)
        entry = ttk.Entry(self.connect_property_from_window)
        entry.place(relx=0.5, rely=0.7, anchor=CENTER)
        entries.append(entry)

        self.submit_button = ttk.Button(self.connect_property_from_window,
                                        text="Submit", command=lambda: self.connect_property(entries))
        self.submit_button.place(relx=0.5, rely=0.85, anchor=CENTER)

    def connect_property(self, entries: List[ttk.Entry]):
        self.connect_property_from_window.destroy()
        type_property = entries[0].get()
        subject = entries[1].get()
        property = entries[2].get()
        object_class = entries[3].get()
        value_type = entries[4].get()

        allows_range = ["xsd:decimal", "xsd:int", "xsd:string"]
        if value_type not in allows_range and type_property == 'DatatypeProperty':
            messagebox.showwarning("Warning", "Check input args.")
            return
        validation = validate_input({
            'NamedIndividual': subject,
            type_property: property
        })
        if not validation[0]:
            messagebox.showwarning("Warning", "Check input args.")
            return
        if type_property == 'ObjectProperty':
            validation = validate_input({
                'NamedIndividual': object_class
            })
            if not validation[0]:
                messagebox.showwarning("Warning", "Check input args.")
                return
            if database.execute_post_query(
                f"<{subject}>", f"<{property}>", f"<{object_class}>"
            ):
                self.refresh_tables(self.tabs)
        elif type_property == 'DatatypeProperty':
            if database.execute_post_query(
                f"<{subject}>", f"<{property}>", f'"{object_class}"^^{value_type}'
            ):
                self.refresh_tables(self.tabs)

    def delete(self, tab: Tab):
        selected_cells = tab.sheet.get_selected_cells()
        data: List[str] = [tab.sheet.get_cell_data(*i) for i in selected_cells]  # type: ignore
        if tab.tab == self.class_tab:
            for i in data:
                self.delete_class(i)
        elif tab.tab == self.individual_tab:
            for i in data:
                self.delete_instance(i)
        elif tab.tab == self.object_property_tab:
            for i in data:
                self.delete_object_property(i)
        elif tab.tab == self.data_property_tab:
            for i in data:
                self.delete_data_property(i)

    def delete_individual_property_form(self, tab: ttk.Frame):
        self.delete_form_window = Tk()
        self.delete_form_window.title("Delete Property Form")
        entries = []
        self.delete_form_window.geometry("500x300")
        label = ttk.Label(self.delete_form_window, text="Property Name")
        label.place(relx=0.5, rely=0.1, anchor=CENTER)
        entry = ttk.Entry(self.delete_form_window)
        entry.place(relx=0.5, rely=0.25, anchor=CENTER)
        entries.append(entry)

        label = ttk.Label(self.delete_form_window, text="Individual Name")
        label.place(relx=0.5, rely=0.4, anchor=CENTER)
        entry = ttk.Entry(self.delete_form_window)
        entry.place(relx=0.5, rely=0.55, anchor=CENTER)
        entries.append(entry)

        self.submit_button = ttk.Button(self.delete_form_window, text="Submit",
                                        command=lambda: self.delete_individual_property(tab, entries))
        self.submit_button.place(relx=0.5, rely=0.8, anchor=CENTER)

    def delete_individual_property(self, tab: ttk.Frame, entries: List[ttk.Entry]):
        self.delete_form_window.destroy()
        if tab == self.data_property_tab:
            self.instance_delete_data_property(entries[0].get(), entries[1].get())
        else:
            self.instance_delete_object_property(entries[0].get(), entries[1].get())

    def instance_delete_data_property(self, data_property: str, individual_name: str, hide=False):
        all_info = get_full_info(individual_name, "owl:NamedIndividual")
        if not all_info:
            messagebox.showwarning("Warning", "Such individual doesn't exist.")
            return
        validation = validate_input({
            'DatatypeProperty': data_property,
        })
        if not validation[0]:
            messagebox.showwarning("Warning", "Check input args.")
            return
        for i in all_info:
            if i["relation"].split("/")[-1][:-1] == data_property:
                database.execute_delete_query(
                    f'<{i["subject"].split("/")[-1][:-1]}>',
                    f'<{i["relation"].split("/")[-1][:-1]}>',
                    f'"{i["object"].split("^^")[0][1:-1]}"^^{data_property_template[i["object"].split("#")[-1][:-1]]}',
                )
        if not hide:
            self.refresh_tables(self.tabs)

    def instance_delete_object_property(self, object_property: str, individual_name: str, hide=False):
        all_info = get_full_info(individual_name, "owl:NamedIndividual")
        if not all_info:
            messagebox.showwarning("Warning", "Such individual doesn't exist.")
            return
        validation = validate_input({
            'ObjectProperty': object_property,
        })
        if not validation[0]:
            messagebox.showwarning("Warning", "Check input args.")
            return
        for i in all_info:
            if i["relation"].split("/")[-1][:-1] == object_property:
                database.execute_delete_query(
                    f'<{i["subject"].split("/")[-1][:-1]}>',
                    f'<{i["relation"].split("/")[-1][:-1]}>',
                    f'<{i["object"].split("/")[-1][:-1]}>',
                )
        if not hide:
            self.refresh_tables(self.tabs)

    def delete_class(self, subject_class: str):
        all_info = get_full_info(subject_class, "owl:Class")
        if not all_info:
            messagebox.showwarning("Warning", "Such class doesn't exist.")
            return
        connected_object: Set[str] = set()
        for i in database.execute_get_query():
            if i["object"].split("/")[-1][:-1] == subject_class:
                connected_object.add(i["subject"].split("/")[-1][:-1])
        for i in connected_object:
            self.delete_instance(i, hide=True)
            self.delete_data_property(i, hide=True)
            self.delete_object_property(i, hide=True)
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

        self.refresh_tables(self.tabs)

    def delete_instance(self, instance_name: str, hide=False):
        all_info = get_full_info(instance_name, "owl:NamedIndividual")
        if not all_info:
            if not hide:
                messagebox.showwarning("Warning", "Such instance doesn't exist.")
            return
        individuals = set()
        for i in database.execute_get_query():
            if i["object"].split("/")[-1][:-1] == instance_name:
                individuals.add((i["subject"].split("/")[-1][:-1], i["relation"].split("/")[-1][:-1]))
        for i in individuals:
            self.instance_delete_object_property(i[1], i[0], hide=True)

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
        if not hide:
            self.refresh_tables(self.tabs)

    def delete_object_property(self, object_property: str, hide=False):
        all_info = get_full_info(object_property, "owl:ObjectProperty")
        if not all_info:
            if not hide:
                messagebox.showwarning("Warning", "Such property doesn't exist.")
            return
        individuals = set()
        for i in database.execute_get_query():
            if i["relation"].split("/")[-1][:-1] == object_property:
                individuals.add(i["subject"].split("/")[-1][:-1])
                individuals.add(i["object"].split("/")[-1][:-1])
        for i in individuals:
            self.instance_delete_object_property(object_property, i, hide=True)

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
        if not hide:
            self.refresh_tables(self.tabs)

    def delete_data_property(self, data_property: str, hide=False):
        all_info = get_full_info(data_property, "owl:DatatypeProperty")
        if not all_info:
            if not hide:
                messagebox.showwarning("Warning", "Such property doesn't exist.")
            return
        individuals = set()
        for i in database.execute_get_query():
            if i["relation"].split("/")[-1][:-1] == data_property:
                individuals.add(i["subject"].split("/")[-1][:-1])
        for i in individuals:
            self.instance_delete_data_property(data_property, i, hide=True)
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
        if not hide:
            self.refresh_tables(self.tabs)

    def run(self):
        self.window.mainloop()


editor = OntotlogyEditor()
editor.run()

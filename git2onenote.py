import ast
import asyncio
import configparser
import datetime
import re
import threading
import time
from configparser import SectionProxy
from pathlib import Path

from msgraph.generated.models.o_data_errors.o_data_error import ODataError

from git import Git
from graph import Graph
from scheduler import Scheduler
from web_server import WebServer


async def sync(
    graph: Graph,
    gitlab: Git,
    last_sync: datetime.datetime,
    links: dict[int, str],
):
    print("Syncing...")

    for link in links:
        gitlab_id, onenote_section_id = link
        print(
            f"Syncing gitlab project {gitlab_id} to onenote section {onenote_section_id}"
        )

        # Get last commit
        last_commit = gitlab.get_commits(gitlab_id)[0]
        if (
            last_sync is not None
            and datetime.strptime(last_commit.created_at) < last_sync
        ):
            print("No new commits since last sync")

        # Sync
        git_pdf_files = gitlab.get_items(
            gitlab_id, name_filter=lambda name: name.endswith(".pdf")
        )
        onenote_pdf_files = (await graph.get_pages(onenote_section_id)).value

        # Compare files by name
        # ignore file extension
        missing_files = [
            file
            for file in git_pdf_files
            if file["name"][:-4] not in [page.title for page in onenote_pdf_files]
        ]

        if not missing_files:
            print("No missing files to upload")
            print("git_pdf_files:", [file["name"] for file in git_pdf_files])
            print("onenote_pdf_files:", [page.title for page in onenote_pdf_files])
            return

        print("Uploading missing files:", [file["name"] for file in missing_files])

        for file in missing_files:
            raw_file = gitlab.get_file(gitlab_id, file["path"])

            file_name = Path(file["name"]).stem

            await graph.create_page_from_pdf(
                onenote_section_id, raw_file=(file_name, raw_file)
            )


async def main():
    # Load settings
    config = configparser.ConfigParser()
    config.read(["config.cfg", "config.dev.cfg"])
    azure_settings = config["azure"]
    gitlab_settings = config["GitLab"]

    links_str = config.get("git2onenote", "links")

    if not re.fullmatch(r"(\(\d+, [^)]+\),?\s*)+", links_str.strip()):
        raise ValueError("Invalid links format")

    matches = re.findall(r"\((\d+),\s*([^)]+)\)", links_str.strip())

    # Converting to list of tuples (int, str)
    links = [(int(num), text) for num, text in matches]
    print("Found gitlab-onenote links:")
    print("gitlab id - onenote section id")
    for link in links:
        print(link)

    graph: Graph = Graph(azure_settings)
    gitlab: Git = Git(gitlab_settings)

    await greet_user(graph)

    async def on_sync():
        return await sync(graph, gitlab, None, links)

    web_server = WebServer()
    web_server.run(on_sync)

    Scheduler(on_sync, "07:55").run()

    choice = -1

    while choice != 0:
        print("Please choose one of the following options:")
        print("0. Exit")
        print("1. Display access token")
        print("2. Select notebook")
        print("3. Sync now")

        try:
            choice = int(input())
        except ValueError:
            choice = -1

        try:
            if choice == 0:
                print("Goodbye...")
            elif choice == 1:
                await display_access_token(graph)
            elif choice == 2:
                await select_section(graph)
            elif choice == 3:
                await sync(graph, gitlab, None, links)
            else:
                print("Invalid choice!\n")
        except ODataError as odata_error:
            print("Error:")
            if odata_error.error:
                print(odata_error.error.code, odata_error.error.message)


async def greet_user(graph: Graph):
    user = await graph.get_user()
    if user:
        print("Hello,", user.display_name)
        # For Work/school accounts, email is in mail property
        # Personal accounts, email is in userPrincipalName
        print("Email:", user.mail or user.user_principal_name, "\n")


async def display_access_token(graph: Graph):
    token = await graph.get_user_token()
    print("User token:", token, "\n")


async def select_section(graph: Graph):
    notebooks = await graph.get_notebooks()
    if not notebooks:
        print("No notebooks found.")
        return

    print("Notebooks:")
    # Display notebooks with index
    for i, notebook in enumerate(notebooks.value):
        print(f"{i}. {notebook.display_name} - {notebook.id}")

    print("Please select a notebook by entering the index:")
    notebook_index = int(input())
    selected_notebook = notebooks.value[notebook_index]
    print("Selected notebook:", selected_notebook.display_name)

    sections = await graph.get_sections(selected_notebook.id)
    if not sections:
        print("No sections found.")
        return

    print("Sections:")
    # Display sections with index
    for i, section in enumerate(sections.value):
        print(f"{i}. {section.display_name} - {section.id}")

    print("Please select a section by entering the index:")
    section_index = int(input())
    selected_section = sections.value[section_index]
    print("Selected section:", selected_section.display_name)

    pages = await graph.get_pages(selected_section.id)
    if not pages:
        print("No pages found.")
        return

    print("Pages:")
    # Display pages with index
    for i, page in enumerate(pages.value):
        print(f"{i}. {page.title} - {page.id}")


# Run main
asyncio.run(main())

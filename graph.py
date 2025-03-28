import os
from configparser import SectionProxy
from pathlib import Path
from typing import Tuple

from azure.identity import DeviceCodeCredential, TokenCachePersistenceOptions
from kiota_abstractions.method import Method
from kiota_abstractions.request_information import RequestInformation
from msgraph import GraphServiceClient
from msgraph.generated.models.onenote_page import OnenotePage
from msgraph.generated.users.item.user_item_request_builder import (
    UserItemRequestBuilder,
)
from requests_toolbelt.multipart.encoder import MultipartEncoder


class Graph:
    settings: SectionProxy
    device_code_credential: DeviceCodeCredential
    user_client: GraphServiceClient

    def __init__(self, config: SectionProxy):
        self.settings = config
        client_id = self.settings["clientId"]
        tenant_id = self.settings["tenantId"]
        graph_scopes = self.settings["graphUserScopes"].split(" ")

        self.device_code_credential = DeviceCodeCredential(
            client_id,
            tenant_id=tenant_id,
        )
        self.user_client = GraphServiceClient(self.device_code_credential, graph_scopes)

    async def get_user_token(self):
        graph_scopes = self.settings["graphUserScopes"]
        access_token = self.device_code_credential.get_token(graph_scopes)
        return access_token.token

    async def get_user(self):
        # Only request specific properties using $select
        query_params = UserItemRequestBuilder.UserItemRequestBuilderGetQueryParameters(
            select=["displayName", "mail", "userPrincipalName"]
        )

        request_config = (
            UserItemRequestBuilder.UserItemRequestBuilderGetRequestConfiguration(
                query_parameters=query_params
            )
        )

        user = await self.user_client.me.get(request_configuration=request_config)
        return user

    async def get_notebooks(self):
        notebooks = await self.user_client.me.onenote.notebooks.get()
        return notebooks

    async def get_sections(self, notebook_id: str):
        sections = await self.user_client.me.onenote.notebooks.by_notebook_id(
            notebook_id
        ).sections.get()
        return sections

    async def get_pages(self, section_id: str):
        pages = await self.user_client.me.onenote.sections.by_onenote_section_id(
            section_id
        ).pages.get()
        return pages

    async def create_page_from_pdf(
        self,
        section_id: str,
        pdf_file_path: str = None,
        raw_file: Tuple[str, bytes] = None,
    ):
        url = f"https://graph.microsoft.com/v1.0/me/onenote/sections/{section_id}/pages"

        if pdf_file_path is None and raw_file is None:
            raise ValueError("Either pdf_file_path or raw_file must be provided")

        if pdf_file_path is not None and raw_file is not None:
            raise ValueError("Only one of pdf_file_path or raw_file can be provided")

        is_raw_file = raw_file is not None

        file_name = (
            Path(os.path.basename(pdf_file_path)).stem
            if not is_raw_file
            else raw_file[0]
        )

        html_content = f"""<!DOCTYPE html>
<html>
  <head>
    <title>{file_name}</title>
  </head>
  <body>
    <img data-render-src="name:file-part" alt="PDF file as images"/>
  </body>
</html>"""

        # Build the multipart files payload. httpx will automatically create a boundary.
        files = {
            "Presentation": (None, html_content, "text/html"),
            "file-part": (
                "file.pdf",
                open(pdf_file_path, "rb") if not is_raw_file else raw_file[1],
                "application/pdf",
            ),
        }

        m = MultipartEncoder(fields=files)

        # generate byte payload for the multipart/form-data
        byte_content = m.to_string()

        # generate request information with the files payload in multipart/form-data
        request_info = RequestInformation()
        request_info.url = url
        request_info.http_method = Method.POST
        request_info.headers.add("Content-Type", m.content_type)
        request_info.content = byte_content

        await self.user_client.request_adapter.send_async(
            request_info, OnenotePage, None
        )

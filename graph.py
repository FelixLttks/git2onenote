from configparser import SectionProxy

from azure.identity import DeviceCodeCredential, TokenCachePersistenceOptions
from msgraph import GraphServiceClient
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.message import Message
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.users.item.mail_folders.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (
    SendMailPostRequestBody,
)
from msgraph.generated.users.item.user_item_request_builder import (
    UserItemRequestBuilder,
)


class Graph:
    settings: SectionProxy
    device_code_credential: DeviceCodeCredential
    user_client: GraphServiceClient

    def __init__(self, config: SectionProxy):
        self.settings = config
        client_id = self.settings["clientId"]
        tenant_id = self.settings["tenantId"]
        graph_scopes = self.settings["graphUserScopes"].split(" ")

        cache_options = TokenCachePersistenceOptions(name="my_graph_app_cache")

        self.device_code_credential = DeviceCodeCredential(
            client_id,
            tenant_id=tenant_id,
            cache_options=cache_options,
            cache_persistence_options=cache_options,
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

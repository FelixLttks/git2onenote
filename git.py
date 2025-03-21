from configparser import SectionProxy

import gitlab


class Git:
    settings: SectionProxy
    gitlab_client: gitlab.Gitlab

    def __init__(self, settings: SectionProxy):
        self.settings = settings

        self.gitlab_client = gitlab.Gitlab(
            url=settings["url"], private_token=settings["token"]
        )
        self.gitlab_client.auth()
        print("Connected to GitLab")

    def get_projects(self):
        projects = self.gitlab_client.projects.list(all=True, owned=True)
        return projects

    def get_project(self):
        project = self.gitlab_client.projects.get(self.settings["project_id"])
        return project

    def get_items(self, recursive=True, name_filter=None):
        project = self.get_project()
        items = project.repository_tree(
            ref=self.settings["branch"], recursive=recursive, all=True
        )

        if name_filter:
            items = [item for item in items if name_filter(item["name"])]
        return items

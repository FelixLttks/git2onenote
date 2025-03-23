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

    def get_project(self, project_id):
        project = self.gitlab_client.projects.get(project_id)
        return project

    def get_items(self, project_id, recursive=True, name_filter=None):
        project = self.get_project(project_id)
        items = project.repository_tree(ref="main", recursive=recursive, all=True)

        if name_filter:
            items = [item for item in items if name_filter(item["name"])]
        return items

    def get_commits(self, project_id):
        commit = self.get_project(project_id).commits.list()
        return commit

    def get_file(self, project_id, file_path, raw=True):
        file = self.get_project(project_id).files.get(file_path, ref="main")
        if raw:
            return file.decode()
        return file

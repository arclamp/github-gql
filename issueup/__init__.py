import click
import os
import requests
from requests import api
import sys
import yaml


def read_config(filename):
    if filename is None:
        return {}

    with open(filename) as f:
        return yaml.safe_load(f)


def get_project_info(api_key, organization, project):
    result = run_query(api_key, f"""
        query {{
            organization(login: "{organization}") {{
                projectNext(number: {project}) {{
                    title
                    id
                }}
            }}
        }}
    """)

    return result["data"]["organization"]["projectNext"]


def collect_all(api_key, template, drill, filt, pull):
    result = run_query(api_key, template.replace("XXX", "null"))
    data = drill(result)
    final = []

    while len(data) > 0:
        final += [pull(v["node"]) for v in data if filt(v)]
        cursor = data[-1]["cursor"]

        result = run_query(api_key, template.replace("XXX", f'"{cursor}"'))
        data = drill(result)

    return final

def get_open_issues(api_key, organization, repo):
    template = f"""
        query {{
            repository(owner: "{organization}", name: "{repo}") {{
                issues(states: [OPEN], first: 50, after: XXX) {{
                    edges {{
                        cursor
                        node {{
                            title
                            id
                            repository {{
                                name
                            }}
                            number
                        }}
                    }}
                }}
            }}
        }}
    """

    drill = lambda rec: rec["data"]["repository"]["issues"]["edges"]
    pull = lambda rec: {
        "title": rec["title"],
        "id": rec["id"],
        "repository": rec["repository"]["name"],
        "number": rec["number"]
    }

    return collect_all(api_key, template, drill, lambda x: True, pull)


def get_project_issues(api_key, organization, project):
    template = f"""
        query {{
            organization(login: "{organization}") {{
                projectNext(number: {project}) {{
                    id
                    items(first: 50, after: XXX) {{
                        edges {{
                            cursor
                            node {{
                                id
                                title
                                databaseId
                                content {{
                                    ... on Issue {{
                                        number
                                        repository {{
                                            name
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
    """

    drill = lambda rec: rec["data"]["organization"]["projectNext"]["items"]["edges"]

    filt = lambda rec: bool(rec["node"]["content"])

    pull = lambda rec: {
        "id": rec["id"],
        "did": rec["databaseId"],
        "title": rec["title"],
        "repository": rec["content"]["repository"]["name"],
        "number": rec["content"]["number"],
    }

    return collect_all(api_key, template, drill, filt, pull)


def run_query(api_key, query):
    req = requests.post(
        "https://api.github.com/graphql",
        json={"query": query},
        headers={"Authorization": f"Bearer {api_key}"}
    )
    if req.status_code == 200:
        return req.json()
    else:
        raise RuntimeError(f"query failed: {req.status_code}")


@click.command()
@click.option("-c", "--config", "config_file", type=click.Path(), help="Path to a YAML config file")
@click.option("--no-config", is_flag=True, default=False, help="Don't use any config file, including the default .issueup")
@click.option("-o", "--organization", type=str, metavar="NAME", help="The GitHub org containing both the beta project and the repo to file issues from")
@click.option("-r", "--repo", "repos", type=str, metavar="NAME", multiple=True, help="The repository from which to file issues in the project (can appear multiple times)")
@click.option("-p", "--project", type=int, metavar="NUMBER", help="The beta project number to file new issues to")
@click.option("-d", "--dry-run", is_flag=True, default=False, help="Don't actually file the issues")
def main(config_file, no_config, organization, repos, project, dry_run):
    """
    A Python script that takes issues from a repository and files them in a GitHub Beta Project.
    """

    # Establish a default config file.
    if config_file is None:
        if os.path.exists(".issueup.yaml"):
            config_file = ".issueup.yaml"

    # Read the config file.
    config = {}
    if not no_config:
        config = read_config(config_file)

    # Get the API key.
    api_key = config.get("gh_api_key") or os.getenv("GH_API_KEY")
    if api_key is None:
        print("No GitHub API key found. Set GH_API_KEY or use the -c option.", file=sys.stderr)
        sys.exit(1)

    # Ensure that all required options are set, either through the command line
    # arguments, or the config file.
    organization = organization or config.get("organization")
    repos = repos or config.get("repo")
    project = project or config.get("project")

    if organization is None or repos is None or project is None:
        print("`organization`, `repo`, and `project` arguments are all required", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        print("This is a DRY RUN")

    # Retrieve project info (the name and the GraphQL ID).
    print(f"Getting project {organization}/{project}...", end="", flush=True)
    project_info = get_project_info(api_key, organization, project)
    print(f'found project "{project_info["title"]}"')

    # Get the existing issues from the project (to prevent attempting to add these again).
    print(f"Getting existing issues from project {project}...", end="", flush=True)
    project_issues = get_project_issues(api_key, organization, project)
    print(f"found {len(project_issues)}")

    # Gather a set of existing issues by org/number.
    filed = {f'{v["repository"]}/{v["number"]}' for v in project_issues}

    # Repeat for each repo provided.
    none = True
    for repo in repos:
        # Get the open issues (the ones that may need to be added to the project).
        print(f"Getting open issues from {organization}/{repo}...", end="", flush=True)
        open_issues = get_open_issues(api_key, organization, repo)
        print(f"found {len(open_issues)}")

        # One by one add issues if they aren't already in the project.
        for issue in open_issues:
            uri = f'{issue["repository"]}/{issue["number"]}'
            if uri not in filed:
                none = False
                print(f"Adding {uri}...", end="", flush=True)
                if not dry_run:
                    run_query(api_key, f"""
                        mutation {{
                            addProjectNextItem(input: {{projectId: "{project_info["id"]}" contentId: "{issue["id"]}"}}) {{
                                projectNextItem {{
                                    id
                                }}
                            }}
                        }}
                    """)
                print("done")

    if none:
        print("No new issues added (project is already up to date)")


if __name__ == "__main__":
    main()

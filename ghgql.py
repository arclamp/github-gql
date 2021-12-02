import click
from pprint import pprint
import requests
from requests import api


def get_api_key(filename):
    with open(filename) as f:
        return f.read().strip()


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
    result = run_query(api_key, template.replace("XXX", ""))
    print(template)
    pprint(result)
    data = drill(result)
    final = []

    while len(data) > 0:
        final += [pull(v["node"]) for v in data if filt(v)]
        cursor = data[-1]["cursor"]

        result = run_query(api_key, template.replace("XXX", f', after: "{cursor}"'))
        data = drill(result)

    return final

def get_open_issues(api_key, organization, repo):
    template = f"""
        query {{
            repository(owner: "{organization}", name: "{repo}") {{
                issues(states: [OPEN], first: 10XXX) {{
                    edges {{
                        cursor
                        node {{
                            title
                            id
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
    }

    return collect_all(api_key, template, drill, lambda x: True, pull)


def get_project_issues(api_key, organization, project):
    template = f"""
        query {{
            organization(login: "{organization}") {{
                projectNext(number: {project}) {{
                    id
                    items(first: 50XXX) {{
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
@click.option("-c", "--credential-file", type=click.Path(), required=True)
@click.option("-o", "--organization", type=str, required=True)
@click.option("-r", "--repo", type=str, required=True)
@click.option("-p", "--project", type=int, required=True)
def main(credential_file, organization, repo, project):
    api_key = get_api_key(credential_file)

    project_info = get_project_info(api_key, organization, project)

    print(f"Getting open issues from {organization}/{repo}")
    open_issues = get_open_issues(api_key, organization, repo)
    print(f"Found {len(open_issues)}")
    pprint(open_issues)

    print(f"Getting items from project {project}")
    project_items = get_project_issues(api_key, organization, project)
    print(f"Found {len(project_items)}")
    pprint(project_items)

if __name__ == "__main__":
    main()
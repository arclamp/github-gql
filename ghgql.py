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


def get_open_issues(api_key, organization, repo):
    result = run_query(api_key, f"""
        query {{
            repository(owner: "{organization}", name: "{repo}") {{
                issues(states: [OPEN], first: 10) {{
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
    """)

    data = result["data"]["repository"]["issues"]["edges"]
    titles = []

    while len(data) > 0:
        titles += [v["node"]["title"] for v in data]
        cursor = data[-1]["cursor"]

        result = run_query(api_key, f"""
            query {{
                repository(owner: "{organization}", name: "{repo}") {{
                    issues(states: [OPEN], first: 50, after: "{cursor}") {{
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
        """)

        data = result["data"]["repository"]["issues"]["edges"]
    
    return titles


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

    pprint(get_project_info(api_key, organization, project))

    open_issues = get_open_issues(api_key, organization, repo)
    pprint(open_issues)
    print(len(open_issues))


if __name__ == "__main__":
    main()
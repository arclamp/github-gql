import click
from pprint import pprint
import requests


def get_api_key(filename):
    with open(filename) as f:
        return f.read().strip()


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
def main(credential_file):
    api_key = get_api_key(credential_file)

    test_query = """
    {
        viewer {
            login
        }
        rateLimit {
            limit
            cost
            remaining
            resetAt
        }
    }
    """

    pprint(run_query(api_key, test_query))


if __name__ == "__main__":
    main()
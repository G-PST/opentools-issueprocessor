""" Entry python module for github action. """

# standard imports
import os
import http
import re
import subprocess
from pathlib import Path
import json
from pydantic import BaseModel

# third-party imports
import requests

from interface import Licenses, Organization, ProgrammingLanguage


def download_data_file(issue_url: str, access_token: str):
    """Function to download issue file."""
    print("Starting to download the file.")
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{issue_url}/comments", headers=headers)

    print(f"Response: {response} {response.status_code} {headers}")
    if response.status_code != http.HTTPStatus.OK:
        return

    comments = response.json()
    print(f"Comments: {comments}")
    if not comments:
        return

    json_files = [
        item
        for item in re.findall(r"(https?://[^\s)]+)", comments[-1]["body"])
        if item.endswith(".json")
    ]

    if not json_files:
        return

    print(f"Detected JSON files {json_files}")

    latest_json_file = json_files[-1]
    file_name = latest_json_file.split("/")[-1]
    file_response = requests.get(latest_json_file)

    if file_response.status_code != http.HTTPStatus.OK:
        return False

    with open(file_name, "wb") as f:
        f.write(file_response.content)

    print(f"File {file_name} downloaded successfully.")
    return file_name


def setup_github_permissions():
    """Some commands to set up github permissions."""
    subprocess.run(
        [
            "git",
            "config",
            "--global",
            "user.email",
            "gpst.opentools@nrel.gov",
        ],
        check=True,
    )
    subprocess.run(
        ["git", "config", "--global", "user.name", "GPST Opentools"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "config",
            "--global",
            "--add",
            "safe.directory",
            "/github/workspace",
        ],
        check=True,
    )


def _check_unique_name(ent: dict):
    """Function to check unique name."""
    if "unique_name" not in ent:
        msg = f"unique name does not exist in {ent=}"
        raise ValueError(msg)
    if not ent["unique_name"]:
        msg = f"Unique name is empty in {ent=}"
        raise ValueError(msg)
    return ent["unique_name"].lower().replace(" ", "-") + ".json"


def dump_new_file(obj: BaseModel, json_file: Path):
    """Dumps to json file."""

    if not json_file.exists():
        with open(json_file, "w", encoding="utf-8") as file_pointer:
            json.dump(obj.model_dump(), file_pointer)


def update_licenses(licenses: list[dict], license_path: Path):
    """Update licenses."""
    for lic in licenses:
        file_name = _check_unique_name(lic)
        lic_pydantic = Licenses(name=lic["name"])
        dump_new_file(lic_pydantic, license_path / file_name)


def update_organizations(orgs: list[dict], org_path: Path):
    """Update organizations."""

    for org in orgs:
        file_name = _check_unique_name(org)
        org_pydantic = Organization(
            name=org["name"], description=org["description"], url=org["url"]
        )
        dump_new_file(org_pydantic, org_path / file_name)


def update_languages(langs: list[dict], lang_path: Path):
    """Update languages."""

    for lang in langs:
        file_name = _check_unique_name(lang)
        lang_pydantic = ProgrammingLanguage(
            name=lang["name"],
            description=lang["description"],
            url=lang["url"],
            licenses=lang["licenses"],
        )
        dump_new_file(lang_pydantic, lang_path / file_name)


def process_issue_json_file(json_file_path: Path, data_path: Path):
    """Process issue json file."""

    with open(json_file_path, "r", encoding="utf-8") as file_pointer:
        issue_content = json.load(file_pointer)

    if "licenses" in issue_content and issue_content["licenses"]:
        update_licenses(issue_content["licenses"], data_path / "licenses")

    if "organizations" in issue_content and issue_content["organizations"]:
        update_organizations(
            issue_content["organizations"], data_path / "organizations"
        )

    if "languages" in issue_content and issue_content["languages"]:
        update_languages(issue_content["languages"], data_path / "languages")


def main():
    """Entry function for github action."""
    issue_number = os.environ["INPUT_ISSUE_NUMBER"]
    issue_title = os.environ["INPUT_ISSUE_TITLE"]
    issue_url = os.environ["INPUT_ISSUE_URL"]
    token = os.environ["INPUT_TOKEN"]

    print(issue_number, issue_title, issue_url, token)

    if issue_number or issue_title or issue_url or token:
        if not (issue_number and issue_title and issue_url and token):
            print("::set-output name=exitcode::1")
            return

        os.environ["GITHUB_TOKEN"] = token
        file_name = download_data_file(issue_url, token)
        if not file_name:
            print("::set-output name=exitcode::0")
            return
        setup_github_permissions()
        branch_name = f"issue_{issue_number}_branch"
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        process_issue_json_file(
            Path(file_name), Path(os.environ["INPUT_DATAPATH"])
        )
        os.remove(file_name)
        subprocess.run(["git", "add", "."], check=True)
        commit_message = f"Add issue file: {file_name}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(
            ["git", "push", "--set-upstream", "origin", branch_name], check=True
        )
        print("::set-output name=exitcode::0")


if __name__ == "__main__":
    main()

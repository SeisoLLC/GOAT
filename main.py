#!/usr/bin/env python3
"""
salacious-code-reviews script entrypoint
"""

import os
import json
import openai
import ast
from github import Github, PullRequest, GithubException

from salacious_code_reviews import config, constants


def get_github_session() -> Github:
    log.info("Creating GitHub Session...")

    if not os.getenv("GITHUB_TOKEN"):
        log.error("Please provide a valid GITHUB_TOKEN environment variable!")
        raise SystemExit(1)

    return Github(os.getenv("GITHUB_TOKEN"))


def set_openai_key() -> None:
    log.info("Setting up OpenAI Session...")

    if not os.getenv("OPENAI_API_KEY"):
        log.error("Please provide a valid OPENAI_API_KEY environment variable!")
        raise SystemExit(1)

    openai.api_key = os.getenv("OPENAI_API_KEY")


def get_repo_and_pr() -> dict:
    repo_and_pr = {"repo": [], "pr": []}

    log.info("Getting repo and pull request from runner environment...")

    if not os.getenv("GITHUB_REF"):
        log.error("Cannot find pull request, exiting!")
        raise SystemExit(1)

    if not os.getenv("GITHUB_REPOSITORY"):
        log.error("Cannot get repository name, exiting!")
        raise SystemExit(1)

    repo_and_pr["repo"].append(os.getenv("GITHUB_REPOSITORY"))
    repo_and_pr["pr"].append(int(os.getenv("GITHUB_REF").split("/")[2]))

    return repo_and_pr


def do_code_review(gh_session: Github, repo_and_pr: dict):
    comments = []
    skipped_files = []
    repo = gh_session.get_repo(repo_and_pr["repo"][0])
    pr = repo.get_pull(repo_and_pr["pr"][0])

    log.info(f"Performing analysis on pull request {pr.number} for {repo.name}...")

    changed_files = pr.get_files()

    for item in changed_files:
        log.info(f"Having Salacious review diff for {item.filename}...")
        if not type(item) == "str":
            if item.patch is None:
                log.warning(f"Skipping empty source file {item.filename}...")
            elif len(item.patch) > constants.MAX_TOKENS:
                log.warning(
                    f"Skipping {item.filename} as size {len(item.patch)} exceeds the "
                    f"limit of {constants.MAX_TOKENS} consider smaller commits..."
                )
                skipped_files.append(item.filename)
            else:
                diff_comment = submit_to_gpt(
                    f"filename: {item.filename} ** {item.patch}"
                )
                if "comments" in diff_comment:
                    comments.append(json.dumps(diff_comment["comments"]))
                    log.info(f"Salacious has completed review of {item.filename}...")
                else:
                    log.error(
                        f"Salacious has failed review of {item.filename} trying again..."
                    )
                    diff_comment = submit_to_gpt(
                        f"filename: {item.filename} ** {item.patch}"
                    )
                    if "comments" in diff_comment:
                        comments.append(json.dumps(diff_comment["comments"]))
                        log.info(
                            f"Salacious has completed review of {item.filename}..."
                        )
                    else:
                        log.error(
                            f"Salacious has failed review of {item.filename} again giving up..."
                        )
                        skipped_files.append(item.filename)

    log.info("Analysis complete, submitting review...")

    if len(skipped_files) > 0:
        log.error(f"The following files were skipped {skipped_files}...")

    submit_review(comments=comments, pr=pr, skipped_files=skipped_files)


def submit_review(
    comments: list, pr: PullRequest.PullRequest, skipped_files: list
) -> None:
    review_body = "Salacious has reviewed your code, please see inline comments."

    if skipped_files:
        review_body += f"\n\n List of skipped files:\n{skipped_files}"

    if not os.getenv("GITHUB_TOKEN"):
        log.error("Please provide a valid GITHUB_TOKEN environment variable!")
        raise SystemExit(1)

    # Ruff: token is assigned but never used
    # token = os.getenv("GITHUB_TOKEN")

    log.debug(f"{comments=}")

    comments_object = [comment for comment in ast.literal_eval(comments[0])]

    try:
        pr.create_review(body=review_body, event="COMMENT", comments=comments_object)
    except GithubException as err:
        log.error(f"Failed to submit review due the following error: {err}!")

    log.info("Submitted pull request review, Salacious B. Crumb signing off!")


def submit_to_gpt(code: str) -> dict:
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": constants.PROMPT},
                {"role": "user", "content": code},
            ],
        )
    except openai.APIError as err:
        log.error(f"Salacious failed due to API error: {err.user_message}")

    review = {}

    try:
        review = json.loads(str(completion.choices[0].message.content))
    except Exception as e:
        log.error(f"Received malformed response from Salacious... {str(e)}")
        pass

    return review


def main():
    set_openai_key()
    gh_session = get_github_session()
    repo_and_pr = get_repo_and_pr()
    do_code_review(gh_session=gh_session, repo_and_pr=repo_and_pr)


if __name__ == "__main__":
    log = config.setup_logging()
    log.info(f"Starting {config.__project_name__} v{config.__version__}...")
    main()

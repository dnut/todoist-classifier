#!/usr/bin/env python3

import json
import logging
import os
import time
from textwrap import dedent
from typing import List, Annotated

import requests
from dotenv import load_dotenv
from openai import OpenAI

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict, NoDecode

TODOIST_URL = "https://api.todoist.com/api/v1"


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TODOIST_CATEGORIZER_")

    project_ids: Annotated[
        list[str], NoDecode, BeforeValidator(lambda x: [s for s in x.split(",")])
    ]
    todoist_api_token: str
    openai_api_key: str
    poll_interval_ms: int
    log_level: Annotated[int, BeforeValidator(lambda x: logging.getLevelNamesMapping()[x])] = "INFO"
    openai_model: str = "gpt-5-nano"


def main():
    load_dotenv()
    config = Config()

    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s %(levelname)s: %(message)s",
    )

    logging.info(
        f"categorizing projects {config.project_ids} with a "
        f"poll interval of {config.poll_interval_ms}"
    )

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {config.todoist_api_token}"})
    client = OpenAI(
        api_key=config.openai_api_key,
        max_retries=0,
        timeout=30.0,
    )

    while True:
        for project_id in config.project_ids:
            poll(session, client, project_id, config.openai_model)
        time.sleep(int(config.poll_interval_ms) / 1000)


def poll(session, client, project_id, model):
    # Fetch sections first. An incomplete section list is unsafe.
    sections, complete = fetch_all(session, "sections", project_id)
    if not complete or not sections:
        logging.error("Cannot proceed without a complete section list")
        return 1

    choices = [
        {
            "id": str(s["id"]),
            "name": s["name"],
            "description": s.get("description") or "",
        }
        for s in sections
    ]
    sections_by_name = {s["name"]: s["id"] for s in choices}
    sections_without_id = [{"name": s["name"], "description": s["description"]} for s in sections]

    # Fetch tasks. If pagination fails, process the pages already fetched.
    tasks, complete = fetch_all(session, "tasks", project_id)
    if not complete:
        logging.warning("Task list incomplete; processing fetched tasks")

    pending = [
        task for task in tasks if task.get("section_id") is None and task.get("parent_id") is None
    ]

    (logging.info if len(pending) else logging.debug)(
        "Found %d sections and %d uncategorized tasks",
        len(sections),
        len(pending),
    )

    seen = set()
    moved = 0
    failed = 0

    for task in pending:
        task_id = task.get("id", "?")
        name = task.get("content", "?")

        if task_id in seen:
            continue
        seen.add(task_id)

        try:
            section_name = classify_task(client, task, sections_without_id, model)

            if section_name not in sections_by_name:
                raise ValueError(f"Unknown section ID: {section_name}")

            section_id = sections_by_name[section_name]

            response = session.post(
                f"{TODOIST_URL}/tasks/{task_id}/move",
                json={"section_id": section_id},
                timeout=30,
            )
            response.raise_for_status()

            moved += 1
            logging.info("%s -> %s", name, section_name)

        except Exception as exc:
            failed += 1
            logging.error("Task %s (%s) failed: %s", task_id, name, exc)
            continue

    (logging.info if moved + failed + len(seen) else logging.debug)(
        "Finished: %d moved, %d failed, %d considered",
        moved,
        failed,
        len(seen),
    )
    return 0


def fetch_all(session, resource, project_id):
    """Fetch paginated Todoist resources, retaining successful pages."""
    items = []
    cursor = None

    while True:
        params = {"project_id": project_id, "limit": 200}
        if cursor:
            params["cursor"] = cursor

        try:
            response = session.get(
                f"{TODOIST_URL}/{resource}",
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            items.extend(data["results"])
            cursor = data.get("next_cursor")
        except Exception as exc:
            logging.error("Fetching %s failed: %s", resource, exc)
            return items, False

        if not cursor:
            return items, True


def classify_task(client, task, sections, model):
    """Ask OpenAI to select an existing Todoist section."""
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": dedent("""
                    Categorize the Todoist task into exactly one of the provided project sections.
                    Use the task name and description, along with the section names and descriptions.
                """).replace("\n", " "),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": {
                            "name": task["content"],
                            "description": task.get("description") or "",
                        },
                        "sections": sections,
                    }
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "classification",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "section_name": {
                            "type": "string",
                            "enum": [s["name"] for s in sections],
                        },
                    },
                    "required": ["section_name"],
                    "additionalProperties": False,
                },
            },
        },
    )

    if response.status != "completed" or not response.output_text:
        raise ValueError("Model returned no completed classification")

    return json.loads(response.output_text)["section_name"]


if __name__ == "__main__":
    raise SystemExit(main())

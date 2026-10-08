# Todoist Categorizer

Automatically categorize Todoist tasks into project sections. The service polls
selected projects, identifies tasks that have no section within the project,
asks an OpenAI model to choose the best matching section, and moves the task to
that section.

For example, a project with **Planning**, **Development**, and **Review**
sections can have a new task such as `draft project brief` placed in
**Planning** automatically.

## Prerequisites

- Python 3.13 or later
- A [Todoist API token](https://app.todoist.com/app/settings/integrations/developer)
- An OpenAI API key
- A Todoist project with one or more sections

## Quick start

These commands can be used to quickly get started running the code:

```bash
# clone the repo
git clone https://github.com/dnut/todoist-categorizer.git
cd todoist-categorizer

# install the service to a local folder
python3.13 -m venv .venv
source .venv/bin/activate
pip install .

# configure the service by modifying the .env file
cp example.env .env

# run the service
todoist-categorizer
```

The process runs until stopped. Use `Ctrl-C` to stop it.

> **Note:** Project IDs, rather than project names, are required. You can list
> them with the [Todoist Projects API](https://developer.todoist.com/rest/v1/#get-all-projects).

## Docker

A `Dockerfile` is provided to facilitate compatibility with docker-based
deployment pipelines. You can deploy this using docker-compose:

```yaml
services:
  todoist-categorizer:
    build: https://github.com/dnut/todoist-categorizer.git#master
    pull_policy: build
    restart: unless-stopped
    env_file: todoist-categorizer.env  # copy from example.env and modify
```

## How it works

- Processes one or more Todoist projects continuously.
- Considers only top-level tasks that are not already in a section.
- Uses task content and descriptions, plus section names and descriptions, to
  choose the best semantic match.
- Moves a task only to a section that already exists in that project.
- Leaves subtasks and already-sectioned tasks unchanged.

The classifier is constrained to return one of the sections supplied by
Todoist. It does not create projects or sections.


## Configuration

Settings may be supplied through environment variables or a `.env` file. All
required categorizer settings use the `TODOIST_CATEGORIZER_` prefix.

| Variable                                | Required | Description                                                                                                                                                                                                                                                                    |
| --------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `TODOIST_CATEGORIZER_TODOIST_API_TOKEN` | Yes      | Todoist personal API token used to read projects and move tasks.                                                                                                                                                                                                               |
| `TODOIST_CATEGORIZER_OPENAI_API_KEY`    | Yes      | OpenAI API key used for classification.                                                                                                                                                                                                                                        |
| `TODOIST_CATEGORIZER_PROJECT_IDS`       | Yes      | Comma-separated Todoist project IDs, without spaces. This can be extracted from the URL when viewing a Todoist project. It's the part of the url that comes after the project name. It's the `abcdefg12345` in `https://app.todoist.com/app/project/project-name-abcdefg12345` |
| `TODOIST_CATEGORIZER_POLL_INTERVAL_MS`  | Yes      | Delay between complete polling cycles, in milliseconds. `2000` polls every two seconds.                                                                                                                                                                                        |
| `TODOIST_CATEGORIZER_LOG_LEVEL`         | No       | Python log level. Defaults to `INFO`; use `DEBUG` for detailed polling output.                                                                                                                                                                                                 |
| `TODOIST_CATEGORIZER_OPENAI_MODEL`      | No       | OpenAI model to use. Defaults to `gpt-5-nano`.                                                                                                                                                                                                                                 |


## Preparing a Todoist project

1. Create or choose a Todoist project you want to organize.
2. Add sections that represent its workflow or categories, such as `Planning`,
   `In progress`, `Waiting`, and `Done` for a project workflow.
3. Optionally add descriptions to sections to make their intended contents
   clearer to the model.
4. Add the project ID to `TODOIST_CATEGORIZER_PROJECT_IDS` and start the
   service.

Use distinct section names within a project. The categorizer identifies the
model's choice by section name, so duplicate names are ambiguous.

## Development

[uv](https://docs.astral.sh/uv/) can install the locked development environment
and run the command without manually managing a virtual environment:

```bash
uv sync
uv run todoist-categorizer
```

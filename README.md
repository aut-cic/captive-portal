# Captive Portal

## Introduction

This django application writen by [Masoud Sadri](https://github.com/msadri70) years ago does management on internet.
In the first generation of the system this captive portal provides APIs for gathering
user information which was moved into [internet](https://github.com/aut-cic/internet) after a few months so those APIs
are useless now.

## Development Setup (uv)

- Python 3.14.x is required (the lockfile is pinned to 3.14). uv can download it automatically if not present.
- Install dependencies with `uv sync` (add `--extra dev` for type-checking tooling).
- Run the Django app with `uv run python CaptivePortal/manage.py runserver 0.0.0.0:8000`.
- Apply migrations with `uv run python CaptivePortal/manage.py migrate` if you are using the local sqlite database; the production settings point at external MySQL instances.

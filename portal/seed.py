"""Seed only public project content, without overwriting existing projects."""
import json
from pathlib import Path
from app import db


def seed():
    projects = json.loads((Path(__file__).parent / 'catalog/projects.json').read_text())['projects']
    with db() as connection:
        columns = {row['name'] for row in connection.execute('PRAGMA table_info(projects)')}
        for project in projects:
            values = {key: value for key, value in project.items() if key in columns and key != 'id'}
            names = list(values)
            connection.execute(
                f"INSERT OR IGNORE INTO projects ({','.join(names)}) VALUES ({','.join('?' for _ in names)})",
                list(values.values()),
            )


if __name__ == '__main__':
    seed()

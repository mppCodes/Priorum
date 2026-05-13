import os
import requests
from requests.auth import HTTPBasicAuth
from app.models.task import TaskCreate

JIRA_BASE_URL = "https://hackatongrupodosviewnext.atlassian.net"
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def map_priority(priority: str):
    """
    Mapea prioridades internas -> Jira
    """
    mapping = {
        "alta": "High",
        "media": "Medium",
        "baja": "Low",
    }
    return mapping.get(priority, "Medium")


async def create_jira_task(task: TaskCreate):
    """
    Crea una issue en Jira usando los datos del modelo TaskCreate
    """

    url = f"{JIRA_BASE_URL}/rest/api/3/issue"

    description_text = f"""
Proyecto: {task.project}

Deadline: {task.deadline}

Tags: {", ".join(task.tags)}
"""

    payload = {
        "fields": {
            "project": {
                "key": "KAN"
            },

            "summary": task.title,

            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": description_text
                            }
                        ]
                    }
                ]
            },

            "issuetype": {
                "name": "Task"
            },

            "priority": {
                "name": map_priority(task.priority.value)
            },

            "labels": task.tags
        }
    }

    response = requests.post(
        url,
        json=payload,
        headers=HEADERS,
        auth=auth
    )

    if response.status_code not in [200, 201]:
        raise Exception(
            f"Error creando issue en Jira: "
            f"{response.status_code} - {response.text}"
        )

    return response.json()
import requests
import logging


logger = logging.getLogger("discord_bot.taiga")


class TaigaClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.token = None
        self.project_cache = {}
        self._reference_cache={} 

    def login(self):
        logger.info("Logging in to Taiga at %s as %s", self.base_url, self.username)
        resp = requests.post(
            f"{self.base_url}/auth",
            json={
                "type": "normal",
                "username": self.username,
                "password": self.password,
            },
        )

        resp.raise_for_status()

        self.token = resp.json()["auth_token"]
        logger.info("Taiga login succeeded")
        return self.token

    def _headers(self):
        if not self.token:
            self.login()

        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _request(self, method, path, **kwargs):
        logger.info("Taiga request %s %s", method, path)
        resp = requests.request(
            method,
            f"{self.base_url}{path}",
            headers=self._headers(),
            **kwargs,
        )

        if resp.status_code == 401:
            logger.warning("Taiga request returned 401, retrying after re-login")
            self.login()
            resp = requests.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers(),
                **kwargs,
            )

        if not resp.ok:
            logger.error("Taiga error status=%s response=%s", resp.status_code, resp.text)

        resp.raise_for_status()

        logger.info("Taiga request succeeded status=%s", resp.status_code)
        return resp.json() if resp.text else None

    def get_project_id(self, slug):
        if slug not in self.project_cache:
            logger.info("Project id for slug %s not cached; fetching", slug)
            data = self._request(
                "GET",
                "/projects/by_slug",
                params={"slug": slug},
            )
            self.project_cache[slug] = data["id"]
            logger.info("Cached project id %s for slug %s", self.project_cache[slug], slug)

        return self.project_cache[slug]

    def create(self, resource, payload):
        logger.info("Creating Taiga resource=%s payload=%s", resource, payload)
        return self._request(
            "POST",
            f"/{resource}",
            json=payload,
        )

    def list(self, resource, **filters):
        logger.info("Listing Taiga resource=%s filters=%s", resource, filters)
        return self._request(
            "GET",
            f"/{resource}",
            params=filters,
        )

    def update(self, resource,id, payload):
        logger.info("Updating Taiga resource=%s id=%s payload=%s", resource, id, payload)
        return self._request(
            "PATCH",
            f"/{resource}/{id}",
            json=payload
        )


    def get(self, resource, id):
        logger.info("Fetching Taiga resource=%s id=%s", resource, id)
        return self._request(
            "GET",
            f"/{resource}/{id}",
        )

    def get_reference_data(self, resource, project_id, force_refresh=False):
        cache_key = (resource,project_id)
        if force_refresh or cache_key not in self._reference_cache:
            logger.info("Fetching Taiga reference data resource=%s project=%s", resource, project_id)
            data = self._request("GET", f"/{resource}", params={"project":project_id})
            self._reference_cache[cache_key] = data or []
        return self._reference_cache[cache_key]

    def get_priorities(self,project_id):
        return self.get_reference_data("priorities",project_id)

    def get_severities(self, project_id):
        return self.get_reference_data("severities", project_id)

    def get_issue_types(self, project_id):
        return self.get_reference_data("issue-types", project_id)
    
    def get_statuses(self, project_id, resource):
        # Each item type has its own status table in Taiga.
        status_resource = {
            "issues": "issue-statuses",
            "tasks": "task-statuses",
            "userstories": "userstory-statuses",
            "epics": "epic-statuses",
        }.get(resource)
        if not status_resource:
            raise ValueError(f"No status resource known for '{resource}'")
        return self.get_reference_data(status_resource, project_id)

    def get_by_ref(self, resource,project_id,ref):
        logger.info("Fetching Taiga resource=%s by ref=%s project=%s", resource, ref, project_id)
        return self._request(
        "GET",
        f"/{resource}/by_ref",
        params={"project": project_id, "ref": ref},
    )

    def get_memberships(self, project_id):
        return self.get_reference_data("memberships", project_id)
 
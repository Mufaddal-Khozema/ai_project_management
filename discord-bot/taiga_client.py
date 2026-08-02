import requests

class TaigaClient:

    # basic project initialization
    def __init__(self,base_url, username,password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
        self.project_cache = {}

    # request send to base url for authorizing token via params
    def login(self):
        resp = requests.post(f"{self.base_url}/auth",json={
            "type":"normal",
            "username": self.username,
            "password": self.password
        })
        resp.raise_for_status()
        self.token= resp.json()["auth_token"]
        return self.token

    def _headers(self):
        # if there is no token then reset login and get auth token.
        if not self.token:
            self.login()
        return {"Authorization": f"Bearer {self.token}"}
    
    def _request(self,method, path, **kwargs):
        resp = requests.request(method, f"{self.base_url}{path}",headers=self._headers(), **kwargs)
        
        if resp.status_code == 401:
            self.login()
            resp= requests.request(method, f"{self.base_url}{path}",headers=self._headers(), **kwargs)
        
        resp.raise_for_status()
        return resp.json() if resp.text else None
    
    # if slug is not in project cache then, send a request on the slug and get the id of the project
    def get_project_id(self, slug):
        if slug not in self.project_cache:
            data= self._request("GET","/projects/by_slug",params={"slug":slug})
            self.project_cache[slug]= data["id"]
        return self.project_cache[slug]
    
    # CRUD
    # resource are named entities such as issues, tasks, epics

    def create(self, resource, payload):
        return self._request("POST",f"/{resource}", json=payload)

    # def list(self,resource, **filters):
    #     return self._request("GET", f"/{resource}", params=filters)
    
    # def get(self,resource,id):
    #     return self._request("GET",f"/{resource}/{id}")
    
    # def update(self,resource, payload,id):
    #     return self._request("POST",f"/{resource}/{id}", json=payload)
    
    # # change this to deactivate instead of deleting.
    # def delete(self, resource,payload, id):
    #     return self._request("DELETE",f"/{resource}/{id}")
import json
import urllib.request
from odoo import models

class BaseFetch(models.AbstractModel):
    _inherit = "base"

    def bfetch(self,url, method, data = None):
        req = urllib.request.Request(url=url, data=json.dumps(data).encode('UTF-8') if data else None, method=method ,headers={
            "Content-Type":"application/json",
        })

        return json.loads(urllib.request.urlopen(req).read().decode('UTF-8'))
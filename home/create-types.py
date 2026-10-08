# Create Homebox entity types with default templates. usage: python3 hb_types.py <base url> <token>
import json, sys, urllib.request
BASE, TOK = sys.argv[1].rstrip("/") + "/api/v1", sys.argv[2]
H = {"Authorization": "Bearer " + TOK, "Content-Type": "application/json"}
def req(m, u, body=None):
    r = urllib.request.urlopen(urllib.request.Request(BASE + u, method=m, data=json.dumps(body).encode() if body is not None else None, headers=H))
    t = r.read(); return json.loads(t) if t else None
TYPES = [
    ("Electronics", "Computers, TVs, phones, speakers, gadgets", True, True, ["Specs", "Support URL"]),
    ("Appliance", "Kitchen and household appliances", True, True, ["Installed on", "Parts / filters", "Support URL"]),
    ("Furniture & Decor", "Furniture, rugs, lamps, art", False, True, ["Dimensions", "Material / colour"]),
    ("Tool", "Power tools, hand tools, garden tools", True, True, ["Battery platform", "Power"]),
]
existing = {t["name"]: t for t in req("GET", "/entity-types")}
templates = {t["name"]: t for t in req("GET", "/templates")}
for name, desc, warranty, purchase, fields in TYPES:
    tname = f"{name} defaults"
    tpl = templates.get(tname) or req("POST", "/templates", {
        "name": tname, "description": f"Fields for new {name.lower()} items", "notes": "",
        "defaultQuantity": 1, "defaultInsured": False, "defaultLifetimeWarranty": False,
        "includeWarrantyFields": warranty, "includePurchaseFields": purchase, "includeSoldFields": False,
        "fields": [{"type": "text", "name": f, "textValue": ""} for f in fields]})
    et = existing.get(name)
    if et:
        et = req("PUT", f"/entity-types/{et['id']}", {"id": et["id"], "name": name, "isLocation": False, "icon": "", "defaultTemplateId": tpl["id"]})
    else:
        et = req("POST", "/entity-types", {"name": name, "isLocation": False, "icon": "", "defaultTemplateId": tpl["id"]})
    print(name, "->", tpl["name"], [f["name"] for f in req("GET", f"/templates/{tpl['id']}")["fields"]])
print("types:", [t["name"] for t in req("GET", "/entity-types")])

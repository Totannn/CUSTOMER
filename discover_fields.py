"""
discover_fields.py  -  List the contact properties in YOUR HubSpot portal.

Run this AFTER setting your token:
    python discover_fields.py

It prints every contact property (label + internal name + sample values).
Copy the output and send it back, and we'll build the exact PROPERTY_MAP.
"""
import requests

import hubspot_sync


def main():
    token = hubspot_sync.get_token()
    if not token:
        print("No token found. Set HUBSPOT_TOKEN or create hubspot_token.txt first.")
        print("See the setup steps at the top of hubspot_sync.py")
        return

    url = "https://api.hubapi.com/crm/v3/properties/contacts"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code == 401:
        print("Token rejected (401). Check the token and that it has "
              "'crm.schemas.contacts.read' scope.")
        return
    resp.raise_for_status()

    props = resp.json().get("results", [])
    # Hide HubSpot's huge list of internal analytics props to keep it readable;
    # show custom + commonly useful ones first.
    custom = [p for p in props if not p.get("hubspotDefined")]
    defined = [p for p in props if p.get("hubspotDefined")]

    def show(group, title):
        print(f"\n===== {title} ({len(group)}) =====")
        for p in sorted(group, key=lambda x: x.get("label", "")):
            opts = ""
            if p.get("options"):
                vals = [o.get("value") for o in p["options"][:6]]
                opts = "  values: " + ", ".join(v for v in vals if v)
            print(f"  {p.get('label','?'):<38} -> {p.get('name','?'):<35}"
                  f" [{p.get('type','?')}]{opts}")

    show(custom, "YOUR CUSTOM PROPERTIES")
    show(defined, "HUBSPOT STANDARD PROPERTIES")
    print(f"\nTotal: {len(props)} properties. "
          "Send the CUSTOM list (and any standard ones you use) back to map them.")


if __name__ == "__main__":
    main()

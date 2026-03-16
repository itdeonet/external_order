import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


def convert_json(data: dict[str, Any]) -> dict[str, Any]:
    recipient: dict[str, Any] = data.get("recipient", {})
    name_lines: list[str] = recipient.get("name_lines", [])
    street_lines: list[str] = recipient.get("street_lines", [])
    assert len(name_lines) >= 2, "Expected at least 2 name lines"

    converted_data: dict[str, Any] = {
        "sale_id": int(re.sub(r"S0*", "", data.get("order_number", ""))),
        "administration_id": 2,
        "customer_id": 5380,
        "order_provider": "HARMAN JBL",
        "pricelist_id": 2,
        "remote_order_id": data.get("remote_number", ""),
        "shipment_type": "harman%b2c"
        if "B2C" in data.get("shipment_type", "")
        else "harman%b2b",
        "description": f"HARMAN JBL order {data.get('remote_number', '')} / {data.get('delivery_note_number', '')}",
        "delivery_instructions": "",
        "status": "confirmed",
        "ship_to": {
            "remote_customer_id": recipient.get("customer_number", ""),
            "company_name": name_lines[0] if name_lines[1] else "",
            "contact_name": name_lines[1] or name_lines[0],
            "email": recipient.get("email_address", ""),
            "phone": recipient.get("phone_number", ""),
            "street1": street_lines[0],
            "street2": street_lines[1] if len(street_lines) > 1 else "",
            "city": recipient.get("city", ""),
            "state": recipient.get("region", ""),
            "postal_code": recipient.get("postal_code", ""),
            "country_code": recipient.get("country_code", ""),
        },
        "line_items": [
            {
                "line_id": item.get("line_number", ""),
                "product_code": item.get("product_sku", ""),
                "quantity": item.get("quantity", 0),
                "artwork": {
                    "artwork_id": item.get("artwork_id", ""),
                    "artwork_line_id": item.get("line_number", ""),
                    "design_url": f"https://api.spectrumcustomizer.com/{item.get('artwork_endpoint', '').lstrip('/')}/"
                    if item.get("artwork_endpoint")
                    else "",
                    "design_paths": [
                        re.sub(r"file:///", "", path)
                        for path in item.get("downloaded_artwork_urls", [])
                        if path.startswith("file:///")
                    ],
                    "placement_url": f"https://api.spectrumcustomizer.com/{item.get('placement_endpoint', '').lstrip('/')}/"
                    if item.get("placement_endpoint")
                    else "",
                    "placement_path": re.sub(
                        r"file:///", "", item.get("downloaded_placement_url", "")
                    )
                    if item.get("downloaded_placement_url")
                    else "",
                },
            }
            for item in data.get("items", [])
        ],
        "created_at": (dt.datetime.now() - dt.timedelta(days=2)).isoformat(),
        "ship_at": (dt.date.today() + dt.timedelta(days=2)).isoformat(),
    }
    return converted_data


def update_paths(data: dict[str, Any]) -> None:
    digitals_dir = Path(
        "C:\\users\\Administrator\\projects-data\\external_order\\digitals"
    )
    for item in data["line_items"]:
        item["artwork"]["design_paths"] = [
            str(digitals_dir / Path(path).name)
            for path in item["artwork"]["design_paths"]
            if path
        ]
        path = Path(item["artwork"]["placement_path"])
        item["artwork"]["placement_path"] = str(digitals_dir / path.name)
        for path in item["artwork"]["design_paths"] + [
            item["artwork"]["placement_path"]
        ]:
            if not Path(path).is_file():
                Path(path).touch()


def main():
    # read folder name from command line argument
    import sys

    if len(sys.argv) != 2:
        print("Usage: python order-json-converter.py <folder_path>")
        sys.exit(1)

    folder_path = Path(sys.argv[1])
    if not folder_path.is_dir():
        print(f"Error: {folder_path} is not a valid directory.")
        sys.exit(1)

    for file in folder_path.glob("S*.json"):
        try:
            try:
                data: dict[str, Any] = json.loads(file.read_text())  # type: ignore
            except UnicodeDecodeError:
                data = json.loads(file.read_text(encoding="utf-8-sig"))  # type: ignore
            new_file = file.parent / f"{data.get('remote_number', file.stem)}.json"
            converted = convert_json(data)
            update_paths(converted)
            new_file.write_text(
                json.dumps(converted, indent=2, default=str), encoding="utf-8"
            )
        except Exception as e:
            print(f"Error processing {file}: {e}")


if __name__ == "__main__":
    main()

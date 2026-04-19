import asyncio

from app.tools.diagnose_symptom import run as diag
from app.store import parts_db


async def main():
    r = await diag(symptom="ice maker not making ice", appliance_type="fridge", brand="Whirlpool")
    for c in r["candidates"]:
        ps = c["ps_number"]
        p = parts_db.get_part(ps)
        if not p:
            print(ps, c.get("name"), "(no blob)")
            continue
        print(f"{ps}  meta_name={c.get('name')!r}  db_name={p.name!r}  oem={p.oem_number}")
        print(f"    source_url={p.source_url}")
        print(f"    image_url={p.image_url}")


asyncio.run(main())

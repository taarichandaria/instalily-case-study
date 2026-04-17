"""HTML -> Part. Depends on PartSelect's current DOM structure (see
memory/feedback_partselect_scraping.md for landmark reference)."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.schemas import (
    ApplianceType,
    InstallDifficulty,
    Part,
    RelatedPart,
)

BASE = "https://www.partselect.com"

PS_NUMBER_RE = re.compile(r"PS\d{6,}")
PS_HREF_RE = re.compile(r"/PS(\d{6,})[-.]")
PRICE_RE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)")
INSTALL_TIME_RE = re.compile(
    r"(?:less than\s+)?(\d+)\s*(?:-\s*(\d+)\s*)?(min|mins|minute|minutes|hour|hours|hr|hrs)",
    re.IGNORECASE,
)


# -- helpers ---------------------------------------------------------------


def _section_content(soup: BeautifulSoup, anchor_id: str) -> Tag | None:
    """Section content lives as the anchor div's next sibling, not inside it."""
    anchor = soup.find(id=anchor_id)
    if anchor is None:
        return None
    nxt = anchor.find_next_sibling()
    return nxt if isinstance(nxt, Tag) else None


def _text_after_label(container: Tag, label: str) -> str | None:
    """Find a label like 'PartSelect Number' and return the value text from the
    same container. Only looks at the immediate parent element (don't escalate —
    that hits the outer page content)."""
    for node in container.find_all(string=re.compile(re.escape(label), re.IGNORECASE)):
        parent = node.parent
        if parent is None:
            continue
        txt = parent.get_text(" ", strip=True)
        stripped = re.sub(re.escape(label), "", txt, flags=re.IGNORECASE).strip(": \n\t")
        if stripped:
            return stripped
    return None


def _classify_appliance(text: str) -> ApplianceType | None:
    t = text.lower()
    if "refrigerator" in t or "fridge" in t:
        return "fridge"
    if "dishwasher" in t:
        return "dishwasher"
    return None


def _normalize_difficulty(text: str) -> InstallDifficulty:
    t = text.lower()
    if "very easy" in t or "really easy" in t:
        return "easy"
    if "easy" in t:
        return "easy"
    if "moderate" in t or "medium" in t:
        return "moderate"
    if "difficult" in t or "hard" in t:
        return "difficult"
    return "unknown"


def _parse_install_time(text: str) -> int | None:
    """Return upper-bound minutes from phrases like 'Less than 15 mins' or '30-60 mins'."""
    m = INSTALL_TIME_RE.search(text)
    if not m:
        return None
    lo = int(m.group(1))
    hi = int(m.group(2)) if m.group(2) else lo
    unit = m.group(3).lower()
    mult = 60 if unit.startswith(("hr", "hour")) else 1
    return hi * mult


# -- main entrypoint -------------------------------------------------------


def parse_part_page(html: str, source_url: str) -> Part | None:
    """Parse a PartSelect part detail page into a Part. Returns None if the
    page doesn't look like a part page (missing key fields)."""
    soup = BeautifulSoup(html, "lxml")

    h1 = soup.find("h1")
    if h1 is None:
        return None
    name = h1.get_text(" ", strip=True)

    # PS number — from text block, then URL fallback
    ps_raw = _text_after_label(soup, "PartSelect Number") or ""
    ps_match = PS_NUMBER_RE.search(ps_raw) or PS_NUMBER_RE.search(source_url)
    if not ps_match:
        return None
    ps_number = ps_match.group(0)

    # OEM number
    oem_raw = _text_after_label(soup, "Manufacturer Part Number") or ""
    oem_match = re.search(r"[A-Z0-9]{5,}", oem_raw)
    oem_number = oem_match.group(0) if oem_match else None

    # Brand — from "Manufactured by X for ..." line
    brand: str | None = None
    mbrand = _text_after_label(soup, "Manufactured by") or ""
    bmatch = re.match(r"([A-Za-z]+)", mbrand.strip())
    if bmatch:
        brand = bmatch.group(1)

    # Appliance type — derive from name/title
    appliance = _classify_appliance(name) or _classify_appliance(
        soup.title.get_text(strip=True) if soup.title else ""
    )
    if appliance is None:
        # fall back to "works with" list
        tr = _section_content(soup, "Troubleshooting")
        if tr:
            for li in tr.select("ul.list-disc li"):
                a = _classify_appliance(li.get_text(" ", strip=True))
                if a:
                    appliance = a
                    break
    if appliance is None:
        return None  # out of scope

    # Price + stock
    price: float | None = None
    in_stock: bool | None = None
    # `.pd__price` includes the `$`; `.js-partPrice` is a bare number. Prefer the
    # labeled one; fall back to bare.
    price_tag = soup.select_one(".pd__price") or soup.select_one(".js-partPrice")
    if price_tag:
        raw = price_tag.get_text(" ", strip=True)
        m = PRICE_RE.search(raw) or re.search(r"([0-9]+(?:\.[0-9]{1,2})?)", raw)
        if m:
            try:
                price = float(m.group(1))
            except ValueError:
                price = None
    # stock via #mainAddToCart nearby text
    main_cart = soup.find(id="mainAddToCart")
    if main_cart:
        cart_text = main_cart.get_text(" ", strip=True).lower()
        if "in stock" in cart_text:
            in_stock = True
        elif "out of stock" in cart_text or "special order" in cart_text:
            in_stock = False

    # Repair rating: difficulty + time. Classes are like `pd__repair-rating__container`
    # — use an attribute-contains selector to match the whole family.
    difficulty: InstallDifficulty = "unknown"
    install_time: int | None = None
    rating = soup.select_one('[class*="pd__repair-rating__container"]')
    if rating:
        rtext = rating.get_text(" ", strip=True)
        difficulty = _normalize_difficulty(rtext)
        install_time = _parse_install_time(rtext)

    # Description
    description = ""
    desc_sib = _section_content(soup, "ProductDescription")
    if desc_sib:
        # Take first substantial paragraph of text
        paragraphs = [p.get_text(" ", strip=True) for p in desc_sib.find_all(["p", "div"])]
        paragraphs = [p for p in paragraphs if len(p) > 60]
        description = paragraphs[0] if paragraphs else desc_sib.get_text(" ", strip=True)
        description = description[:2000]

    # Symptoms (Troubleshooting section, first .list-disc ul)
    symptoms: list[str] = []
    tr = _section_content(soup, "Troubleshooting")
    if tr:
        for block in tr.find_all("div", recursive=False):
            label = block.find(class_="bold")
            if label and "symptom" in label.get_text(strip=True).lower():
                for li in block.select("ul.list-disc li"):
                    s = li.get_text(" ", strip=True)
                    if s:
                        symptoms.append(s)
                break

    # Install video (YouTube ID in data-yt-init)
    video_url: str | None = None
    pv = _section_content(soup, "PartVideos")
    if pv:
        yt = pv.select_one("[data-yt-init]")
        if yt:
            yt_id = yt.get("data-yt-init")
            if yt_id:
                video_url = f"https://www.youtube.com/watch?v={yt_id}"

    # Install steps — PartSelect's "install instructions" are crowd-sourced customer
    # repair stories. Pull the top 3 as (title, instruction) pairs.
    install_steps: list[str] = []
    install_sib = _section_content(soup, "InstallationInstructions")
    if install_sib:
        # Match only the outer .repair-story divs (not .repair-story__title etc.)
        for story in install_sib.find_all("div", class_="repair-story"):
            title_el = story.select_one(".repair-story__title")
            instr_el = story.select_one(".repair-story__instruction")
            title = title_el.get_text(" ", strip=True) if title_el else ""
            instr = instr_el.get_text(" ", strip=True) if instr_el else ""
            # instr can contain nested "Other Parts Used" — trim on that marker
            instr = re.split(r"Other Parts Used", instr, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            combined = f"{title} — {instr}" if title and instr else title or instr
            if combined and len(combined) > 15:
                install_steps.append(combined[:500])
            if len(install_steps) >= 3:
                break

    # You may also need — multiple <a> tags per card (image + title). Collect the
    # longest-text name per PS number and the card's price.
    ymn: list[RelatedPart] = []
    rp = _section_content(soup, "RelatedParts")
    if rp:
        names: dict[str, str] = {}
        prices: dict[str, float] = {}
        for a in rp.find_all("a", href=PS_HREF_RE):
            m = PS_HREF_RE.search(a.get("href", ""))
            if not m:
                continue
            ps = f"PS{m.group(1)}"
            txt = a.get_text(" ", strip=True)
            if txt and len(txt) > len(names.get(ps, "")):
                names[ps] = txt
            # price from a nearby card container
            if ps not in prices:
                card = a.find_parent("div") or a.parent
                if card:
                    pm = PRICE_RE.search(card.get_text(" ", strip=True))
                    if pm:
                        try:
                            prices[ps] = float(pm.group(1))
                        except ValueError:
                            pass
        for ps, nm in names.items():
            ymn.append(RelatedPart(ps_number=ps, name=nm, price_usd=prices.get(ps)))
            if len(ymn) >= 10:
                break

    # Compat models (first page of the cross-reference)
    compat: list[str] = []
    mcr = _section_content(soup, "ModelCrossReference")
    if mcr:
        seen_m: set[str] = set()
        for a in mcr.find_all("a", href=re.compile(r"/Models/([A-Z0-9]+)/?")):
            m = re.search(r"/Models/([A-Z0-9]+)", a.get("href", ""))
            if not m:
                continue
            mn = m.group(1)
            if mn in seen_m:
                continue
            seen_m.add(mn)
            compat.append(mn)

    # Main product image
    image_url: str | None = None
    main_img = soup.select_one("img.main-image, img.pd__img, #main img")
    if main_img:
        src = main_img.get("data-src") or main_img.get("src")
        if src and src.startswith("http"):
            image_url = src
        elif src and src.startswith("/"):
            image_url = urljoin(BASE, src)

    return Part(
        ps_number=ps_number,
        oem_number=oem_number,
        name=name,
        brand=brand,
        appliance_type=appliance,
        price_usd=price,
        in_stock=in_stock,
        description=description,
        symptoms_fixed=symptoms,
        install_difficulty=difficulty,
        install_time_min=install_time,
        install_steps=install_steps,
        install_tools=[],
        install_video_url=video_url,
        safety_flags=[],
        you_may_also_need=ymn,
        compat_models=compat,
        image_url=image_url,
        source_url=source_url,
    )


def parse_model_parts_page(html: str, model_number: str) -> dict[str, str]:
    """From a model page, return a mapping of PS number -> URL path (e.g.
    `/PS3406971-Whirlpool-W10195416-Lower-Dishrack-Wheel.htm`). We need the
    full slug — the bare `/PSxxx.htm` form returns 500 on PartSelect."""
    soup = BeautifulSoup(html, "lxml")
    out: dict[str, str] = {}
    for a in soup.find_all("a", href=PS_HREF_RE):
        href = a.get("href", "")
        m = PS_HREF_RE.search(href)
        if not m:
            continue
        ps = f"PS{m.group(1)}"
        if ps in out:
            continue
        # Strip query string; keep the `/PSxxx-slug.htm` path only.
        path = href.split("?", 1)[0]
        out[ps] = path
    return out

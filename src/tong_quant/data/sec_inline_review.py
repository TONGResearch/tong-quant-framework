"""Conservative single-document Inline XBRL numeric subset, not a conformance validator."""

import re
from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal, localcontext
from hashlib import sha256
from io import BytesIO
from typing import Any, cast
from xml.etree import ElementTree as ET
from xml.parsers import expat

from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.sec_body import MAX_BODY_BYTES
from tong_quant.domain.models import require_timezone
from tong_quant.version import SEC_INLINE_EXCLUSION_VERSION, SEC_INLINE_REVIEW_VERSION

IX = "http://www.xbrl.org/2013/inlineXBRL"
XBRLI = "http://www.xbrl.org/2003/instance"
ISO = "http://www.xbrl.org/2003/iso4217"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
TRANSFORMS = {
    ("http://www.xbrl.org/inlineXBRL/transformation/2015-02-26", "numdotdecimal"),
    ("http://www.xbrl.org/inlineXBRL/transformation/2020-02-12", "num-dot-decimal"),
    ("http://www.xbrl.org/inlineXBRL/transformation/2022-02-16", "num-dot-decimal"),
}
DEFAULT_TAGS = ("RevenueFromContractWithCustomerExcludingAssessedTax", "NetIncomeLoss",
                "NetCashProvidedByUsedInOperatingActivities")


def _bounded_xml(content: bytes) -> None:
    if not isinstance(content, bytes) or not 0 < len(content) <= MAX_BODY_BYTES:
        raise ValueError("body size outside supported bounds")
    parser = expat.ParserCreate()
    depth = nodes = 0

    def start(name: str, attrs: dict[str, str]) -> None:
        nonlocal depth, nodes
        depth += 1
        nodes += 1
        if depth > 128 or nodes > 250_000 or len(attrs) > 256:
            raise ValueError("XML structure exceeds review bounds")

    def end(name: str) -> None:
        nonlocal depth
        depth -= 1

    def doctype(name: str, system: str | None, public: str | None, subset: int) -> None:
        if name.lower() != "html" or system or public or subset:
            raise ValueError("DTD/entity expansion is unsupported")

    def entity(*args: Any) -> None:
        raise ValueError("DTD/entity expansion is unsupported")

    def external(*args: Any) -> int:
        raise ValueError("external entities are unsupported")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.StartDoctypeDeclHandler = doctype
    parser.EntityDeclHandler = entity
    parser.ExternalEntityRefHandler = external
    parser.Parse(content, True)


def _qname(value: str, scope: dict[str, str]) -> tuple[str, str]:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*(?::[A-Za-z_][A-Za-z0-9_.-]*)?", value) is None:
        raise ValueError("invalid QName")
    prefix, local = value.split(":") if ":" in value else ("", value)
    if prefix not in scope:
        raise ValueError("unbound QName")
    return scope[prefix], local


def _date(text: str | None) -> str:
    if not text or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text) is None:
        raise ValueError("unsupported context date")
    return date.fromisoformat(text).isoformat()


def _context(element: ET.Element, cik: str, cutoff: datetime) -> dict[str, Any]:
    if (len(element.findall(f"{{{XBRLI}}}entity")) != 1
            or len(element.findall(f"{{{XBRLI}}}period")) != 1
            or any(child.tag not in {f"{{{XBRLI}}}entity", f"{{{XBRLI}}}period"}
                   for child in element)
            or element.find(f"{{{XBRLI}}}scenario") is not None
            or element.find(f"{{{XBRLI}}}entity/{{{XBRLI}}}segment") is not None):
        raise ValueError("dimensional or malformed context is unsupported")
    identifiers = element.findall(f"{{{XBRLI}}}entity/{{{XBRLI}}}identifier")
    entity = element.find(f"{{{XBRLI}}}entity")
    if len(identifiers) != 1 or entity is None or len(entity) != 1 or len(identifiers[0]):
        raise ValueError("ambiguous context entity")
    identifier = identifiers[0]
    text = (identifier.text or "").strip()
    if (identifier.get("scheme") != "http://www.sec.gov/CIK"
            or re.fullmatch(r"[0-9]{1,10}", text) is None or text.zfill(10) != cik):
        raise ValueError("context entity does not match CIK")
    period = element.find(f"{{{XBRLI}}}period")
    assert period is not None
    children = list(period)
    if len(children) == 1 and children[0].tag == f"{{{XBRLI}}}instant":
        start, end = None, _date(children[0].text)
    elif ([child.tag for child in children] ==
          [f"{{{XBRLI}}}startDate", f"{{{XBRLI}}}endDate"]):
        start, end = _date(children[0].text), _date(children[1].text)
        if start > end:
            raise ValueError("reversed context period")
    else:
        raise ValueError("unsupported context period")
    if end > cutoff.astimezone(UTC).date().isoformat():
        raise ValueError("future context period")
    return {"period_start": start, "period_end": end, "entity_cik": cik}


def _amount(element: ET.Element, scope: dict[str, str]) -> str:
    if (any(key in element.attrib for key in ("continuedAt", "tupleRef", "target", "tupleID"))
            or any(child.tag.startswith(f"{{{IX}}}") for child in element.iter()
                   if child is not element)):
        raise ValueError("continued/nested/targeted numeric content is unsupported")
    if element.get(f"{{{XSI}}}nil", "false") not in {"false", "0"}:
        raise ValueError("nil or malformed nil value is not zero")
    text = "".join(element.itertext()).strip()
    if len(text) > 128:
        raise ValueError("numeric text exceeds bounds")
    if "format" in element.attrib:
        if _qname(element.attrib["format"], scope) not in TRANSFORMS:
            raise ValueError("unsupported numeric transformation")
        # A strict subset of registry dot-decimal inputs, not full registry support.
        if re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?", text) is None:
            raise ValueError("unsupported dot-decimal lexical form")
        text = text.replace(",", "")
    elif re.fullmatch(r"-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)", text) is None:
        raise ValueError("unsupported decimal lexical form")
    scale = element.get("scale", "0")
    decimals = element.get("decimals", "")
    sign = element.get("sign", "")
    if (re.fullmatch(r"-?[0-9]{1,2}", scale) is None or not -18 <= int(scale) <= 18
            or sign not in {"", "-"} or sign and text.startswith("-")
            or decimals != "INF" and re.fullmatch(r"-?[0-9]{1,3}", decimals) is None):
        raise ValueError("unsupported scale/sign/precision")
    with localcontext() as context:
        context.prec = 100
        value = Decimal(text) * (Decimal(10) ** int(scale)) * (-1 if sign else 1)
        exponent = value.as_tuple().exponent
        if (abs(value) > Decimal(10) ** 24 or not isinstance(exponent, int)
                or exponent < -36):
            raise ValueError("amount outside review bounds")
        return format(value, "f")


def _exclusion_structure(element: ET.Element, contexts: dict[str | None, ET.Element],
                         ids: Counter[str | None]) -> dict[str, Any]:
    context_id = element.get("contextRef")
    identity = ("MISSING_REFERENCE" if not context_id else
                "AMBIGUOUS_ID" if ids[context_id] > 1 else
                "MISSING_CONTEXT" if context_id not in contexts else "UNIQUE_CONTEXT")
    context = contexts.get(context_id) if identity == "UNIQUE_CONTEXT" else None
    return {"context_reference_status": identity,
        "entity_count": len(context.findall(f"{{{XBRLI}}}entity")) if context is not None else None,
        "period_count": len(context.findall(f"{{{XBRLI}}}period")) if context is not None else None,
        "segment_count": len(context.findall(f"{{{XBRLI}}}entity/{{{XBRLI}}}segment"))
            if context is not None else None,
        "scenario_count": len(context.findall(f"{{{XBRLI}}}scenario"))
            if context is not None else None,
        "other_context_child_count": sum(child.tag not in {
            f"{{{XBRLI}}}entity", f"{{{XBRLI}}}period", f"{{{XBRLI}}}scenario"}
            for child in context) if context is not None else None,
        "context_validity": "NOT_VALIDATED", "dimension_semantics": "NOT_VALIDATED",
        "excluded_value_admitted": False}


def review_inline_body(content: bytes, cik: str, *, as_of: datetime,
                       tags: tuple[str, ...] = DEFAULT_TAGS,
                       explain_exclusions: bool = False) -> dict[str, Any]:
    require_timezone(as_of, "Inline XBRL review cutoff")
    if type(explain_exclusions) is not bool:
        raise ValueError("exclusion explanation must be an explicit boolean")
    if (re.fullmatch(r"[0-9]{10}", cik) is None or int(cik) == 0 or not 1 <= len(tags) <= 16
            or len(set(tags)) != len(tags) or any(
                re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,127}", tag) is None for tag in tags)):
        raise ValueError("explicit CIK and bounded native tags are required")
    result: dict[str, Any] = {"model_version": SEC_INLINE_REVIEW_VERSION,
        "status": "UNSUPPORTED_OR_INVALID_DOCUMENT", "facts": [], "warnings": [],
        "accounting_definition_qualified": False, "independent_numeric_corroboration": False,
        "financial_scoring_authorized": False, "historical_replay_eligible": False,
        "validation_authorized": False, "execution_authorized": False}
    exclusions = []
    structure_cache: dict[str | None, dict[str, Any]] = {}
    try:
        _bounded_xml(content)
        stack: list[dict[str, str]] = []
        pending: dict[str, str] = {}
        scopes: dict[ET.Element, dict[str, str]] = {}
        blocked: dict[ET.Element, bool] = {}
        scope_blocks: list[bool] = []
        elements: list[ET.Element] = []
        stream = ET.iterparse(BytesIO(content), events=("start-ns", "start", "end"))
        for event, item in cast(Any, stream):
            if event == "start-ns":
                prefix, uri = item
                pending[prefix] = uri
            elif event == "start":
                scope = {**(stack[-1] if stack else {}), **pending}
                if len(scope) > 256:
                    raise ValueError("namespace scope exceeds review bounds")
                pending.clear()
                stack.append(scope)
                elements.append(item)
                blocked[item] = bool(scope_blocks and scope_blocks[-1])
                scope_blocks.append(blocked[item] or "target" in item.attrib or item.tag in {
                    f"{{{IX}}}tuple", f"{{{IX}}}nonNumeric", f"{{{IX}}}nonFraction"})
                if item.tag in {f"{{{IX}}}nonFraction", f"{{{XBRLI}}}measure"}:
                    scopes[item] = scope
            else:
                stack.pop()
                scope_blocks.pop()
        ids = Counter(element.get("id") for element in elements if element.get("id"))
        contexts = {element.get("id"): element for element in elements
                    if element.tag == f"{{{XBRLI}}}context" and element.get("id")}
        units = {element.get("id"): element for element in elements
                 if element.tag == f"{{{XBRLI}}}unit" and element.get("id")}
        targeted_document = any(element.tag.startswith(f"{{{IX}}}")
                                and "target" in element.attrib for element in elements)
        for index, element in enumerate(elements):
            if (element.tag != f"{{{IX}}}nonFraction"
                    or element.get("name", "").split(":")[-1] not in tags):
                continue
            fact: dict[str, Any] = {"element_index": index,
                "native_attributes": dict(element.attrib),
                "raw_text": "".join(element.itertext())[:512], "status": "UNSUPPORTED_FACT",
                "value": None, "tag": element.get("name", "").split(":")[-1],
                "period_start": None, "period_end": None, "unit": None, "reason": None}
            result["facts"].append(fact)
            if len(result["facts"]) > 10_000:
                raise ValueError("selected fact count exceeds review bounds")
            try:
                if blocked[element] or targeted_document:
                    raise ValueError("nested or targeted document scope is unsupported")
                namespace, tag = _qname(element.attrib["name"], scopes[element])
                if re.fullmatch(r"https?://fasb.org/us-gaap/[0-9]{4}", namespace) is None:
                    raise ValueError("unsupported concept namespace")
                context_id, unit_id = element.get("contextRef"), element.get("unitRef")
                if (not context_id or not unit_id or ids[context_id] != 1 or ids[unit_id] != 1
                        or context_id not in contexts or unit_id not in units
                        or element.get("id") and ids[element.get("id")] != 1):
                    raise ValueError("missing or ambiguous fact/context/unit identity")
                fact.update(_context(contexts[context_id], cik, as_of))
                unit = units[unit_id]
                measures = list(unit)
                if (len(measures) != 1 or measures[0].tag != f"{{{XBRLI}}}measure"
                        or len(measures[0])
                        or _qname((measures[0].text or "").strip(), scopes[measures[0]])
                        != (ISO, "USD")):
                    raise ValueError("unsupported unit; no currency conversion is inferred")
                fact.update(unit="USD", taxonomy="us-gaap", namespace=namespace, tag=tag)
                fact.update(value=_amount(element, scopes[element]), status="OBSERVED_UNQUALIFIED")
            except (ValueError, KeyError, ArithmeticError) as error:
                fact["reason"] = str(error) if isinstance(error, ValueError) else "invalid fact"
                if explain_exclusions:
                    context_id = element.get("contextRef")
                    if context_id not in structure_cache:
                        structure_cache[context_id] = _exclusion_structure(element, contexts, ids)
                    exclusions.append({"element_index": index, "tag": fact["tag"],
                        "original_reason": fact["reason"],
                        **structure_cache[context_id],
                        "inline_ancestor_scope_blocked": blocked[element],
                        "targeted_document_present": targeted_document})
        result["status"] = "SUBSET_REVIEW_UNQUALIFIED"
        if not result["facts"]:
            result["warnings"].append("No selected Inline XBRL numeric tags found")
    except (ValueError, expat.ExpatError, ET.ParseError, RecursionError):
        result["facts"] = []
        exclusions = []
        result["warnings"].append(
            "Malformed or unsupported XML/DTD/entity/structure; no repair attempted")
    if explain_exclusions:
        audit = {"model_version": SEC_INLINE_EXCLUSION_VERSION,
            "numeric_review_version": SEC_INLINE_REVIEW_VERSION,
            "source_body_sha256": (sha256(content).hexdigest() if isinstance(content, bytes)
                                   and 0 < len(content) <= MAX_BODY_BYTES else None),
            "cik": cik, "as_of": as_of.astimezone(UTC), "requested_tags": list(tags),
            "inventory_status": ("STRUCTURE_OBSERVED" if result["status"] ==
                                 "SUBSET_REVIEW_UNQUALIFIED" else "DOCUMENT_UNAVAILABLE"),
            "selected_occurrence_count": len(result["facts"]),
            "excluded_occurrence_count": len(exclusions), "occurrences": exclusions,
            "accounting_definition_qualified": False, "values_changed": False,
            "financial_scoring_authorized": False, "historical_replay_eligible": False,
            "validation_authorized": False, "execution_authorized": False,
            "limitations": (
                "Structural presence is not XBRL conformance or dimension validation",
                "Exclusion causes may overlap; no classification as valid or malformed financials",
                "Selected-tag occurrences are not document, company or historical coverage",
                "Original reasons, accepted subset and blocked values remain unchanged",
            )}
        result["exclusion_audit"] = {**audit,
            "input_hash": sha256(financial_input_json(audit).encode()).hexdigest()}
    return result

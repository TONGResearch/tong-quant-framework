"""Read exact filing windows without admitting financial comparability or arithmetic."""

import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.providers.sec_body import body_subject
from tong_quant.data.providers.yahoo_identity import validate_yahoo_equity_subject
from tong_quant.data.sec_period_inputs import (
    SECPeriodResearchInput,
    SECPeriodSelection,
    read_sec_period_research_input,
)
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.domain.models import require_timezone
from tong_quant.version import (
    SEC_SOURCE_CAPTURE_IDENTITY_VERSION,
    SEC_SOURCE_CHECK_GAP_VERSION,
    SEC_SOURCE_COMPACT_VIEW_VERSION,
    SEC_SOURCE_RECORD_PROJECTION_VERSION,
    SEC_SOURCE_REFERENCE_VERSION,
    SEC_WINDOW_INVENTORY_VERSION,
)


@dataclass(frozen=True, slots=True)
class SECWindowPair:
    left: SECPeriodSelection
    right: SECPeriodSelection
    expected_namespace: str

    def __post_init__(self) -> None:
        if (type(self.left) is not SECPeriodSelection or type(self.right) is not SECPeriodSelection
                or self.left.native_tag != self.right.native_tag
                or not isinstance(self.expected_namespace, str)
                or re.fullmatch(r"https?://fasb.org/us-gaap/[0-9]{4}", self.expected_namespace,
                                flags=re.ASCII) is None):
            raise ValueError("SEC window pair requires one exact tag and an explicit namespace")
        self.left.__post_init__()
        self.right.__post_init__()


def _key(selection: SECPeriodSelection) -> tuple[str, str | None, str]:
    return (selection.native_tag, selection.period_start.isoformat() if selection.period_start
            else None, selection.period_end.isoformat())


def _side(check: dict[str, Any], namespace: str, cik: str, inspected: bool) -> dict[str, Any]:
    blockers = []
    if check["status"] != "OBSERVED_SUBSET_UNQUALIFIED":
        blockers.append(f"period_check:{check['status']}")
    if check["unresolved_tag_contexts_present"]:
        blockers.append("unresolved_tag_contexts")
    rows = check["matching_occurrences"]
    if inspected and any(row.get("namespace") != namespace for row in rows):
        blockers.append("namespace_mismatch_or_mixed_namespaces")
    if inspected and any(row.get("unit") != "USD" or row.get("entity_cik") != cik for row in rows):
        blockers.append("unit_or_entity_mismatch")
    references = [{"element_index": row["element_index"], "status": row["status"],
        "namespace": row.get("namespace"), "tag": row["tag"], "unit": row.get("unit"),
        "entity_cik": row.get("entity_cik"), "period_start": row["period_start"],
        "period_end": row["period_end"],
        "context_ref": row["native_attributes"].get("contextRef"),
        "unit_ref": row["native_attributes"].get("unitRef")} for row in rows]
    return {"selection": {name: check[name] for name in (
                "native_tag", "period_start", "period_end")},
        "check_status": check["status"], "requested_period_basis": check["period_basis"],
        "requested_duration_calendar_days": check["duration_calendar_days"],
        "numeric_agreement_within_supported_subset": check["numeric_agreement_within_subset"],
        "matching_occurrence_count": len(rows) if inspected else None,
        "occurrence_references": references,
        "unresolved_tag_contexts_present": check["unresolved_tag_contexts_present"] if inspected
                                          else None,
        "unresolved_tag_occurrence_indices": check["unresolved_tag_occurrence_indices"] if inspected
                                             else None,
        "unresolved_context_scope": "REQUESTED_TAG_NOT_VERIFIED_WINDOW",
        "blocking_reasons": blockers}


def read_sec_window_inventory(
    store: SQLiteStore, artifacts: FileSystemArtifactStore, cik: str, accession: str,
    *, symbol: str, as_of: datetime, pairs: tuple[SECWindowPair, ...],
    maximum_capture_age_seconds: int,
) -> dict[str, Any]:
    return _read_sec_window_inventory(store, artifacts, cik, accession, symbol=symbol,
        as_of=as_of, pairs=pairs, maximum_capture_age_seconds=maximum_capture_age_seconds)[0]


def _read_sec_window_inventory(
    store: SQLiteStore, artifacts: FileSystemArtifactStore, cik: str, accession: str,
    *, symbol: str, as_of: datetime, pairs: tuple[SECWindowPair, ...],
    maximum_capture_age_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any] | None, SECPeriodResearchInput]:
    """One original factory read for all requested windows; no caller receipt input."""
    require_timezone(as_of, "SEC window inventory cutoff")
    try:
        cutoff = as_of.astimezone(UTC)
    except OverflowError:
        raise ValueError("SEC window inventory cutoff outside UTC bounds") from None
    subject = body_subject(cik, accession)
    validate_yahoo_equity_subject(Market.US, symbol)
    if not store.read_only:
        raise ValueError("SEC window inventory requires a read-only existing store")
    if type(maximum_capture_age_seconds) is not int or maximum_capture_age_seconds <= 0:
        raise ValueError("SEC window inventory requires a positive integer capture-age limit")
    if (type(pairs) is not tuple or not 1 <= len(pairs) <= 8
            or any(type(pair) is not SECWindowPair for pair in pairs)):
        raise ValueError("SEC window inventory requires one to eight typed pairs")
    for pair in pairs:
        pair.__post_init__()
    if len(set(pairs)) != len(pairs):
        raise ValueError("SEC window inventory rejects duplicate pairs")
    ordered = tuple(sorted(pairs, key=lambda item: financial_input_json(asdict(item))))
    selections = tuple({item for pair in ordered for item in (pair.left, pair.right)})
    with store.read_snapshot():
        bound = read_sec_period_research_input(store, artifacts, cik, accession, symbol=symbol,
            as_of=cutoff, selections=selections, sector_profile="unknown")
        bound.validate_context(symbol=symbol, market=Market.US, as_of=cutoff)
        document = bound.document()
    if document["subject"] != subject:
        raise ValueError("SEC window inventory source identity mismatch")
    checks = {(row["native_tag"], row["period_start"], row["period_end"]): row
              for row in document["checks"]}
    if set(checks) != {_key(item) for item in selections}:
        raise ValueError("SEC window inventory source selections mismatch")
    capture = next((row for row in document["source_captures"]
                    if row["evidence_id"] == document.get("source_evidence_id")), None)
    age, freshness = None, "UNASSESSED"
    if capture is not None:
        elapsed = cutoff - datetime.fromisoformat(capture["available_at"]).astimezone(UTC)
        if elapsed.days < 0:
            raise ValueError("SEC window inventory cannot use future capture")
        age = elapsed.total_seconds()
        within = (elapsed.days * 86400 + elapsed.seconds, elapsed.microseconds) <= (
            maximum_capture_age_seconds, 0)
        freshness = "WITHIN_LIMIT" if within else "STALE"
    inspected = document["status"] == "SOURCE_SUBSET_REVIEW"
    source_blockers = []
    if not inspected:
        source_blockers.append(f"source_unavailable:{document['source_status']}")
    if freshness != "WITHIN_LIMIT":
        source_blockers.append("capture_not_within_configured_limit")
    results = []
    for pair in ordered:
        left = _side(checks[_key(pair.left)], pair.expected_namespace, cik, inspected)
        right = _side(checks[_key(pair.right)], pair.expected_namespace, cik, inspected)
        blockers = [*source_blockers, *(f"left:{reason}" for reason in left["blocking_reasons"]),
                    *(f"right:{reason}" for reason in right["blocking_reasons"])]
        if (pair.left.period_start is None) != (pair.right.period_start is None):
            blockers.append("instant_duration_basis_mismatch")
        results.append({"pair": asdict(pair), "left": left, "right": right,
            "raw_context_status": "BLOCKED" if blockers else "OBSERVED_UNQUALIFIED",
            "blocking_reasons": blockers, "economic_comparison_status": "NOT_ADMITTED"})
    output = {"model_version": SEC_WINDOW_INVENTORY_VERSION,
        "mode": "FINANCIAL_WINDOW_OBSERVATION", "requested_symbol": symbol,
        "market": Market.US.value, "subject": subject, "as_of": cutoff,
        "snapshot_scope": "single_read_only_database_snapshot",
        "source_status": document["source_status"], "source_bound": document["source_bound"],
        "source_period_input_hash": document["input_hash"],
        "source_research_binding_hash": bound.binding_hash,
        "source_input_hash": document["source_input_hash"],
        "source_body_sha256": document["source_body_sha256"],
        "source_parent_binding": document["source_parent_binding"],
        "source_selected_evidence_id": document["source_evidence_id"],
        "source_model_version": document["model_version"],
        "source_review_version": document["source_review_version"],
        "capture_available_at": capture["available_at"] if capture else None,
        "capture_age_seconds": age, "maximum_capture_age_seconds": maximum_capture_age_seconds,
        "capture_freshness": freshness, "freshness_policy_independently_reviewed": False,
        "source_occurrence_inventory_evaluated": inspected,
        "source_requested_tags": sorted({selection.native_tag for selection in selections}),
        "source_occurrence_count": (document["selected_fact_occurrence_count"]
                                    if inspected else None),
        "unsupported_source_occurrence_count": document["unsupported_fact_occurrence_count"]
                                               if inspected else None,
        "pairs": results, "source_record_changes": "NOT_ASSESSED",
        "fundamental_assessment": "NOT_ASSESSED", "economic_comparison_status": "NOT_ADMITTED",
        "review_gaps": ["issuer_share_class_linkage", "accounting_definition_and_statement_scope",
            "fiscal_window_and_column_roles", "publication_revision_and_freshness_qualification",
            "independent_source_and_method_validation"],
        "research_only": True, "source_qualified": False, "pit_qualified": False,
        "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        "issuer_to_instrument_verified": False, "accounting_definitions_admitted": False,
        "financial_scoring_authorized": False, "investment_scoring_authorized": False,
        "validation_authorized": False, "historical_replay_eligible": False,
        "holding_management_authorized": False, "execution_authorized": False,
        "research_report_created": False,
        "limitations": ["raw_context_alignment_is_not_verified_financial_comparability",
            "capture_age_is_not_publication_age_or_current_financial_completeness",
            "same_filing_comparative_windows_are_not_original_historical_vintages",
            "unresolved_tag_contexts_are_not_verified_to_belong_to_requested_window",
            "unknown_dimensions_scope_and_definitions_are_not_synthesized",
            "no_amounts_growth_arithmetic_source_change_comparator_or_trade_instructions"]}
    reject_sensitive_structure(output)
    return ({**output, "inventory_hash": sha256(financial_input_json(output).encode()).hexdigest()},
            capture, bound)


def _reference_axis(previous: object, current: object) -> dict[str, Any]:
    left = financial_input_json(previous) if previous is not None else None
    right = financial_input_json(current) if current is not None else None
    return {"status": "NOT_EVALUATED" if left is None or right is None else
            "OBSERVED_SAME" if left == right else "OBSERVED_DIFFERENT",
        "previous_material_hash": sha256(left.encode()).hexdigest() if left is not None else None,
        "current_material_hash": sha256(right.encode()).hexdigest() if right is not None else None}


def _check_gap_material(frame: dict[str, Any]) -> dict[str, Any]:
    pairs = []
    for pair in frame["pairs"]:
        sides = {}
        for name in ("left", "right"):
            side = pair[name]
            indices = side["unresolved_tag_occurrence_indices"]
            sides[name] = {key: side[key] for key in (
                "selection", "check_status", "requested_period_basis",
                "requested_duration_calendar_days", "matching_occurrence_count",
                "numeric_agreement_within_supported_subset", "unresolved_tag_contexts_present")}
            sides[name]["unresolved_tag_occurrence_count"] = (
                len(indices) if indices is not None else None)
        pairs.append({"expected_namespace": pair["pair"]["expected_namespace"], **sides,
            "raw_context_status": pair["raw_context_status"],
            "blocking_reasons": pair["blocking_reasons"]})
    return {key: frame[key] for key in ("source_model_version", "source_review_version",
        "source_occurrence_count", "unsupported_source_occurrence_count")} | {"pairs": pairs}


def _record_material(
    frame: dict[str, Any], bound: SECPeriodResearchInput, identity: object,
) -> dict[str, Any]:
    bound.validate_context(symbol=frame["requested_symbol"], market=Market.US, as_of=frame["as_of"])
    document = bound.document()
    if (bound.binding_hash != frame["source_research_binding_hash"]
            or document["input_hash"] != frame["source_period_input_hash"]
            or document["subject"] != frame["subject"]
            or document["model_version"] != frame["source_model_version"]
            or document["source_review_version"] != frame["source_review_version"]):
        raise ValueError("SEC record projection requires its original source binding")
    capture = next((row for row in document["source_captures"]
                    if row["evidence_id"] == document["source_evidence_id"]), None)
    if capture is None or {key: capture[key] for key in (
            "evidence_id", "available_at", "raw_data_hash")} != identity:
        raise ValueError("SEC record projection requires its original selected capture")
    parsed, representation, counts = [], [], []
    for check in document["checks"]:
        selection = {key: check[key] for key in ("native_tag", "period_start", "period_end")}
        rows = check["matching_occurrences"]
        projected = [{key: row.get(key) for key in (
            "tag", "taxonomy", "namespace", "entity_cik", "period_start", "period_end",
            "unit", "value", "status", "reason")} for row in rows]
        parsed.append({"selection": selection,
                       "occurrences": sorted(projected, key=financial_input_json)})
        representation.append({"selection": selection,
                               "occurrences": sorted(rows, key=financial_input_json)})
        counts.append({"selection": selection, "matching_occurrence_count": len(rows)})
    return {"parsed_subset_records": sorted(parsed, key=financial_input_json),
        "parser_occurrence_representation": sorted(representation, key=financial_input_json),
        "selection_counts": sorted(counts, key=financial_input_json)}


def _compact_source_observation(result: dict[str, Any]) -> dict[str, Any]:
    """Project the just-recomputed observation, not caller receipts or new research."""
    fields = ("as_of", "source_period_input_hash", "source_research_binding_hash",
        "source_status", "source_bound", "source_body_sha256", "source_selected_evidence_id",
        "source_model_version", "source_review_version", "capture_available_at",
        "capture_age_seconds", "maximum_capture_age_seconds", "capture_freshness",
        "source_occurrence_inventory_evaluated", "source_requested_tags", "source_occurrence_count",
        "unsupported_source_occurrence_count", "review_gaps")
    skipped = {"occurrence_references", "unresolved_tag_occurrence_indices"}
    view = {key: value for key, value in result.items()
            if key not in {"model_version", "observation_hash", "previous_inventory",
                           "current_inventory"}}
    omitted: set[str] = set()
    for name in ("previous", "current"):
        frame = result[f"{name}_inventory"]
        pairs = []
        for pair in frame["pairs"]:
            item = {key: value for key, value in pair.items() if key not in {"left", "right"}}
            for side in ("left", "right"):
                original = pair[side]
                item[side] = {key: value for key, value in original.items() if key not in skipped}
                indices = original["unresolved_tag_occurrence_indices"]
                item[side]["unresolved_tag_occurrence_count"] = (
                    len(indices) if indices is not None else None)
            pairs.append(item)
        view[f"{name}_source_summary"] = {key: frame[key] for key in fields} | {
            "inventory_model_version": frame["model_version"],
            "full_inventory_hash": frame["inventory_hash"], "pairs": pairs}
        omitted.update(set(frame) - set(fields) - {"pairs", "model_version", "inventory_hash"})
    view.update(model_version=SEC_SOURCE_COMPACT_VIEW_VERSION,
        output_scope="COMPACT_SOURCE_OBSERVATION_VIEW",
        source_observation_model_version=result["model_version"],
        source_observation_hash=result["observation_hash"],
        omitted_inventory_fields=sorted(omitted), omitted_occurrence_fields=sorted(skipped))
    view["limitations"] = [*result["limitations"],
        "compact_view_omits_detail_and_is_not_a_new_source_or_research_report"]
    reject_sensitive_structure(view)
    return {**view, "summary_hash": sha256(financial_input_json(view).encode()).hexdigest()}


def read_sec_source_reference_changes(
    store: SQLiteStore, artifacts: FileSystemArtifactStore, cik: str, accession: str,
    *, symbol: str, previous_as_of: datetime, as_of: datetime,
    pairs: tuple[SECWindowPair, ...], maximum_capture_age_seconds: int,
    with_selected_capture_identity: bool = False,
    with_check_gap_state: bool = False,
    with_record_projections: bool = False,
    compact: bool = False,
) -> dict[str, Any]:
    """Two original inventories on one DB snapshot; compare references, never financial values."""
    if type(with_selected_capture_identity) is not bool:
        raise ValueError("SEC selected-capture identity option requires an exact boolean")
    if type(with_check_gap_state) is not bool:
        raise ValueError("SEC check-gap state option requires an exact boolean")
    if with_check_gap_state and not with_selected_capture_identity:
        raise ValueError("SEC check-gap state requires complete selected-capture identity")
    if type(with_record_projections) is not bool:
        raise ValueError("SEC record-projection option requires an exact boolean")
    if with_record_projections and not with_check_gap_state:
        raise ValueError("SEC record projections require check-gap state")
    if type(compact) is not bool:
        raise ValueError("SEC compact-view option requires an exact boolean")
    if type(previous_as_of) is not datetime or type(as_of) is not datetime:
        raise ValueError("SEC source-reference observation requires explicit datetime cutoffs")
    require_timezone(previous_as_of, "previous SEC source-reference cutoff")
    require_timezone(as_of, "current SEC source-reference cutoff")
    try:
        previous_cutoff, cutoff = previous_as_of.astimezone(UTC), as_of.astimezone(UTC)
    except OverflowError:
        raise ValueError("SEC source-reference cutoff outside UTC bounds") from None
    if previous_cutoff >= cutoff:
        raise ValueError("SEC source-reference cutoffs must strictly increase in actual UTC")
    if not store.read_only:
        raise ValueError("SEC source-reference observation requires a read-only existing store")
    previous_capture, current_capture = None, None
    previous_bound, current_bound = None, None
    with store.read_snapshot():
        if with_selected_capture_identity:
            previous, previous_capture, previous_bound = _read_sec_window_inventory(
                store, artifacts, cik, accession, symbol=symbol, as_of=previous_cutoff,
                pairs=pairs, maximum_capture_age_seconds=maximum_capture_age_seconds)
            current, current_capture, current_bound = _read_sec_window_inventory(
                store, artifacts, cik, accession, symbol=symbol, as_of=cutoff,
                pairs=pairs, maximum_capture_age_seconds=maximum_capture_age_seconds)
        else:
            previous = read_sec_window_inventory(store, artifacts, cik, accession, symbol=symbol,
                as_of=previous_cutoff, pairs=pairs,
                maximum_capture_age_seconds=maximum_capture_age_seconds)
            current = read_sec_window_inventory(store, artifacts, cik, accession, symbol=symbol,
                as_of=cutoff, pairs=pairs, maximum_capture_age_seconds=maximum_capture_age_seconds)

    def material(frame: dict[str, Any], name: str) -> object:
        if not (frame["source_bound"] is True
                and frame["source_occurrence_inventory_evaluated"] is True
                and frame["capture_freshness"] == "WITHIN_LIMIT"):
            return None
        if name == "selected_capture_reference":
            reference = (frame["source_selected_evidence_id"], frame["capture_available_at"])
            return reference if all(type(value) is str and value for value in reference) else None
        if name == "parent_binding":
            value = frame["source_parent_binding"]
            return value if isinstance(value, dict) and value else None
        value = frame["source_body_sha256"]
        return value if type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) else None

    axes = {name: _reference_axis(material(previous, name), material(current, name))
            for name in ("selected_capture_reference", "parent_binding", "body_bytes")}
    axes["period_receipt_identity"] = _reference_axis(
        previous["source_period_input_hash"], current["source_period_input_hash"])
    output = {"model_version": SEC_SOURCE_REFERENCE_VERSION,
        "mode": "SOURCE_REFERENCE_OBSERVATION", "requested_symbol": symbol,
        "market": Market.US.value, "subject": current["subject"],
        "previous_as_of": previous_cutoff, "as_of": cutoff,
        "snapshot_scope": "single_read_only_database_snapshot_across_both_cutoffs",
        "previous_inventory": previous, "current_inventory": current,
        "source_reference_observations": axes,
        "source_record_changes": "PARTIAL_REFERENCE_OBSERVATION_ONLY",
        "unimplemented_comparison_axes": ["full_selected_capture_including_raw_data_hash",
            "parsed_subset_records", "representation_location", "check_gap_state_projection"],
        "fundamental_assessment": "NOT_ASSESSED", "economic_comparison_status": "NOT_ADMITTED",
        "research_only": True, "trust_ceiling": "LOW", "availability_precision": "retrieval_time",
        **{name: False for name in ("source_qualified", "pit_qualified",
            "issuer_to_instrument_verified", "accounting_definitions_admitted",
            "financial_scoring_authorized", "investment_scoring_authorized",
            "validation_authorized", "historical_replay_eligible", "holding_management_authorized",
            "execution_authorized", "research_report_created",
            "freshness_policy_independently_reviewed")},
        "limitations": ["reference_changes_are_not_business_growth_or_verified_issuer_restatements",
            "receipt_identity_can_change_only_because_query_cutoff_changes",
            "capture_reference_excludes_raw_data_hash_and_is_not_full_capture_identity",
            "parent_binding_difference_does_not_prove_changed_parent_document",
            "body_bytes_do_not_establish_changed_financial_magnitude_or_definition",
            "missing_failed_or_stale_source_comparisons_are_not_unchanged",
            "one_db_snapshot_does_not_lock_external_artifact_files_or_establish_source_truth",
            "not_the_complete_source_change_comparator_or_a_holding_instruction"]}
    if with_selected_capture_identity:
        def capture_identity(frame: dict[str, Any], capture: dict[str, Any] | None) -> object:
            if material(frame, "selected_capture_reference") is None or capture is None:
                return None
            raw_hash = capture.get("raw_data_hash")
            if (capture.get("evidence_id") != frame["source_selected_evidence_id"]
                    or capture.get("available_at") != frame["capture_available_at"]
                    or type(raw_hash) is not str
                    or re.fullmatch(r"[0-9a-f]{64}", raw_hash) is None):
                return None
            return {name: capture[name]
                    for name in ("evidence_id", "available_at", "raw_data_hash")}

        identities = {"previous": capture_identity(previous, previous_capture),
                      "current": capture_identity(current, current_capture)}
        axes["selected_capture_identity"] = _reference_axis(
            identities["previous"], identities["current"])
        output["model_version"] = SEC_SOURCE_CAPTURE_IDENTITY_VERSION
        output["selected_capture_identity_material"] = identities
        output["unimplemented_comparison_axes"].remove("full_selected_capture_including_raw_data_hash")
        output["limitations"].append(
            "capture_identity_is_retained_record_identity_not_source_authentication")
        if with_check_gap_state:
            gaps = {name: _check_gap_material(frame) if identities[name] is not None else None
                    for name, frame in (("previous", previous), ("current", current))}
            axis = _reference_axis(gaps["previous"], gaps["current"])
            versions_match = (all(value is not None for value in gaps.values())
                and all(previous[key] == current[key]
                        for key in ("source_model_version", "source_review_version")))
            axis["interpretation_status"] = ("SAME_VERSIONS" if versions_match else
                "VERSION_CHANGED" if all(value is not None for value in gaps.values())
                else "NOT_EVALUATED")
            if not versions_match:
                axis["status"] = "NOT_EVALUATED"
            axes["check_gap_state"] = axis
            output["check_gap_state_material"] = gaps
            output["model_version"] = SEC_SOURCE_CHECK_GAP_VERSION
            output["unimplemented_comparison_axes"].remove("check_gap_state_projection")
            output["limitations"].append(
                "check_gap_changes_are_not_source_qualification_or_financial_improvement")
            output["limitations"].append(
                "unresolved_counts_are_tag_scoped_not_verified_window_conflict_counts")
            if with_record_projections:
                records: dict[str, dict[str, Any] | None] = {}
                for name, frame, bound in (("previous", previous, previous_bound),
                                            ("current", current, current_bound)):
                    if identities[name] is None:
                        records[name] = None
                    else:
                        if bound is None:
                            raise ValueError("SEC record projection requires its original input")
                        records[name] = _record_material(frame, bound, identities[name])
                for name in ("parsed_subset_records", "parser_occurrence_representation"):
                    axis = _reference_axis(
                        records["previous"][name] if records["previous"] is not None else None,
                        records["current"][name] if records["current"] is not None else None)
                    axis["interpretation_status"] = axes["check_gap_state"]["interpretation_status"]
                    if not versions_match:
                        axis["status"] = "NOT_EVALUATED"
                    axes[name] = axis
                output["model_version"] = SEC_SOURCE_RECORD_PROJECTION_VERSION
                output["record_projection_counts"] = {name: value["selection_counts"]
                    if value is not None else None for name, value in records.items()}
                output["representation_scope"] = "PARSER_OCCURRENCE_PROJECTION_ONLY"
                output["full_source_change_mode_implemented"] = False
                output["unimplemented_comparison_axes"] = ["full_lexical_representation"]
                output["limitations"].extend([
                    "record_material_is_hashed_internally_without_publishing_financial_values",
                    "parser_records_do_not_represent_complete_original_xml_or_text",
                    "normalized_value_strings_and_duplicate_multiplicity_are_not_reinterpreted"])
    reject_sensitive_structure(output)
    result = {**output,
              "observation_hash": sha256(financial_input_json(output).encode()).hexdigest()}
    return _compact_source_observation(result) if compact else result

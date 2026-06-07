from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_BACKLOG = Path("reports/frontier_backlog/frontier_backlog.json")
DEFAULT_UNIQUENESS_GATE = Path("../hard-discovery-factory/AI_IT_UNIQUENESS_GATE.json")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_next_packet(backlog: dict[str, Any], preferred_candidate: str | None = None) -> dict[str, Any]:
    packets = backlog.get("narrowing_packets", [])
    if not packets:
        raise ValueError("frontier backlog contains no narrowing packets to review")
    if preferred_candidate:
        for packet in packets:
            if packet["candidate_id"] == preferred_candidate or packet["id"] == preferred_candidate:
                return packet
        raise ValueError(f"preferred candidate not found in narrowing packets: {preferred_candidate}")
    return sorted(packets, key=lambda packet: packet["id"])[0]


def top_uniqueness_entry(gate: dict[str, Any]) -> dict[str, Any]:
    entries = gate.get("entries", [])
    if not entries:
        raise ValueError("uniqueness gate contains no entries")
    return entries[0]


def build_review_packet(
    backlog_path: Path,
    uniqueness_gate_path: Path,
    preferred_candidate: str | None = None,
) -> dict[str, Any]:
    backlog = load_json(backlog_path)
    gate = load_json(uniqueness_gate_path)
    packet = select_next_packet(backlog, preferred_candidate)
    uniqueness = top_uniqueness_entry(gate)
    blockers = [
        "decision is block",
        "correctness.score is below 4",
        "sense.score is below 4",
        "originality.score is below 4",
        "originality.collision_risk is high",
        "originality.differentiator is empty or only renames an existing surface",
        "originality.claim_scope is broad, such as agent safety benchmark or data analytics benchmark",
        "implementation_readiness.ready is false",
        "frontier backlog has zero accepted candidates and reviewer does not approve a narrowing packet",
        "any critical risk lacks a mitigation",
    ]
    return {
        "review_type": "second_agent_next_step_review",
        "status": "requires_second_agent_review",
        "candidate_id": packet["candidate_id"],
        "proposed_next_artifact": packet,
        "current_uniqueness_gate": {
            "project_id": uniqueness["id"],
            "verdict": uniqueness["uniqueness_verdict"],
            "max_collision_risk": uniqueness["max_collision_risk"],
            "nearest_baselines": uniqueness["nearest_baselines"][:4],
            "narrowed_claim": uniqueness["narrowed_claim"],
        },
        "required_reviewer_json_schema": {
            "decision": "approve | revise | block",
            "correctness": {
                "score": "integer 0-5",
                "issues": ["string"],
                "required_fixes": ["string"],
            },
            "sense": {
                "score": "integer 0-5",
                "rationale": "string",
                "expected_project_gain": "string",
            },
            "originality": {
                "score": "integer 0-5",
                "collision_risk": "low | medium | high",
                "nearest_prior_work": ["string"],
                "differentiator": "string",
                "claim_scope": "string",
            },
            "implementation_readiness": {
                "ready": "boolean",
                "missing_artifacts": ["string"],
                "required_narrowing": ["string"],
            },
            "blocking_conditions": ["string"],
            "recommended_next_step": "string",
        },
        "implementation_blockers": blockers,
    }


def render_markdown(packet: dict[str, Any]) -> str:
    artifact = packet["proposed_next_artifact"]
    uniqueness = packet["current_uniqueness_gate"]
    lines = [
        "# Next Step Review Packet",
        "",
        "This packet must be reviewed by a second agent before implementation.",
        "",
        "## Proposed Next Artifact",
        "",
        f"- candidate_id: `{packet['candidate_id']}`",
        f"- artifact_id: `{artifact['id']}`",
        f"- implementation_status: `{artifact['implementation_status']}`",
        f"- narrow_claim: {artifact['narrow_claim']}",
        f"- new_local_surface: `{artifact['new_local_surface']}`",
        f"- required_evidence_contract: {', '.join(artifact['required_evidence_contract'])}",
        f"- nearest_baselines_to_recheck: {', '.join(artifact['nearest_baselines_to_recheck'])}",
        "",
        "Deterministic validator:",
        "",
    ]
    for item in artifact["deterministic_validator"]:
        lines.append(f"- {item}")
    if "minimal_chart_spec_schema" in artifact:
        lines.extend(
            [
                "",
                "Minimal chart spec schema:",
                "",
                "```json",
                json.dumps(artifact["minimal_chart_spec_schema"], indent=2),
                "```",
            ]
        )
    if "role_change_event_schema" in artifact:
        lines.extend(
            [
                "",
                "Role change event schema:",
                "",
                "```json",
                json.dumps(artifact["role_change_event_schema"], indent=2),
                "```",
            ]
        )
    if "access_decision_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Access decision output contract:",
                "",
                "```json",
                json.dumps(artifact["access_decision_output_contract"], indent=2),
                "```",
            ]
        )
    if "allowed_public_columns" in artifact:
        lines.extend(
            [
                "",
                f"Allowed public columns: {', '.join(artifact['allowed_public_columns'])}",
                f"Denied hidden columns: {', '.join(artifact['denied_hidden_columns'])}",
            ]
        )
    if "schema_report_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Schema report output contract:",
                "",
                "```json",
                json.dumps(artifact["schema_report_output_contract"], indent=2),
                "```",
            ]
        )
    if "allowed_public_join_keys" in artifact:
        lines.extend(
            [
                "",
                f"Allowed public join keys: {', '.join(artifact['allowed_public_join_keys'])}",
                f"Denied private join keys: {', '.join(artifact['denied_private_join_keys'])}",
            ]
        )
    if "join_plan_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Join plan output contract:",
                "",
                "```json",
                json.dumps(artifact["join_plan_output_contract"], indent=2),
                "```",
            ]
        )
    if "threshold_k" in artifact:
        lines.extend(
            [
                "",
                f"Threshold k: `{artifact['threshold_k']}`",
                f"Allowed group fields: {', '.join(artifact['allowed_group_fields'])}",
                f"Denied small groups: {', '.join(artifact['denied_small_groups'])}",
            ]
        )
    if "aggregate_table_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Aggregate table output contract:",
                "",
                "```json",
                json.dumps(artifact["aggregate_table_output_contract"], indent=2),
                "```",
            ]
        )
    if "allowed_cohort_labels" in artifact:
        lines.extend(
            [
                "",
                f"Allowed cohort labels: {', '.join(artifact['allowed_cohort_labels'])}",
                f"Denied descriptive labels: {', '.join(artifact['denied_descriptive_labels'])}",
            ]
        )
    if "cohort_label_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Cohort label output contract:",
                "",
                "```json",
                json.dumps(artifact["cohort_label_output_contract"], indent=2),
                "```",
            ]
        )
    if "allowed_public_reasons" in artifact:
        lines.extend(
            [
                "",
                f"Allowed public reasons: {', '.join(artifact['allowed_public_reasons'])}",
                f"Denied private reasons: {', '.join(artifact['denied_private_reasons'])}",
            ]
        )
    if "suppression_audit_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Suppression audit output contract:",
                "",
                "```json",
                json.dumps(artifact["suppression_audit_output_contract"], indent=2),
                "```",
            ]
        )
    if "allowed_sampling_frame_labels" in artifact:
        lines.extend(
            [
                "",
                f"Allowed sampling frame labels: {', '.join(artifact['allowed_sampling_frame_labels'])}",
                f"Denied frame aliases: {', '.join(artifact['denied_frame_aliases'])}",
            ]
        )
    if "sampling_frame_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Sampling frame output contract:",
                "",
                "```json",
                json.dumps(artifact["sampling_frame_output_contract"], indent=2),
                "```",
            ]
        )
    if "allowed_outlier_policy_labels" in artifact:
        lines.extend(
            [
                "",
                f"Allowed outlier policy labels: {', '.join(artifact['allowed_outlier_policy_labels'])}",
                f"Denied outlier aliases: {', '.join(artifact['denied_outlier_aliases'])}",
            ]
        )
    if "outlier_policy_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Outlier policy output contract:",
                "",
                "```json",
                json.dumps(artifact["outlier_policy_output_contract"], indent=2),
                "```",
            ]
        )
    if "allowed_imputation_rule_labels" in artifact:
        lines.extend(
            [
                "",
                f"Allowed imputation rule labels: {', '.join(artifact['allowed_imputation_rule_labels'])}",
                f"Denied missingness aliases: {', '.join(artifact['denied_missingness_aliases'])}",
            ]
        )
    if "imputation_rule_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Imputation rule output contract:",
                "",
                "```json",
                json.dumps(artifact["imputation_rule_output_contract"], indent=2),
                "```",
            ]
        )
    if "allowed_calibration_slice_labels" in artifact:
        lines.extend(
            [
                "",
                f"Allowed calibration slice labels: {', '.join(artifact['allowed_calibration_slice_labels'])}",
                f"Denied calibration aliases: {', '.join(artifact['denied_calibration_aliases'])}",
            ]
        )
    if "calibration_report_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Calibration report output contract:",
                "",
                "```json",
                json.dumps(artifact["calibration_report_output_contract"], indent=2),
                "```",
            ]
        )
    if "allowed_validation_split_labels" in artifact:
        lines.extend(
            [
                "",
                f"Allowed validation split labels: {', '.join(artifact['allowed_validation_split_labels'])}",
                f"Denied validation split aliases: {', '.join(artifact['denied_validation_split_aliases'])}",
            ]
        )
    if "allowed_drift_window_labels" in artifact:
        lines.extend(
            [
                "",
                f"Allowed drift window labels: {', '.join(artifact['allowed_drift_window_labels'])}",
                f"Denied drift window aliases: {', '.join(artifact['denied_drift_window_aliases'])}",
            ]
        )
    if "allowed_alert_route_labels" in artifact:
        lines.extend(
            [
                "",
                f"Allowed alert route labels: {', '.join(artifact['allowed_alert_route_labels'])}",
                f"Denied alert route aliases: {', '.join(artifact['denied_alert_route_aliases'])}",
            ]
        )
    if "allowed_feature_bucket_labels" in artifact:
        lines.extend(
            [
                "",
                f"Allowed feature bucket labels: {', '.join(artifact['allowed_feature_bucket_labels'])}",
                f"Denied feature bucket aliases: {', '.join(artifact['denied_feature_bucket_aliases'])}",
            ]
        )
        if "denied_feature_derivation_details" in artifact:
            lines.append(f"Denied feature derivation details: {', '.join(artifact['denied_feature_derivation_details'])}")
    if "allowed_model_card_segment_labels" in artifact:
        lines.extend(
            [
                "",
                f"Allowed model-card segment labels: {', '.join(artifact['allowed_model_card_segment_labels'])}",
                f"Denied model-card segment aliases: {', '.join(artifact['denied_model_card_segment_aliases'])}",
            ]
        )
        if "denied_model_card_population_details" in artifact:
            lines.append(f"Denied model-card population details: {', '.join(artifact['denied_model_card_population_details'])}")
    if "allowed_counterfactual_labels" in artifact:
        lines.extend(
            [
                "",
                f"Allowed counterfactual labels: {', '.join(artifact['allowed_counterfactual_labels'])}",
                f"Denied contrast cases: {', '.join(artifact['denied_contrast_cases'])}",
                f"Denied neighbor provenance: {', '.join(artifact['denied_neighbor_provenance'])}",
            ]
        )
        if "denied_row_derived_rationale_details" in artifact:
            lines.append(
                f"Denied row-derived rationale details: {', '.join(artifact['denied_row_derived_rationale_details'])}"
            )
    if "allowed_root_cause_labels" in artifact:
        lines.extend(
            [
                "",
                f"Allowed root-cause labels: {', '.join(artifact['allowed_root_cause_labels'])}",
                f"Denied incident exemplars: {', '.join(artifact['denied_incident_exemplars'])}",
                f"Denied cause-chain details: {', '.join(artifact['denied_cause_chain_details'])}",
            ]
        )
    if "validation_split_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Validation split output contract:",
                "",
                "```json",
                json.dumps(artifact["validation_split_output_contract"], indent=2),
                "```",
            ]
        )
    if "drift_window_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Drift window output contract:",
                "",
                "```json",
                json.dumps(artifact["drift_window_output_contract"], indent=2),
                "```",
            ]
        )
    if "alert_route_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Alert route output contract:",
                "",
                "```json",
                json.dumps(artifact["alert_route_output_contract"], indent=2),
                "```",
            ]
        )
    if "feature_bucket_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Feature bucket output contract:",
                "",
                "```json",
                json.dumps(artifact["feature_bucket_output_contract"], indent=2),
                "```",
            ]
        )
    if "model_card_segment_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Model-card segment output contract:",
                "",
                "```json",
                json.dumps(artifact["model_card_segment_output_contract"], indent=2),
                "```",
            ]
        )
    if "counterfactual_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Counterfactual output contract:",
                "",
                "```json",
                json.dumps(artifact["counterfactual_output_contract"], indent=2),
                "```",
            ]
        )
    if "root_cause_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Root-cause output contract:",
                "",
                "```json",
                json.dumps(artifact["root_cause_output_contract"], indent=2),
                "```",
            ]
        )
    if "allowed_denominator_labels" in artifact:
        lines.extend(
            [
                "",
                f"Allowed denominator labels: {', '.join(artifact['allowed_denominator_labels'])}",
                f"Denied denominator aliases: {', '.join(artifact['denied_denominator_aliases'])}",
            ]
        )
    if "metric_card_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Metric card output contract:",
                "",
                "```json",
                json.dumps(artifact["metric_card_output_contract"], indent=2),
                "```",
            ]
        )
    if "validator_output_contract" in artifact:
        lines.extend(
            [
                "",
                "Validator output contract:",
                "",
                "```json",
                json.dumps(artifact["validator_output_contract"], indent=2),
                "```",
            ]
        )
    if "baseline_collision_note" in artifact:
        lines.extend(["", "Baseline collision note:", ""])
        for baseline, note in artifact["baseline_collision_note"].items():
            lines.append(f"- {baseline}: {note}")
    lines.extend(
        [
            "",
            f"Safe fixture: {artifact['safe_fixture']}",
            f"Leaky fixture: {artifact['leaky_fixture']}",
            "",
            "## Current Uniqueness Gate",
            "",
            f"- project_id: `{uniqueness['project_id']}`",
            f"- verdict: `{uniqueness['verdict']}`",
            f"- max_collision_risk: `{uniqueness['max_collision_risk']}`",
            f"- narrowed_claim: {uniqueness['narrowed_claim']}",
            "",
            "Nearest baselines:",
            "",
        ]
    )
    for baseline in uniqueness["nearest_baselines"]:
        lines.append(f"- `{baseline['baseline_id']}` risk={baseline['collision_risk']}: {baseline['baseline_name']} ({baseline['url']})")

    lines.extend(
        [
            "",
            "## Required Reviewer Output",
            "",
            "Return exactly one JSON object matching this shape. Do not answer with prose outside the JSON.",
            "",
            "```json",
            json.dumps(packet["required_reviewer_json_schema"], indent=2),
            "```",
            "",
            "## Implementation Blockers",
            "",
        ]
    )
    for blocker in packet["implementation_blockers"]:
        lines.append(f"- {blocker}")
    lines.extend(
        [
            "",
            "## Reviewer Task",
            "",
            "Evaluate whether this next step is correct, useful, and sufficiently original. Search or cite nearby work if needed. If the claim is too broad or the differentiator is weak, use `decision: revise` or `decision: block` and propose a sharper local artifact.",
        ]
    )
    return "\n".join(lines)


def write_review_packet(
    out_dir: Path,
    backlog_path: Path,
    uniqueness_gate_path: Path,
    preferred_candidate: str | None = None,
) -> dict[str, Any]:
    packet = build_review_packet(backlog_path, uniqueness_gate_path, preferred_candidate)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "NEXT_STEP_REVIEW_PACKET.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "NEXT_STEP_REVIEW_PACKET.md").write_text(render_markdown(packet) + "\n", encoding="utf-8")
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a second-agent review packet for the next proposed step.")
    parser.add_argument("--backlog", type=Path, default=DEFAULT_BACKLOG)
    parser.add_argument("--uniqueness-gate", type=Path, default=DEFAULT_UNIQUENESS_GATE)
    parser.add_argument("--preferred-candidate", default="root_cause_summary_trace_leak")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/next_step_review"))
    args = parser.parse_args(argv)

    write_review_packet(args.out_dir, args.backlog, args.uniqueness_gate, args.preferred_candidate)
    print(args.out_dir / "NEXT_STEP_REVIEW_PACKET.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

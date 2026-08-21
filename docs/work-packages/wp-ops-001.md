# Work Package: WP-OPS-001

Status: `ready`

## Objective

Turn provider contract history into an operator-visible health process without
coupling it to the Tong Quant Notification Engine.

## Scope

- Define monitor retention and artifact naming.
- Surface CI failures for implementation defects.
- Define operator ownership, acknowledgement, and recovery steps.
- Track repeated degradation separately from one-off downtime.

## Acceptance Criteria

- Missing required fields fail the scheduled contract job.
- External downtime remains distinguishable from implementation defects.
- Reports contain no credentials or raw provider exception messages.
- Historical reports can be correlated with code and contract versions.

## Non-Goals

- Do not change `tong_quant.notifications`.
- No Telegram, WeChat, Email, trading, or live alert delivery.

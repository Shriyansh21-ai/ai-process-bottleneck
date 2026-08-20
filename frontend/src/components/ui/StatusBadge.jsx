import {
  CheckCircle2,
  XCircle,
  Loader2,
  AlertTriangle,
  Circle,
} from "lucide-react";
import { statusTone, statusLabel } from "../../lib/format.js";

const TONE_META = {
  ok: { cls: "badge-ok", Icon: CheckCircle2 },
  danger: { cls: "badge-danger", Icon: XCircle },
  info: { cls: "badge-info", Icon: Loader2 },
  warn: { cls: "badge-warn", Icon: AlertTriangle },
  neutral: { cls: "badge-neutral", Icon: Circle },
};

/**
 * Status pill that conveys state through icon + text + color together, so it is
 * never color-only (Phase 19 accessibility). `running`/`pending` get a spinner.
 */
export default function StatusBadge({ status, label }) {
  const tone = statusTone(status);
  const { cls, Icon } = TONE_META[tone] || TONE_META.neutral;
  const spin = tone === "info" ? "spin" : "";
  return (
    <span className={`badge ${cls}`}>
      <Icon size={12} className={spin} aria-hidden="true" />
      {label || statusLabel(status)}
    </span>
  );
}

/** Boolean approval rendered with an explicit label, not color alone. */
export function ApprovalBadge({ approved }) {
  if (approved === null || approved === undefined) {
    return <span className="badge badge-neutral">— N/A</span>;
  }
  return approved ? (
    <span className="badge badge-ok">
      <CheckCircle2 size={12} aria-hidden="true" /> Approved
    </span>
  ) : (
    <span className="badge badge-danger">
      <XCircle size={12} aria-hidden="true" /> Rejected
    </span>
  );
}

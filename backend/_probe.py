"""One-shot probe: writes compact line-numbered anchor report to disk."""
import re
from pathlib import Path

BACKEND = Path(r"C:\Users\USER\Desktop\currency-X-AI\backend")
FRONTEND = Path(r"C:\Users\USER\Desktop\currency-X-AI\frontend")
out = []


def probe(rel, sig_pats, kw_pats=(), base=BACKEND, ctx=2):
    p = base / rel
    out.append(f"\n===== {rel} [{'EXISTS' if p.exists() else 'MISSING'}] =====")
    if not p.exists():
        return
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    out.append(f"total_lines={len(lines)}")
    show = set()
    for i, ln in enumerate(lines):
        if any(re.search(pt, ln) for pt in sig_pats):
            for j in range(max(0, i - ctx), min(len(lines), i + ctx + 1)):
                show.add(j)
        elif any(re.search(pt, ln) for pt in kw_pats):
            show.add(i)
    for j in sorted(show):
        out.append(f"{j + 1:4d}| {lines[j]}")


# 1. Payment router: endpoints, auth deps, amount usage
probe("app/api/razorpay_pay.py",
      [r"@router\.(post|get|patch|put)", r"^async def ", r"^def ", r"^from ", r"^import "],
      [r"amount", r"Depends\(", r"current_user", r"password", r"proof", r"demo", r"verify"],
      ctx=1)

# 2. Recovery API: endpoints + status transition logic
probe("app/api/revenue_recovery.py",
      [r"@router\.(post|get|patch|put|delete)", r"^async def ", r"^def "],
      [r"status", r"EXECUTED", r"ACCEPTED", r"DISMISSED", r"PENDING", r"uuid", r"current_user"],
      ctx=1)

# 3. Recovery service: transition methods
probe("app/services/revenue_recovery.py",
      [r"^    (async )?def ", r"^class ", r"^def "],
      [r"EXECUTED", r"update_recommendation", r"mark_recovered", r"retry", r"dismiss",
       r"complete", r"status\s*=|status ="],
      ctx=1)

# 4. Auth API: verify-password endpoint?
probe("app/api/auth.py",
      [r"@router\.(post|get)", r"^async def "],
      [r"password", r"verify", r"proof"],
      ctx=1)

# 5. deps.py — full dump (small)
probe("app/core/deps.py", [r"."], ctx=0)

# 6. confirmation_proof.py — full dump
probe("app/core/confirmation_proof.py", [r"."], ctx=0)

# 7. config: JWT secret + algo + settings fields
probe("app/config.py",
      [r"^class |^    [a-zA-Z_]+\s*[:=]"],
      [r"secret", r"SECRET", r"jwt", r"algorithm", r"ALGORITHM"],
      ctx=0)

# 8. payments.py (analysis) — auth scoping
probe("app/api/payments.py",
      [r"@router\.(post|get|patch|delete)", r"^async def "],
      [r"current_user", r"user_id", r"Depends\("],
      ctx=1)

# 9. security hardening tests present?
probe("tests/test_security_hardening.py", [r"^def test_|^async def test_"], ctx=0)

# 10. frontend api.js — JWT + payment helpers
probe("src/services/api.js",
      [r"paymentRequest|createPaymentOrder|verifyPayment|verifyPassword|confirmPassword"],
      [r"Authorization|token|isAuthenticated|auth"],
      base=FRONTEND, ctx=1)

# 11. models: payment analysis user linkage?
probe("app/models/payment.py", [r"^class ", r"user_id|ForeignKey"], ctx=1)

report = "\n".join(out)
(BACKEND / "_probe_report.txt").write_text(report, encoding="utf-8")
print(report[:10500])
print(f"\n[REPORT chars={len(report)} written to _probe_report.txt]")

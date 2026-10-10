# Ledger code list (ops)

| result | why | meaning |
|---|---|---|
| PTP | | at least one promise recorded |
| PAID | | member says already paid |
| XFER | PLAN, DESK, CARE | transferred, with the queue |
| PTP-NO | REFUSED, CARE-DECL, DISPUTE, SYSERR | no promise |
| SEC-FAIL | | failed security |
| SEC-REF | | refused security |
| NC-UNC | | not confirmed who answered |
| NC-WRG | | wrong number |
| NC-DEC | | member deceased |
| NC-CBK | | call-back booked |
| NC-NCB | | no call-back possible |

Promises are recorded per account. Notes are not used.

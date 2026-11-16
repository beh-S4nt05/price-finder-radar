# ICEBERG 2.0 — Release gates

**Status: NOT READY.** This is a checklist, not evidence of completed validation.

- [ ] Run backend pytest suite and resolve failures.
- [ ] Run frontend typecheck and production build.
- [ ] Implement real authorized connectors for every promised category.
- [ ] Verify source policies, DNS/redirect safety and data quality in isolation.
- [ ] Validate live vehicle listings and year/model/mileage accuracy.
- [ ] Validate real flight, cruise, stay and package pricing including mandatory fees.
- [ ] Confirm coupons in permitted checkout/test environments; never guess.
- [ ] Connect frontend filters to backend APIs and persistence.
- [ ] Execute E2E tests on desktop and mobile viewports.
- [ ] Run security review, rate limits, CI/CD and rollback rehearsal.
- [ ] Review all PRs before merging to main.

No mock offer may be presented as a live offer. Unverified offers and coupons
must remain explicitly marked unverified.

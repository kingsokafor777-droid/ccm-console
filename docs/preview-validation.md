# Local preview validation

On 2026-08-22, the local Next.js preview rendered the synthetic ccm-console
overview route. Text extraction confirmed the supplied assessment count, open-case count,
assessment table, and explicit unavailable-evidence signal. The preview is intentionally
labelled synthetic and contains no authenticated session, live FastAPI connection, cloud
integration, raw evidence body, credential, or customer data.

The follow-up interactive browser viewer timed out before a second visual capture. This is
recorded as a tooling limitation, not a product success claim. The local frontend lint,
TypeScript, component-test, and production-build gates remain the reproducible validation
evidence for the UI.

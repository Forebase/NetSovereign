# ADR 0002: Separate world intent, capabilities, provider bindings, and observed state
Status: Accepted for v0.1

World intent is canonical institutional meaning. Capabilities state what materialisation must eventually provide. Provider bindings are explicitly replaceable choices whose free-form configuration cannot leak into domain objects. Observed state belongs to a later reconciliation runtime and is absent in v0.1. This separation permits deterministic validation without network or provider execution.

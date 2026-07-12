# Controlled Event Dataset — Superseded Plan

This filename is retained because the frozen pilot preregistration links to it. The original mock
schema, examples, CSV template, and readiness audit were retired on 2026-07-12; they were the only
users of a second legacy event shape.

Current authorities:

- collection design: [pilot_design_prereg.md](pilot_design_prereg.md)
- event envelope: [`event_grammar.v1.schema.json`](../../schemas/event_grammar.v1.schema.json)
- partner study contract: [partner_collection_pipeline.md](partner_collection_pipeline.md)
- formal evaluation: [task_relevant_compression_audit.md](../spine/task_relevant_compression_audit.md)

New collection records must begin with a declared capture policy and use the maintained grammar or
partner schemas; do not recreate the retired mock packet.

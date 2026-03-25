# Infrastructure Design Plan — UOW-03 Push & Scheduling

## Status
- [x] Step 1: Analyze design artifacts (functional-design + nfr-design revisados)
- [x] Step 2: Identify infra delta (muy acotado: 1 tabla + IAM update)
- [x] Step 3: Confirm no ambiguities (stack heredado, decisiones ya tomadas en NFR)
- [x] Step 4: Generate infrastructure-design.md
- [x] Step 5: Generate deployment-architecture.md
- [x] Step 6: Present completion

## Decisions taken (from NFR)
| Topic | Decision |
|---|---|
| Scheduler | In-process, tick 15 min, mismo contenedor ECS |
| New infra | Solo `ppai-preferences` DynamoDB table |
| Dispatch persistence | `ppai-cycles` + event log (ya existe) |
| GSI | Ninguno en MVP (acceso solo por PK userId) |
| Networking | Sin cambios |
| ECS topology | Sin cambios |
| CloudWatch | Sin grupos nuevos |

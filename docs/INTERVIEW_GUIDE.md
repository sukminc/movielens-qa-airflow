# Interview walkthrough

## A short introduction

"I extended a MovieLens ranking exercise into a personal QA and data-pipeline
project. I used Airflow to replay daily batches, validate inputs and stored results,
and verify rankings before publishing a CSV. I also built a separate regression
testing DAG. The project let me revisit ideas from my previous QA work in a small,
reproducible environment."

## A deeper explanation

"The source dataset is static, so I split it by timestamp to simulate incoming
data. Each batch is inserted into SQLite in a transaction with a processing ledger.
If a named batch is submitted again unchanged, ingestion skips it. I generate
rankings in SQL and independently recalculate them in Python to check the output.
Before publication, I check that the candidate still matches its validated hash,
then replace the published file atomically. A replay checkpoint advances only
after successful publication. There are 24 unit tests, including 13 for the
extension, and a separate Airflow DAG runs the extension tests. This is a local
learning project; I would change the storage and concurrency model for production."

The extension was developed with AI assistance. Be ready to describe which parts
you ran, inspected, changed, and can explain yourself. Do not describe it as a
production deployment or a reproduction of proprietary employer code.

## Five-minute demonstration

1. Show the two DAGs and explain data processing versus regression testing.
2. Open a successful data run and trace input validation through publication.
3. Trigger an already processed date in manual mode. Show the ingestion result
   `status=skipped` while the Airflow task succeeds; the DB is not duplicated.
4. Show regression test logs, including wrong-order and wrong-average detection.
5. Show the published CSV and replay state. Explain why batch commit and overall
   workflow completion are separate records.

Use manual execution for a controlled demo. The clean-bootstrap instructions are
in RUNBOOK.md. Avoid mixing external CLI writes with an active data DAG.

## Questions to be able to answer

| Question | Point to explain |
| --- | --- |
| Why Airflow? | Dependencies, task status/logs, scheduling, and repeatable execution. Python implements the actual business rules. |
| What makes ingestion idempotent? | A named-batch ledger plus a content hash, checked and recorded in the same transaction as inserts. This is not universal event deduplication. |
| Why not retry every error? | Malformed input will not become valid by retrying. Automatic retries are currently disabled; transient failures could get a separate policy. |
| Why an independent validator? | SQL and Python express the aggregation differently, while known-answer tests provide an additional reference. Neither validates the truth of the original human ratings. |
| Why a publication hash? | It detects changed candidate bytes after validation; it is an integrity check, not an authentication signature. |
| What happens after DB commit but before publication? | DB changes remain. The replay checkpoint stays behind, allowing another run to skip duplicate ingestion and repeat downstream work. Full Airflow fault-injection coverage for this sequence is future work. |
| Is QA an automatic deployment gate? | No. The regression DAG is independent. Data-validation dependencies gate publication within the data DAG. |
| How would you scale it? | Shared durable storage, a database-backed checkpoint/locking design, explicit event/update semantics, operational monitoring, and integration tests. |
| What is still missing? | Rating updates/deletions, late-arrival handling, production auth, cloud deployment, and UI integration with the published output. |

## Evidence to point to

- `practice/test_apply_batch.py`: duplicate handling, changed-file rejection,
  transactional rollback, and successful ingestion.
- `practice/test_rankings.py`: known ranking results and detection of invalid output.
- `practice/test_replay.py`: checkpoint selection, ordering, idempotency, and completion.
- `practice/check_publication_guard.py`: temporary-file demonstration of publication
  refusal after candidate modification.
- `.github/workflows/tests.yml`: automated unit tests; not an Airflow integration test.

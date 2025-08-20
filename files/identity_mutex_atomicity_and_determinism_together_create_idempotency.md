---
title: Identity, mutex, atomicity, and determinism together create idempotency
date: 2025-07-21
tags: tech
---
# Identity, mutex, atomicity, and determinism together create idempotency
## We’d like to build ETLs that can get interrupted at any time and restart safely
Our system has to stay healthy through any interruption—Kubernetes evictions, network disconnects, even a fat-fingered kubectl delete pod. That requires two properties:

- **Interruptibility:** every subroutine is atomic, so we can kill a job at any point with zero corruption.
- **Restartability:** the ETL as a whole is idempotent, so rerunning it again after interruption lands in the exact same final state.

Interruptibility is the easy part. Restartability—modifying our system such that any ETL can be safely restarted without creating duplicate data, sending an email twice, or processing the wrong records is much more challenging. Restartability requires that every step or “subroutine” that makes up each ETL is **idempotent**, or can be run and re-run safely.
## Four properties that together forge idempotency

**Identity** gives every unit of work—both the whole ETL and each subroutine inside it—a unique, reproducible name. With that name the system can ask, *“have I done this exact thing before?”*

**Atomicity** makes each subroutine all-or-nothing. If we crash halfway through creating a bulk job, for example, no half-written data survives, so a retry can safely pick up the work to complete it.

**Mutex** enforces mutual exclusion when two runs target the same logical work but carry different identities—say, two timestamp-triggered invocations of the same monthly job. By serializing those runs, it eliminates write conflicts and other race conditions that identity alone can’t stop.

**Determinism** removes randomness from business logic. Given the same inputs and order, every replay walks the exact same decision path and converges on the same result.
Only when all four are true can a retry be both safe *and* a no-op for completed work. 
```
           +--------------------------------------+
           |          One ETL Operation           |
           |   id = "generate-statements-2025-07" |
           +------------------+-------------------+
                              |
      +-----------------------+-----------------------+
      |         Ordered chain of subroutines          |
      +----+-----------+-----------+-----------+------+
           |           |           |           |
           v           v           v           v
        [SR1]       [SR2]       [SR3]       [SR4]   …
        key=ETL-id  key=…       key=…       key=…
        bulk query  manipulate1 manipulate2 bulk load

Each subroutine key = {ETL-id} + short suffix,
```

With Identity to tag, Atomicity to protect, Mutex to coordinate, and Determinism to keep logic pure, every interrupted ETL can be restarted fearlessly.

Let’s dive into the first concept laddering up to idempotency: Identity. 
## Both ETLs and their constituent subroutines have identities
**Identity** serves as the foundation for everything else because it determines what constitutes unique work. Identity operates at two levels in our system: ETL Identity defines what constitutes a single logical ETL operation that should be retried as a unit, while Subroutine Identity ensures each individual step within an ETL can be uniquely identified, tracked and retried accurately. 
### Every ETL operation needs a unique identity value to distinguish retries from new work
Every ETL run needs an identity that marks it as either “the same work” or “new work.” The simplest way to supply that identity is through the job’s own inputs: if two invocations receive identical inputs, they represent the same logical operation and can be retried interchangeably; if the inputs differ, they represent distinct work. A parameter-less function such as `parseFile()` offers no such signal, so after one successful execution the system must treat any subsequent call as a duplicate and refuse to run it again. Add meaningful business data—say clientId + accountId, statementId + month, or a filename—and that data becomes the identity key. Adding filename, now `parseFile("file_A.csv")` can be replayed safely until it finishes, while `parseFile("file_B.csv")` proceeds as a separate, independent operation.
### Subroutines are the true unit of identity for tracking completion
ETL identity draws the outer boundary of a job—“parse this file” or “generate statements for July”—while subroutine identity names every atomic action that happens inside that boundary. We build each subroutine key by fusing the ETL context with details of the step itself. For example, the identifier `PARSE_FILE:INSERT:span-abc123:001` reads left-to-right as: the ETL (`PARSE_FILE`), the kind of ETL verb (`INSERT`), the workflow run that owns all retries (`span-abc123`), and a developer-assigned suffix (`001`) that guarantees uniqueness within that run. Because every subroutine key inherits the ETL key, the system can always trace a single step back to its parent job and decide—unambiguously—whether that step has already been done.
### Business-data based identities coordinate naturally while coarse-grained identities require explicit coordination
We can create ETL identities in two ways, and this choice fundamentally affects how much coordination our system needs.

**Business-data based ETL identities** come from meaningful inputs like filenames or customer IDs. For example, the ETL `parseFile("2025_ACHO.pgp")` gets the ETL identity `parse-file-2025_ACHO.pgp` and `generateStatements("2025-01")` gets the identity `generate-statements-2025-01`. When multiple operations share the same business-data based identity, their subroutines can reuse that same business data for their own idempotency checks, creating natural deduplication. If you don’t quite follow at this point, no worries. We’ll show a practical example when we discuss Mutex. 

**Coarse-grained ETL identities** are created when no obvious fine-grained business data exists to create an ETL identity from. In these cases, we create ETL identity based on coarser business context like the ETL type and the time it was triggered. For example, `syncCustomerData()` might get the identity `sync-customer-data-2025-01-23-14:30:15`. These identities create a coordination problem: different coarse-grained identities represent the same logical work, but the system treats them as separate operations. This means multiple instances of what should be the same job can run concurrently and produce unpredictable results. We need a mutual exclusion (mutex) mechanism to ensure that these kinds of ETLs don't run concurrently and interfere with one another.
## ETL Mutex requirements depend on whether we’re using business-data based identities, or coarse-grained identities
 ETLs with business-data identities don't need mutex most of the time, while ETLs with coarse-grained identities are more likely to need mutex. Let's explore why.
### Coarse-grained identities need job-type level mutex to prevent conflicts
When using coarse-grained identities, multiple requests for the same logical work get different identities. For example, looking at two HTTP requests to generate statements sent one second apart: request 1 might get identity `generate-statements-2025-01-23-14:30:15` while request 2 gets `generate-statements-2025-01-23-14:30:16`. The system thinks these are different operations and runs them concurrently, causing duplicate work on the same customers, file conflicts database race conditions, and inconsistent completion states. We solve this with job-type level mutex that prevents concurrent instances of the same job type from running simultaneously. That means ETLs of the same type i.e. two ETLs of the type `generate-statements` can't run at the same time.
### Business-data based identities often eliminate the need for mutex because they naturally don’t interfere with one another
When using business-data based identities, the identity itself often provides coordination without needing ETL-type mutex. Let’s explore exactly what we mean by that. 

Operations with different business inputs like `parse-file-A.csv` and `parse-file-B.csv` can run concurrently without logical conflict because they're naturally working on separate data. Operations with identical business inputs like two concurrent calls of ETL `parseFile(2025_ACHO.pgp)` share the same identity, so their subroutines naturally deduplicate through the same business data, converging to identical final states regardless of execution order. Note that resource-level contention (disk I/O, database write locks) may still occur, but this lower-level contention is acceptable.

**A practical example: File parsing with globally unique filenames**

Consider what happens when we receive two simultaneous requests to parse `2025_ACHO.pgp`:

1. Both ETL operations get the same identity: `parse-file-2025_ACHO.pgp`.
2. Both operations decompose into idempotent subroutines.
3. Each subroutine can determine if its work is already done using the filename.
4. The operations can run concurrently because they use shared deduplication based on filename.
5. The final state is identical regardless of which operation "wins" each step.

The external identity—the filename in this case—provides natural coordination between concurrent operations, eliminating the need for explicit locking.
## Atomicity ensures each subroutine completes fully or leaves no trace
Once we have proper identity tracking and mutex in place, we need to ensure that each individual step doesn't make a mess, even if interrupted in the middle. That’s where **Atomicity** comes in. Atomicity ensures each subroutine either completes fully or leaves no trace, giving us **interruptibility**. ETL operations can be interrupted at any point without leaving the system corrupted because every subroutine follows an "all-or-nothing" pattern. If a subroutine succeeds, all its changes are committed. If a subroutine fails, no changes are left behind. In other words, no subroutine can leave data in a half-written or otherwise corrupt state.
## Determinism ensures operations behave like pure functions
With proper identity, mutex, and atomicity in place, we need one more guarantee for truly safe retries. **Determinism** ensures convergent state: retries must end up doing the same things against the same data regardless of execution path.

Without determinism, an ETL that randomly selects 100 checks from a pool of 1000 to send could pick different checks on retry, even with perfect identity tracking and atomicity. To maintain determinism, in this example the check-sending algorithm must sort data before processing, use otherwise deterministic selection algorithms, and avoid any randomness or time-based variations that could cause retries to converge on different final states.
## Idempotency emerges when all four concepts work together
**Idempotency** is the emergent property we get when Identity, Mutex, Atomicity, and Determinism work together properly. Operations become safely retryable because the system can determine what work has already been completed and reproduce convergent results.
## Three specialized tables and a cache implement these concepts in practice
Moving from concepts to implementation, we use three specialized tables and a hot-cache for volume jobs that each handle a specific concern related to identity, mutex, and atomicity coordination. 

These data stores also work with SpanIds, which are globally unique identifiers that our system generates for each ETL operation to link records across tables and enable retry detection through infrastructure like Argo.
### The ETL table stores unique identities for ETLs
The ETL table establishes what work we're doing by storing the unique identity for each ETL. The columns contain an identity and the SpanId of the job that picked up that ETL. 
| Identity | SpanId |
|----------|--------|
| generate-statements-2025-01 | span-abc123 |
| parse-file-customer-data.csv | span-def456 |
| sync-customer-data-2025-01-23-14:30:15 | span-ghi789 |
### The Mutex table prevents conflicting job types from running together
The Mutex table determines whether operations should be allowed to start by preventing conflicts between operations that use course-grained identities:

| ETL Type            | SpanId      |
|---------------------|-------------|
| generate-statements | span-abc123 |
| clear-transactions  | span-ghi789 |
### The Action table enables atomic completion tracking for each subroutine
The **Action table** remains the authoritative ledger: every subroutine writes its key there atomically alongside the business‑logic DML.

| Key |
|-----|
| STATEMENT_LINK-INSERT-span-abc123-001 |
| PARSE_FILE-UPDATE-span-def456-002 |
| GENERATE_STATEMENTS-DELETE-span-ghi789-003 |

Key format follows `<NAME>-<DML_TYPE>-<SPANID>-<INDEX>` where the developer assigns the index to ensure uniqueness within each ETL operation. These records are inserted atomically with business logic DML using composite requests.

 But some workflows—most obviously bulk delivery of statement emails—may touch 100K‑plus sub‑actions in a single ETL run. Round‑tripping to the database for each check would choke throughput, so we add those keys into Redis only as a hot cache. Each email gets its own identity such as its statement id, stored as a simple Redis key with an expiry.  During email send execution we consult Redis first to decide whether the step has already run. This two‑tier scheme lets idempotency checks stay fast even in high-volume situations. The Action table gives us easier access and higher persistence for ETLs with a low volume of transactions.
## Choose your Mutex approach based on whether you have meaningful business data
With the implementation details in place, the practical question becomes: how do you choose which Mutex approach to use for each ETL type? Your choice depends entirely on whether your ETL type has meaningful business data to create natural identity and coordination.
### ETLs with meaningful business inputs need minimal coordination
When business inputs are meaningful, you can skip mutex entirely since natural coordination happens through business data.
### Operations without meaningful business inputs require explicit coordination
For operations without meaningful business inputs, you'll need to use coarse-grained identity that's based on timestamp or some other available value. You'll also need job-type level mutex to prevent conflicts between operations that represent the same logical work but have different coarse-grained identities.
### Transform coarse-grained identities into meaningful ones when possible
To improve coarse-grained identity operations, look for hidden business context like month-year for monthly jobs that can transform coarse-grained identities into meaningful ones. Consider refactoring operations to accept proper external inputs that provide natural business-data identities. When technical debt prevents clean solutions, you can create meaningful coarse-grained inputs like dates that still provide better coordination than pure timestamp-based identities.

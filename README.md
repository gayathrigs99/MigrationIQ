An AI-assisted Oracle-to-PostgreSQL migration workflow with retrieval-grounded conversion and deterministic validation.

MigrationIQ converts Oracle SQL and PL/SQL (procedures, functions, triggers, queries, DDL) to PostgreSQL. It does not rely on a single LLM prompt. A LangGraph workflow analyzes the input, retrieves relevant migration knowledge, asks Gemini for a conversion, validates the result with deterministic checks, and retries with the validation feedback when the output is not acceptable. The final report lists what changed, why, which sources were used, and what a human still needs to review.

WORKING

Oracle SQL / PL/SQL
        |
        v
   [ analyze ]    rule-based detection of Oracle constructs (37 rules)
        |
        v
   [ retrieve ]   one metadata-filtered ChromaDB query per construct
        |
        v
   [ convert ]    Gemini, grounded in the retrieved documentation
        |
        v
   [ validate ]   leftover-Oracle scan, SQLGlot parse, PL/pgSQL structure checks
        |
   pass |   fail, retries left
        |      +-----------------> back to [ convert ] with the validation errors
        v
   [ report ]     converted SQL, transformations, references, warnings, tests

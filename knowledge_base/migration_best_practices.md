# Oracle to PostgreSQL Migration Best Practices

Common semantic differences and review guidance.

## Empty string and NULL

Oracle treats the empty string `''` as NULL. PostgreSQL treats them as different values. This changes comparisons, `NOT NULL` constraints, concatenation, `COALESCE` results and `WHERE col IS NULL` filters.

```sql
-- Oracle: both are true
SELECT 1 FROM DUAL WHERE '' IS NULL;
-- PostgreSQL: false; '' is a value
```

Review every place that stores, compares or concatenates strings that may be empty.

## Integer division

Oracle `/` always returns a decimal result (`5 / 2` gives 2.5). PostgreSQL truncates when both operands are integers (`5 / 2` gives 2). Cast one operand to `numeric` when mapped columns became `integer`.

```sql
SELECT total::numeric / count_items FROM stats;
```

## Implicit type conversion

Oracle converts types silently, for example `WHERE varchar_col = 123`. PostgreSQL raises an error. Add explicit casts and use matching types in comparisons and joins.

## Identifier case

Oracle stores unquoted identifiers in upper case, PostgreSQL in lower case. Avoid quoted mixed-case names in the target schema.

## Optimizer hints

Oracle hints such as `/*+ INDEX(e idx) */` are plain comments in PostgreSQL and have no effect. Remove them and tune using `EXPLAIN ANALYZE` and indexes.

## Synonyms and database links

PostgreSQL has no synonyms. Use views, schema-qualified names or `search_path`. Database links map to `postgres_fdw` or `dblink`.

## Sequences

Gaps and caching behave similarly, but identity columns (`GENERATED ... AS IDENTITY`) are the preferred replacement for trigger plus sequence patterns.

## Case-sensitive text comparison and collation

Sort order and string comparison depend on collation in both databases and often differ by default. Test `ORDER BY` and `LIKE` on text with mixed case and accents.

## Constructs that always need manual review

Autonomous transactions, package state, dynamic SQL, hierarchical queries (`CONNECT BY`), `(+)` joins with extra conditions, bulk collection logic, and any date arithmetic involving month ends.

## Treat the output as a draft

A converted statement that parses is not proven correct. Run it on PostgreSQL, compare results with Oracle on the same synthetic data, and test NULLs, empty strings, date boundaries, error paths and large inputs before release.

## Suggested test checklist

Cover NULL and empty-string inputs, boundary dates (month ends, leap days), numeric rounding and division, duplicate and missing rows, error conditions and the error codes callers depend on, and transaction rollback behavior.

## Never run generated code on production

Review generated SQL, run it first in a sandbox with synthetic data, and require explicit approval before changing a real database.

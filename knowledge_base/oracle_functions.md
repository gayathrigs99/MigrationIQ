# Oracle Functions and SQL Syntax: PostgreSQL Equivalents

Conversion patterns for Oracle-specific functions and SQL syntax.

## NVL to COALESCE

Replace `NVL(a, b)` with `COALESCE(a, b)`. COALESCE accepts more than two arguments and evaluates lazily.

```sql
-- Oracle
SELECT NVL(commission, 0) FROM employees;
-- PostgreSQL
SELECT COALESCE(commission, 0) FROM employees;
```

Both arguments must have compatible types in PostgreSQL. Oracle converts implicitly; add a cast if needed.

## NVL2 to CASE

Replace `NVL2(expr, if_not_null, if_null)` with a CASE expression.

```sql
-- Oracle
SELECT NVL2(commission, 'Paid', 'None') FROM employees;
-- PostgreSQL
SELECT CASE WHEN commission IS NOT NULL THEN 'Paid' ELSE 'None' END FROM employees;
```

## DECODE to CASE

Replace `DECODE(expr, s1, r1, s2, r2, default)` with a simple CASE. DECODE treats two NULLs as equal; CASE does not, so add an explicit `IS NULL` branch when NULL can occur.

```sql
-- Oracle
SELECT DECODE(status, 'A', 'Active', 'I', 'Inactive', 'Unknown') FROM accounts;
-- PostgreSQL
SELECT CASE status WHEN 'A' THEN 'Active' WHEN 'I' THEN 'Inactive' ELSE 'Unknown' END FROM accounts;
```

PostgreSQL has a function named `decode` but it decodes binary text. It is not a replacement.

## SYSDATE to CURRENT_TIMESTAMP

Oracle `SYSDATE` returns a DATE that includes the time of day. Use `CURRENT_TIMESTAMP` (timestamptz) or `LOCALTIMESTAMP` (timestamp without time zone).

`CURRENT_TIMESTAMP` is fixed at the start of the transaction. Use `clock_timestamp()` when the actual wall-clock time at each call is required, for example when measuring elapsed time inside a function.

```sql
-- Oracle
SELECT SYSDATE FROM DUAL;
-- PostgreSQL
SELECT LOCALTIMESTAMP;
```

## SYSTIMESTAMP to CURRENT_TIMESTAMP

`SYSTIMESTAMP` returns a TIMESTAMP WITH TIME ZONE. The PostgreSQL equivalent is `CURRENT_TIMESTAMP` (transaction start) or `clock_timestamp()` (real time).

## FROM DUAL

PostgreSQL does not need a dummy table. Remove `FROM DUAL`.

```sql
-- Oracle
SELECT 1 + 1 FROM DUAL;
-- PostgreSQL
SELECT 1 + 1;
```

## Date arithmetic

Oracle adds numbers to dates as days and `date - date` returns a number of days. In PostgreSQL use intervals.

```sql
-- Oracle
SELECT SYSDATE + 7, SYSDATE - hire_date FROM employees;
-- PostgreSQL
SELECT LOCALTIMESTAMP + INTERVAL '7 days',
       CURRENT_DATE - hire_date::date      -- integer days
FROM employees;
```

`timestamp - timestamp` returns an interval. Use `EXTRACT(EPOCH FROM ...)` or `date - date` to get a number.

## TO_DATE keeps no time of day

Oracle `TO_DATE('2024-01-31 14:30', 'YYYY-MM-DD HH24:MI')` keeps the time because Oracle DATE has a time part. PostgreSQL `to_date` returns a `date` and drops it. Use `to_timestamp` when time matters.

```sql
-- PostgreSQL
SELECT to_timestamp('2024-01-31 14:30', 'YYYY-MM-DD HH24:MI');
```

Check format masks that differ between the databases (for example two-digit year masks).

## TO_CHAR on numbers without a format

Oracle allows `TO_CHAR(n)`. PostgreSQL requires a format for numerics. Use a cast for the plain conversion.

```sql
-- Oracle
SELECT TO_CHAR(salary) FROM employees;
-- PostgreSQL
SELECT salary::text FROM employees;
-- With a format mask, to_char(salary, 'FM999999.00') works in both.
```

## TRUNC on dates

Oracle `TRUNC(date)` removes the time. PostgreSQL `trunc` only handles numbers. For dates use `date_trunc` or a cast.

```sql
-- Oracle
SELECT TRUNC(SYSDATE), TRUNC(SYSDATE, 'MM') FROM DUAL;
-- PostgreSQL
SELECT CURRENT_DATE, date_trunc('month', CURRENT_DATE);
```

`TRUNC(number, n)` maps directly to `trunc(numeric, n)`.

## ADD_MONTHS

Use interval arithmetic.

```sql
-- Oracle
SELECT ADD_MONTHS(hire_date, 6) FROM employees;
-- PostgreSQL
SELECT hire_date + INTERVAL '6 months' FROM employees;
```

Edge case: Oracle returns the last day of the target month when the input is the last day of a month (Feb 28 plus 1 month gives Mar 31). PostgreSQL keeps the day number (Feb 28 plus 1 month gives Mar 28). Flag this for review.

## MONTHS_BETWEEN

No direct equivalent. Oracle returns a fractional number. For whole months use `age()`.

```sql
-- PostgreSQL (whole months only)
SELECT EXTRACT(YEAR FROM age(d1, d2)) * 12 + EXTRACT(MONTH FROM age(d1, d2));
```

If fractional months are required, implement a custom function and test it against Oracle output.

## LISTAGG to STRING_AGG

```sql
-- Oracle
SELECT LISTAGG(name, ', ') WITHIN GROUP (ORDER BY name) FROM employees;
-- PostgreSQL
SELECT STRING_AGG(name, ', ' ORDER BY name) FROM employees;
```

`ON OVERFLOW` clauses have no equivalent.

## INSTR to POSITION or strpos

`INSTR(s, sub)` becomes `strpos(s, sub)` or `POSITION(sub IN s)`. Both return 0 when not found.

```sql
-- Oracle
SELECT INSTR(email, '@') FROM users;
-- PostgreSQL
SELECT strpos(email, '@') FROM users;
```

`INSTR` with a start position, negative position, or occurrence number has no direct equivalent. Use `substring` with `strpos`, or `regexp_instr` style logic via `regexp_match`.

## SUBSTR with negative start

Oracle `SUBSTR(s, -3)` returns the last three characters. PostgreSQL treats a start before 1 differently. Use `right(s, 3)` for the end of a string.

```sql
-- Oracle
SELECT SUBSTR(code, -3) FROM items;
-- PostgreSQL
SELECT right(code, 3) FROM items;
```

## String concatenation with NULL

In Oracle `'a' || NULL` is `'a'` because NULL and the empty string are the same. In PostgreSQL the result is NULL. Use `concat()` (ignores NULLs) or wrap operands in `COALESCE`.

```sql
-- PostgreSQL
SELECT concat(first_name, ' ', last_name) FROM employees;
```

## ROWNUM to LIMIT

`WHERE ROWNUM <= n` becomes `LIMIT n`. Oracle applies ROWNUM before ORDER BY, so the Oracle top-N pattern uses a subquery. PostgreSQL applies ORDER BY first.

```sql
-- Oracle
SELECT * FROM (SELECT * FROM employees ORDER BY salary DESC) WHERE ROWNUM <= 5;
-- PostgreSQL
SELECT * FROM employees ORDER BY salary DESC LIMIT 5;
```

Use `ROW_NUMBER() OVER (...)` when ROWNUM is used to number rows or in the SELECT list.

## Sequences: NEXTVAL and CURRVAL

```sql
-- Oracle
INSERT INTO orders (id) VALUES (order_seq.NEXTVAL);
SELECT order_seq.CURRVAL FROM DUAL;
-- PostgreSQL
INSERT INTO orders (id) VALUES (nextval('order_seq'));
SELECT currval('order_seq');
```

`currval` fails if `nextval` has not been called in the same session, as in Oracle.

## MINUS to EXCEPT

Replace the `MINUS` set operator with `EXCEPT`. The semantics (distinct rows) are the same. Use `EXCEPT ALL` only when duplicates must be kept.

## Oracle outer join operator (+)

Rewrite `(+)` joins as ANSI joins. The `(+)` goes on the side that may be missing.

```sql
-- Oracle
SELECT e.name, d.name FROM employees e, departments d WHERE e.dept_id = d.id(+);
-- PostgreSQL
SELECT e.name, d.name FROM employees e LEFT JOIN departments d ON e.dept_id = d.id;
```

Conditions with `(+)` on filters belong in the `ON` clause, not `WHERE`. Review complex cases manually.

## CONNECT BY to WITH RECURSIVE

```sql
-- Oracle
SELECT id, name, LEVEL FROM employees
START WITH manager_id IS NULL CONNECT BY PRIOR id = manager_id;
-- PostgreSQL
WITH RECURSIVE tree AS (
  SELECT id, name, manager_id, 1 AS level FROM employees WHERE manager_id IS NULL
  UNION ALL
  SELECT e.id, e.name, e.manager_id, t.level + 1
  FROM employees e JOIN tree t ON e.manager_id = t.id
)
SELECT id, name, level FROM tree;
```

`SYS_CONNECT_BY_PATH`, `CONNECT_BY_ISLEAF`, `ORDER SIBLINGS BY` and cycle handling need manual rewrites. Review manually.

## MERGE

PostgreSQL 15 and later support `MERGE`, with differences from Oracle (no `DELETE` inside the `UPDATE` branch, different concurrency behavior). For older versions, or for simple upserts, use `INSERT ... ON CONFLICT`.

```sql
-- PostgreSQL
INSERT INTO accounts (id, balance) VALUES (1, 100)
ON CONFLICT (id) DO UPDATE SET balance = EXCLUDED.balance;
```

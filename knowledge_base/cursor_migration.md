# Cursor and Collection Migration: PL/SQL to PL/pgSQL

Patterns for explicit cursors, cursor variables, bulk operations and collections.

## Explicit cursor declaration

Oracle `CURSOR name IS query` becomes `name CURSOR FOR query` in the `DECLARE` section. Parameters keep the same idea.

```sql
-- Oracle
CURSOR c_emp (p_dept NUMBER) IS SELECT id, name FROM employees WHERE dept_id = p_dept;
-- PostgreSQL
c_emp CURSOR (p_dept integer) FOR SELECT id, name FROM employees WHERE dept_id = p_dept;
```

`OPEN c_emp(10); FETCH c_emp INTO v_id, v_name; CLOSE c_emp;` is unchanged.

## Cursor FOR loop

The loop is nearly identical. Remove the parentheses around inline queries.

```sql
-- Oracle
FOR r IN (SELECT id, name FROM employees) LOOP ... END LOOP;
-- PostgreSQL
FOR r IN SELECT id, name FROM employees LOOP ... END LOOP;
```

A bound cursor variable also works: `FOR r IN c_emp(10) LOOP`.

## Cursor attributes

| Oracle | PostgreSQL |
|---|---|
| `c%NOTFOUND` after FETCH | `NOT FOUND` (special variable) |
| `c%FOUND` | `FOUND` |
| `c%ISOPEN` | no equivalent; track state in a variable |
| `c%ROWCOUNT` | count manually in a variable |
| `SQL%ROWCOUNT` | `GET DIAGNOSTICS v_count = ROW_COUNT;` |
| `SQL%NOTFOUND` | `NOT FOUND` after INSERT, UPDATE or DELETE |

```sql
LOOP
  FETCH c_emp INTO v_id, v_name;
  EXIT WHEN NOT FOUND;
END LOOP;
```

## REF CURSOR and SYS_REFCURSOR

Use the `refcursor` type. `OPEN cur FOR query` is unchanged. The caller must fetch inside the same transaction.

```sql
-- Oracle
PROCEDURE get_emps(p_cur OUT SYS_REFCURSOR) IS BEGIN OPEN p_cur FOR SELECT * FROM employees; END;
-- PostgreSQL
CREATE FUNCTION get_emps() RETURNS refcursor LANGUAGE plpgsql AS $$
DECLARE cur refcursor;
BEGIN OPEN cur FOR SELECT * FROM employees; RETURN cur; END; $$;
```

A set-returning function (`RETURNS TABLE (...)` with `RETURN QUERY`) is often simpler for client applications.

## BULK COLLECT

No direct equivalent. Collect into an array with `array_agg` or `ARRAY(subquery)`, or process the rows in one set-based statement.

```sql
-- Oracle
SELECT id BULK COLLECT INTO v_ids FROM employees WHERE dept_id = 10;
-- PostgreSQL
SELECT array_agg(id) INTO v_ids FROM employees WHERE dept_id = 10;
```

`BULK COLLECT ... LIMIT` batch loops usually become one set-based statement. Review manually.

## FORALL

`FORALL` has no equivalent. Replace it with a set-based statement using `unnest`.

```sql
-- Oracle
FORALL i IN 1..v_ids.COUNT UPDATE employees SET salary = salary * 1.1 WHERE id = v_ids(i);
-- PostgreSQL
UPDATE employees SET salary = salary * 1.1 WHERE id = ANY (v_ids);
```

## PL/SQL collections

`TABLE OF`, `VARRAY` and associative arrays become PostgreSQL arrays (`integer[]`), composite types, or temporary tables for large data. Index access changes from `v(i)` to `v[i]`, and arrays are 1-based. The methods `COUNT`, `EXTEND`, `DELETE` and `EXISTS` map to `array_length`, `array_append`, array slicing and subscript tests.

## Prefer set-based SQL

Row-by-row loops that run one DML statement per row are much slower in PostgreSQL than a single `INSERT ... SELECT` or `UPDATE ... FROM`. Rewrite when the loop body has no side effects between rows.

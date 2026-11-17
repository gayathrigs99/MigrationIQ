# Procedure, Function and Package Migration

How to convert PL/SQL program units to PL/pgSQL.

## Function structure

The body moves into a dollar-quoted string. `RETURN type` in the header becomes `RETURNS type`, `IS`/`AS` before the declarations becomes `AS $$ DECLARE`, and a `LANGUAGE plpgsql` clause is required.

```sql
-- Oracle
CREATE OR REPLACE FUNCTION get_bonus(p_salary IN NUMBER) RETURN NUMBER IS
  v_rate NUMBER := 0.1;
BEGIN
  RETURN NVL(p_salary, 0) * v_rate;
END;
/
-- PostgreSQL
CREATE OR REPLACE FUNCTION get_bonus(p_salary numeric) RETURNS numeric
LANGUAGE plpgsql AS $$
DECLARE
  v_rate numeric := 0.1;
BEGIN
  RETURN COALESCE(p_salary, 0) * v_rate;
END;
$$;
```

Remove the SQL*Plus `/` terminator.

## Procedure structure

PostgreSQL 11 and later support `CREATE PROCEDURE` and `CALL`. Replace `EXEC proc(args)` with `CALL proc(args)`. `OUT` parameters in procedures need PostgreSQL 14 or later; older versions use `INOUT`.

```sql
CREATE OR REPLACE PROCEDURE raise_salary(p_id integer, p_pct numeric)
LANGUAGE plpgsql AS $$
BEGIN
  UPDATE employees SET salary = salary * (1 + p_pct / 100) WHERE id = p_id;
END;
$$;
```

## Parameter modes

`IN` stays `IN`. `IN OUT` becomes `INOUT`. Remove `NOCOPY`. Default values (`DEFAULT` or `:=`) are supported. Functions with several `OUT` parameters return a record.

## Declarations and control flow

Variable declarations, `:=` assignment, `IF / ELSIF / ELSE`, `CASE`, `WHILE`, `FOR i IN 1..n`, `EXIT WHEN` and `CONTINUE WHEN` work the same. `GOTO` and labels for jumping are not supported. Restructure with loops and conditions.

## Local (nested) subprograms

Procedures and functions declared inside another block are not supported. Move them to separate top-level functions and pass the needed variables as parameters.

## Transaction control

Functions cannot run `COMMIT` or `ROLLBACK`. Procedures can, but only when called outside an explicit transaction block and not inside a block that has an `EXCEPTION` clause. Move commit logic to the caller if the code is a function.

## PRAGMA AUTONOMOUS_TRANSACTION

There is no equivalent. Common substitutes: a loop-back connection with `dblink`, the `pg_background` extension, or moving the audit or logging write to the application or a queue. Each changes behavior. Review manually.

## Dynamic SQL

`EXECUTE IMMEDIATE` becomes `EXECUTE`. Bind placeholders change from `:1` or `:name` to `$1`, `$2`. Build identifiers with `format('%I', name)` and literals with `%L` to avoid injection.

```sql
-- Oracle
EXECUTE IMMEDIATE 'SELECT COUNT(*) FROM ' || p_table || ' WHERE id = :1' INTO v_count USING p_id;
-- PostgreSQL
EXECUTE format('SELECT COUNT(*) FROM %I WHERE id = $1', p_table) INTO v_count USING p_id;
```

## DBMS_OUTPUT

Replace `DBMS_OUTPUT.PUT_LINE(msg)` with `RAISE NOTICE '%', msg;`. Output goes to the client message stream or the server log, not a buffer.

## Packages

PostgreSQL has no packages. Use one schema per package and one function per subprogram, so `pkg.proc(...)` becomes `pkg.proc(...)`. Package-level variables and initialization blocks have no equivalent; keep state in a table, a temporary table, or session settings via `set_config` and `current_setting`. Overloaded subprograms remain possible. Review manually.

## Returning result sets

Pipelined functions and functions returning collections of rows become set-returning functions.

```sql
CREATE FUNCTION list_emps(p_dept integer) RETURNS TABLE (id integer, name text)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY SELECT e.id, e.name FROM employees e WHERE e.dept_id = p_dept;
END;
$$;
```

Qualify column names with a table alias in `RETURN QUERY`, because output column names are also variables inside the function.

## Triggers

PostgreSQL needs a trigger function (returning `trigger`) plus a separate `CREATE TRIGGER`. Replace `:NEW` and `:OLD` with `NEW` and `OLD`. Before-row triggers must `RETURN NEW` (or `NULL` to skip the row).

```sql
CREATE FUNCTION set_updated() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at := now(); RETURN NEW; END; $$;
CREATE TRIGGER trg_set_updated BEFORE UPDATE ON employees
FOR EACH ROW EXECUTE FUNCTION set_updated();
```

## DETERMINISTIC and function volatility

Oracle `DETERMINISTIC` maps to `IMMUTABLE`. Functions that read tables should be `STABLE`. The default is `VOLATILE`. Wrong volatility can give wrong results in indexes and queries.

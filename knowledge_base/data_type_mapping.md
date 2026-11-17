# Oracle to PostgreSQL Data Type Mapping

Recommended target types for Oracle column and variable types.

## VARCHAR2 and NVARCHAR2

`VARCHAR2(n)` becomes `varchar(n)`, or `text` when no length limit is needed. `NVARCHAR2(n)` also becomes `varchar(n)` when the database encoding is UTF8.

Oracle lengths default to bytes (`VARCHAR2(10 BYTE)`); PostgreSQL lengths are always characters. Remove `BYTE` and `CHAR` qualifiers.

```sql
-- Oracle
name VARCHAR2(100 CHAR)
-- PostgreSQL
name varchar(100)
```

## NUMBER

`NUMBER(p, s)` becomes `numeric(p, s)`. For integer columns, narrower types are faster:

| Oracle | PostgreSQL |
|---|---|
| `NUMBER(p)` with p up to 4 | `smallint` |
| `NUMBER(p)` with p up to 9 | `integer` |
| `NUMBER(p)` with p up to 18 | `bigint` |
| `NUMBER(p, s)`, larger p, or plain `NUMBER` | `numeric` |

When mapping to `integer`, remember integer division truncates in PostgreSQL. See migration_best_practices.

## FLOAT, BINARY_FLOAT, BINARY_DOUBLE

`BINARY_FLOAT` becomes `real`. `BINARY_DOUBLE` and `FLOAT` become `double precision`. Use `numeric` when exact decimal results are required.

## DATE

Oracle `DATE` stores date and time to the second. Map it to `timestamp(0)`, not PostgreSQL `date`, unless the time portion is never used.

```sql
-- Oracle
hire_date DATE
-- PostgreSQL
hire_date timestamp(0)
```

## TIMESTAMP types

`TIMESTAMP(n)` becomes `timestamp(n)`. `TIMESTAMP WITH TIME ZONE` and `TIMESTAMP WITH LOCAL TIME ZONE` become `timestamptz`. Verify session time zone behavior, as Oracle's LOCAL TIME ZONE type converts to the session zone on read.

## INTERVAL types

`INTERVAL YEAR TO MONTH` and `INTERVAL DAY TO SECOND` both map to `interval`. Operations on intervals can differ; test them.

## CLOB, NCLOB and LONG

All map to `text`. PostgreSQL `text` holds up to 1 GB and needs no special LOB API. Remove `DBMS_LOB` calls and use text functions such as `length`, `substr` and `||`.

## BLOB, RAW and LONG RAW

All map to `bytea`. Very large binary objects can use PostgreSQL large objects (`lo_*` functions) instead.

## CHAR

`CHAR(n)` becomes `char(n)`. Both pad with spaces; comparison semantics differ slightly, so prefer `varchar` for new designs.

## Boolean flags

Oracle SQL traditionally has no boolean column type; flags are `NUMBER(1)` or `CHAR(1)`. Converting to `boolean` is cleaner but requires changing every comparison (`flag = 1` becomes `flag`). Keep the original type if changing application code is out of scope.

## ROWID

`ROWID` has no stable equivalent. PostgreSQL `ctid` changes on updates and vacuum. Replace `ROWID` logic with the primary key.

## XMLTYPE

`XMLTYPE` becomes `xml`. XQuery and XMLTABLE usage needs manual conversion to PostgreSQL XML functions (`xpath`, `xmltable`).

## Anchored types

`%TYPE` and `%ROWTYPE` work in PL/pgSQL with the same syntax. Keep them to follow column type changes automatically.

```sql
v_salary employees.salary%TYPE;
r_employee employees%ROWTYPE;
```

## Identifier case

Oracle folds unquoted identifiers to upper case; PostgreSQL folds them to lower case. Use unquoted lower-case names. Quoted mixed-case identifiers must stay quoted everywhere.

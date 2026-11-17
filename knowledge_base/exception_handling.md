# Exception Handling: Oracle PL/SQL to PL/pgSQL

Differences in error handling syntax and behavior.

## Exception block syntax

The block structure is the same. Handlers use `EXCEPTION WHEN condition THEN` and `WHEN OTHERS THEN` catches all errors except query cancellation and assertion failures.

```sql
BEGIN
  -- statements
EXCEPTION
  WHEN OTHERS THEN
    RAISE;  -- re-raise the current error
END;
```

## Predefined exception names

| Oracle | PostgreSQL condition name |
|---|---|
| `NO_DATA_FOUND` | `no_data_found` (see SELECT INTO below) |
| `TOO_MANY_ROWS` | `too_many_rows` (see SELECT INTO below) |
| `DUP_VAL_ON_INDEX` | `unique_violation` |
| `ZERO_DIVIDE` | `division_by_zero` |
| `INVALID_NUMBER` | `invalid_text_representation` |
| `VALUE_ERROR` | `numeric_value_out_of_range`, `string_data_right_truncation` or `invalid_text_representation`, depending on cause |

```sql
EXCEPTION
  WHEN unique_violation THEN ...
  WHEN division_by_zero THEN ...
```

## SELECT INTO and NO_DATA_FOUND

In Oracle, `SELECT ... INTO` raises `NO_DATA_FOUND` for zero rows and `TOO_MANY_ROWS` for several. In PostgreSQL it does neither by default: zero rows set the variables to NULL and several rows silently use the first. Add `STRICT` to get Oracle behavior.

```sql
-- PostgreSQL
SELECT name INTO STRICT v_name FROM employees WHERE id = p_id;
```

Without `STRICT`, `WHEN NO_DATA_FOUND` handlers never fire for SELECT INTO.

## RAISE_APPLICATION_ERROR

Use `RAISE EXCEPTION` with a message and a custom SQLSTATE. Oracle codes `-20000` to `-20999` have no direct mapping; choose a documented five-character SQLSTATE for each.

```sql
-- Oracle
RAISE_APPLICATION_ERROR(-20001, 'Insufficient balance');
-- PostgreSQL
RAISE EXCEPTION 'Insufficient balance' USING ERRCODE = 'P0001';
```

Callers that test the numeric Oracle code must be updated to test the SQLSTATE.

## SQLCODE and SQLERRM

`SQLERRM` exists in PL/pgSQL. `SQLCODE` does not; use `SQLSTATE`, which is a five-character string, not a number.

```sql
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE 'Error % : %', SQLSTATE, SQLERRM;
```

## User-defined exceptions

PL/pgSQL has no `EXCEPTION` variables. Raise with a custom SQLSTATE and catch it by that code.

```sql
-- Oracle
e_invalid EXCEPTION;
... RAISE e_invalid; ...
EXCEPTION WHEN e_invalid THEN ...
-- PostgreSQL
RAISE EXCEPTION 'Invalid input' USING ERRCODE = 'U0001';
EXCEPTION WHEN SQLSTATE 'U0001' THEN ...
```

`PRAGMA EXCEPTION_INIT` is removed; catch the specific SQLSTATE or condition name instead.

## Error rolls back the whole block

A PL/pgSQL block with an `EXCEPTION` clause runs in a subtransaction. When an error is caught, all changes made inside that block are rolled back. Oracle rolls back only the failing statement. Review handlers that rely on earlier statements surviving the error.

Blocks with exception clauses are also slower, so avoid them inside tight loops.

## Error diagnostics

Replace `DBMS_UTILITY.FORMAT_ERROR_BACKTRACE` and `FORMAT_ERROR_STACK` with `GET STACKED DIAGNOSTICS`.

```sql
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT, v_context = PG_EXCEPTION_CONTEXT;
```

## Failed transactions

In PostgreSQL an unhandled error aborts the whole transaction; later statements fail until `ROLLBACK`. Oracle keeps the transaction usable after a failed statement. Wrap statements in an exception block if the code must continue after an error.

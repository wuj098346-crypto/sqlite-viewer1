# Table Row Editing Design

## Purpose

Allow users to add and update rows directly in the SQLite database they opened. The data page remains the only write surface: the SQL page continues to accept only read-only statements, and the application does not add delete or schema-editing capabilities.

## Scope

- Add `Add row` and `Edit row` actions to the data page for tables.
- Write changes back to the opened SQLite file.
- Keep all primary-key fields immutable during edits.
- Let SQLite generate a single `INTEGER PRIMARY KEY` when adding a row.
- Require user-provided values for composite and text primary keys when adding a row.
- Support nullable fields with an explicit `NULL` control that is distinct from an empty string.
- Refresh the current page after a successful write.

Views and indexes are not editable. The feature does not add delete operations, arbitrary write SQL, or schema modification.

## Interface

The data page toolbar contains `Add row` and `Edit row` actions. `Edit row` stays disabled until the user selects a row.

Both actions open a form dialog generated from the selected table's column metadata.

- Edit forms render primary-key fields as read-only values and allow changes only to non-primary-key fields.
- Add forms omit a single `INTEGER PRIMARY KEY` field so SQLite generates it. Composite and text primary-key fields are editable and required.
- Nullable columns include a `NULL` checkbox. Selecting it disables the value input and writes SQL `NULL`; leaving it clear permits an empty string.
- Non-nullable editable fields must contain a value. Validation failures remain in the dialog with an actionable message.
- SQLite constraint or write errors remain visible in the dialog and preserve every entered value.

## Connection And Write Design

The application opens databases with a normal read-write connection for table editing. It continues to restrict `SqlView` through the existing read-only query validator, so allowing the connection itself does not allow arbitrary write statements from the SQL editor.

Create a focused write service that owns parameterized row insertion and updates. It takes table metadata, values, and stable row identity; it quotes identifiers with the existing schema helper and passes all values as SQLite parameters.

The update statement includes only non-primary-key columns in `SET`. Its `WHERE` clause addresses the original primary-key values, preventing primary-key modifications. For tables without a declared primary key, the table query provides SQLite's hidden `rowid` as internal row identity and updates use that value. A `WITHOUT ROWID` table has a declared key and follows the primary-key path.

## Data Flow

1. Selecting a table loads its column metadata and a paginated data result.
2. The data view retains the source row values and, when needed, the internal `rowid` identity without exposing it as an editable field.
3. The user opens the add or edit dialog and submits validated values.
4. The database tab invokes the write service.
5. On success, the tab reloads the selected table's current page and closes the dialog.
6. On failure, the dialog stays open and shows the service error.

## Error Handling

- No table is selected: disable both row actions.
- No row is selected: disable `Edit row`.
- A required primary or non-nullable value is absent: block submission before writing.
- SQLite rejects a constraint, type, lock, or I/O operation: show the database error without discarding values.
- Unsupported objects such as views and indexes: do not expose row actions.

## Tests

Service tests cover:

- SQLite-generated values for single `INTEGER PRIMARY KEY` inserts.
- Required composite and text primary-key values.
- Explicit `NULL` versus empty-string persistence.
- Updates that omit primary-key fields from `SET`.
- Updates to tables without declared primary keys using `rowid`.

Presentation tests cover:

- Data-page action enablement based on table and row selection.
- Read-only primary-key fields in edit dialogs.
- Omitted auto-generated integer primary key in add dialogs.
- Validation and error presentation.
- Data refresh after a successful add or update.

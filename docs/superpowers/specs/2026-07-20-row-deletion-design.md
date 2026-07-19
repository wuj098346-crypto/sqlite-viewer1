# Row deletion design

## Goal

Allow a user to permanently delete one selected row from the currently opened SQLite table.

## Scope

- Add a delete action beside the existing add and edit row actions.
- Keep row actions disabled until a table is selected.
- Require an explicit confirmation before issuing a deletion.
- Delete rows by their primary-key values when a primary key exists; otherwise, use the displayed row's `rowid`.
- Refresh the current table page after a successful deletion.
- Surface database errors through the existing write-error handling path.
- Update the README to describe row deletion and clarify that SQL execution remains read-only.

## Non-goals

- Deleting tables, views, indexes, or database files.
- Deleting multiple rows at once.
- Changing the read-only restrictions on the SQL editor.
- Adding an undo mechanism.

## Design

`DataView` exposes a delete request for the selected row and keeps its delete control in the same enabled state as its existing row actions. `DatabaseTab` asks the user to confirm the permanent deletion. On confirmation, it derives the row locator using the same primary-key-then-`rowid` policy as editing and delegates to `RowWriteService`.

`RowWriteService.delete` builds a parameterized `DELETE` statement using quoted identifiers. It raises `DatabaseWriteError` when no primary key or `rowid` is available, and maps SQLite failures to that existing error type. After a successful write, `DatabaseTab` reloads the current page.

## Validation

- Service tests prove deletion by primary key and by `rowid` for a keyless table.
- Presentation tests prove a deletion refreshes the displayed data and that actions are unavailable before selecting a table.
- The full test suite remains green.

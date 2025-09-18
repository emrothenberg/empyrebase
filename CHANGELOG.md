## 2.3.3
### Fixed
- Absolute path issue in create_document

## 2.3.2
### Fixed
- Isolated update_document and delete_document now work
- Fixed run query

## 2.3.1
### Fixed
- Update document and batch_get_documents bug fixes

## 2.3.0
### Added
- Firestore path segments

### Fixed
- Firestore collection detection bugs
- Isolated firestore collection/document/get_document sub-instances

## 2.2.0
### Added
- doubleValue support

### Fixed
- Dependency issues

### Thanks
Thanks to @fahhem for adding doubleValue support

## 2.1.2
### Fixed
- Type hints
- Errors on document updates

## 2.1.1
### Fixed
- Removed deprecated dependencies

## 2.1.0
### Added
- Auth: Google account and OAuth login

## 2.0.0
### Added
- Firestore: Query builder
- Firestore: Protected private variables for safer usage

### Fixed
- Firestore: `.document()` and `.collection()` can now safely get multi-level refs

### Removed
- Firestore: `base_url` specification on initialization

## 1.2.1
### Fixed
- Firestore: Type issue in document request

## 1.2.0
### Added
- Firestore: Document existence check
- Firestore: Server timestamp support
- Firestore: `.collection()` and `.document()` methods for granular operations
- General: Outdated version warning

## 1.1.3
### Fixed
- RTDB: Improved reauth robustness
- Firestore: Boolean no longer treated as integer

## 1.1.2
### Fixed
- Firestore: Read from database on document creation

## 1.1.1
### Added
- RTDB: Max retries for auto refresh

## 1.1.0
### Added
- RTDB: Auto reauth

### Fixed
- Compatibility: Python 3.11 integration issues

## 1.0.3
### Added
- Firestore: Warning for unsupported types

### Fixed
- Firestore: Crash when fetching empty array

## 1.0.2
### Added
- Firestore: Support for arrays and null values

## 1.0.1
### Fixed
- General: Import errors

## 1.0.0
### Added
- Firestore: Full CRUD support

### Fixed
- General: Code structure improvements
- General: Dependency upgrades

### Changed
- Renamed `pyrebase` to `empyrebase`

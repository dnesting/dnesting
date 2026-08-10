# macOS Sandbox SBPL Reference

This reference was automatically generated from the SBPL profiles shipped in `/System/Library/Sandbox/Profiles`.
It describes patterns observed in `(allow ...)` and `(deny ...)` forms, not a complete grammar or authoritative compatibility contract.
Some entries may be helper functions rather than primitive language features, observed pairings may not be exclusive, and unobserved operations, filters, modifiers, or pairings may still exist.
It would be logical to infer that many filters actually apply more broadly than the operations they were observed with, but I did not attempt to do this unless filters were used with globs specifically.

This is not an authoritative resource and should not be relied upon.

- Generated from: macOS Tahoe 26.4.1 (build 25E253) on 2026-05-02
- Source directory: `/System/Library/Sandbox/Profiles`
<!--
- Profiles with extracted rules: 508
- Extracted `allow`/`deny` forms: 10610
- Operations: 144
- Filters: 109
- Modifiers: 11
-->

## Language Overview

SBPL is an S-expression language. Lists are function calls, atoms are symbols or literals, and comments begin with `;`. This reference focuses on unquoted `(allow ...)` and `(deny ...)` calls, but the profiles around those rules use Scheme-like helpers to build reusable predicates.

A minimal rule has an action followed by one or more operations and optional filter expressions:

```scheme
(allow file-read* (subpath "/Library/Preferences"))
(deny file-write* (with no-report))
```

Scheme numeric literals can include radix prefixes. For example, `#o0004` is an octal spelling of the integer `4`, which is convenient for Unix file mode bits:

```scheme
(allow file-read* (file-mode #o0004))
```

This corpus also uses `#"..."` for regex-like strings:

```scheme
(allow file-read* (regex #"^/Library/.*\.plist$"))
```

`let`, `let*`, and `letrec` bind local names. A bound name can hold a filter expression or a function that returns one, so calls to bound names are not treated as primitive filters:

```scheme
(let ((_home-subpath (lambda (suffix) (subpath (string-append _home suffix)))))
  (allow file-read* (_home-subpath "/Library/Application Support/AddressBook")))
```

`define` and `define-once` introduce profile-wide helpers. `lambda` introduces parameters. Tracking those bindings helps separate profile-local helpers from built-in-looking predicates.

```scheme
(define home-cache (subpath "/Users/example/Library/Caches"))

(define (home-subpath suffix)
  (subpath (string-append "/Users/example" suffix)))

(define home-regex
  (lambda (suffix)
    (regex (string-append "^/Users/example" suffix))))

(allow file-read*
  home-cache
  (home-subpath "/Library/Preferences")
  (home-regex "/Library/Logs/.*"))
```

`require-all`, `require-any`, and `require-not` appear to combine filter expressions: all, any, and negation. Their child expressions are still included in the filter data, but the combinator calls themselves are treated as structural language forms.

```scheme
(allow file-read*
  (require-all
    (subpath "/System")
    (require-not (file-mode 0))))
```

`with-filter` applies a filter expression to nested rule forms:

```scheme
(with-filter (require-entitlement "com.apple.security.smartcard")
  (allow mach-lookup (global-name "com.apple.ctkd.watcher-client")))
```

The extraction pass found 421 `with-filter` wrappers. Predicate heads only observed under `with-filter` in this corpus: `%entitlement-is-present`, `filesystem-name`, `process-is-plugin`, `process-path`, `process-path-regex`, `require-entitlement`, `uid`.

`with` attaches a modifier to a single rule. Modifier arguments follow the modifier name:

```scheme
(deny syscall-unix (with send-signal SIGKILL))
```

## Extraction Notes

The extraction pass looks for structural signals that suggest a parenthesized form is not a primitive filter.

- Bound local/profile names are excluded from the filter list.
- Top-level `define` and `define-once` names from imported profiles, and helper names defined elsewhere in the observed corpus, are treated as profile helper functions rather than primitive filters.
- Logical combinators are documented as language structure rather than filters.
- Forms that carry nested rule bodies are treated as higher-order helpers rather than filters.
- Zero-argument predicates remain in the filter reference when they appear directly as rule predicates and do not otherwise look structural in this corpus.

## Operations

### `appleevent-send`

- Filters:
  - `(appleevent-destination string)`; example: `name`

### `authorization-right-obtain`

- Filters:
  - `(right-name string...)`; example: `"system.burn"`
  - `(right-name-regex string)`; example: `"^system\\.volume\\.(external|optical|removable)\\.unmount$"`

### `darwin-notification-post`

- Filters:
  - `(notification-name string)`; example: `"com.apple.test.sandbox-disallow"`
- Modifiers:
  - `(with report)`

### `default`

- Modifiers:
  - `(with message string)`; example: `"media-extension-format-reader"`
  - `(with no-callout)`
  - `(with partial-symbolication)`
  - `(with report)`
  - `(with telemetry)`

---

### `device-camera`

- Modifiers:
  - `(with no-report)`

### `device-microphone`

- Modifiers:
  - `(with no-report)`

---

### `distributed-notification-post`


### `dynamic-code-generation`

- Modifiers:
  - `(with no-report)`
  - `(with report)`
  - `(with telemetry)`

---

### `file*`

- Filters:
  - `(literal string...)`; example: `"/dev/fsevents"`
  - `(mount-relative-literal string)`; example: `"/.TemporaryItems"`
  - `(mount-relative-regex string)`; example: `#"^/\.TemporaryItems/folders.[0-9]+(/|$)"`
  - `(regex string...)`; example: `"^/dev/tty[^\\.]"`
  - `(subpath string...)`; example: `"/var/root"`
  - `(vnode-type symbol...)`; example: `TTY`
- Modifiers:
  - `(with no-log)`

#### `file-clone`

- Filters:
  - `(extension string...)`; example: `"com.apple.app-sandbox.read-write"`
- Modifiers:
  - `(with report)`

#### `file-ioctl`

- Filters:
  - `(device-conforms-to string)`; example: `"IOBDMedia"`
  - `(path string)`; example: `"/dev/fsevents"`
  - `(prefix string...)`; example: `"/dev/disk"`

#### `file-issue-extension*`

- Filters:
  - `(extension-class string...)`; example: `"com.apple.app-sandbox.read-write"`

##### `file-issue-extension`

- Filters:
  - `(extension string...)`; example: `"com.apple.app-sandbox.read" "com.apple.app-sandbox.read-write" "com.apple.cfprefsd.read" "com.apple.cfprefsd.read-wr...`
  - `(mount-relative-subpath string)`; example: `"/.AppInstallationStaging/com.apple.appinstall.temp"`
- Modifiers:
  - `(with no-report)`
  - `(with report)`

#### `file-link`

- Modifiers:
  - `(with report)`

#### `file-map-executable`

- Filters:
  - `(extension string...)`; example: `"com.apple.sandbox.oopjit"`
  - `(path string)`; example: `"/System/Library/Components/AudioCodecs.component/Contents/MacOS/AudioCodecs"`
  - `(prefix string...)`; example: `"/System/Library/Extensions/AGXMetal"`
- Modifiers:
  - `(with report)`
  - `(with telemetry)`

#### `file-mknod`


#### `file-mount`


#### `file-read*`

- Filters:
  - `(device-conforms-to string)`; example: `"IOBDMedia"`
  - `(extension string...)`; example: `"com.apple.app-sandbox.read"`
  - `(file-attribute symbol)`; example: `apfs-preboot-volume`
  - `(file-mode integer...)`; example: `#o0004`
  - `(mount-relative-subpath string)`; example: `"/var/db/ExtensibleSSO/Configuration"`
  - `(path string)`; example: `"/Library/Application Support/CrashReporter/DiagnosticMessagesHistory.plist"`
  - `(path-ancestors string)`; example: `"/Library/Audio/Plug-Ins/Components"`
  - `(prefix string...)`; example: `"/Library/Preferences/com.apple.security."`
- Modifiers:
  - `(with errno symbol)`; example: `EACCES`
  - `(with no-report)`
  - `(with report)`
  - `(with telemetry)`

##### `file-read-data`

- Filters:
  - `(extension-path-ancestor)`

##### `file-read-metadata`

- Filters:
  - `(extension-path-ancestor)`

##### `file-read-xattr`

- Filters:
  - `(extension-path-ancestor)`
  - `(xattr string...)`; example: `"com.apple.file-provider-domain-id"`
  - `(xattr-prefix string)`; example: `"com.apple.security.private."`
  - `(xattr-regex string)`; example: `#"^com\.apple\.security\.private\."`

#### `file-revoke`


#### `file-search`


#### `file-test-existence`

- Filters:
  - `(path-ancestors string)`; example: `"/System/Volumes/Data/private"`
- Modifiers:
  - `(with errno symbol)`; example: `EACCES`

#### `file-unlink`


#### `file-unmount`


#### `file-write*`

- Filters:
  - `(extension string...)`; example: `"com.apple.app-sandbox.read-write"`
  - `(file-attribute symbol)`; example: `apfs-preboot-volume`
  - `(file-mode integer...)`; example: `0`
  - `(mount-relative-subpath string)`; example: `"/var/db/ExtensibleSSO/Configuration"`
  - `(path string)`; example: `"/Library/Application Support/CrashReporter/DiagnosticMessagesHistory.plist"`
  - `(prefix string...)`; example: `"/cores/"`
- Modifiers:
  - `(with message string)`; example: `"124470244"`
  - `(with no-report)`
  - `(with report)`
  - `(with telemetry)`

##### `file-write-acl`


##### `file-write-create`


##### `file-write-data`


##### `file-write-flags`


##### `file-write-mode`


##### `file-write-owner`


##### `file-write-setugid`


##### `file-write-unlink`


##### `file-write-xattr`

- Filters:
  - `(xattr string...)`; example: `"com.apple.quarantine"`
  - `(xattr-prefix string)`; example: `"com.apple.security.private."`
  - `(xattr-regex string)`; example: `#"^com\.apple\.security\.private\."`

---

### `generic-issue-extension`

- Filters:
  - `(extension-class string...)`; example: `"com.apple.webkit.mach-bootstrap"`
  - `(extension-class-prefix string)`; example: `"com.apple.shortcuts.access."`
  - `(extension-class-regex string)`; example: `#"^com\.apple\.tcc\."`

### `hid-control`


---

### `iokit*`


#### `iokit-async-external-method`

- Filters:
  - `(iokit-method-number integer...)`; example: `0`

#### `iokit-external-method`

- Filters:
  - `(iokit-method-number integer...)`; example: `1 2 5`

#### `iokit-get-properties`

- Filters:
  - `(iokit-property string...)`; example: `"MetalPluginClassName" "MetalPluginName" "AAPL,slot-name" "IOAVDHEVCDecodeCapabilities" "IOGVAHEVCDecode" "SafeEjectR...`
  - `(iokit-registry-entry-class string...)`; example: `"CoreStorageLogical"`
- Modifiers:
  - `(with message string)`; example: `"115993961-iokit-get-properties"`
  - `(with no-report)`
  - `(with report)`
  - `(with telemetry)`

#### `iokit-issue-extension`

- Filters:
  - `(extension-class string...)`; example: `"com.apple.webkit.extension.iokit"`

#### `iokit-open*`

- Filters:
  - `(iokit-user-client-class string...)`; example: `"AGXDeviceUserClient"`

##### `iokit-open`

- Filters:
  - `(extension string...)`; example: `"com.apple.app-sandbox.iokit-client"`
  - `(extension-class string...)`; example: `"com.apple.webkit.extension.iokit"`
  - `(iokit-connection string)`; example: `"IOGPU"`
  - `(iokit-registry-entry-class string...)`; example: `"AppleDiagNVRAM"`
  - `(iokit-registry-entry-class-prefix string...)`; example: `"AppleGraphicsControl"`
  - `(iokit-user-client-class-regex string)`; example: `#"AccelDevice$"`
- Modifiers:
  - `(with telemetry)`

##### `iokit-open-service`

- Filters:
  - `(iokit-connection string)`; example: `"AppleGraphicsDeviceControl"`
  - `(iokit-registry-entry-class string...)`; example: `"IntelAccelerator" "IOSurfaceRoot"`
  - `(iokit-registry-entry-class-prefix string...)`; example: `"AGXAcceleratorG"`
- Modifiers:
  - `(with message string)`; example: `"88289132-iokit-open-service"`
  - `(with telemetry)`

##### `iokit-open-user-client`

- Filters:
  - `(iokit-connection string)`; example: `"AppleHDAEngineInput"`
  - `(iokit-registry-entry-class string...)`; example: `"AppleNVMeEANUC" "IOHIDParamUserClient" "IOSurfaceRootUserClient"`
  - `(iokit-registry-entry-class-prefix string...)`; example: `"AGXAcceleratorG"`
  - `(iokit-user-client-class-regex string)`; example: `#"AccelDevice$"`
- Modifiers:
  - `(with report)`

#### `iokit-set-properties`

- Filters:
  - `(extension string...)`; example: `"com.apple.core-audio.iokit-user-client-class"`
  - `(iokit-connection string)`; example: `"IODisplay"`
  - `(iokit-property string...)`; example: `"NVMe Controller Info"`
  - `(iokit-user-client-class string...)`; example: `name`

---

### `ipc-posix*`

- Filters:
  - `(ipc-posix-name string...)`; example: `"com.apple.securityd"`
  - `(ipc-posix-name-prefix string)`; example: `(string-append suite "/")`
- Modifiers:
  - `(with report)`

#### `ipc-posix-sem*`


##### `ipc-posix-sem`

- Filters:
  - `(semaphore-owner symbol)`; example: `self`

##### `ipc-posix-sem-create`


##### `ipc-posix-sem-open`


##### `ipc-posix-sem-post`


##### `ipc-posix-sem-unlink`


##### `ipc-posix-sem-wait`


#### `ipc-posix-shm*`

- Filters:
  - `(ipc-posix-name-regex string)`; example: `#"^/tmp/com\.apple\.csseed\.[0-9]+$"`

##### `ipc-posix-shm`

- Modifiers:
  - `(with no-report)`

##### `ipc-posix-shm-read*`


###### `ipc-posix-shm-read-data`

- Filters:
  - `(global-name string...)`; example: `"com.apple.AppleDatabaseChanged"`

###### `ipc-posix-shm-read-metadata`


##### `ipc-posix-shm-write*`


###### `ipc-posix-shm-write-create`

- Filters:
  - `(global-name string...)`; example: `"com.apple.AppleDatabaseChanged"`

###### `ipc-posix-shm-write-data`

- Filters:
  - `(global-name string...)`; example: `"com.apple.AppleDatabaseChanged"`

###### `ipc-posix-shm-write-unlink`


---

### `job-creation`


### `lsopen`


---

### `mach-bootstrap`


### `mach-cross-domain-lookup`


### `mach-issue-extension`

- Filters:
  - `(extension-class string...)`; example: `"com.apple.webkit.extension.mach"`
  - `(global-name string...)`; example: `"com.apple.cmio.registerassistantservice"`

### `mach-lookup`

- Filters:
  - `(extension string...)`; example: `"com.apple.app-sandbox.mach"`
  - `(global-name string...)`; example: `"com.apple.cache_delete" "com.apple.cache_delete.public" "com.apple.diagnosticpipeline.service" "com.apple.diagnostic...`
  - `(global-name-prefix string...)`; example: `(string-append suite ".")`
  - `(global-name-regex string)`; example: `"_OpenStep$"`
  - `(local-name string)`; example: `"com.apple.CFPasteboardClient"`
  - `(local-name-prefix string)`; example: `"com.apple.axserver"`
  - `(subpath string...)`; example: `"/Library/Video/Plug-Ins"`
  - `(xpc-service-name string...)`; example: `"com.apple.audio.AudioConverterService"`
  - `(xpc-service-name-prefix string)`; example: `""`
  - `(xpc-service-name-regex string)`; example: `#".*"`
- Modifiers:
  - `(with message string)`; example: `"Unexpected WebKit Usage"`
  - `(with no-report)`
  - `(with report)`
  - `(with send-signal symbol)`; example: `SIGKILL`
  - `(with telemetry)`

### `mach-per-user-lookup`


### `mach-priv-host-port`

- Filters:
  - `(subpath string...)`; example: `temp-directory`

### `mach-register`

- Filters:
  - `(global-name string...)`; example: `"com.apple.screencapture.interactive"`
  - `(global-name-prefix string...)`; example: `(string-append suite ".")`
  - `(local-name string)`; example: `name`
  - `(local-name-prefix string)`; example: `""`
- Modifiers:
  - `(with report)`
  - `(with telemetry)`

### `mach-task-name`

- Filters:
  - `(target symbol)`; example: `others`

### `mach-task-read`

- Filters:
  - `(target symbol)`; example: `others`

### `mach-task-special-port*`


---

### `managed-preference-read`

- Filters:
  - `(preference-domain string...)`; example: `"com.apple.SystemConfiguration"`
  - `(preference-domain-prefix string)`; example: `"com.apple.wifi.analytics"`

### `necp-client-open`


---

### `network*`

- Filters:
  - `(extension string...)`; example: `"com.apple.OpenGLProfiler"`
  - `(literal string...)`; example: `"/private/var/run/racoon.sock"`
  - `(local symbol string...)`; example: `udp`
  - `(remote symbol string...)`; example: `udp`

#### `network-bind`


#### `network-inbound`

- Filters:
  - `(path string)`; example: `"/private/var/run/vpncontrol.sock"`
  - `(socket-domain symbol)`; example: `AF_SYSTEM`
  - `(subpath string...)`; example: `(param "application_darwin_temp_dir")`

#### `network-outbound`

- Filters:
  - `(control-name string)`; example: `"com.apple.uart.stockholm"`
  - `(control-name-prefix string)`; example: `"com.apple.spmi.nfc"`
  - `(path string)`; example: `"/private/var/run/mDNSResponder"`
  - `(socket-domain symbol)`; example: `AF_SYSTEM`
  - `(socket-protocol integer)`; example: `2`
  - `(subpath string...)`; example: `"/private/var/run/mDNSResponder"`
  - `(vnode-type symbol...)`; example: `SOCKET`

---

### `nvram*`

- Filters:
  - `(nvram-variable string...)`; example: `"boot_errors"`
- Modifiers:
  - `(with report)`
  - `(with telemetry)`

#### `nvram-delete`

- Filters:
  - `(nvram-variable-prefix string)`; example: `"ota-"`

#### `nvram-get`

- Filters:
  - `(nvram-variable-prefix string)`; example: `"ota-"`

#### `nvram-set`

- Filters:
  - `(iokit-property string...)`; example: `"IONVRAM-FORCESYNCNOW-PROPERTY" "policy-nonce-digests"`

---

### `process-codesigning`

- Filters:
  - `(codesigning-operation symbol symbol)`; example: `CS_OPS_DER_ENTITLEMENTS_BLOB CS_OPS_STATUS`

### `process-codesigning-blob-get`


### `process-codesigning-cdhash-get`


### `process-codesigning-entitlements-blob-get`


### `process-codesigning-identity-get`


### `process-codesigning-status*`

- Filters:
  - `(target symbol)`; example: `self`

#### `process-codesigning-status-get`


#### `process-codesigning-status-set`


### `process-codesigning-teamid-get`


### `process-codesigning-text-offset-get`


### `process-exec*`

- Filters:
  - `(literal string...)`; example: `"/System/Library/CoreServices/loginwindow.app/Contents/MacOS/loginwindow"`
  - `(path string)`; example: `"/System/Library/Frameworks/AddressBook.framework/Versions/A/Helpers/AddressBookSync.app/Contents/MacOS/AddressBookSync"`
  - `(subpath string...)`; example: `"/Library/Frameworks"`
- Modifiers:
  - `(with no-sandbox)`
  - `(with telemetry-backtrace)`

#### `process-exec`

- Modifiers:
  - `(with report)`

#### `process-exec-interpreter`


### `process-fork`

- Modifiers:
  - `(with no-report)`

### `process-info*`

- Filters:
  - `(target symbol)`; example: `self`
- Modifiers:
  - `(with report)`
  - `(with telemetry)`

#### `process-info-codesignature`

- Filters:
  - `(target-signing-identifier string)`; example: `"com.apple.classroom"`
- Modifiers:
  - `(with no-report)`

#### `process-info-dirtycontrol`


#### `process-info-ledger`


#### `process-info-listpids`


#### `process-info-pidfdinfo`


#### `process-info-pidfileportinfo`


#### `process-info-pidinfo`


#### `process-info-rusage`


#### `process-info-setcontrol`


---

### `pseudo-tty`


### `qtn-user`

- Filters:
  - `(extension string...)`; example: `"com.apple.app-sandbox.read-write"`

### `signal`

- Filters:
  - `(target symbol)`; example: `self`

---

### `socket-ioctl`

- Filters:
  - `(ioctl-command symbol...)`; example: `CTLIOCGINFO SIOCGIFFLAGS`

### `socket-option*`


#### `socket-option-get`

- Filters:
  - `(socket-option-name symbol|integer symbol symbol...)`; example: `262 SO_ERROR SO_NREAD SO_REUSEPORT`

#### `socket-option-set`

- Filters:
  - `(socket-option-name symbol|integer symbol symbol...)`; example: `SO_DEBUG SO_KEEPALIVE SO_NECP_ATTRIBUTES SO_NECP_CLIENTUUID SO_NOADDRERR SO_NOSIGPIPE SO_RCVBUF SO_RCVTIMEO SO_SNDTIMEO`

---

### `syscall*`


#### `syscall-mach`

- Filters:
  - `(machtrap-number symbol...)`; example: `MSC__kernelrpc_mach_port_allocate_trap MSC__kernelrpc_mach_port_construct_trap MSC__kernelrpc_mach_port_deallocate_tr...`
  - `(syscall-number symbol...)`; example: `MSC_mach_generate_activity_id`
  - `(system-attribute symbol)`; example: `apple-internal`
- Modifiers:
  - `(with message string)`; example: `"syscall-mach-denied"`
  - `(with send-signal symbol)`; example: `SIGKILL`
  - `(with telemetry)`

#### `syscall-mig`

- Filters:
  - `(kernel-mig-routine symbol...)`; example: `_mach_make_memory_entry clock_get_time host_get_io_master host_info io_connect_method io_connect_method_var_output io...`
- Modifiers:
  - `(with message string)`; example: `"88289132-syscall-mig"`
  - `(with telemetry)`

#### `syscall-unix`

- Filters:
  - `(syscall-group-bsdthread)`
  - `(syscall-group-chflags)`
  - `(syscall-group-close)`
  - `(syscall-group-fcntl)`
  - `(syscall-group-getfsstat)`
  - `(syscall-group-kevent)`
  - `(syscall-group-kqueue)`
  - `(syscall-group-mach-eventlink)`
  - `(syscall-group-mkdir)`
  - `(syscall-group-necp-client)`
  - `(syscall-group-network-channel)`
  - `(syscall-group-open)`
  - `(syscall-group-open-dprotected)`
  - `(syscall-group-pthread)`
  - `(syscall-group-pthread-cv)`
  - `(syscall-group-pthread-locks)`
  - `(syscall-group-read)`
  - `(syscall-group-recv)`
  - `(syscall-group-rlimit)`
  - `(syscall-group-select)`
  - `(syscall-group-send)`
  - `(syscall-group-signal)`
  - `(syscall-group-sockopt)`
  - `(syscall-group-stat)`
  - `(syscall-group-statfs)`
  - `(syscall-group-ulock)`
  - `(syscall-group-write)`
  - `(syscall-number symbol...)`; example: `SYS___disable_threadsignal SYS___mac_syscall SYS___semwait_signal_nocancel SYS_abort_with_payload SYS_access SYS_conn...`
- Modifiers:
  - `(with message string)`; example: `"73669976"`
  - `(with send-signal symbol)`; example: `SIGKILL`
  - `(with telemetry)`

---

### `sysctl*`

- Filters:
  - `(sysctl-name string...)`; example: `"kern.ipc.io_policy.throttled"`
  - `(sysctl-name-prefix string)`; example: `"net."`

#### `sysctl-read`

- Modifiers:
  - `(with message string)`; example: `"115993961-sysctl-read"`
  - `(with report)`
  - `(with telemetry)`

#### `sysctl-write`


---

### `system-audit`


### `system-automount`

- Filters:
  - `(process-attribute symbol)`; example: `is-platform-binary`

### `system-fcntl`

- Filters:
  - `(fcntl-command symbol...)`; example: `F_ADDFILESIGS_RETURN F_CHECK_LV F_GETFD F_GETPATH F_GETPROTECTIONCLASS F_GETSIGSINFO F_NOCACHE F_SETFD F_SPECULATIVE_...`
- Modifiers:
  - `(with report)`

### `system-fsctl`

- Filters:
  - `(fsctl-command symbol|_IO(...)|integer symbol...)`; example: `HFSIOC_SET_HOTFILE_STATE`

### `system-info`

- Filters:
  - `(info-type string)`; example: `"net.link.addr"`

### `system-kext*`


#### `system-kext-load`

- Filters:
  - `(kext-bundle-id string)`; example: `"com.apple.iokit.IONetworkingFamily"`

#### `system-kext-query`


#### `system-kext-unload`


### `system-mac-syscall`

- Filters:
  - `(mac-policy-name string...)`; example: `"AMFI" "Quarantine" "Sandbox"`
  - `(mac-syscall-number integer...)`; example: `95`
- Modifiers:
  - `(with message string)`; example: `"88289132-system-mac-syscall"`
  - `(with telemetry)`

### `system-necp-client-action`

- Filters:
  - `(necp-client-action symbol...)`; example: `NECP_CLIENT_ACTION_ADD NECP_CLIENT_ACTION_ADD_FLOW NECP_CLIENT_ACTION_COPY_AGENT NECP_CLIENT_ACTION_COPY_INTERFACE NE...`

### `system-package-check`


### `system-privilege`

- Filters:
  - `(privilege-id symbol)`; example: `PRIV_GLOBAL_PROC_INFO`
- Modifiers:
  - `(with no-report)`

### `system-sched`

- Filters:
  - `(target symbol)`; example: `self`

### `system-socket`

- Filters:
  - `(socket-domain symbol)`; example: `AF_SYSTEM`
  - `(socket-protocol integer)`; example: `2`

### `system-suspend-resume`


---

### `user-preference*`

- Filters:
  - `(preference-domain string...)`; example: `"com.apple.AppSSO" "com.apple.CFNetwork" "com.apple.PlatformSSO" "com.apple.AppSSODaemon" "com.apple.loginwindow" "co...`
  - `(preference-domain-prefix string)`; example: `"com.apple.UARPHIDUpdater"`
  - `(preference-domain-regex string)`; example: `#"^com\.apple\.coreservices\.useractivityd"`
- Modifiers:
  - `(with no-report)`

#### `user-preference-read`

- Filters:
  - `(global-name string...)`; example: `"com.apple.parsecd"`
  - `(literal string...)`; example: `"swtransparencyd"`
  - `(process-attribute symbol)`; example: `is-apple-signed-executable`
  - `(regex string...)`; example: `#"com\.apple\.private\.health\..*"`
- Modifiers:
  - `(with report)`

#### `user-preference-write`

- Filters:
  - `(regex string...)`; example: `#"com\.apple\.private\.health\..*"`
- Modifiers:
  - `(with message string)`; example: `"124470244"`
  - `(with telemetry)`

---

## Filters

Operations listed here are the highest observed operation levels after glob inheritance pruning.

| Filter | Highest observed operations | All Symbols | Example Arguments |
| --- | --- | --- | --- |
| `(%entitlement-is-present string)` | `with-filter` | - | `"com.apple.private.applemediaservices"` |
| `(appleevent-destination string)` | `appleevent-send` (5) | - | `name`, `(car value)` |
| `(codesigning-operation symbol symbol)` | `process-codesigning` (1) | `CS_OPS_DER_ENTITLEMENTS_BLOB`, `CS_OPS_STATUS` | `CS_OPS_DER_ENTITLEMENTS_BLOB CS_OPS_STATUS` |
| `(control-name string)` | `network-outbound` (15) | - | `"com.apple.uart.stockholm"`, `"com.apple.fileutil.kext.stateful.ctl"` |
| `(control-name-prefix string)` | `network-outbound` (2) | - | `"com.apple.spmi.nfc"` |
| `(device-conforms-to string)` | `file-ioctl` (1), `file-read*` (1) | - | `"IOBDMedia"`, `"IODVDMedia"` |
| `(extension string...)` | `file-clone` (1), `file-issue-extension` (22), `file-map-executable` (1), `file-read*` (215), `file-write*` (143), `iokit-open` (2), `iokit-set-properties` (2), `mach-lookup` (5), `network*` (2), `qtn-user` (2) | - | `"com.apple.app-sandbox.read"`, `"com.apple.app-sandbox.read-write"` |
| `(extension-class string...)` | `file-issue-extension*` (1), `generic-issue-extension` (9), `iokit-issue-extension` (3), `iokit-open` (1), `mach-issue-extension` (11) | - | `"com.apple.app-sandbox.read" "com.apple.app-sandbox.read-write"`, `"com.apple.cfprefsd.read"` |
| `(extension-class-prefix string)` | `generic-issue-extension` (2) | - | `"com.apple.shortcuts.access."`, `"com.apple.virtualization.extension."` |
| `(extension-class-regex string)` | `generic-issue-extension` (1) | - | `#"^com\.apple\.tcc\."` |
| `(extension-path-ancestor)` | `file-read-data` (1), `file-read-metadata` (2), `file-read-xattr` (1) | - | - |
| `(fcntl-command symbol...)` | `system-fcntl` (16) | `F_ADDFILESIGS_RETURN`, `F_CHECK_LV`, `F_DUPFD_CLOEXEC`, `F_GETFD`, `F_GETPATH`, `F_GETPROTECTIONCLASS`, `F_GETSIGSINFO`, `F_NOCACHE`, `F_PREALLOCATE`, `F_SETFD`, `F_SETLKW`, `F_SETPROTECTIONCLASS`, `F_SINGLE_WRITER`, `F_SPECULATIVE_READ` | `F_ADDFILESIGS_RETURN F_CHECK_LV F_GETFD F_GETPATH F_GETPROTECTIONCLASS F_GETSIGSINFO F_NOCACHE F_SETFD F_SPECULATIVE_...`, `F_ADDFILESIGS_RETURN F_CHECK_LV F_GETFD F_GETPATH F_GETPROTECTIONCLASS F_GETSIGSINFO F_NOCACHE F_SETFD F_SPECULATIVE_...` |
| `(file-attribute symbol)` | `file-read*` (2), `file-write*` (2) | `apfs-preboot-volume`, `fileprovider-owned` | `apfs-preboot-volume`, `fileprovider-owned` |
| `(file-mode integer...)` | `file-read*` (6), `file-write*` (5) | - | `#o0004`, `0` |
| `(filesystem-name string)` | `with-filter` | - | `"devfs"` |
| `(fsctl-command symbol\|_IO(...)\|integer symbol...)` | `system-fsctl` (57) | `APFSIOC_DOC_ID_TO_FILE_ID`, `APFSIOC_GET_CLONE_INFO`, `HFSIOC_SET_HOTFILE_STATE`, `HFSIOC_TRANSFER_DOCUMENT_ID` | `HFSIOC_SET_HOTFILE_STATE`, `APFSIOC_DOC_ID_TO_FILE_ID` |
| `(global-name string...)` | `ipc-posix-shm-read-data` (3), `ipc-posix-shm-write-create` (3), `ipc-posix-shm-write-data` (3), `mach-issue-extension` (3), `mach-lookup` (921), `mach-register` (54), `user-preference-read` (2) | - | `"com.apple.cache_delete" "com.apple.cache_delete.public" "com.apple.diagnosticpipeline.service" "com.apple.diagnostic...`, `"com.apple.AppSSO.service-xpc"` |
| `(global-name-prefix string...)` | `mach-lookup` (12), `mach-register` (7) | - | `(string-append suite ".")`, `"com.apple.aps."` |
| `(global-name-regex string)` | `mach-lookup` (12) | - | `"_OpenStep$"`, `#"^com\.apple\.distributed_notifications"` |
| `(info-type string)` | `system-info` (10) | - | `"net.link.addr"` |
| `(ioctl-command symbol...)` | `socket-ioctl` (5) | `CTLIOCGINFO`, `SIOCGIFCLAT46ADDR`, `SIOCGIFFLAGS`, `SIOCGIFMEDIA` | `CTLIOCGINFO SIOCGIFFLAGS`, `CTLIOCGINFO` |
| `(iokit-connection string)` | `iokit-open` (1), `iokit-open-service` (1), `iokit-open-user-client` (4), `iokit-set-properties` (1) | - | `"AppleHDAEngineInput"`, `"AppleHDAEngineOutput"` |
| `(iokit-method-number integer...)` | `iokit-async-external-method` (10), `iokit-external-method` (37) | - | `0`, `1 2 5` |
| `(iokit-property string...)` | `iokit-get-properties` (187), `iokit-set-properties` (50), `nvram-set` (1) | - | `"NVMe Controller Info"`, `"MetalPluginClassName" "MetalPluginName" "AAPL,slot-name" "IOAVDHEVCDecodeCapabilities" "IOGVAHEVCDecode" "SafeEjectR...` |
| `(iokit-registry-entry-class string...)` | `iokit-get-properties` (5), `iokit-open` (20), `iokit-open-service` (17), `iokit-open-user-client` (1) | - | `"IntelAccelerator" "IOSurfaceRoot"`, `"IOPMrootDomain"` |
| `(iokit-registry-entry-class-prefix string...)` | `iokit-open` (2), `iokit-open-service` (7), `iokit-open-user-client` (1) | - | `"AGXAcceleratorG"`, `"AppleGraphicsControl"` |
| `(iokit-user-client-class string...)` | `iokit-open*` (4), `iokit-set-properties` (9) | - | `"AppleNVMeUpdateUC" "AppleNVMeEANUC" "AppleAPFSUserClient" "AppleNVMeSMARTUserClient" "AppleNVMePassThroughUC" "RootD...`, `"IOHIDResourceDeviceUserClient"` |
| `(iokit-user-client-class-regex string)` | `iokit-open` (8), `iokit-open-user-client` (2) | - | `#"AccelDevice$"`, `#"SharedUserClient$"` |
| `(ipc-posix-name string...)` | `ipc-posix*` (1) | - | `"com.apple.AppleDatabaseChanged"`, `"com.apple.ColorSync.Gen.lock"` |
| `(ipc-posix-name-prefix string)` | `ipc-posix*` (3) | - | `(string-append suite "/")`, `"CFPBS:"` |
| `(ipc-posix-name-regex string)` | `ipc-posix-shm*` (1) | - | `"^gdt-[A-Za-z0-9]+-(c\|s)$"`, `"^Apple MIDI (in\|out) [0-9]+$"` |
| `(kernel-mig-routine symbol...)` | `syscall-mig` (18) | `_mach_make_memory_entry`, `clock_get_time`, `host_get_io_master`, `host_info`, `io_connect_add_client`, `io_connect_async_method`, `io_connect_method`, `io_connect_method_var_output`, `io_iterator_is_valid`, `io_iterator_next`, `io_object_conforms_to`, `io_registry_entry_create_iterator`, `io_registry_entry_from_path`, `io_registry_entry_get_child_iterator`, `io_registry_entry_get_name_in_plane`, `io_registry_entry_get_parent_iterator`, `io_registry_entry_get_property_bin_buf`, `io_registry_entry_get_property_bytes`, `io_registry_entry_get_registry_entry_id`, `io_registry_get_root_entry`, `io_server_version`, `io_service_add_interest_notification_64`, `io_service_add_notification_bin_64`, `io_service_get_matching_service_bin`, `io_service_get_matching_services_bin`, `io_service_open_extended`, `mach_exception_raise`, `mach_port_deallocate`, `mach_port_get_context_from_user`, `mach_port_get_refs`, `mach_port_is_connection_for_service`, `mach_port_set_attributes`, `mach_vm_copy`, `mach_vm_map_external`, `mach_vm_remap_external`, `semaphore_create`, `semaphore_destroy`, `task_get_special_port_from_user`, `task_info_from_user`, `task_restartable_ranges_synchronize`, `task_threads_from_user`, `thread_info`, `thread_policy_set`, `thread_resume`, `thread_suspend`, `thread_terminate` | `_mach_make_memory_entry clock_get_time host_get_io_master host_info io_connect_method io_connect_method_var_output io...`, `mach_port_deallocate mach_vm_remap_external task_threads_from_user thread_resume thread_suspend thread_terminate` |
| `(kext-bundle-id string)` | `system-kext-load` (2) | - | `"com.apple.iokit.IONetworkingFamily"`, `"com.apple.iokit.IOTimeSyncFamily"` |
| `(literal string...)` | `file*` (8), `network*` (1), `process-exec*` (10), `user-preference-read` (3) | - | `"/usr/libexec"`, `"/usr/libexec/ASPCarryLog"` |
| `(local symbol string...)` | `network*` (4) | `ip`, `tcp`, `udp` | `ip`, `udp` |
| `(local-name string)` | `mach-lookup` (17), `mach-register` (2) | - | `"com.apple.CFPasteboardClient"`, `"com.apple.coredrag"` |
| `(local-name-prefix string)` | `mach-lookup` (2), `mach-register` (2) | - | `""`, `"com.apple.axserver"` |
| `(mac-policy-name string...)` | `system-mac-syscall` (8) | - | `"AMFI" "Quarantine" "Sandbox"`, `"Quarantine" "Sandbox"` |
| `(mac-syscall-number integer...)` | `system-mac-syscall` (20) | - | `95`, `180` |
| `(machtrap-number symbol...)` | `syscall-mach` (19) | `MSC__kernelrpc_mach_port_allocate_trap`, `MSC__kernelrpc_mach_port_construct_trap`, `MSC__kernelrpc_mach_port_deallocate_trap`, `MSC__kernelrpc_mach_port_destruct_trap`, `MSC__kernelrpc_mach_port_get_attributes_trap`, `MSC__kernelrpc_mach_port_guard_trap`, `MSC__kernelrpc_mach_port_insert_member_trap`, `MSC__kernelrpc_mach_port_insert_right_trap`, `MSC__kernelrpc_mach_port_mod_refs_trap`, `MSC__kernelrpc_mach_port_request_notification_trap`, `MSC__kernelrpc_mach_port_type_trap`, `MSC__kernelrpc_mach_vm_allocate_trap`, `MSC__kernelrpc_mach_vm_deallocate_trap`, `MSC__kernelrpc_mach_vm_map_trap`, `MSC__kernelrpc_mach_vm_protect_trap`, `MSC__kernelrpc_mach_vm_purgable_control_trap`, `MSC_host_create_mach_voucher_trap`, `MSC_host_self_trap`, `MSC_iokit_user_client_trap`, `MSC_mach_generate_activity_id`, `MSC_mach_msg2_trap`, `MSC_mach_msg_overwrite_trap`, `MSC_mach_msg_trap`, `MSC_mach_reply_port`, `MSC_mach_timebase_info_trap`, `MSC_mach_voucher_extract_attr_recipe_trap`, `MSC_mk_timer_arm`, `MSC_mk_timer_create`, `MSC_mk_timer_destroy`, `MSC_pid_for_task`, `MSC_semaphore_signal_trap`, `MSC_semaphore_timedwait_trap`, `MSC_semaphore_wait_trap`, `MSC_syscall_thread_switch`, `MSC_task_dyld_process_info_notify_get`, `MSC_task_self_trap`, `MSC_thread_get_special_reply_port`, `MSC_thread_self_trap` | `MSC__kernelrpc_mach_port_allocate_trap MSC__kernelrpc_mach_port_construct_trap MSC__kernelrpc_mach_port_deallocate_tr...`, `MSC_task_dyld_process_info_notify_get` |
| `(mount-relative-literal string)` | `file*` (1) | - | `"/.TemporaryItems"` |
| `(mount-relative-regex string)` | `file*` (1) | - | `#"^/[^/]+/cryptex1/"`, `#"^/[^/]+/downlevel($\|/)"` |
| `(mount-relative-subpath string)` | `file-issue-extension` (1), `file-read*` (11), `file-write*` (10) | - | `"/var/db/ExtensibleSSO/Configuration"`, `"/private/var/db/ExtensibleSSO/Configuration"` |
| `(necp-client-action symbol...)` | `system-necp-client-action` (4) | `NECP_CLIENT_ACTION_ADD`, `NECP_CLIENT_ACTION_ADD_FLOW`, `NECP_CLIENT_ACTION_COPY_AGENT`, `NECP_CLIENT_ACTION_COPY_INTERFACE`, `NECP_CLIENT_ACTION_COPY_RESULT`, `NECP_CLIENT_ACTION_COPY_ROUTE_STATISTICS`, `NECP_CLIENT_ACTION_COPY_UPDATED_RESULT`, `NECP_CLIENT_ACTION_MAP_SYSCTLS`, `NECP_CLIENT_ACTION_REMOVE`, `NECP_CLIENT_ACTION_REMOVE_FLOW` | `NECP_CLIENT_ACTION_ADD NECP_CLIENT_ACTION_ADD_FLOW NECP_CLIENT_ACTION_COPY_AGENT NECP_CLIENT_ACTION_COPY_INTERFACE NE...`, `NECP_CLIENT_ACTION_ADD NECP_CLIENT_ACTION_ADD_FLOW NECP_CLIENT_ACTION_COPY_AGENT NECP_CLIENT_ACTION_COPY_INTERFACE NE...` |
| `(notification-name string)` | `darwin-notification-post` (4) | - | `"com.apple.test.sandbox-disallow"`, `"com.apple.test.sandbox-allow"` |
| `(nvram-variable string...)` | `nvram*` (4) | - | `"rdma-enable"`, `"4D1EDE05-38C7-4a6a-9CC6-4BCCA8B38C14:HW_ICT"` |
| `(nvram-variable-prefix string)` | `nvram-delete` (1), `nvram-get` (1) | - | `"ota-"`, `"OTA-"` |
| `(path string)` | `file-ioctl` (1), `file-map-executable` (6), `file-read*` (22), `file-write*` (10), `network-inbound` (1), `network-outbound` (7), `process-exec*` (3) | - | `"/Library/Application Support/CrashReporter/DiagnosticMessagesHistory.plist"`, `"/private/var/root/Library/Preferences/com.apple.ASPCarryLog.plist"` |
| `(path-ancestors string)` | `file-read*` (4), `file-test-existence` (1) | - | `(param "DARWIN_USER_CACHE_DIR")`, `"/Library/Keychains/System.keychain"` |
| `(preference-domain string...)` | `managed-preference-read` (16), `user-preference*` (43) | - | `"com.apple.ASPCarryLog" "com.apple.nandCarryLogs"`, `"kCFPreferencesAnyApplication" "com.apple.da" "com.apple.SubmitDiagInfo"` |
| `(preference-domain-prefix string)` | `managed-preference-read` (1), `user-preference*` (1) | - | `"com.apple.UARPHIDUpdater"`, `"com.apple.appleh13camerad"` |
| `(preference-domain-regex string)` | `user-preference*` (1) | - | `#"^com\.apple\.coreservices\.useractivityd"` |
| `(prefix string...)` | `file-ioctl` (2), `file-map-executable` (2), `file-read*` (23), `file-write*` (15) | - | `"/cores/"`, `"/Library/Preferences/com.apple.security."` |
| `(privilege-id symbol)` | `system-privilege` (5) | `PRIV_GLOBAL_PROC_INFO` | `PRIV_GLOBAL_PROC_INFO` |
| `(process-attribute symbol)` | `system-automount` (1), `user-preference-read` (1) | `is-apple-signed-executable`, `is-platform-binary`, `is-restricted` | `is-apple-signed-executable`, `is-platform-binary` |
| `(process-is-plugin)` | `with-filter` | - | - |
| `(process-path string)` | `with-filter` | - | `"/usr/sbin/screencapture"`, `"/System/Library/PrivateFrameworks/CoreAnalytics.framework/Support/analyticsagent"` |
| `(process-path-regex string)` | `with-filter` | - | `"/analyticsagent$"` |
| `(regex string...)` | `file*` (7), `user-preference-read` (1), `user-preference-write` (1) | - | `(string-append "^" (regex-quote (param "_HOME")))`, `"/private/var/root/Library/Logs/Bluetooth/*"` |
| `(remote symbol string...)` | `network*` (5) | `ip`, `tcp` | `ip "localhost:631"`, `ip` |
| `(require-entitlement string)` | `with-filter` | - | `"com.apple.security.smartcard"`, `"com.apple.developer.identity-document-services.web-presentment-controller"` |
| `(right-name string...)` | `authorization-right-obtain` (65) | - | `"system.burn"`, `"system.volume.optical.mount"` |
| `(right-name-regex string)` | `authorization-right-obtain` (2) | - | `"^system\\.volume\\.(external\|optical\|removable)\\.unmount$"`, `#"^system\.volume\.(external\|optical\|removable)\.unmount$"` |
| `(semaphore-owner symbol)` | `ipc-posix-sem` (1) | `self` | `self` |
| `(socket-domain symbol)` | `network-inbound` (2), `network-outbound` (1), `system-socket` (32) | `AF_SYSTEM` | `AF_SYSTEM`, `39` |
| `(socket-option-name symbol\|integer symbol symbol...)` | `socket-option-get` (2), `socket-option-set` (2) | `SO_DEBUG`, `SO_ERROR`, `SO_KEEPALIVE`, `SO_NECP_ATTRIBUTES`, `SO_NECP_CLIENTUUID`, `SO_NOADDRERR`, `SO_NOSIGPIPE`, `SO_NREAD`, `SO_RCVBUF`, `SO_RCVTIMEO`, `SO_REUSEPORT`, `SO_SNDTIMEO`, `SO_TRAFFIC_CLASS` | `262 SO_ERROR SO_NREAD SO_REUSEPORT`, `SO_DEBUG SO_KEEPALIVE SO_NECP_ATTRIBUTES SO_NECP_CLIENTUUID SO_NOADDRERR SO_NOSIGPIPE SO_RCVBUF SO_RCVTIMEO SO_SNDTIMEO` |
| `(socket-protocol integer)` | `network-outbound` (1), `system-socket` (9) | - | `2` |
| `(subpath string...)` | `file*` (14), `mach-lookup` (3), `mach-priv-host-port` (1), `network-inbound` (1), `network-outbound` (9), `process-exec*` (3) | - | `"/private/var/log/iolog_unsent"`, `"/private/var/db/NANDTelemetryServices"` |
| `(syscall-group-bsdthread)` | `syscall-unix` (14) | - | - |
| `(syscall-group-chflags)` | `syscall-unix` (1) | - | - |
| `(syscall-group-close)` | `syscall-unix` (9) | - | - |
| `(syscall-group-fcntl)` | `syscall-unix` (12) | - | - |
| `(syscall-group-getfsstat)` | `syscall-unix` (10) | - | - |
| `(syscall-group-kevent)` | `syscall-unix` (13) | - | - |
| `(syscall-group-kqueue)` | `syscall-unix` (5) | - | - |
| `(syscall-group-mach-eventlink)` | `syscall-unix` (1) | - | - |
| `(syscall-group-mkdir)` | `syscall-unix` (11) | - | - |
| `(syscall-group-necp-client)` | `syscall-unix` (4) | - | - |
| `(syscall-group-network-channel)` | `syscall-unix` (3) | - | - |
| `(syscall-group-open)` | `syscall-unix` (4) | - | - |
| `(syscall-group-open-dprotected)` | `syscall-unix` (6) | - | - |
| `(syscall-group-pthread)` | `syscall-unix` (12) | - | - |
| `(syscall-group-pthread-cv)` | `syscall-unix` (4) | - | - |
| `(syscall-group-pthread-locks)` | `syscall-unix` (6) | - | - |
| `(syscall-group-read)` | `syscall-unix` (13) | - | - |
| `(syscall-group-recv)` | `syscall-unix` (3) | - | - |
| `(syscall-group-rlimit)` | `syscall-unix` (12) | - | - |
| `(syscall-group-select)` | `syscall-unix` (5) | - | - |
| `(syscall-group-send)` | `syscall-unix` (12) | - | - |
| `(syscall-group-signal)` | `syscall-unix` (12) | - | - |
| `(syscall-group-sockopt)` | `syscall-unix` (4) | - | - |
| `(syscall-group-stat)` | `syscall-unix` (12) | - | - |
| `(syscall-group-statfs)` | `syscall-unix` (11) | - | - |
| `(syscall-group-ulock)` | `syscall-unix` (16) | - | - |
| `(syscall-group-write)` | `syscall-unix` (4) | - | - |
| `(syscall-number symbol...)` | `syscall-mach` (1), `syscall-unix` (40) | `SYS___disable_threadsignal`, `SYS___mac_syscall`, `SYS___semwait_signal_nocancel`, `SYS_abort_with_payload`, `SYS_access`, `SYS_clonefileat`, `SYS_connect`, `SYS_csops_audittoken`, `SYS_csrctl`, `SYS_dup`, `SYS_exit`, `SYS_faccessat`, `SYS_ffsctl`, `SYS_fgetattrlist`, `SYS_fgetxattr`, `SYS_flistxattr`, `SYS_fsetattrlist`, `SYS_fsgetpath`, `SYS_ftruncate`, `SYS_getattrlist`, `SYS_getattrlistbulk`, `SYS_getdirentries64`, `SYS_getentropy`, `SYS_geteuid`, `SYS_getgid`, `SYS_gethostuuid`, `SYS_getrusage`, `SYS_gettimeofday`, `SYS_getuid`, `SYS_getxattr`, `SYS_ioctl`, `SYS_issetugid`, `SYS_kdebug_trace`, `SYS_kdebug_trace64`, `SYS_kdebug_trace_string`, `SYS_kdebug_typefilter`, `SYS_listxattr`, `SYS_lseek`, `SYS_madvise`, `SYS_mmap`, `SYS_mprotect`, `SYS_mremap_encrypted`, `SYS_munmap`, `SYS_open`, `SYS_open_dprotected_np`, `SYS_open_nocancel`, `SYS_openat`, `SYS_pathconf`, `SYS_proc_info`, `SYS_readlink`, `SYS_rename`, `SYS_rmdir`, `SYS_shared_region_map_and_slide_2_np`, `SYS_shm_open`, `SYS_socket`, `SYS_sysctl`, `SYS_sysctlbyname`, `SYS_thread_selfid`, `SYS_umask`, `SYS_workq_kernreturn`, `SYS_workq_open` | `SYS___disable_threadsignal SYS___mac_syscall SYS___semwait_signal_nocancel SYS_abort_with_payload SYS_access SYS_conn...`, `SYS_csrctl` |
| `(sysctl-name string...)` | `sysctl*` (1) | - | `"kern.memorystatus_freeze_pageouts"`, `"kern.osrevision"` |
| `(sysctl-name-prefix string)` | `sysctl*` (1) | - | `"vm.compressor_"`, `"hw.optional."` |
| `(system-attribute symbol)` | `syscall-mach` (5) | `apple-internal` | `apple-internal` |
| `(target symbol)` | `mach-task-name` (6), `mach-task-read` (1), `process-codesigning-status*` (1), `process-info*` (336), `signal` (15), `system-sched` (1) | `self` | `self` |
| `(target-signing-identifier string)` | `process-info-codesignature` (1) | - | `"com.apple.classroom"` |
| `(uid integer)` | `with-filter` | - | `0` |
| `(vnode-type symbol...)` | `file*` (1), `network-outbound` (1) | `DIRECTORY`, `SYMLINK`, `TTY` | `TTY`, `DIRECTORY` |
| `(xattr string...)` | `file-read-xattr` (7), `file-write-xattr` (8) | - | `"com.apple.file-provider-domain-id"`, `"com.apple.file-provider-domain-id#PN"` |
| `(xattr-prefix string)` | `file-read-xattr` (7), `file-write-xattr` (7) | - | `"com.apple.security.private."`, `"com.apple.security."` |
| `(xattr-regex string)` | `file-read-xattr` (1), `file-write-xattr` (1) | - | `#"^com\.apple\.security\.private\."` |
| `(xpc-service-name string...)` | `mach-lookup` (20) | - | `"com.apple.audio.AudioConverterService"`, `"com.apple.geod"` |
| `(xpc-service-name-prefix string)` | `mach-lookup` (10) | - | `""`, `"com.apple.WebKit"` |
| `(xpc-service-name-regex string)` | `mach-lookup` (3) | - | `#".*"` |

## Modifiers

Operations listed here are the highest observed operation levels after glob inheritance pruning.

| Modifier | Highest observed operations | All Symbols | Example Arguments |
| --- | --- | --- | --- |
| `(with errno symbol)` | `file-read*` (2), `file-test-existence` (2) | `EACCES` | `EACCES` |
| `(with message string)` | `default` (3), `file-write*` (8), `iokit-get-properties` (1), `iokit-open-service` (4), `mach-lookup` (4), `syscall-mach` (7), `syscall-mig` (4), `syscall-unix` (10), `sysctl-read` (1), `system-mac-syscall` (3), `user-preference-write` (7) | - | `"73669976"`, `"syscall-mach-denied"` |
| `(with no-callout)` | `default` (1) | - | - |
| `(with no-log)` | `file*` (1) | - | - |
| `(with no-report)` | `device-camera` (1), `device-microphone` (1), `dynamic-code-generation` (1), `file-issue-extension` (1), `file-read*` (1), `file-write*` (1), `iokit-get-properties` (1), `ipc-posix-shm` (1), `mach-lookup` (8), `process-fork` (1), `process-info-codesignature` (5), `system-privilege` (5), `user-preference*` (4) | - | - |
| `(with no-sandbox)` | `process-exec*` (7) | - | - |
| `(with partial-symbolication)` | `default` (1) | - | - |
| `(with report)` | `darwin-notification-post` (2), `default` (25), `dynamic-code-generation` (24), `file-clone` (2), `file-issue-extension` (2), `file-link` (2), `file-map-executable` (25), `file-read*` (12), `file-write*` (5), `iokit-get-properties` (16), `iokit-open-user-client` (2), `ipc-posix*` (2), `mach-lookup` (5), `mach-register` (1), `nvram*` (25), `process-exec` (2), `process-info*` (25), `sysctl-read` (1), `system-fcntl` (2), `user-preference-read` (2) | - | - |
| `(with send-signal symbol)` | `mach-lookup` (4), `syscall-mach` (1), `syscall-unix` (1) | `SIGKILL` | `SIGKILL` |
| `(with telemetry)` | `default` (5), `dynamic-code-generation` (1), `file-map-executable` (1), `file-read*` (1), `file-write*` (10), `iokit-get-properties` (2), `iokit-open` (1), `iokit-open-service` (4), `mach-lookup` (6), `mach-register` (1), `nvram*` (1), `process-info*` (1), `syscall-mach` (4), `syscall-mig` (4), `syscall-unix` (11), `sysctl-read` (5), `system-mac-syscall` (4), `user-preference-write` (7) | - | - |
| `(with telemetry-backtrace)` | `process-exec*` (1) | - | - |

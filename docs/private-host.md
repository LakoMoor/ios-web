# Private server on port 8080

The site can be served with either `scripts/host.py` (Python standard library only) or `scripts/host.mjs` (Node standard library only). Both require administrator authentication and serve the static `dist` directory. `/admin` reports the actual runtime state.

Set `PORT=8080`, `STATIC_ROOT` to the static directory, and `ADMIN_CREDENTIAL_FILE` to a JSON file containing `username`, a hex-encoded random `salt`, and a 64-byte scrypt `key`. Parameters are N=16384, r=8, p=1. Keep this file outside the static directory and restrict its permissions to 0600. No plaintext password is stored.

For trusted HTTPS, set `TLS_CERT_FILE` and `TLS_KEY_FILE` to the server's existing certificate and key. HTTP on a public hostname cannot provide the secure context needed for SharedArrayBuffer and OPFS. Isolation headers alone do not solve that restriction.

`scripts/deploy-remote.py` installs into its new task directory and refuses to replace an existing listener on port 8080. It starts the host as a detached process, writes its PID to `host.pid`, and writes observed state to `deployment.json`. This launch does not configure automatic startup after a server reboot.

Deploying the interface does not establish that the unfinished Inferno WASM runtime builds or that iOS boots. The administrator endpoint reports a missing runtime as `not-built`.

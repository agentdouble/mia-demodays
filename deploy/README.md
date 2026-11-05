# Delivery on ovh3

The development checkout stays on the main Mac. Runtime directories are
`/srv/mia-demodays/staging` and `/srv/mia-demodays/production` on ovh3.
Host deployment files are root-owned in `/usr/local/lib/mia-demodays`.

## Branches and releases

The original `main` is retained as history. Daily changes and checks run on `dev`.
Fast-forward an explicitly selected candidate to `stg`, then dispatch the Release
workflow there with `target=staging`. This builds/publishes an amd64 image once
and deploys its digest into the private staging environment.

Use SSH forwarding to access staging:

```sh
ssh -N -L 127.0.0.1:18081:127.0.0.1:18081 ovh3
```

Open `http://mia-staging.localhost:18081/recommander`. Staging HTTP stays on loopback
and is transported over SSH; unlike production it deliberately has no Secure cookie.
No staging endpoint is exposed publicly. Do not import production data into staging.
After testing the candidate, an administrator records the validation:

```sh
ssh ovh3 'sudo /usr/local/sbin/mia-release validate-staging'
```

Fast-forward `prod` to **that exact commit**, then dispatch Release on `prod` with
`target=production` and the staging `sha256:...` digest. Production refuses another
digest or commit, or a staging release not marked validated. It pulls the same image;
there is no production rebuild. This is a manual operator gate, not an independent
second-person approval rule in GitHub environments.

The CI deployment key is forced to stage/promote a MIA image, with forwarding disabled.
It cannot open a shell or record staging validation. The registry token is temporary
and its Docker configuration is removed after pulling. There is no personal PAT or
personal SSH key stored in GitHub. Actions and base images are pinned.

## Initial host installation

An administrator copies this deployment kit to the server, generates a dedicated
SSH deployment key, then runs `sudo python3 deploy/install-host.py <public-key-file>`.
Only the new deployment private key and the already verified SSH host public key
are configured as the repository secrets `DEPLOY_KEY` / `DEPLOY_KNOWN_HOSTS`.
Application secrets are generated independently on the host and never printed.

Install the kit before the first release; update root-owned deployment files explicitly
when their contracts change. New images never execute repository deployment scripts
as root. Compose has separate projects, private networks/data and loopback ports 18081/18080.

## SQLite and operation

SQLite persists outside containers at `production/data/mia.sqlite3` (WAL, FULL sync).
The application runs as uid 10001, with a read-only root filesystem, dropped
capabilities and resource/log limits. Caddy is the only public HTTP/HTTPS listener,
with automatic certificates. There is no web administration/reset endpoint.

`mia-backup.timer` takes a consistent snapshot daily around 03:15 UTC, verifies
an isolated restoration and preserves 14 days of root-only snapshots in
`/var/backups/mia-demodays`. An additional snapshot precedes each production release.
Expired games are purged after 30 days. Backups can contain older game records for
their additional 14-day retention. The application cannot access snapshots.

```sh
ssh ovh3 'sudo systemctl start mia-backup.service'
ssh ovh3 'sudo systemctl status mia-backup.timer --no-pager'
```

The first backup can be copied privately to the Mac; automatic off-server replication
is not configured. Keep a periodic off-server copy for recovery from a lost VPS.

For rollback, retain the previous `release.env` image digest and its compatible data.
The controller restores the previous image reference on deployment failure; it never
automatically replaces the live database with an old backup. Schema changes need an
explicit compatibility decision. Restore snapshots into a separate database first,
verify integrity/content, then stop writers before an explicitly chosen replacement.

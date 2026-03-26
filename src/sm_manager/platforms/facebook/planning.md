# Facebook Planning

Status: roadmap only

Do not implement this platform until explicitly approved by the user.

## Objective

Add a Facebook Pages adapter after Instagram is stable, reusing the shared scheduler, secrets layer, UI, and audit model.

## Expected Scope

- Facebook Pages only
- official Pages API publishing flows
- page-level enable or disable controls
- shared scheduling and job history

## Constraints

- no personal-profile automation
- no platform implementation before Instagram approval
- no credential-driven browser automation as the default path

## Planned Work

1. account and page connection flow
2. page posting adapter
3. shared queue and scheduling integration
4. page metrics mapping
5. per-page controls in the master UI

## Notes

- Facebook should inherit the same rights-gated content intake model as Instagram
- publish flows should remain isolated in this directory

## References

- Meta Pages API posts: https://developers.facebook.com/docs/pages-api/posts/

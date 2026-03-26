# TikTok Planning

Status: roadmap only

Do not implement this platform until explicitly approved by the user.

## Objective

Add a TikTok adapter after Instagram is stable, using official TikTok developer APIs and the shared local control plane.

## Expected Scope

- account connection
- content posting
- shared scheduler integration
- shared audit logging
- per-account controls in the master UI

## Constraints

- use official TikTok posting APIs
- do not assume unrestricted public scraping support
- verify app-review and audit requirements before implementation

## Important Platform Note

TikTok's Content Posting API supports direct posting, but unverified clients can face visibility restrictions until audit or verification requirements are satisfied. This must be validated before build work starts.

## Planned Work

1. verify onboarding and review requirements
2. implement auth and token lifecycle
3. implement media publishing adapter
4. integrate scheduler and UI controls
5. map publish results and metrics

## References

- TikTok Content Posting API: https://developers.tiktok.com/products/content-posting-api
- TikTok developer docs: https://developers.tiktok.com/doc
